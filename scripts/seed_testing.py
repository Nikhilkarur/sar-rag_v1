"""
Seed the MOCK client (client_0) into the unified per-client storage:

  backend/storage/clients/client_0/
  ├── policy.pdf            # synthetic Aegis policy (built by scripts/build_policy.py)
  ├── alerts/01..05.json    # labeled test transactions ({"raw_payload": {...}})
  └── eval.json             # answer key for IR eval (schema + rule->section)

This is the SAME folder shape that real clients get (theirs filled live by uploads +
the ingest API). The eval (ir_metrics / ragas_eval) reads these folders, so whatever
we do for the mock we do for real clients.

Run:  python scripts/seed_testing.py
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT0 = os.path.join(ROOT, "backend", "storage", "clients", "client_0")

# answer key for IR eval (sections as they appear in client_0's policy)
EVAL_CONFIG = {
    "display_name": "DUMMY/TEST CLIENT (client_0 — synthetic Aegis Bank)",
    "schema_preset": "STANDARD_FINTECH",
    "always_relevant": ["5.1"],
    "rule_to_section": {
        "Structuring / Smurfing": "4.1",
        "Rapid Movement of Funds": "4.2",
        "Large Round Number": "4.3",
        "Dormant Account Activation": "4.4",
        "High Risk Transaction Type": "4.5",
        "High Velocity": "4.6",
        "High Risk Counterparty": "4.7",
        "Risk Score Threshold Exceeded": "4.8",
    },
}

# labeled test transactions (cover all 8 typologies)
ALERTS = {
    "01_structuring_intlwire.json": {
        "customer": {"full_name": "Rohan Mehta", "id": "CUST-884213"},
        "account": {"number": "5012-7788-2231"},
        "txn": {"ref_id": "TXN-EVAL-01", "amount": 945000, "currency": "INR",
                "type": "INTERNATIONAL_WIRE", "direction": "OUTBOUND",
                "timestamp": "2026-04-16T11:42:07+05:30"},
        "counterparty": {"account": "AE070331234567890123456",
                         "name": "Gulf Horizon Trading FZE", "bank": "Emirates NBD"},
        "metadata": {"ip": "203.0.113.57", "device_id": "dev-9f3c1a77"},
        "risk": {"score": 88, "reason": "Large outbound transfer just below the reporting threshold to a newly added overseas beneficiary."},
    },
    "02_dormant_velocity.json": {
        "customer": {"full_name": "Sunita Rao", "id": "CUST-551200"},
        "account": {"number": "6101-2233-9090"},
        "txn": {"ref_id": "TXN-EVAL-02", "amount": 250000, "currency": "INR",
                "type": "TRANSFER", "direction": "OUTBOUND", "timestamp": "2026-05-02T09:15:00+05:30"},
        "counterparty": {"account": "1122-3344-5566", "name": "Anil Kumar", "bank": "HDFC Bank"},
        "metadata": {"ip": "198.51.100.22", "device_id": "dev-2210bbef"},
        "risk": {"score": 92, "reason": "Dormant account suddenly reactivated with unusually high velocity of outbound transfers."},
    },
    "03_roundnum_crypto.json": {
        "customer": {"full_name": "Vikram Shah", "id": "CUST-330815"},
        "account": {"number": "7788-1100-4455"},
        "txn": {"ref_id": "TXN-EVAL-03", "amount": 500000, "currency": "INR",
                "type": "CRYPTO_PURCHASE", "direction": "OUTBOUND", "timestamp": "2026-05-10T18:05:30+05:30"},
        "counterparty": {"account": "EXCH-99812", "name": "CoinExchange Pte", "bank": "CoinExchange Pte"},
        "metadata": {"ip": "192.0.2.71", "device_id": "dev-77aa12cd"},
        "risk": {"score": 70, "reason": "Customer purchased virtual assets in an exact round-figure amount."},
    },
    "04_refund_counterparty.json": {
        "customer": {"full_name": "Meera Iyer", "id": "CUST-770450"},
        "account": {"number": "9001-5566-7788"},
        "txn": {"ref_id": "TXN-EVAL-04", "amount": 320000, "currency": "INR",
                "type": "REFUND", "direction": "INBOUND", "timestamp": "2026-05-14T13:20:10+05:30"},
        "counterparty": {"account": "SHL-0098", "name": "Opaque Holdings", "bank": "Shell Bank Ltd"},
        "metadata": {"ip": "203.0.113.200", "device_id": "dev-55cd91aa"},
        "risk": {"score": 60, "reason": "Large refund processed shortly after credit; counterparty institution could not be verified."},
    },
    "05_hawala_structuring.json": {
        "customer": {"full_name": "Imran Sheikh", "id": "CUST-119077"},
        "account": {"number": "4455-6677-2200"},
        "txn": {"ref_id": "TXN-EVAL-05", "amount": 870000, "currency": "INR",
                "type": "HAWALA", "direction": "OUTBOUND", "timestamp": "2026-05-20T20:45:00+05:30"},
        "counterparty": {"account": "NA", "name": "Unknown Intermediary", "bank": "Local Agent"},
        "metadata": {"ip": "198.51.100.88", "device_id": "dev-9001ffaa"},
        "risk": {"score": 72, "reason": "Funds moved via an informal value-transfer arrangement in an amount just below the threshold."},
    },
}


def _w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    print(f"  wrote {os.path.relpath(path, ROOT)}")


def main():
    print("Seeding mock client_0 into backend/storage/clients/client_0/ :")
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_policy.py")], check=True)
    _w(os.path.join(CLIENT0, "eval.json"), EVAL_CONFIG)
    for name, payload in ALERTS.items():
        _w(os.path.join(CLIENT0, "alerts", name), {"raw_payload": payload})
    print("Done — client_0 ready (policy + alerts + eval.json).")


if __name__ == "__main__":
    main()
