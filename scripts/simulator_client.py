"""
simulator_client.py — synthetic fintech client for Aegis AML.

Simulates a real tenant's TMS pushing transaction alerts to the ingest API,
exactly as production traffic would arrive: HTTP POST, X-API-Key +
X-Tenant-ID headers, STANDARD_FINTECH-shaped JSON payloads, one
Idempotency-Key per transaction.

Setup (PowerShell):
    $env:AEGIS_API_KEY   = "sk-ae-..."      # printed once by backend/seed.py
    $env:AEGIS_TENANT_ID = "TEN-0001"       # default
    $env:AEGIS_API_URL   = "http://localhost:8000"   # default

Usage:
    python scripts/simulator_client.py --scenario normal      --count 10
    python scripts/simulator_client.py --scenario structuring --count 5
    python scripts/simulator_client.py --scenario velocity    --count 3
    python scripts/simulator_client.py --scenario high-risk   --count 3
    python scripts/simulator_client.py --scenario mixed       --count 20 --delay 0.5

Scenario → expected pipeline outcome (per compliance_analyzer.py):
    normal        amounts ₹5k–₹2.8L, risk 5–30      → COMPLETED_CLEAN
    structuring   ₹9.0–9.99L cash, risk ~58          → STRUCTURING(HIGH) → SAR
    velocity      bursts, risk 90                    → VELOCITY+THRESHOLD → SAR
    high-risk     INTERNATIONAL_WIRE etc., risk ~58  → HIGH_RISK_TYPE → SAR

NOTE: SAR drafting calls Groq. Without a real GROQ_API_KEY in the backend
environment, high-risk alerts will land as PROCESSING_FAILED (the alert and
compliance analysis still persist; only the LLM draft is missing).
"""
import argparse
import json
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone

try:
    import httpx
except ImportError:
    print("Missing dependency: pip install httpx")
    sys.exit(1)

try:
    from faker import Faker
except ImportError:
    print("Missing dependency: pip install faker")
    sys.exit(1)

fake = Faker("en_IN")

API_URL = os.environ.get("AEGIS_API_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.environ.get("AEGIS_API_KEY", "")
TENANT_ID = os.environ.get("AEGIS_TENANT_ID", "TEN-0001")

INGEST_ENDPOINT = f"{API_URL}/api/v1/ingest/"  # trailing slash matters (no 307)

BANKS = ["HDFC Bank", "ICICI Bank", "State Bank of India", "Axis Bank", "Kotak Mahindra Bank", "Yes Bank"]
SHADY_BANKS = ["Shell Bank Ltd", "Offshore Co. Holdings", "Unknown Bank"]


def _base_txn(amount: float, txn_type: str, risk_score: int, reason: str,
              direction: str = "DEBIT", counterparty_bank: str | None = None) -> dict:
    """One STANDARD_FINTECH-shaped raw payload (matches the seeded field_map)."""
    return {
        "customer": {
            "full_name": fake.name(),
            "id": f"CUST-{fake.numerify('######')}",
        },
        "account": {
            "number": fake.numerify("############"),  # 12-digit India-style account
        },
        "txn": {
            "ref_id": f"TXN-{fake.numerify('########')}",
            "amount": amount,
            "currency": "INR",
            "type": txn_type,
            "direction": direction,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "counterparty": {
            "account": fake.numerify("############"),
            "name": fake.name(),
            "bank": counterparty_bank or random.choice(BANKS),
        },
        "metadata": {
            "ip": fake.ipv4_public(),
            "device_id": f"DEV-{fake.numerify('######')}",
        },
        "risk": {
            "score": risk_score,
            "reason": reason,
        },
    }


def make_normal() -> dict:
    # Avoid exact lakh multiples so ROUND_NUMBER never fires on "normal"
    amount = round(random.uniform(5_000, 280_000), 2)
    if amount % 100_000 == 0:
        amount += 7
    return _base_txn(
        amount=amount,
        txn_type=random.choice(["UPI", "TRANSFER", "CARD_PAYMENT", "BILL_PAY"]),
        risk_score=random.randint(5, 30),
        reason="Routine transaction monitoring",
        direction=random.choice(["DEBIT", "CREDIT"]),
    )


def make_structuring() -> dict:
    # ₹9.0–9.99L just under the ₹10L CTR threshold → STRUCTURING fires HIGH
    return _base_txn(
        amount=float(random.randint(900_001, 999_499)),
        txn_type="CASH_DEPOSIT",
        risk_score=random.randint(55, 60),
        reason="Cash deposit just below reporting threshold",
        direction="CREDIT",
        counterparty_bank=random.choice(BANKS + SHADY_BANKS),
    )


def make_velocity() -> dict:
    # risk 90 → VELOCITY (HIGH) + RISK_SCORE_THRESHOLD (HIGH)
    return _base_txn(
        amount=round(random.uniform(80_000, 240_000), 2),
        txn_type="TRANSFER",
        risk_score=90,
        reason=f"High velocity — {random.randint(6, 12)} transactions in {random.randint(40, 75)} minutes",
    )


def make_high_risk() -> dict:
    return _base_txn(
        amount=round(random.uniform(200_000, 850_000), 2),
        txn_type=random.choice(["INTERNATIONAL_WIRE", "CRYPTO_PURCHASE", "FOREX_TRANSFER"]),
        risk_score=random.randint(55, 60),
        reason="High-risk transaction channel",
        counterparty_bank=random.choice(SHADY_BANKS),
    )


GENERATORS = {
    "normal": make_normal,
    "structuring": make_structuring,
    "velocity": make_velocity,
    "high-risk": make_high_risk,
}


def make_payload(scenario: str) -> dict:
    if scenario == "mixed":
        # Realistic traffic shape: mostly clean, a tail of suspicious
        pick = random.choices(
            ["normal", "structuring", "velocity", "high-risk"],
            weights=[70, 12, 9, 9],
        )[0]
        return GENERATORS[pick]()
    return GENERATORS[scenario]()


def send_one(client: httpx.Client, payload: dict) -> tuple[bool, str]:
    headers = {
        "X-API-Key": API_KEY,
        "X-Tenant-ID": TENANT_ID,
        "Content-Type": "application/json",
        "Idempotency-Key": str(uuid.uuid4()),
    }
    body = json.dumps(payload)
    resp = client.post(INGEST_ENDPOINT, content=body, headers=headers)

    if resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", "5"))
        print(f"    rate-limited; retrying in {retry_after}s ...")
        time.sleep(retry_after)
        headers["Idempotency-Key"] = str(uuid.uuid4())
        resp = client.post(INGEST_ENDPOINT, content=body, headers=headers)

    txn_id = payload["txn"]["ref_id"]
    amount = payload["txn"]["amount"]
    if resp.status_code == 200:
        data = resp.json()
        sar = "SAR triggered" if data.get("risk_score", 0) >= 75 else "clean"
        return True, f"{txn_id}  Rs {amount:>11,.0f}  risk={data.get('risk_score'):>3}  [{sar}]  alert={data.get('alert_id')}"
    if resp.status_code == 401:
        return False, "401 Unauthorized — check $env:AEGIS_API_KEY and $env:AEGIS_TENANT_ID (run backend/seed.py to mint them)"
    if resp.status_code == 403:
        return False, f"403 — tenant is not ACTIVE: {resp.text[:200]}"
    return False, f"{resp.status_code} — {resp.text[:200]}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthetic fintech client for Aegis AML ingest")
    parser.add_argument("--scenario", choices=[*GENERATORS.keys(), "mixed"], default="mixed")
    parser.add_argument("--count", type=int, default=5, help="number of transactions to send")
    parser.add_argument("--delay", type=float, default=0.2, help="seconds between sends")
    parser.add_argument("--url", default=None, help="override AEGIS_API_URL")
    args = parser.parse_args()

    global INGEST_ENDPOINT
    if args.url:
        INGEST_ENDPOINT = f"{args.url.rstrip('/')}/api/v1/ingest/"

    if not API_KEY:
        print("ERROR: AEGIS_API_KEY is not set.")
        print('  PowerShell:  $env:AEGIS_API_KEY = "sk-ae-..."   (printed by backend/seed.py)')
        return 2

    print(f"Target   : {INGEST_ENDPOINT}")
    print(f"Tenant   : {TENANT_ID}")
    print(f"Scenario : {args.scenario}  x{args.count}\n")

    ok = failed = 0
    try:
        with httpx.Client(timeout=30.0) as client:
            for i in range(args.count):
                payload = make_payload(args.scenario)
                try:
                    success, line = send_one(client, payload)
                except httpx.ConnectError:
                    print(f"ERROR: cannot reach {INGEST_ENDPOINT} — is the backend running?")
                    print("  cd backend ; python -m uvicorn app.main:app --port 8000")
                    return 3
                status = "OK " if success else "ERR"
                print(f"[{i + 1:>3}/{args.count}] {status} {line}")
                if success:
                    ok += 1
                else:
                    failed += 1
                    if "401" in line:  # credentials wrong — no point continuing
                        return 2
                if args.delay and i < args.count - 1:
                    time.sleep(args.delay)
    except KeyboardInterrupt:
        print("\nInterrupted.")

    print(f"\nDone: {ok} accepted, {failed} failed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
