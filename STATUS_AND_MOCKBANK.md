# Aegis — Status & Mock-Bank Guide

Companion to **`PROJECT_REFERENCE.md`** (which explains everything + every command).
This file = **what's done, what's left, and how the mock bank integrates.**
Last updated: 2026-06-19.

---

## Table of contents

- [1. What Aegis is (1 minute)](#1-what-aegis-is-1-minute)
- [2. What's DONE (built & verified)](#2-whats-done-built--verified)
- [3. What's LEFT](#3-whats-left)
- [4. Key facts & how to run the live loop](#4-key-facts--how-to-run-the-live-loop)
- [5. Mock-Bank integration guide (the teammate's brief)](#5-mock-bank-integration-guide-the-teammates-brief)

---

## 1. What Aegis is (1 minute)

Banks/fintechs in India must file a **Suspicious Transaction Report (SAR/STR)** with the
regulator (FIU-India) when they spot a suspicious transaction. **Aegis automates writing
that report:** a bank sends a flagged transaction → Aegis masks PII, retrieves the bank's
own AML policy, an LLM drafts a SAR that **cites the policy** → a compliance officer
approves → Aegis delivers a regulator-ready **goAML JSON + PDF** back to the bank.

Full loop: **transaction → policy-cited SAR → officer approves → goAML + PDF to the bank.**

---

## 2. What's DONE (built & verified)

### Live backend (the product)
| Phase | What it does | Status |
|-------|--------------|--------|
| **P1** | Live SARs cite the policy (RAG wired into `ingest.py`) | Live-verified |
| **P2** | Approve → goAML + PDF + HMAC-signed webhook to the bank | Live-verified |
| **P3** | Document upload endpoint (bank self-serve policy upload) | Live-verified |
| **P4.1/4.2** | TEN-0001 seeded; CORS allows the mock-bank origins | Done |
| **P6.1** | SAR PDF table-clipping fix | Done |

- **P1 proof:** POSTed a structuring txn → SAR cited Sections 4.1, 4.5, 5.1; no segfault.
- **P2 proof:** approve → `200`; PDF downloadable at `/files/sar/<id>.pdf`; webhook payload
  carried `goaml_str` (report_code STR) + `pdf_url`.

### RAG pipeline & eval
- Vanilla RAG (index → retrieve → generate) built and proven; reranking/hybrid NOT needed.
- **IR metrics:** Recall@8 = 1.0, MRR = 1.0, nDCG@8 ≈ 0.98 (deterministic, `client_0`).
- **RAGAS:** native impl (Groq judge + bge), faithfulness ≈ 0.81, answer-relevancy ≈ 0.70.

### Unified per-client storage refactor (2026-06-19)
- Replaced the confusing `testing/` vs `production/` split with ONE root:
  `backend/storage/clients/<client_id>/` (`policy.pdf` + `alerts/` + `sar/` + `eval.json`)
  — the SAME folders the live system writes and the eval reads.
- Policy PDF → upload → folder + Chroma (NOT in DB). Alerts → Postgres `alerts` table
  (source of truth; not mirrored to disk). SARs → the client's `sar/` folder.
- `client_0` is the offline test bench; real clients = `TEN-xxxx`.
- Added `scripts/export_alerts.py` (DB alerts → folder JSON for real-client RAGAS).
- Deleted dead folders; moved `build_policy.py` → `scripts/`.

### Prod-readiness pass (2026-06-19)
- **Schema fallacy fixed** — eval hardcoded `STANDARD_FINTECH`; now uses the DB-computed
  `normalized_payload`/`masked_payload` so it scores any schema correctly. (See
  `PROJECT_REFERENCE.md` §21.)
- `reset.py --barebone` wipes only `client_0` (real clients kept); `--all-clients` to nuke.
- `ragas_eval.py` fails fast without a Groq key.
- `documents.py` upload rejects a tenant-less super-admin (`400`); `files.py` returns
  `404` (not `500`) for a non-UUID `sar_id`.

---

## 3. What's LEFT

### Blocked on the mock bank (do when it lands)
- **B1** — point the webhook at the bank: set `TEN-0001`'s `WebhookConfig.callback_url` to
  the bank's receiver URL and `use_internal_sink = false`. (HMAC POST logic already built.)
- **B2** — run the full live loop with the bank: bank POSTs a flagged txn → SAR → officer
  approves → confirm the bank's inbox receives the goAML + PDF link.
- **B3** — hand the teammate: base URL (`http://localhost:8000`), the `TEN-0001` API key,
  and a sample webhook payload.

### Optional / hardening (not blockers)
- **LLM outage resilience** — add a retry queue (Celery/Redis) for the background SAR task;
  today a Groq outage degrades to no-context generation but doesn't retry.
- **Async webhook** — `_deliver_webhook` POSTs inline with an 8s timeout; background it so
  a slow bank can't delay approval.
- **Wrap scripts** in a Makefile/CLI (`make seed`, `make eval`) and put the offline smoke
  tests (`ir_metrics`, `rag_smoke_test`) in CI.
- **P4.3** — confirm the officer dashboard's Approve button calls `/queue/{id}/approve`.
- Optional `TenantDocument` DB table for richer policy/upload audit (P3.1, deferred).
- Optional per-client `eval.json` if you ever want IR (not just RAGAS) for a real client.

---

## 4. Key facts & how to run the live loop

- **Segfault gotcha:** load the torch/embedding model BEFORE any DB connection.
  `embeddings.py` sets OMP/tokenizer guards at import; `main.py` warms the model at
  startup; DB-using scripts load the model first. Keep this pattern.
- **TEN-0001** uuid = `a334155d-0733-43e3-bb93-dd8b98ad4414`; Chroma keyed by uuid
  (`tenant_{uuid}_docs`). Compliance login: `admin@testfintech.in` / `TestFintech2026!`.
  Recover the API key: `decrypt_json(tenant.api_key_encrypted)`.
- **GROQ_API_KEY** lives in gitignored `backend/.env` (now working).

```bash
# 1. start the backend (from backend/)
python -m uvicorn app.main:app --port 8000
# 2. seed the tenant's policy once (or use the upload endpoint)
python scripts/seed_policy.py
# 3. ingest a txn (the bank's job; simulate with X-API-Key + X-Tenant-ID)
#    POST http://localhost:8000/api/v1/ingest/  -> alert_id; policy-cited SAR generated
# 4. officer approves -> POST /api/v1/alerts/queue/{id}/approve
#    -> goAML + PDF at /files/sar/<id>.pdf, webhook fired to the bank
```

(Full command list — eval, seed/reset, export, demo — is in `PROJECT_REFERENCE.md` §0.)

---

## 5. Mock-Bank integration guide (the teammate's brief)

**They build a fake bank app** with a **customer side** (a customer makes transactions)
and a **bank-admin side** (auto-flags risky transactions, sends them to Aegis, shows the
reports we send back). We build everything in between. For the demo, their app plays the
bank (we have no real bank).

### The flow
1. A **customer makes a transaction** (customer side).
2. The bank's **risk rules check it automatically**; if risky, the app **auto-POSTs it to
   Aegis** as JSON (no human action).
3. Aegis masks PII, retrieves policy, drafts the SAR; the **bank's compliance officer**
   reviews & approves on the Aegis dashboard (we run this side).
4. Aegis **POSTs the finished report back** (goAML JSON + PDF link).
5. The bank shows it in an **inbox**.

> The report is a **legal filing for the regulator (FIU-India)** — the customer NEVER sees
> it (telling them is "tipping-off," illegal). No "send to customer" anywhere. The admin
> only *files with FIU* / flags the account.

### What the teammate builds
- **Customer side:** a simple screen to make a transaction (amount, recipient, type → Send).
- **Bank-admin side:** automatic risk rules → auto-POST risky txns to Aegis; a monitoring
  list (`sent → processing → report received`); an **inbox** (goAML JSON + open-PDF button);
  optional "File with FIU" / flag-account actions.
- They do **NOT** build masking, AI, SAR drafting, or officer approval — that's us.

Risk rules can use common red flags: amount just under ₹10,00,000 (structuring) ·
high-risk type (`INTERNATIONAL_WIRE`, `CRYPTO_PURCHASE`, `HAWALA`, `FOREX_TRANSFER`) ·
large refund/reversal · dormant account suddenly active · shady counterparty bank ·
round-number amount · high velocity.

### Constraints
- **Everything local, nothing deployed.** Delivered as a ZIP with a short README +
  run steps; runs offline.
- We run the Aegis backend at `http://localhost:8000`; our frontend uses `5173`, so the
  **bank app must use a different port** (e.g. `5174`/`3000`; receiver e.g. `8001`).
- Make URLs configurable via env (`AEGIS_BASE_URL`, `BANK_WEBHOOK_URL`).

### A) Send a transaction (bank → Aegis)
```
POST  http://localhost:8000/api/v1/ingest/
Headers: X-API-Key: <given>   X-Tenant-ID: TEN-0001   Content-Type: application/json
```
```json
{
  "customer":     { "full_name": "Rohan Mehta", "id": "CUST-884213" },
  "account":      { "number": "5012-7788-2231" },
  "txn":          { "ref_id": "TXN-001", "amount": 945000, "currency": "INR",
                    "type": "INTERNATIONAL_WIRE", "direction": "OUTBOUND",
                    "timestamp": "2026-04-16T11:42:07+05:30" },
  "counterparty": { "account": "AE0703...", "name": "Gulf Horizon FZE", "bank": "Emirates NBD" },
  "metadata":     { "ip": "203.0.113.57", "device_id": "dev-9f3c1a77" },
  "risk":         { "score": 88, "reason": "Large outbound transfer just below threshold." }
}
```
Response: `{ "status": "success", "alert_id": "...", "risk_score": 100, "message": "..." }`
(The JSON shape above is the `STANDARD_FINTECH` schema — what `TEN-0001` uses.)

### B) Receive the report (Aegis → bank)
After the officer approves, Aegis POSTs to the bank's receiver URL:
```json
{
  "event": "sar.approved",
  "sar_id": "SAR-....",
  "goaml_str": { "report": { "report_code": "STR", "...": "..." } },
  "pdf_url": "http://localhost:8000/files/sar/SAR-....pdf"
}
```
The inbox shows the fields + a button to open `pdf_url`. (Locally you don't need to verify
the webhook signature; in prod that's the `X-Aegis-Signature` HMAC header.)

### We give the teammate
- The **API key** + **tenant id** (`TEN-0001`) + confirmed **base URL**.
- A **sample report payload** so they can build the inbox before we wire it live.

### TL;DR
Bank app, two sides: customer (make a txn) + bank-admin (rules flag it → auto-send risky
ones to Aegis → receive goAML JSON + PDF in an inbox). All local, ZIP, ports ≠ 5173.
