# Aegis — AI-Powered AML Compliance Platform

Aegis is a Retrieval-Augmented Generation (RAG) system that automates **Suspicious Activity Report (SAR)** drafting for banks. A bank flags a risky transaction → Aegis retrieves the bank's own AML policy, masks customer PII, and an LLM drafts a policy-cited SAR → the finished goAML-compliant report (JSON + PDF) is delivered back to the bank via webhook.

```
sar-rag_v1/
├── backend/      FastAPI + PostgreSQL + ChromaDB   → http://localhost:8000
└── frontend/     React + Vite + TypeScript         → http://localhost:5173
```

The companion **Mock Bank** repo (`mock-bank`) simulates a real bank (Meridian Bank) on the other end of the integration — customers make transactions, the bank's rule engine flags risky ones and forwards them to Aegis. See [MOCKBANK_INTEGRATION.md](MOCKBANK_INTEGRATION.md) for full setup.

---

## Prerequisites

- **Python 3.11+**
- **Node.js 18+** and npm
- **PostgreSQL 14+** running locally on port `5432`
- A free **Groq API key** → [console.groq.com](https://console.groq.com) (used for LLM drafting)

---

## 1. Clone & set up the backend

```bash
git clone https://github.com/Nikhilkarur/sar-rag_v1.git
cd sar-rag_v1/backend

# Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

---

## 2. Configure environment

```bash
# from backend/
copy .env.example .env    # Windows
# cp .env.example .env   # macOS/Linux
```

Edit `backend/.env`:
- `DATABASE_URL` — set your local Postgres password
- `GROQ_API_KEY` — paste your free Groq key
- `SECRET_KEY` — any random 32-char string (e.g. `openssl rand -hex 16`)
- Leave everything else as-is for local dev

---

## 3. Create the database & seed

```bash
# Create the DB (from psql or pgAdmin)
psql -U postgres -c "CREATE DATABASE aegis_db1;"

# From backend/ (venv active):
python create_db.py      # runs Alembic migrations
python seed.py           # creates super-admin + a pre-seeded demo tenant (TEN-0001)
```

---

## 4. Run

**Backend** (port 8000) — terminal 1:
```bash
cd backend
python -m uvicorn app.main:app --port 8000
```
Health check: `http://localhost:8000/health` → `{"status":"ok"}`

**Frontend** (port 5173) — terminal 2:
```bash
cd frontend
npm install
npm run dev
```

---

## 5. Add the Mock Bank (full end-to-end demo)

Clone the companion repo and follow its `README.md`:
```bash
git clone https://github.com/<your-friend-username>/mock-bank.git
```

Then read **[MOCKBANK_INTEGRATION.md](MOCKBANK_INTEGRATION.md)** in this repo for:
- How to onboard Meridian Bank as a tenant (signup → super-admin approve → policy upload → webhook)
- All credentials (Aegis dashboard + bank UI logins)
- The full 4-service start sequence
- Verified test results and known edge cases

For a step-by-step demo walkthrough once everything is running, see **[DEMO_GUIDE.md](DEMO_GUIDE.md)**.

---

## Key docs

| File | Purpose |
|---|---|
| [DEMO_GUIDE.md](DEMO_GUIDE.md) | How to run the full demo end-to-end |
| [MOCKBANK_INTEGRATION.md](MOCKBANK_INTEGRATION.md) | Mock bank ↔ Aegis wiring runbook |
| [AEGIS_KNOWLEDGE_BASE.md](AEGIS_KNOWLEDGE_BASE.md) | Full system architecture & design |
| [APISpec.md](APISpec.md) | REST API reference |
| [DatabaseSchema.md](DatabaseSchema.md) | Database schema |
| [IMPROVEMENTS_LOG.md](IMPROVEMENTS_LOG.md) | Full change history |

---

## Demo accounts

**Aegis dashboard** (`http://localhost:5173`):
| Login | Password | Role |
|---|---|---|
| `admin@aegis-aml.com` | `AegisAdmin2026!` | Super-admin (approves tenants) |
| `compliance@meridianbank.example` | `MeridianBank2026!` | Meridian Bank compliance officer |

**Mock Bank UI** (`http://localhost:5174`):
| Login | Password | Role |
|---|---|---|
| `rohan` | `demo123` | Customer (active account) |
| `kavya` | `demo123` | Customer (dormant — triggers rule R5) |
| `admin` | `admin123` | Bank compliance staff |
| Transaction PIN | `1234` | Required for customer transfers |
