# Aegis — Production Readiness Roadmap

**Purpose.** A concrete, checkable path from "works end-to-end as an MVP" to "production-ready."
Complete the checklist and the system is deployable, scalable, observable, and safe to run for
real tenants — with one honest caveat (read the next section).

## What "production ready" means here (read this first)

There are **two** meanings, and it matters which one you're claiming:

1. **Engineering production-ready** — deployable, horizontally scalable, observable, tested,
   recoverable, and secure at the code/infra level. **Tiers 1–2 below get you here.** This is a
   pure engineering effort, fully in your control.
2. **Launch-ready for a regulated customer** — everything above **plus** the compliance/legal
   layer: security certifications, a pen test, a signed data-processing agreement, and the
   regulator/customer accepting an LLM-assisted filing workflow. **Tier 3 gets you here**, and it
   is partly *process/legal* work that lives outside this repo.

> **So: finishing Tiers 1–2 = "engineering production-ready" (you can deploy and run it safely).
> Finishing Tier 3 = "ready to onboard a real bank/fintech with their customers' data."**
> Don't claim the second while only having the first.

---

## Already done (the foundation — don't redo these)

These are implemented and verified, and a real production system needs them:

- [x] **Multi-tenant isolation** — per-tenant Chroma collections, tenant-scoped DB queries, per-tenant schemas/keys/webhooks.
- [x] **PII masking** before any LLM call; rehydration only at finalization.
- [x] **PII encryption at rest** (Fernet) across all sensitive columns (`encrypted_types.py`); versioned key prefix (`enc::v1::`) ready for rotation.
- [x] **SAR PDFs never persisted to disk** (rendered in memory).
- [x] **Auth hardening** — bcrypt + timing-equalization, JWT type-claims, refresh-token rotation, RBAC.
- [x] **Input hardening** — payload size caps, idempotency/replay protection, prompt-injection fencing, SSRF guard (validate + send-time re-check).
- [x] **Fail-closed production boot** — refuses to start in prod without `PII_ENCRYPTION_KEY` / a non-default `SECRET_KEY`.
- [x] **Deterministic rule engine + RAG grounding** — SARs cite the tenant's real policy; indicators come from rules, not the LLM's imagination.
- [x] **goAML STR output** as JSON **and** well-formed XML (`build_goaml_xml`).
- [x] **Unit test suite** — `backend/tests/`, 55 tests (scoring, rules, masking, goAML, encryption).
- [x] **DB migrations** via Alembic; connection pooling configured.
- [x] **Secrets hygiene** — no real credentials committed; `.env.example` template.

---

## Tier 1 — Structural (hard to retrofit — do these first)

The pieces that are painful to add *after* you've scaled, because they change the shape of the app.

### 1. Containerize the whole stack
- [ ] `Dockerfile` for the backend (uvicorn/gunicorn with workers).
- [ ] `Dockerfile` for the frontend (build → served by nginx).
- [ ] `docker-compose.yml` for the full local stack: Postgres + Chroma + backend + frontend.
- [ ] Pin dependency versions (`requirements.txt` with hashes / lockfile; frontend already has `package-lock`).
- **Why:** reproducible, deployable anywhere; and running multiple workers immediately surfaces the state problems below.

### 2. Durable async job queue (the biggest architectural change)
- [ ] Replace FastAPI `BackgroundTasks` (`ingest.py::process_alert_background`) with a real queue (Celery / RQ / Arq + Redis, or a DB-backed queue).
- [ ] SAR generation becomes an enqueued **job**, not a request side-effect.
- [ ] Retry with backoff at the queue level (retire the in-process retry stopgap).
- [ ] A **sweeper/reconciler** job: find alerts stuck in `PROCESSING` beyond N minutes → re-enqueue or flag.
- **Why:** today a process crash mid-SAR strands the alert forever, and it can't scale across workers. A dropped SAR is a *regulatory* gap.

### 3. Make the app stateless (externalize in-process state)
- [ ] Move the rate limiter (`ingest.py::_rate_buckets`) to **Redis** (per-process today → wrong under N workers).
- [ ] Ensure no other request-spanning state lives in process memory.
- **Why:** required for horizontal scaling; structural, cheap now, annoying later.

### 4. Observability
- [ ] Structured JSON logging with a **correlation/request ID** threaded request → job.
- [ ] **Error tracking** (e.g. Sentry).
- [ ] `/ready` readiness endpoint (checks DB + Chroma + LLM) distinct from `/health` (liveness).
- [ ] Metrics: SAR success/failure rate, LLM latency + cost per tenant, queue depth, ingest throughput.
- [ ] **Alerting on SAR-generation failure** — a silent failure is a silent compliance gap.

### 5. CI pipeline
- [ ] CI (GitHub Actions or similar) running `pytest` + `tsc --noEmit` + lint on every push.
- [ ] **API-level tests**, especially **tenant isolation** (tenant A cannot read tenant B) and the ingest→SAR happy path.
- [ ] Fail the build on test/type/lint errors.

---

## Tier 2 — Add incrementally (current structure already supports it)

- [ ] **Config/secrets from a manager** (env injection / Vault / AWS Secrets Manager / Doppler); explicit `PII_ENCRYPTION_KEY`; separate dev/staging/prod configs.
- [ ] **Key rotation** support (the `enc::v1::` prefix anticipates it; add a re-encrypt-on-rotate path).
- [ ] **Pagination** on list endpoints (queue is a hard `limit 500` today; admin logs too).
- [ ] **Backups** — automated Postgres backup/restore; Chroma index persistence + backup (or move to a managed vector store / pgvector).
- [ ] **Data-retention policy** — PMLA 5-year retention **and** PII minimization/expiry.
- [ ] **Audit-trail completeness** — every sensitive action (SAR approve, PII reveal, key rotation, data export) immutably logged. For a compliance product this is a *feature*.
- [ ] **Per-tenant rule/threshold config** (also the multi-vertical story: bank vs broker vs insurer typologies + goAML codes).
- [ ] **Graceful DB/LLM degradation** — clear behavior + user messaging when a dependency is down.

---

## Tier 3 — Before real customer data (process + legal, not just code)

- [ ] **Third-party penetration test** and remediation.
- [ ] **Security certifications** a regulated customer will demand — SOC 2 Type II and/or ISO 27001.
- [ ] **Dependency/vulnerability scanning** in CI (`npm audit`, `pip-audit`, Dependabot).
- [ ] **Close residual SSRF TOCTOU** — pin the validated IP at connect time (DNS rebinding).
- [ ] **TLS/HTTPS everywhere**, HSTS; webhook-to-bank enforced HTTPS in prod (already gated on `ENVIRONMENT=production`).
- [ ] **Per-tenant encryption keys via KMS/HSM** (not one app-wide Fernet key).
- [ ] **Data Processing Agreement / contracts** with each customer; documented incident-response plan.
- [ ] **Regulatory validation** — goAML XML validated against the official FIU-IND **XSD**; confirm the LLM-assisted-filing workflow is acceptable to the customer's compliance team.

---

## Definition of Done (exit criteria)

**Engineering production-ready** (deploy + run safely) — ALL of:
- Tier 1 complete: one command (`docker compose up`) brings the whole stack up; SAR generation runs on a durable queue with retries + a stuck-alert sweeper; app is stateless behind Redis; logs/metrics/error-tracking live; CI green on every push including a tenant-isolation test.
- Tier 2: secrets from a manager, backups running, pagination on list endpoints, audit trail complete.

**Launch-ready for a regulated customer** — the above **plus** Tier 3: pen test passed, certifications in progress/obtained, goAML XSD-validated, DPA + incident-response in place.

---

## Suggested order

1. **Docker + compose + CI** (Tier 1 #1, #5) — the skeleton; low-risk; makes it *behave* production-shaped.
2. **Job queue + Redis state** (Tier 1 #2, #3) — the real reliability/scaling unlock.
3. **Observability** (Tier 1 #4) — weave in alongside #1–#2.
4. **Tier 2** incrementally as you approach a first design-partner.
5. **Tier 3** only when a real customer + their data are on the horizon.

> Reality check: Tiers 1–2 are a few focused weeks of engineering. Tier 3 is measured in months and
> is mostly process/legal — start those conversations early, they gate revenue more than code does.
