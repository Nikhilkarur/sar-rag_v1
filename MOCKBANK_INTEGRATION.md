# Mock Bank ↔ Aegis — Live Integration Runbook

**What this is:** the working, end-to-end integration between the teammate's **mock bank**
(Meridian Bank — Java Spring Boot + React, at `C:\Users\nkk77\Desktop\mock-bank`) and the
**Aegis** AML backend (this repo). It documents the current running state, how it was wired,
the one bug that was fixed, and exactly how to bring it all up and demo it.

**Status: WORKING end-to-end (verified 2026-07-04).** A bank customer makes a risky
transaction → the bank auto-flags and forwards it to Aegis → Aegis drafts a policy-cited SAR
→ the (Meridian) compliance officer approves it on the Aegis dashboard → a goAML report + PDF
lands back in the bank's inbox via webhook.

> Companion docs: `MOCKBANK_BRIEF.md` (the build spec handed to the teammate),
> `STATUS_AND_MOCKBANK.md` §3 (post-ZIP runbook), `AEGIS_KNOWLEDGE_BASE.md` (system map).

---

## 1. Current state (what's live)

| Piece | Value |
|---|---|
| Aegis tenant for the bank | **`TEN-0005` — "Meridian Bank Limited"** (onboarded via real signup → super-admin approval) |
| Aegis policy for the tenant | Meridian Bank AML/CFT policy **v4.0** (enriched; regenerable via `scripts/build_meridian_policy.py`), uploaded via `POST /documents/upload` (**32 chunks** in Chroma) |
| Aegis webhook | points at the bank: `http://localhost:8001/aegis/webhook` (internal sink OFF) |
| Mock bank config | `mock-bank/.env` → `AEGIS_TENANT_ID=TEN-0005` + that tenant's API key (pasted by us) |
| DBs | Aegis: Postgres `aegis_db1` · Bank: Postgres `mockbank` (both `postgres`/`karur123`) |

**Verified:** customer transfer (₹9,45,000 intl wire) → bank score 100 → forwarded → SAR
generated citing the Meridian policy → officer approved → goAML `rentity_name = "Meridian Bank
Limited"`, indicators `[STRUCTURING_BELOW_THRESHOLD, HIGH_RISK_INSTRUMENT, HIGH_VELOCITY,
HIGH_COMPOSITE_RISK_SCORE]`, PDF served, report in the bank inbox.

---

## 2. The four services + how to start them

All four must run. Ports are fixed by config.

| Service | Port | Start command |
|---|---|---|
| **Aegis API** | 8000 | from `sar-rag_v1/backend/`: `python -m uvicorn app.main:app --port 8000` |
| **Aegis dashboard** | 5173 | from `sar-rag_v1/frontend/`: `npm run dev` |
| **Bank backend** | 8001 | from `mock-bank/backend/` (see Maven note): `mvn spring-boot:run` |
| **Bank frontend** | 5174 | from `mock-bank/frontend/`: `npm run dev` |

**Prereqs on this machine (already installed):** Java 17 (`C:\Program Files\Java\jdk-17`),
Node 22, PostgreSQL (running, `postgres`/`karur123`), and a **portable Maven** at
`C:\Users\nkk77\maven\apache-maven-3.9.9` (installed this session — Maven was not on the
system otherwise).

**Maven note (bank backend):** Maven isn't on PATH, so start the bank backend with JAVA_HOME
+ the portable Maven, e.g. from Git Bash:
```bash
cd /c/Users/nkk77/Desktop/mock-bank/backend
export JAVA_HOME='C:/Program Files/Java/jdk-17'
export PATH="/c/Users/nkk77/maven/apache-maven-3.9.9/bin:$PATH"
mvn.cmd spring-boot:run
```

**Before the very first Aegis start after a `chroma_data` wipe:** re-index the policy, or the
SAR won't cite it. (It's currently indexed for TEN-0005; only needed if Chroma is wiped —
then re-upload via the portal/endpoint, or `python scripts/seed_policy.py TEN-0005 <pdf>`.)

---

## 3. Credentials (all logins)

**Aegis dashboard** (`http://localhost:5173`):
- **Super-admin** (approves tenants, sees all): `admin@aegis-aml.com` / `AegisAdmin2026!`
- **Meridian compliance officer** (reviews/approves SARs): `compliance@meridianbank.example` / `MeridianBank2026!`
- Meridian API key: stored in `mock-bank/.env` as `AEGIS_API_KEY` (revealable in the portal → Settings → Credentials).

**Bank UI** (`http://localhost:5174`):
- Customer: `rohan` / `demo123` (active account) · `kavya` / `demo123` (dormant account → rule R5)
- Bank staff (monitoring + inbox): `admin` / `admin123`
- Transaction **PIN** for customers: **`1234`**

---

## 4. How Meridian was onboarded (the real self-serve flow)

This is the faithful path (not the pre-seeded TEN-0001 shortcut):

1. **Signup** — `POST /api/v1/auth/signup` `{company_name: "Meridian Bank Limited",
   company_type: "FINTECH", admin_email: compliance@meridianbank.example, admin_password: …,
   admin_name: …}` → tenant created `PENDING_VERIFICATION` + a `TENANT_ADMIN` user.
2. **Super-admin approves** — login as `admin@aegis-aml.com` → `GET /api/v1/admin/verifications`
   (sees the pending tenant) → `POST /api/v1/admin/tenants/{uuid}/approve`. Approval provisions
   the **API key** (returned once), the **public id `TEN-0005`**, a webhook config, and an LLM
   config, and flips the tenant to `ACTIVE`.
3. **Tenant self-configures** (as the Meridian admin): `POST /tenant/schemas/select-preset`
   `{template_key: STANDARD_FINTECH}` → `POST /documents/upload` (the Meridian policy PDF) →
   `PUT /tenant/webhook` `{use_internal_sink:false, callback_url: http://localhost:8001/aegis/webhook}`.
4. **We paste the API key + tenant id** into `mock-bank/.env`.

> **Gap noted:** approval does NOT auto-create the ingestion schema — the tenant must select a
> preset (step 3), or ingest returns `400 "No active schema found"`. Also, there is **no
> policy-upload button in the Aegis dashboard yet** — upload is API-only (a known frontend gap).

Reusable driver scripts (this session) live in the scratchpad: `onboard.py` (steps 1–4),
`cycle_ten0005.py` (full loop verification).

---

## 5. The one bug that was fixed (in the teammate's code)

`mock-bank/backend/.../client/AegisClient.java` hit **`411 Content-Length required`** — under
Spring Boot 3.5, `RestClient` + `SimpleClientHttpRequestFactory` streams the body chunked, so
Aegis (which requires `Content-Length` pre-auth) rejected it. **Fix applied:** inject an
`ObjectMapper` and pre-serialize the payload to `byte[]` before `.body(...)`, so Spring's
`ByteArrayHttpMessageConverter` sets `Content-Length`. Send this one-file diff back to the
teammate for their repo.

---

## 6. Verified test results (2026-07-04)

- **Onboarding cycle (TEN-0005):** signup → approve → schema → policy → webhook → transfer →
  SAR → approve → inbox. ✅ goAML names "Meridian Bank Limited".
- **Scenario matrix** (run earlier against the tenant): the 6 clear "report" cases
  (structuring, intl wire, crypto, hawala, refund, dormant) all forward + generate SARs;
  clean + round-number correctly clear.
- **SAR quality:** narrative cites Meridian policy sections (4.1/4.2/4.3/4.6/4.8), structured
  `recommended_action` populated, PDF served.

**Known nuances (not bugs):**
- **Velocity alone doesn't produce a SAR:** a velocity-only transaction is forwarded (bank
  score 60) but Aegis scores it 60 + velocity-MEDIUM 10 = 70 < 75 → "No SAR". Velocity produces
  a report only combined with another flag or when the score reaches ≥90. (Appendix D in the
  brief was slightly optimistic here.)
- **Velocity co-firing:** running many transfers from one customer in an hour makes velocity
  (+60) fire on later ones, so "should-not-forward" cases can forward if the customer is busy —
  correct rule behaviour, just test ordering.
- **Leftover dev server:** after a session restart, an old bank-frontend process may still hold
  `:5174` (a new `npm run dev` then errors "port in use"). The old instance still works (same
  SPA, proxies to `:8001`). If needed, kill the PID on 5174 and restart.

---

## 7. Demo script (for manual testing of both ends)

With all four services up (`AUTO_APPROVE_SARS = True`, the default):
1. **Bank UI** `http://localhost:5174` → sign in **`rohan` / `demo123`** → *Send Money* →
   quick-fill chip **"₹9,45,000 · intl. wire"** → PIN **`1234`** → Confirm.
2. **`admin` / `admin123`** → *Transaction monitoring*: the row goes **sent → processing →
   report received** on its own (**auto-approved** — no manual step).
3. **Report inbox** → open the report → **Download PDF ↓** (or **Open ↗**) → optionally
   **File with FIU** (the bank admin's final call).
4. *(Optional)* **Aegis dashboard** `http://localhost:5173` → **`compliance@meridianbank.example` /
   `MeridianBank2026!`** → the SAR shows in the Review Queue already **approved**. To require a
   manual officer click instead, set `AUTO_APPROVE_SARS = False` in `backend/app/config.py` and
   restart the Aegis API.

The customer must never see any suspicion/report (tipping-off) — that's admin-only.

> **Workflow note:** SAR approval is **automatic** by default — the report is finalized and
> delivered to the bank the moment it's drafted; the bank admin makes the final file-with-FIU
> call. Also new: **Download PDF** on the inbox, and the Aegis dashboard login is now
> session-scoped (closing the browser requires re-login). See `IMPROVEMENTS_LOG.md` (2026-07-04).

---

## 8. Reproduce from scratch (future agent)

If starting cold (e.g. new machine / wiped DBs):
1. Ensure Postgres has `aegis_db1` (Aegis) and `mockbank` (bank) DBs. Aegis: run migrations +
   `python seed.py` (creates super-admin + the pre-seeded TEN-0001). Bank: Flyway auto-creates
   `mockbank` schema + seed on first backend start.
2. Start the Aegis API (`:8000`).
3. Onboard the bank tenant (signup → super-admin approve → schema → policy upload → webhook) —
   see §4, or re-run `scratchpad/onboard.py` (adjust if the scratchpad is gone).
4. Put the new tenant id + API key in `mock-bank/.env`.
5. Start the bank backend (`:8001`, Maven), bank frontend (`:5174`), Aegis dashboard (`:5173`).
6. Verify with a transfer → approve → inbox (see `cycle_ten0005.py`).

---

## 9. Change log

- **2026-07-04 (secure PDF):** The bank now keeps its **own** copy of the SAR PDF. Aegis's
  approval webhook carries `pdf_base64` (`sar_delivery.py`); the bank decodes it into
  `sar_reports.pdf_bytes` and serves it from `GET /api/admin/reports/{id}/pdf`; the UI Download/Open
  buttons hit the bank, not Aegis. Aegis's `GET /files/sar/<id>.pdf` is now tenant-JWT-authenticated
  (own-tenant only), not an open link. Also fixed the pre-existing `AegisClientTest` 1-arg
  constructor break. Full detail in `IMPROVEMENTS_LOG.md`. Requires an Aegis backend restart + a bank
  backend restart (Flyway `V5__report_pdf.sql`).
- **2026-07-04:** Received the mock-bank ZIP; validated it against the brief (contract-faithful);
  fixed the `AegisClient` Content-Length bug; installed portable Maven; created `mockbank` DB;
  onboarded **Meridian Bank as TEN-0005** via the real signup→approve flow; uploaded a rebranded
  Meridian AML policy; wired the webhook; verified the full loop end-to-end. Next step: user
  manually tests both UIs.
