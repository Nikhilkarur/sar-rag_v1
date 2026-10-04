# Aegis — AI-Powered AML Compliance Platform

Aegis is a Retrieval-Augmented Generation (RAG) system that automates **Suspicious Activity Report (SAR)** drafting for banks. A bank flags a risky transaction → Aegis retrieves the bank's own AML policy, masks customer PII, and an LLM drafts a policy-cited SAR → the finished goAML-compliant report (JSON + PDF) is delivered back to the bank via webhook.

```
sar-rag_v1/
├── backend/      FastAPI + PostgreSQL + ChromaDB   → http://localhost:8000
└── frontend/     React + Vite + TypeScript         → http://localhost:5173
```

The companion **Mock Bank** repo (`mock-bank`) simulates a real bank (Meridian Bank) on the other end of the integration — customers make transactions, the bank's rule engine flags risky ones and forwards them to Aegis. See [MOCKBANK_INTEGRATION.md](MOCKBANK_INTEGRATION.md) for full setup.

---

## Quick start with Docker (recommended)

The only thing you need installed is [Docker](https://docs.docker.com/get-docker/), with Compose v2. One command starts Postgres, the API and the dashboard.

```bash
git clone https://github.com/Nikhilkarur/sar-rag_v1.git
cd sar-rag_v1

cp .env.example .env
# Edit .env and set at least: POSTGRES_PASSWORD, SECRET_KEY (openssl rand -hex 32), GROQ_API_KEY

docker compose up --build -d
docker compose logs -f backend    # wait for "Application startup complete"
```

| What | URL |
|---|---|
| Dashboard | http://localhost:5173 |
| API / health | http://localhost:8000/health |
| API docs (dev only) | http://localhost:8000/docs |

On first start the backend applies the database migrations and seeds a super-admin and the demo tenant `TEN-0001`. The demo tenant's API key is printed **once** in `docker compose logs backend`. The logins are listed under [Demo accounts](#demo-accounts) below.

**Notes**
- The first build takes a few minutes because it installs PyTorch (CPU-only) for the local embedding model. The embedding model (~130 MB) downloads the first time a policy is ingested and is cached in a volume.
- Data persists in named Docker volumes (`pgdata`, `chroma_data`, `client_storage`, `hf_cache`). `docker compose down` keeps them. `docker compose down -v` **deletes everything**.
- Ports are bound to `127.0.0.1` by default, so the stack is reachable only from your machine. To expose it, set `BIND_ADDRESS=0.0.0.0` in `.env` and put a TLS-terminating reverse proxy in front.
- Postgres is not published to the host. To use `psql` or pgAdmin, uncomment the `ports` block under `db` in `docker-compose.yml`.
- For production: set `ENVIRONMENT=production`, a strong `SECRET_KEY`, a `PII_ENCRYPTION_KEY` (the app refuses to start without one), `SEED_ON_START=false`, and change the seeded passwords.
- **Mock Bank with Docker:** the Mock Bank reaches the API at `http://localhost:8000` as usual. When you set its webhook URL in the Aegis portal, use `http://host.docker.internal:<port>/...` instead of `localhost`, because inside the container `localhost` is the container itself.
- Useful commands: `docker compose ps`, `docker compose logs -f backend`, `docker compose exec backend python seed.py`, `docker compose up --build -d` (after pulling new code).

The manual (non-Docker) setup follows below.

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
