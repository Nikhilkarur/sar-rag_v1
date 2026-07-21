# Aegis + Mock Bank — Demo / Presentation Guide

How to bring the whole thing up and show it to someone, end to end, on this laptop.

**The 30-second pitch:** A bank customer makes a transaction → the bank's AML engine auto-flags
risky ones and forwards them to **Aegis** → Aegis masks the customer's PII, retrieves the bank's
own AML policy, and an LLM drafts a **policy-cited Suspicious Transaction Report (STR)** → the
report is finalized and delivered back to the bank's compliance console with a downloadable PDF.

---

## 1. Prerequisites

- **Python 3.11+**, **Node 18+**, **PostgreSQL 14+** running on port 5432
- **Java 17+ JDK** and **Maven 3.8+** (for the mock bank backend)
- Two Postgres DBs created: `aegis_db1` (Aegis) and `mockbank` (the bank)
- `GROQ_API_KEY` set in `sar-rag_v1/backend/.env` (needed for SAR generation + the RAGAS eval)
- See the repo `README.md` for full setup steps if starting fresh.

## 2. Start the four services

Run each in its own terminal (Git Bash). Order doesn't matter much, but start the Aegis API first.

```bash
# 1) Aegis API  (:8000)
cd sar-rag_v1/backend
# Activate your venv first: .venv\Scripts\activate (Windows) or source .venv/bin/activate
python -m uvicorn app.main:app --port 8000

# 2) Aegis dashboard  (:5173)
cd sar-rag_v1/frontend
npm run dev

# 3) Bank backend  (:8001)  — requires Java 17+ and Maven on PATH
cd mock-bank/backend
mvn spring-boot:run

# 4) Bank frontend  (:5174)
cd mock-bank/frontend
npm run dev
```

Wait until each is up: Aegis `http://localhost:8000/health` → `{"status":"ok"}`, bank
`http://localhost:8001/actuator/health` → `{"status":"UP"}`, and the two Vite URLs print
`localhost:5173` / `localhost:5174`.

> If a Vite server says "port in use," a stale one from a previous run is holding it — kill that
> PID and restart, or it'll pick the next port (then just use that URL).

## 3. Logins

**Bank UI** — `http://localhost:5174`
| Who | Login | Notes |
|---|---|---|
| Customer | `rohan` / `demo123` | active account; transaction **PIN `1234`** |
| Customer | `kavya` / `demo123` | dormant account (triggers the dormant rule) |
| Bank compliance staff | `admin` / `admin123` | the compliance console |

**Aegis dashboard** — `http://localhost:5173`
| Who | Login | Opens |
|---|---|---|
| Bank's compliance officer (client view) | `compliance@meridianbank.example` / `MeridianBank2026!` | Meridian's client dashboard (queue, SAR workspace, settings) |
| Aegis super-admin (platform operator) | `admin@aegis-aml.com` / `AegisAdmin2026!` | admin console (tenant approvals, all customers, logs) |

## 4. The live demo (the money shot)

1. **Bank UI (`:5174`) as `rohan`** → *Send Money* → click the quick-fill chip
   **"₹9,45,000 · intl. wire"** → **Continue** → **Confirm & Send** → PIN **`1234`**. The customer
   just sees "Transaction submitted" — never anything about suspicion (that's the tipping-off rule).
2. **Switch to `admin`** (Logout → sign in as `admin`/`admin123`) → **Alert Transactions**.
   The row appears and moves **sent → processing → report received** on its own (auto-approved —
   no manual step). Point out: **Alert Transactions** shows only escalated txns; **General
   Transaction Monitoring** shows every transaction (like a real bank splits them).
3. On the **report received** row → **View report** → the modal shows the goAML STR: the
   **policy-cited narrative**, the indicators (`STRUCTURING_BELOW_THRESHOLD`, `HIGH_RISK_INSTRUMENT`…),
   customer/counterparty, recommended action → **Download PDF ↓**, and **File with FIU** (the
   bank's final call).
4. **(Optional) Aegis client view (`:5173`)** as `compliance@meridianbank.example` → the same SAR
   is in the Review Queue, already approved, showing the masked-then-rehydrated narrative and the
   Meridian policy sections it cites.
5. **(Optional) Aegis super-admin** (`admin@aegis-aml.com`) → **Customers** → shows
   `TEN-0005 · Meridian Bank Limited · ACTIVE` — i.e. the bank onboarded via the real
   signup → approval flow.

**Show a "clean" one too:** send **₹25,000 · regular transfer** → it shows as **cleared — no
report** (correctly *not* escalated). That proves the engine isn't just flagging everything.

## 5. Prove the RAG quality (the eval tests)

These run offline against the built-in test client **`client_0`** (a synthetic policy + 5 labeled
alerts with a known answer key). They show *why* the SARs are trustworthy. Run from the repo root:

```bash
# From sar-rag_v1/ repo root (venv active):

# Retrieval quality (top-k) — deterministic, no LLM. Proves RAG fetches the RIGHT policy sections.
python eval/ir_metrics.py client_0
#   expect: Recall@8 = 1.0, MRR = 1.0, nDCG@8 ≈ 0.96  (top-k = 8 chunks)

# Generation quality — LLM-judge (Groq) + bge embeddings. Proves the SAR is grounded + on-topic.
python eval/ragas_eval.py client_0
#   expect: Faithfulness ≈ 0.89, Answer Relevancy ≈ 0.70
```

**What to say about them:**
- **Top-k / IR metrics** — we retrieve the **top 8** policy chunks per alert (one sub-query per
  fired rule, merged + deduped). `Recall@8 = 1.0` means every relevant policy section is retrieved;
  `MRR = 1.0` means the #1 hit is always relevant. This is *why* we didn't need reranking or hybrid
  search — the numbers proved plain RAG is enough.
- **RAGAS** — **Faithfulness ≈0.89** = the SAR's claims are supported by the transaction data +
  retrieved policy (not hallucinated). **Answer Relevancy ≈0.70** = the SAR stays on-topic for the
  alert. (Numbers wobble ±0.02 run-to-run — LLM judge.)

## 6. Where things live (FAQ)

- **The SAR PDF is authored on the Aegis side** (`sar-rag_v1/backend/storage/clients/TEN-0005/
  sar/<sar_id>.pdf`) **and now also delivered to the bank as bytes.** The approval webhook carries
  `pdf_base64`; the bank decodes it into `sar_reports.pdf_bytes` in its `mockbank` DB and serves
  its **own** copy from `GET /api/admin/reports/{id}/pdf`. The bank's Download/Open buttons fetch
  from the bank — not Aegis — so the bank isn't dependent on Aegis being reachable. Aegis's
  `GET /files/sar/<id>.pdf` still exists but is now **tenant-authenticated** (JWT, own-tenant only),
  no longer an open link. (Older reports received before this change have no stored bytes and show
  "PDF unavailable".)
- **How the two apps link:** the bank is an Aegis **tenant** (`TEN-0005`, holds an API key +
  webhook config). Two REST calls: bank → Aegis `POST /api/v1/ingest/` (send a flagged txn), and
  Aegis → bank `POST /aegis/webhook` (deliver the finished report). Nothing is imported across the
  two — see `MOCKBANK_INTEGRATION.md`.

## 7. One-command health check

```bash
# From sar-rag_v1/ repo root (venv active):
python scripts/verify_stack.py     # expect: 27 passed, 0 failed
```

---

*Related docs: `MOCKBANK_INTEGRATION.md` (the integration runbook), `IMPROVEMENTS_LOG.md` (every
change made), `AEGIS_KNOWLEDGE_BASE.md` (the system map), `PROJECT_REFERENCE.md` (deep RAG + security).*
