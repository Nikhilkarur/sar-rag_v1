# Aegis AML — Build Order & Claude Code Master Prompt
**Version:** 1.0 — MVP (No RAG)
**Last Updated:** 2026-06-10

---

## How to Use This Document

This document is the master specification prompt for Claude Code (and Fable for frontend).
Feed each phase as a separate Claude Code session in the order listed.
Each phase is self-contained and produces testable output before the next phase begins.

**Phase execution order:**
1. Project Scaffold & Database
2. Backend Core (Auth + Admin + Tenant Config)
3. Backend Pipeline (Ingestion + AML + Groq + SAR)
4. **Frontend — Client Portal** ← Use Fable model here
5. **Frontend — Admin Dashboard** ← Use Fable model here
6. Integration & Testing

---

---

# PHASE 1 — Project Scaffold & Database

## Prompt for Claude Code:

```
You are building "Aegis AML" — a B2B SaaS for Indian fintechs and brokers to automatically generate
Suspicious Activity Reports (SARs) using AI. This is Phase 1: project scaffold and database setup.

## Project Structure

Create a monorepo with this structure:

aegis-aml/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Settings via pydantic-settings
│   │   ├── database.py          # SQLAlchemy engine + session
│   │   ├── models/              # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── tenant.py
│   │   │   ├── user.py
│   │   │   ├── schema.py
│   │   │   ├── webhook.py
│   │   │   ├── llm_config.py
│   │   │   ├── alert.py
│   │   │   ├── pii_map.py
│   │   │   ├── compliance.py
│   │   │   ├── sar.py
│   │   │   ├── delivery.py
│   │   │   ├── audit.py
│   │   │   └── api_log.py
│   │   ├── schemas/             # Pydantic request/response models
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── tenant.py
│   │   │   ├── alert.py
│   │   │   └── sar.py
│   │   ├── routers/             # FastAPI routers (one per domain)
│   │   ├── services/            # Business logic
│   │   ├── middleware/          # Logging, CORS
│   │   ├── data/
│   │   │   └── schema_presets.py   # Hardcoded schema templates
│   │   └── utils/
│   │       ├── security.py     # JWT, bcrypt, API key generation
│   │       └── audit.py        # Audit log helpers
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── .env.example
│   └── seed.py
├── frontend/
│   ├── src/
│   └── package.json
└── README.md

## Dependencies (requirements.txt)

fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy==2.0.30
alembic==1.13.1
psycopg2-binary==2.9.9
pydantic==2.7.1
pydantic-settings==2.2.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
httpx==0.27.0
groq==0.9.0
reportlab==4.1.0
python-dotenv==1.0.1

## Environment Variables (.env.example)

DATABASE_URL=postgresql://postgres:karur123@localhost:5432/aegis_db1
SECRET_KEY=your-super-secret-jwt-key-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
GROQ_API_KEY=your-groq-api-key
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:5173

## Database Models

Create all 13 SQLAlchemy models exactly as defined in DatabaseSchema.md.
Use SQLAlchemy 2.0 style (mapped_column, Mapped type hints).
Every model inherits from a Base class defined in database.py.
All UUID primary keys use server_default=text("gen_random_uuid()").
All timestamps use server_default=func.now().

Key model details:

### Tenant model (models/tenant.py)
Fields: id, name, slug, company_type, cin, sebi_reg_no, website, status, rejection_reason,
api_key_hash, api_key_prefix, tenant_id_public, approved_at, approved_by, suspended_at,
suspended_by, created_at, updated_at
Status is a Python Enum: PENDING_VERIFICATION, ACTIVE, REJECTED, SUSPENDED

### Alert model (models/alert.py)
Fields: id, tenant_id, schema_id, status, raw_payload (JSONB), normalized_payload (JSONB),
masked_payload (JSONB), transaction_id, transaction_amount (Numeric), transaction_currency,
transaction_type, transaction_direction, transaction_timestamp, risk_score, processing_started_at,
processing_completed_at, processing_error, reviewed_by, reviewed_at, rejection_reason,
is_deleted, deleted_at, source, ingested_from_ip, created_at, updated_at

Alert status Enum: PENDING_INGESTION, PROCESSING, PENDING_REVIEW, APPROVED, REJECTED,
DELIVERED, DELIVERY_FAILED

### All other models as per DatabaseSchema.md

## Alembic Setup

1. Initialize alembic: `alembic init alembic`
2. Configure env.py to use DATABASE_URL from settings
3. Create one migration per model group:
   - 001_create_tenants_users.py
   - 002_create_schemas_webhook_llm.py
   - 003_create_alerts_pii_maps.py
   - 004_create_compliance_sar_deliveries.py
   - 005_create_audit_api_logs_sink.py

## Seed Script (seed.py)

Create seed.py that:
1. Creates the super admin user: email=admin@aegis-aml.com, password=AegisAdmin2026!, role=SUPER_ADMIN
2. Creates a demo tenant: name="DemoFintech Pvt Ltd", slug="demofintech", status=ACTIVE
3. Creates a demo user linked to demo tenant: email=demo@demofintech.com, password=Demo2026!
4. Creates ingestion schema for demo tenant using STANDARD_FINTECH preset
5. Creates webhook config for demo tenant (use_internal_sink=True)
6. Creates llm config for demo tenant (provider=GROQ)
Print success confirmation after each step.

## Schema Presets (data/schema_presets.py)

Define SCHEMA_PRESETS dict with 3 templates: STANDARD_FINTECH, SEBI_BROKER, PAYMENT_GW
Each has: name, description, field_map (dict of standard_field → json_path), pii_fields (list)

STANDARD_FINTECH field_map:
{
    "customer_name": "customer.full_name",
    "customer_id": "customer.id",
    "account_id": "account.number",
    "transaction_id": "txn.ref_id",
    "transaction_amount": "txn.amount",
    "transaction_currency": "txn.currency",
    "transaction_type": "txn.type",
    "transaction_direction": "txn.direction",
    "transaction_timestamp": "txn.timestamp",
    "counterparty_account": "counterparty.account",
    "counterparty_name": "counterparty.name",
    "counterparty_institution": "counterparty.bank",
    "ip_address": "metadata.ip",
    "device_id": "metadata.device_id",
    "risk_score": "risk.score",
    "alert_reason": "risk.reason"
}
pii_fields: ["customer_name", "customer_id", "account_id", "counterparty_account",
             "counterparty_name", "ip_address", "device_id"]

## main.py

Set up FastAPI app with:
- CORS middleware (allow origins from CORS_ORIGINS env var)
- API logging middleware (logs every request to api_logs table)
- Include all routers (add as stubs for now — actual implementation in Phase 2)
- Health check: GET /health returns {"status": "ok", "version": "1.0.0"}

## Deliverable

Running `alembic upgrade head` should create all 13 tables.
Running `python seed.py` should populate demo data.
Running `uvicorn app.main:app --reload` should start with no errors.
```

---

---

# PHASE 2 — Backend Core: Auth, Admin, Tenant Config

## Prompt for Claude Code:

```
You are continuing the Aegis AML backend build. Phase 1 (DB + scaffold) is complete.
Now implement Phase 2: Auth, Admin, and Tenant Config API endpoints.
All endpoints are defined in APISpec.md. Implement them exactly as specified.

## Auth Domain (routers/auth.py + services/auth_service.py)

Implement these endpoints:
- POST /api/v1/auth/signup
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- GET /api/v1/auth/me

### JWT Implementation (utils/security.py)
- create_access_token(data, expires_delta) → JWT string
- create_refresh_token(data) → JWT string (7-day expiry)
- verify_token(token) → payload dict or raise HTTPException 401
- hash_password(password) → bcrypt hash
- verify_password(plain, hashed) → bool
- generate_api_key() → 40-char hex string ("sk-ae-" prefix + 34 hex chars)
- hash_api_key(key) → bcrypt hash
- verify_api_key(plain_key, stored_hash) → bool
- generate_tenant_id_public() → "TEN-XXXX" format, auto-incremented from DB count

### Dependencies (utils/deps.py)
- get_current_user(token: str = Depends(oauth2_scheme)) → User
- get_current_active_tenant_user(user = Depends(get_current_user)) → User (enforces ACTIVE tenant)
- get_super_admin(user = Depends(get_current_user)) → User (enforces SUPER_ADMIN role)
- get_tenant_admin(user = ...) → User (enforces TENANT_ADMIN role)
- get_compliance_user(user = ...) → User (TENANT_ADMIN or COMPLIANCE_OFFICER)
- authenticate_api_key(x_api_key: str = Header(), x_tenant_id: str = Header()) → Tenant

### Signup Logic
1. Check email uniqueness
2. Create Tenant (status=PENDING_VERIFICATION, no api_key yet)
3. Create User (role=TENANT_ADMIN, linked to tenant)
4. Write audit log: action=TENANT_SIGNUP
5. Return JWT pair + user info

## Admin Domain (routers/admin.py + services/admin_service.py)

Implement these endpoints:
- GET /api/v1/admin/verifications (paginated)
- POST /api/v1/admin/tenants/{tenant_id}/approve
- POST /api/v1/admin/tenants/{tenant_id}/reject
- GET /api/v1/admin/tenants (with filters)
- POST /api/v1/admin/tenants/{tenant_id}/suspend
- POST /api/v1/admin/tenants/{tenant_id}/reinstate
- GET /api/v1/admin/logs (with filters)
- GET /api/v1/admin/groq-usage

### Approval Logic (critical — implement exactly)
1. Validate tenant status is PENDING_VERIFICATION (else 400)
2. Generate API key: "sk-ae-" + 34 random hex chars
3. Store bcrypt hash of key, store prefix (first 12 chars)
4. Generate tenant_id_public: query COUNT of existing tenants, format "TEN-{count+1:04d}"
5. Update tenant: status=ACTIVE, approved_at=now, approved_by=current_user.id
6. Create webhook_configs record (use_internal_sink=True, generate secret)
7. Create llm_configs record (provider=GROQ, model=llama-3.3-70b-versatile)
8. Write audit logs: TENANT_APPROVED + API_KEY_GENERATED
9. Return full plaintext API key in response (only time it's returned)

## Tenant Config Domain (routers/tenant.py + services/tenant_service.py)

Implement these endpoints:
- GET /api/v1/tenant/profile
- GET /api/v1/tenant/credentials
- POST /api/v1/tenant/credentials/rotate
- GET /api/v1/tenant/webhook
- PUT /api/v1/tenant/webhook
- POST /api/v1/tenant/webhook/test
- GET /api/v1/tenant/schemas
- POST /api/v1/tenant/schemas/select-preset
- GET /api/v1/tenant/llm-config
- PUT /api/v1/tenant/llm-config
- GET /api/v1/tenant/usage

### Webhook Test Logic
If use_internal_sink=True: write a dummy SAR payload directly to webhook_sink_events.
If use_internal_sink=False: send HTTP POST to callback_url with dummy payload + HMAC header.
Update webhook_configs.last_tested_at and last_test_status.

## API Logging Middleware (middleware/logging.py)

Create FastAPI middleware that:
1. Records start time before request
2. Processes request
3. After response: extract tenant_id (from JWT or X-Tenant-ID header), user_id (from JWT),
   method, endpoint path, status code, latency_ms, request_ip
4. Write to api_logs table (fire-and-forget, don't block response)
Skip logging for: /health, /docs, /openapi.json

## Error Handling

Create app/exceptions.py with custom exception classes:
- AegisException(code, message, http_status)
- TenantNotActiveException
- TenantSuspendedException
- InvalidAPIKeyException
- InsufficientPermissionsException

Add global exception handler in main.py that converts these to the standard error response shape.

## Deliverable

All auth/admin/tenant config endpoints return correct responses per APISpec.md.
Test with: uvicorn app.main:app --reload and curl commands from APISpec.md.
```

---

---

# PHASE 3 — Backend Pipeline: Ingestion, AML Analysis, Groq, SAR

## Prompt for Claude Code:

```
You are continuing the Aegis AML backend. Phases 1–2 (DB, auth, admin, config) are complete.
Now implement Phase 3: the core alert processing pipeline.

## Pipeline Overview

POST /api/v1/alerts/ingest receives a transaction payload and returns 202 immediately.
A FastAPI BackgroundTask runs the full pipeline asynchronously:
    normalize → mask PII → analyze AML → generate SAR draft → update queue

## 3.1 Alert Ingestion Router (routers/alerts.py)

Implement:
- POST /api/v1/alerts/ingest  (API key auth via authenticate_api_key dependency)
- GET /api/v1/queue           (JWT auth, COMPLIANCE_OFFICER or TENANT_ADMIN)
- GET /api/v1/queue/{alert_id}
- PUT /api/v1/queue/{alert_id}/draft
- GET /api/v1/queue/{alert_id}/preview-rehydrated
- POST /api/v1/queue/{alert_id}/approve
- POST /api/v1/queue/{alert_id}/reject
- POST /api/v1/simulator/submit-test-alert

## 3.2 Schema Normalizer (services/schema_normalizer.py)

Function: normalize_payload(raw_payload: dict, field_map: dict) → dict

Uses the tenant's field_map to extract values from the raw payload using dot-notation paths.
Example: field_map = {"customer_name": "customer.full_name"}
         raw_payload = {"customer": {"full_name": "Rajesh Kumar"}}
         Result: {"customer_name": "Rajesh Kumar", ...}

Use a recursive key resolver for nested dot-notation paths.
If a path doesn't exist in the payload: set value to None (don't raise error — graceful degradation).
Return a dict with all Aegis standard fields, None for missing ones.

## 3.3 PII Masker (services/pii_masker.py)

Function: mask_payload(normalized: dict, pii_fields: list, alert_id: uuid) → (masked: dict, token_map: dict)

For each field in pii_fields that has a non-None value:
1. Generate a deterministic token based on field type:
   - customer_name, counterparty_name → "USR_" + first 8 chars of sha256(value)
   - account_id, counterparty_account → "ACC_" + first 8 chars of sha256(value)
   - ip_address → "IP_" + first 8 chars of sha256(value)
   - device_id → "DEV_" + first 8 chars of sha256(value)
   - customer_id → "CID_" + first 8 chars of sha256(value)
   - default → "TOK_" + first 8 chars of sha256(value)
2. Replace the value in the payload copy with the token
3. Add to token_map: {token: original_value}

Return (masked_payload, token_map)
Also store token_map in pii_maps table linked to alert_id.

Function: rehydrate_text(text: str, token_map: dict) → str
Replace all tokens in the text with their original values from token_map.

## 3.4 Compliance Analyzer (services/compliance_analyzer.py)

Function: analyze(normalized: dict) → list[ComplianceMatch]

Implement all 8 AML typology checks as pure functions.
Each check returns: {rule_id, rule_name, triggered, confidence, evidence}

### Check 1: STRUCTURING
triggered = transaction_amount is not None and 800000 <= transaction_amount <= 999999
confidence = "HIGH" if 900000 <= amount <= 999999 else "MEDIUM"
evidence = {"field": "transaction_amount", "value": str(amount),
            "explanation": f"Transaction of ₹{amount:,.0f} is near but below the ₹10,00,000 reporting threshold — a common structuring indicator."}

### Check 2: RAPID_MOVEMENT
triggered = transaction_type in ["REVERSAL", "REFUND"] and transaction_amount > 100000
confidence = "MEDIUM"
evidence = {"explanation": "Reversal/refund of a large amount suggests funds may have passed through briefly."}

### Check 3: ROUND_NUMBER
triggered = transaction_amount is not None and transaction_amount % 100000 == 0 and transaction_amount > 0
confidence = "MEDIUM" if transaction_amount >= 500000 else "LOW"
evidence = {"field": "transaction_amount", "value": str(transaction_amount),
            "explanation": f"Exact round number of ₹{transaction_amount:,.0f} with no fractional component."}

### Check 4: DORMANT_ACTIVATION
triggered = alert_reason is not None and "dormant" in alert_reason.lower()
confidence = "HIGH"
evidence = {"field": "alert_reason", "explanation": "TMS flagged account as dormant prior to this activity."}

### Check 5: HIGH_RISK_TYPE
HIGH_RISK_TYPES = ["CRYPTO_PURCHASE", "INTERNATIONAL_WIRE", "FOREX_TRANSFER", "HAWALA"]
triggered = transaction_type is not None and transaction_type.upper() in HIGH_RISK_TYPES
confidence = "HIGH"
evidence = {"field": "transaction_type", "value": transaction_type,
            "explanation": f"Transaction type '{transaction_type}' is classified as high-risk under AML guidelines."}

### Check 6: VELOCITY
triggered = (alert_reason is not None and "velocity" in alert_reason.lower()) or
            (risk_score is not None and risk_score >= 90)
confidence = "HIGH" if risk_score and risk_score >= 90 else "MEDIUM"
evidence = {"explanation": "High-velocity pattern detected — multiple transactions within a short window."}

### Check 7: COUNTERPARTY_RISK
HIGH_RISK_INSTITUTIONS = ["Unknown Bank", "Shell Bank", "Offshore Co.", "Anonymous"]
triggered = any(inst.lower() in (counterparty_institution or "").lower()
               for inst in HIGH_RISK_INSTITUTIONS)
confidence = "MEDIUM"
evidence = {"field": "counterparty_institution", "explanation": "Counterparty institution matches high-risk pattern."}

### Check 8: RISK_SCORE_THRESHOLD
THRESHOLD = 75
triggered = risk_score is not None and risk_score >= THRESHOLD
confidence = "HIGH" if risk_score >= 85 else "MEDIUM"
evidence = {"field": "risk_score", "value": str(risk_score),
            "explanation": f"Risk score of {risk_score} exceeds the threshold of {THRESHOLD}."}

### Overall Risk Calculation
If 2+ HIGH confidence rules triggered → overall_risk = "HIGH"
If 1 HIGH or 2+ MEDIUM → overall_risk = "MEDIUM"
Otherwise → overall_risk = "LOW"

## 3.5 Groq SAR Generator (services/sar_generator.py)

Function: generate_sar_draft(masked_payload: dict, compliance_matches: list, tenant_name: str, template_style: str) → str

Build this system prompt (exact wording matters for quality):

SYSTEM_PROMPT = """You are an expert AML compliance officer specializing in drafting Suspicious Activity
Reports (SARs) for the Financial Intelligence Unit of India (FIU-India) under the Prevention of Money
Laundering Act (PMLA), 2002.

You will be provided with:
1. A masked transaction payload (customer identifiers replaced with tokens for privacy)
2. A list of AML typology rules that were triggered

Your task: Draft a formal, structured SAR following FIU-India's goAML report format.

IMPORTANT RULES:
- Use the token identifiers exactly as provided (e.g., USR_a1b2c3d4) — do NOT invent names
- Be specific about which rules triggered and cite the specific values from the transaction
- Use formal legal/compliance language
- Structure the report with clear sections
- Keep the narrative factual, not speculative
- The report will be reviewed and edited by a human compliance officer before submission

OUTPUT FORMAT:
---
SUSPICIOUS ACTIVITY REPORT (DRAFT)

Reporting Entity: {tenant_name}
Date of Draft: {today}
FIU-India Report Type: STR (Suspicious Transaction Report)

1. REPORT REFERENCE
Transaction Reference: {transaction_id}
Date of Suspicious Activity: {transaction_date}

2. SUBJECT OF REPORT
Customer Reference: {customer_token}
Account Reference: {account_token}
Transaction Amount: {amount} {currency}
Transaction Type: {type}
Transaction Direction: {direction}

3. COUNTERPARTY DETAILS
Counterparty Account: {counterparty_token}
Counterparty Institution: {institution}

4. SUSPICIOUS ACTIVITY INDICATORS
[List each triggered rule with explanation]

5. NARRATIVE DESCRIPTION
[2–3 paragraphs describing the suspicious activity, linking the transaction details to
the triggered AML indicators, and explaining why this warrants regulatory reporting]

6. OFFICER DECLARATION
This report has been prepared based on available transaction data and automated AML analysis.
The reporting compliance officer has reviewed and certifies this report for submission.

[OFFICER TO COMPLETE: Name, Designation, Date of Approval]
---
"""

USER_PROMPT = f"""
Transaction Data (PII-masked):
{json.dumps(masked_payload, indent=2)}

Triggered AML Rules:
{format_triggered_rules(compliance_matches)}

Tenant/Reporting Entity Name: {tenant_name}
Today's Date: {today}

Please draft the SAR.
"""

Call Groq API:
- model: "llama-3.3-70b-versatile"
- messages: [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": USER_PROMPT}]
- temperature: 0.3 (low for consistency)
- max_tokens: 1500

Return the generated text. Also return prompt_tokens, completion_tokens, latency_ms.
Update tenant's llm_configs.total_tokens_used.

## 3.6 PDF Generator (services/pdf_generator.py)

Function: generate_sar_pdf(rehydrated_text: str, alert: Alert, tenant: Tenant, officer: User) → bytes

Using reportlab:
1. Create a PDF with:
   - Header: "SUSPICIOUS ACTIVITY REPORT" in large bold text
   - Sub-header: "Prepared by Aegis AML Platform | Confidential"
   - Horizontal rule
   - SAR text body (formatted with section headers)
   - Footer on each page: "Tenant: {tenant.name} | Alert ID: {alert.id} | Generated: {datetime}"
   - Final page: "APPROVAL METADATA" section with officer name, timestamp, Aegis version

2. Return PDF as bytes

Store PDF bytes to a file path: f"pdfs/{tenant.slug}/{alert.id}.pdf" (create dir if needed)
Return the file path.

## 3.7 Webhook Dispatcher (services/webhook_dispatcher.py)

Function: deliver_webhook(sar_draft: SARDraft, alert: Alert, tenant: Tenant) → WebhookDelivery

1. Get tenant's webhook_config
2. If use_internal_sink=True:
   - Write to webhook_sink_events table directly
   - Return delivery record with status=DELIVERED
3. If use_internal_sink=False:
   - Build payload (sar_id, alert_id, approved_at, narrative_text, pdf_base64, etc.)
   - Compute HMAC-SHA256 over json.dumps(payload).encode() using webhook secret
   - POST to callback_url with headers: X-Aegis-Signature, X-Aegis-Delivery-ID, X-Aegis-Timestamp
   - On success (2xx): create delivery record with status=DELIVERED
   - On failure: retry up to 3 times with delays [5, 30, 120] seconds
   - After 3 failures: create delivery record with status=FAILED

## 3.8 Alert Approval Flow (services/sar_service.py)

Function: approve_alert(alert_id, officer_user, db) → dict

1. Fetch alert, verify status=PENDING_REVIEW and belongs to officer's tenant
2. Fetch sar_draft linked to alert
3. Fetch pii_map for alert
4. Rehydrate: replace tokens in sar_draft.approved_text (or draft_text if no edits) with real values
5. Store rehydrated_text in sar_draft
6. Generate PDF → store path in sar_draft.pdf_path
7. Deliver webhook → create webhook_delivery record
8. Update alert status to APPROVED, set reviewed_by, reviewed_at
9. Write audit logs: ALERT_APPROVED, SAR_REHYDRATED, PDF_GENERATED, WEBHOOK_DELIVERED
10. Return success response with delivery status

## 3.9 Simulator (services/simulator.py)

Function: generate_test_alert(tenant, scenario, db) → Alert

Build realistic synthetic payloads per scenario:

STRUCTURING scenario:
{
  "customer": {"full_name": "Test User Alpha", "id": "CUST-TEST-001"},
  "account": {"number": "HDFC-TEST-99999"},
  "txn": {"ref_id": f"TEST-TXN-{timestamp}", "amount": 990000, "currency": "INR",
          "type": "NEFT_TRANSFER", "direction": "DEBIT",
          "timestamp": datetime.utcnow().isoformat()},
  "counterparty": {"account": "ICICI-TEST-88888", "name": "Test Counterparty",
                   "bank": "ICICI Bank"},
  "metadata": {"ip": "192.168.1.100", "device_id": "TEST-DEV-001"},
  "risk": {"score": 87, "reason": "Large outward transfer near reporting threshold"}
}

RAPID_MOVEMENT: amount=500000, type="REVERSAL", risk.score=78
HIGH_RISK_TYPE: amount=250000, type="INTERNATIONAL_WIRE", risk.score=82
VELOCITY: amount=50000, risk.reason="High velocity: 8 transactions in 1 hour", risk.score=91
DEFAULT: STRUCTURING scenario

After building payload, inject it into the full pipeline as if it came from POST /alerts/ingest.

## Deliverable

POST /api/v1/alerts/ingest should:
1. Accept the demo tenant's API key
2. Return 202 with alert_id
3. Process in background: normalize → mask → analyze → Groq → queue
4. Alert should appear in GET /api/v1/queue within 10 seconds

POST /api/v1/queue/{alert_id}/approve should:
1. Re-hydrate the SAR draft
2. Generate a PDF file
3. Deliver to internal sink
4. Return success with delivery status
```

---

---

# PHASE 4 — Frontend: Client Portal (USE FABLE MODEL)

## Prompt for Fable:

```
You are building the frontend for "Aegis AML" — a B2B SaaS compliance platform for Indian fintechs
and brokers. You are building the CLIENT PORTAL (not the admin dashboard).

This is a React + Vite + TypeScript application. The design must be stunning — dark mode,
professional, modern. Think Linear meets Stripe Dashboard. Every interaction should feel fast,
intentional, and high-quality.

## Tech Stack

- React 18 + TypeScript
- Vite
- Tailwind CSS v3 (with custom CSS variables in index.css)
- React Router v6
- Zustand (global auth state)
- React Query (@tanstack/react-query v5) for all server state
- Recharts for charts
- Lucide React for icons
- axios for HTTP (configured with interceptors)

## Install Dependencies

npm create vite@latest frontend -- --template react-ts
cd frontend
npm install react-router-dom @tanstack/react-query zustand axios recharts lucide-react
npm install -D @types/node

## Design System (index.css)

Add these CSS custom properties to :root:

:root {
  --bg-base: #09090b;
  --bg-surface: #18181b;
  --bg-elevated: #27272a;
  --bg-hover: #2d2d32;
  --border: #3f3f46;
  --border-subtle: #27272a;

  --accent: #6366f1;
  --accent-hover: #4f46e5;
  --accent-glow: rgba(99,102,241,0.15);
  --accent-text: #a5b4fc;

  --success: #22c55e;
  --success-bg: rgba(34,197,94,0.1);
  --warning: #f59e0b;
  --warning-bg: rgba(245,158,11,0.1);
  --danger: #ef4444;
  --danger-bg: rgba(239,68,68,0.1);
  --info: #38bdf8;
  --info-bg: rgba(56,189,248,0.1);

  --text-primary: #fafafa;
  --text-secondary: #a1a1aa;
  --text-muted: #71717a;

  --font-sans: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

  --radius: 8px;
  --radius-lg: 12px;
  --shadow: 0 4px 6px -1px rgba(0,0,0,0.4);
  --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.5);
}

body {
  background: var(--bg-base);
  color: var(--text-primary);
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
}

Add Google Fonts import for Inter and JetBrains Mono in index.html.

## Project Structure

frontend/src/
├── api/
│   ├── axios.ts           # Base axios instance with interceptors
│   ├── auth.ts
│   ├── tenant.ts
│   ├── alerts.ts
│   └── admin.ts
├── store/
│   └── auth.ts            # Zustand store: user, tokens, isAuthenticated
├── hooks/
│   ├── useAuth.ts
│   ├── useAlerts.ts
│   └── useTenant.ts
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   ├── TopBar.tsx
│   │   └── AppLayout.tsx
│   ├── ui/
│   │   ├── Badge.tsx          # AlertStatusBadge
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Input.tsx
│   │   ├── Modal.tsx
│   │   ├── Toast.tsx
│   │   ├── Skeleton.tsx
│   │   ├── Spinner.tsx
│   │   ├── Table.tsx
│   │   ├── APIKeyReveal.tsx
│   │   └── CodeBlock.tsx      # Syntax-highlighted JSON viewer
│   ├── CommandPalette.tsx
│   └── WebhookEventCard.tsx
├── pages/
│   ├── auth/
│   │   ├── Login.tsx
│   │   └── Signup.tsx
│   ├── portal/
│   │   ├── Dashboard.tsx
│   │   ├── StatusPage.tsx
│   │   ├── Queue.tsx
│   │   ├── SARWorkspace.tsx
│   │   ├── Usage.tsx
│   │   └── settings/
│   │       ├── Credentials.tsx
│   │       ├── Webhook.tsx
│   │       ├── Schema.tsx
│   │       └── LLMConfig.tsx
├── router/
│   └── index.tsx
└── main.tsx

## API Client (api/axios.ts)

Create axios instance with:
- baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000"
- Request interceptor: add Authorization: Bearer {token} from localStorage
- Response interceptor: on 401, try refresh token → if refresh fails, clear auth + redirect to /login

## Auth Store (store/auth.ts)

Zustand store with:
- user: { id, email, fullName, role, tenant: { id, name, status, tenantIdPublic } } | null
- accessToken: string | null
- isAuthenticated: boolean
- setAuth(user, accessToken, refreshToken): void
- clearAuth(): void
- On app load: read tokens from localStorage, call GET /auth/me to hydrate user

## Router (router/index.tsx)

Routes:
- /login → Login (public)
- /signup → Signup (public)
- /dashboard → Dashboard (protected, TENANT_ADMIN or COMPLIANCE_OFFICER)
- /queue → Queue (protected)
- /queue/:alertId → SARWorkspace (protected)
- /usage → Usage (protected)
- /settings/credentials → Credentials (protected, TENANT_ADMIN)
- /settings/webhook → Webhook (protected, TENANT_ADMIN)
- /settings/schema → Schema (protected, TENANT_ADMIN)
- /settings/llm → LLMConfig (protected, TENANT_ADMIN)
- / → redirect to /dashboard

Route guard: if not authenticated → redirect to /login
If tenant status is not ACTIVE → show StatusPage regardless of route
If ACTIVE → show requested route

## Sidebar (components/layout/Sidebar.tsx)

Dark sidebar, 240px width (collapsible to 64px icon rail).

Aegis logo at top (design a clean logo: a small shield icon + "AEGIS" wordmark in bold).
Below logo: tenant name in small muted text.

Navigation items (with Lucide icons):
- Dashboard (LayoutDashboard icon)
- Review Queue (InboxIcon) — show badge with pending count
- Usage (BarChart2)
- Divider with label "Settings" (only for TENANT_ADMIN)
- API Credentials (KeyRound)
- Webhook (Webhook icon)
- Alert Schema (Database)
- LLM Config (Cpu)

Bottom of sidebar:
- User avatar (initials circle) + name + role label
- Logout button

Active state: left border accent (3px indigo), bg accent-glow, text white.
Hover state: bg-elevated.

## TopBar (components/layout/TopBar.tsx)

64px height, border-bottom.
Left: Page title (passed as prop)
Right: Cmd+K hint ("⌘K"), notification bell, user avatar

## Login Page (pages/auth/Login.tsx)

Full-page dark background with very subtle animated dot grid pattern (CSS only, no canvas).
Center card: 400px wide, bg-surface, rounded-lg, shadow-lg, padding 40px.

- Aegis shield logo + "AEGIS AML" title (large, gradient text: indigo to blue)
- Subtitle: "Compliance Intelligence Platform"
- Email field + Password field (styled inputs, dark bg-elevated, border on focus glows indigo)
- "Sign in" button: full-width, indigo bg, white text, hover brightens
- "Don't have an account? Request access" link to /signup
- On submit: show loading spinner in button, call POST /auth/login, store tokens, redirect

## Signup Page (pages/auth/Signup.tsx)

3-step wizard with animated step progress bar at top.
Same background as login.
Card: 480px wide.

Step 1 — "Company Details":
  Fields: Company Name, Company Type (dropdown: Fintech / Broker / NBFC / Payment Company / Other),
  CIN number (optional help text: "Corporate Identity Number"), Website URL
  "Continue" button

Step 2 — "Administrator Details":
  Fields: Full Name, Work Email, Phone, Designation
  "Continue" button, "Back" link

Step 3 — "Review & Submit":
  Summary card showing all entered data (two columns)
  Terms checkbox: "I confirm this entity is regulated under PMLA/SEBI AML guidelines"
  "Submit Application" button → calls POST /auth/signup
  On success → redirect to /status

Animate step transitions: slide left/right using CSS transitions.

## Dashboard Page (pages/portal/Dashboard.tsx)

If tenant status ≠ ACTIVE: render StatusPage component instead.

Header: "Good [morning/afternoon/evening], {firstName}" (based on time of day)
Sub-header: "Here's what's happening with your AML pipeline."

4 stat cards in a grid (2x2 on tablet, 1x4 on desktop):
Each card: dark bg-surface, subtle border, hover: slight border-color brightens.
  - "Alerts This Month" — number, InboxIcon, compare to last month (% delta badge)
  - "Pending Review" — number, amber if > 0, ClockIcon
  - "Approved SARs" — number, green, CheckCircleIcon
  - "Avg. Review Time" — "X min", TrendingDownIcon (green if < 30min)

Line chart (Recharts): "Alerts Over Time" — last 14 days, indigo line, minimal grid, dark bg.

Recent Activity table: last 5 alerts. Columns: Transaction ID, Amount, Risk Score, Rules Fired, Status, Time.
Status shown as colored badge.

"Submit Test Alert" button (top right area): indigo, Zap icon. Opens a small modal:
  - Scenario selector: dropdown (Structuring, Rapid Movement, High-Risk Type, Velocity, Default)
  - "Inject Alert" button
  - On success: toast "Test alert submitted! Check the Review Queue."

## Status Page (pages/portal/StatusPage.tsx)

Shown when tenant is PENDING_VERIFICATION or REJECTED.

PENDING_VERIFICATION:
- Large pulsing amber dot + "Under Review" heading
- "Your application is being manually verified. This typically takes 1–2 business days."
- Timeline component: 3 steps (Submitted ✓ / Under Review [pulsing] / Active □)
- Contact email: support@aegis-aml.com

REJECTED:
- Red X icon + "Application Not Approved"
- Show rejection_reason from API
- "Contact us to discuss" CTA button

## Review Queue Page (pages/portal/Queue.tsx)

Page title: "Review Queue" + count badge (e.g., "12 pending")

Filter bar (horizontal, sticky below topbar):
- Status chips: All / Pending Review / Approved / Rejected (pill buttons, active = indigo)
- Search input: "Search by Transaction ID..." (with SearchIcon, clears on Escape)
- Date range: simple from/to date inputs

Alert table:
Headers: Alert ID | Amount | Type | Risk Score | Rules Triggered | Received | Status | Action
Rows: alternating bg-surface and bg-elevated subtly.
Risk score: colored text (< 50 green, 50–74 amber, 75+ red)
Rules Triggered: pill badges, max 2 shown + "+N more" if more exist (indigo outline pills)
Status: AlertStatusBadge component
Action: "Review" button (small, indigo)

New alerts (< 30s old): show a subtle left-border flash animation in indigo.

Empty state: centered illustration (simple SVG shield with checkmark) + "All clear. No pending alerts."

## SAR Workspace (pages/portal/SARWorkspace.tsx)

THIS IS THE MOST IMPORTANT PAGE. Make it exceptional.

Full viewport height. 3 columns via CSS grid. Resizable drag handles between panels.

### Panel 1 — Transaction Intelligence (left)

Dark bg, slightly lighter than base. Overflow-y: auto.

Header: small badge "Transaction Data" + alert ID in monospace.

Transaction Summary card:
- Amount: large font, bold, currency colored
- Direction chip: DEBIT (red) or CREDIT (green)
- Type + Timestamp
- Risk Score: a circular progress gauge (SVG, colored by severity)

Customer card:
- "Subject" label
- Fields shown with monospace token values (e.g., USR_a1b2c3d4)
- Small lock icon next to masked fields with tooltip "PII masked for analysis"

Counterparty card (same pattern)

Raw Payload accordion: "View Raw JSON" → expands to syntax-highlighted JSON viewer
(use a simple pre tag with CSS highlighting for JSON keys/values/strings).

### Panel 2 — Compliance Analysis (centre)

Header: "AML Analysis" + overall risk badge (HIGH/MEDIUM/LOW)

For each TRIGGERED rule: show a card with:
- Rule name in bold
- Evidence text (italic, slightly muted)
- Confidence pill: HIGH (red), MEDIUM (amber), LOW (green)
- A small icon representing the rule type (e.g., AlertTriangle for HIGH)

"Clean Checks" accordion at bottom: shows non-triggered rules in muted text.
Collapsed by default. Click to expand.

### Panel 3 — SAR Draft (right)

Header: "SAR Draft" + small badge "Groq · llama-3.3-70b-versatile"

The draft text is displayed in a contenteditable div.
Style: font-mono-like but readable, line-height 1.7, padding 20px.
On focus: subtle indigo border glow.
Character count displayed bottom-right.
"Last edited by you, X minutes ago" if edits were made.

Bottom action bar (sticky to bottom of panel, separated by border-top):
- "Preview Rehydrated SAR" button (secondary, ghost style)
- "Reject Alert" button (danger-ghost, opens reason modal)
- "Approve & Send ↗" button (primary, full indigo, right-aligned)

### Approve & Send Modal

Opens on "Approve & Send" click.
Shows: SAR summary (amount, rules triggered), confirmation text.
"Confirm Approval" button.
On confirm: show loading state "Generating PDF & delivering..."
On success: modal becomes a success card with animation:
  - Green checkmark with particle burst (CSS animation, no library)
  - "SAR Approved & Delivered"
  - Delivery timestamp
  - "View Delivery Receipt" link (navigates to webhook console)
  - "Back to Queue" button

### Preview Rehydrated SAR Modal

Full-screen modal. Dark overlay.
Content: the rehydrated SAR text in a clean document-like white-on-dark box.
Red banner at top: "🔒 Confidential Preview — Contains Real PII. Not stored by Aegis."
"Close Preview" button.

## Usage Page (pages/portal/Usage.tsx)

4 stat cards (same style as dashboard).
Bar chart: "Monthly SARs" — last 6 months, Recharts bar chart, indigo bars.
Line chart: "Alerts Ingested Daily" — last 30 days.
Recent SARs table: last 20 approved SARs with "Download PDF" button per row.

## Settings Pages

### Credentials (pages/portal/settings/Credentials.tsx)

Two sections on the page.

Section 1: "API Credentials"
- Tenant ID card: label + monospace value + CopyIcon button (shows tooltip "Copied!" for 2s)
- API Key card:
  - Shows: sk-ae-a1b2••••••••••••••••••••••••••••••••
  - "Reveal" button: on click asks "Confirm your password" in a mini modal → on success reveals for 10s with countdown timer
  - CopyIcon appears when revealed
  - "Rotate API Key" button (danger-ghost): opens confirmation modal → on confirm calls POST /credentials/rotate → shows new key once with prominent warning banner

Section 2: "Integration Guide" (collapsible card)
- Tab bar: "cURL" / "Python" / "Node.js"
- Code block with syntax highlighting showing how to call /alerts/ingest
- CopyIcon on code block

### Webhook (pages/portal/settings/Webhook.tsx)

Section 1: "Delivery Configuration"
- Toggle: "Use Aegis Test Receiver" (styled toggle switch, indigo when on)
- When ON: show read-only text field with internal sink URL + copy button
- When OFF: show editable URL field for their callback URL
- "Save & Generate Secret" button (only visible when OFF)
- Webhook secret: same blur-reveal pattern as API key

Section 2: "Test & Verify"
- "Send Test Payload" button → calls POST /webhook/test → shows toast with result

Section 3: "Delivery Log" (live-updating)
- Polling every 3s when tab is active
- List of WebhookEventCard components (last 10 events)
- Each card: timestamp, HMAC Valid badge (green tick or red X), HTTP status, expandable JSON payload

WebhookEventCard: expandable. Collapsed: one-line summary. Expanded: full JSON in code block.

### Schema (pages/portal/settings/Schema.tsx)

3 preset template cards in a grid:
Each card: icon, name, description, "Select" button.
Active card: indigo border, checkmark in corner, "Active" badge.
Selecting a card calls POST /schemas/select-preset and shows success toast.

Below: "What Aegis extracts" — a visual table showing the standard fields and example values.

### LLM Config (pages/portal/settings/LLMConfig.tsx)

Provider selection: two cards — "SaaS Managed (Groq)" and "Private LLM (Coming Soon)"
Groq card is selectable (shows checkmark when selected). Private LLM card is locked.

SAR Template Style: 3 radio options with descriptions:
- "Narrative" — Long-form prose SAR narrative
- "Structured" — Key fields + summary table
- "Both" — Full narrative + structured fields (Recommended)

Token usage section: shows total tokens used (from GET /llm-config)

## Components

### AlertStatusBadge (components/ui/Badge.tsx)
Props: status: string
Returns a colored pill badge:
- PENDING_INGESTION: grey
- PROCESSING: blue with pulsing dot animation
- PENDING_REVIEW: amber
- APPROVED: green
- REJECTED: red with strikethrough
- DELIVERED: indigo

### APIKeyReveal (components/ui/APIKeyReveal.tsx)
Shows masked API key. Reveal button triggers password confirmation modal. When revealed, 
shows countdown timer (10s) then re-masks. Copy button active during reveal window.

### CommandPalette (components/CommandPalette.tsx)
Triggered by Ctrl+K / Cmd+K. Floating modal with search input.
Results: navigation pages, recent alert IDs (from React Query cache).
Keyboard navigable with arrow keys. Enter navigates. Escape closes.

### Toast System (components/ui/Toast.tsx)
Bottom-right fixed stack. Auto-dismiss after 4s with progress bar animation.
Types: success (green left border), error (red), info (indigo), warning (amber).

## Final Notes

Every data fetch uses React Query. Loading states show SkeletonLoader components.
Error states show inline error cards (not full-page crashes).
All page transitions: fade-in 150ms.
All modals: backdrop blur + scale-in animation.
Mobile: sidebar collapses to icon rail. Tables scroll horizontally.
```

---

---

# PHASE 5 — Frontend: Super Admin Dashboard (USE FABLE MODEL)

## Prompt for Fable:

```
You are continuing the Aegis AML frontend. The Client Portal (Phase 4) is complete.
Now build the SUPER ADMIN DASHBOARD — the internal console for Aegis operators.

The admin dashboard uses the same design system (dark theme, same components) but has a
distinctly different navigation and data. It's accessible only to users with role=SUPER_ADMIN.

## Admin Routes (add to router/index.tsx)

- /admin → redirect to /admin/verifications
- /admin/verifications → Verifications (SUPER_ADMIN only)
- /admin/customers → Customers (SUPER_ADMIN only)
- /admin/logs → API Logs (SUPER_ADMIN only)
- /admin/groq → Groq Usage (SUPER_ADMIN only)

Route guard: if role !== SUPER_ADMIN → redirect to /dashboard

## Admin Sidebar (components/layout/AdminSidebar.tsx)

Same design as client sidebar but with different nav items:
- "Aegis AML" logo + "Admin Console" subtitle in amber text (distinguishes from client portal)
- Verifications (UserCheck icon) + pending count badge
- Customers (Building2 icon)
- API Logs (Activity icon)
- Groq Usage (Zap icon)
- Divider
- "View Client Portal" link (opens in new tab if the admin is also a test user)
- Logout button

## Admin Verifications Page (pages/admin/Verifications.tsx)

Page title: "Verification Queue" + pending count badge.

Table with columns: Company | Type | CIN | Contact | Website | Submitted | Actions
Actions: "Approve" (green button) + "Reject" (red outline button)

Approve flow:
- Click Approve → confirmation modal: "Approve [Company Name]?"
- "Confirm Approval" button → calls POST /admin/tenants/{id}/approve
- On success: show a special modal with:
  - Green checkmark
  - "Tenant Approved!"
  - Credentials box showing API key and Tenant ID in monospace
  - Warning: "Copy these credentials now — the API key will never be shown again."
  - Copy both button
  - "Done" button
- Row disappears from table with smooth slide-out animation

Reject flow:
- Click Reject → modal with textarea "Reason for rejection" + "Confirm Rejection" button
- Calls POST /admin/tenants/{id}/reject
- Row disappears with animation

Empty state: "All caught up. No pending verifications."

## Admin Customers Page (pages/admin/Customers.tsx)

Filter bar: status filter chips (All / Active / Pending / Suspended / Rejected), search input

Table columns: Tenant | ID | Type | Status | Alerts | Approved SARs | Joined | Actions

Actions per row (kebab menu icon):
- "Suspend" (amber) — confirmation modal → calls POST /suspend
- "Reinstate" (green, shown when suspended) — calls POST /reinstate
- "View Details" — expands row to show full company info

Status badge colors: Active (green), Pending (amber), Suspended (red), Rejected (grey)

## Admin API Logs Page (pages/admin/Logs.tsx)

Filter bar: Tenant selector, Endpoint input, Status Code selector (2xx/4xx/5xx/all), Date range

Table: Timestamp | Tenant | Method | Endpoint | Status | Latency
Latency: color coded — < 200ms green, 200–500ms amber, > 500ms red
Status code: colored badge (2xx green, 4xx amber, 5xx red)

Row hover: slight bg highlight. No row expansion needed for MVP.

Auto-refresh toggle (top right): when on, polls every 10s.

## Admin Groq Usage Page (pages/admin/GroqUsage.tsx)

Header cards: Total Tokens (all time) | Tokens This Month | Est. Cost This Month (USD)

Per-tenant breakdown table: Tenant | Tokens This Month | Total Requests | Est. Cost | Last Active

Simple bar chart: top 5 tenants by token usage this month (horizontal bar chart, Recharts).

Note at bottom: "Costs estimated at $0.0015/1K input tokens, $0.002/1K output tokens (Groq pricing)."
```

---

---

# PHASE 6 — Integration & Testing

## Prompt for Claude Code:

```
You are finalizing the Aegis AML MVP. Phases 1–5 (backend + frontend) are complete.
Now integrate and verify the full system works end-to-end.

## 6.1 Environment Setup

Create docker-compose.yml for local development:
version: '3.8'
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: aegis_aml
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/aegis_aml
    env_file: ./backend/.env
    depends_on:
      - db
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://localhost:8000
    command: npm run dev -- --host

volumes:
  postgres_data:

## 6.2 Backend Dockerfile

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

## 6.3 Frontend Dockerfile

FROM node:20-alpine
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]

## 6.4 End-to-End Test Script (test_e2e.py)

Write a Python script that:
1. Signs up a new test tenant
2. Logs in as super admin and approves the tenant
3. Logs in as the tenant and checks ACTIVE status
4. Configures webhook to use internal sink
5. Submits a test alert (STRUCTURING scenario) via the simulator endpoint
6. Polls GET /queue until the alert appears in PENDING_REVIEW (timeout 15s)
7. Calls GET /queue/{alert_id} and verifies all 3 data sections are present
8. Edits the draft text with a small change
9. Calls POST /queue/{alert_id}/approve
10. Calls GET /webhooks/sink/{tenant_id}/events and verifies the delivery event exists
11. Verifies HMAC signature on the received payload
12. Prints test results with PASS/FAIL per step

## 6.5 README.md

Write a clear README.md covering:
- Project overview (2 sentences)
- Prerequisites (Python 3.11, Node 20, PostgreSQL 15, Groq API key)
- Setup: backend (venv, pip install, alembic upgrade, seed.py)
- Setup: frontend (npm install, .env)
- Running locally (uvicorn + vite)
- Running with Docker Compose
- Default credentials (admin@aegis-aml.com / AegisAdmin2026!, demo@demofintech.com / Demo2026!)
- How to run the e2e test script
- The 5-minute demo script summary

## 6.6 VITE Frontend Config

vite.config.ts:
- proxy /api to http://localhost:8000 (avoids CORS in local dev)
- build output to dist/

## Verification Checklist

Before marking the build complete, verify:
[ ] alembic upgrade head creates 13 tables with no errors
[ ] seed.py creates super admin + demo tenant with no errors
[ ] POST /auth/login returns JWT for admin@aegis-aml.com
[ ] POST /admin/tenants/{id}/approve returns api_key in response
[ ] POST /alerts/ingest with demo tenant's API key returns 202
[ ] GET /queue shows the alert within 10s with status PENDING_REVIEW
[ ] GET /queue/{id} returns compliance matches and sar_draft
[ ] POST /queue/{id}/approve returns delivery status DELIVERED
[ ] GET /webhooks/sink/{tenant_id}/events shows the received payload
[ ] Frontend: login page loads at localhost:5173
[ ] Frontend: 3-panel SAR workspace renders with all panels
[ ] Frontend: "Approve & Send" shows success animation
[ ] HMAC verification passes on the webhook sink event
```

---

## Build Sequence Summary

| Phase | Model | Duration | Output |
|-------|-------|----------|--------|
| 1 — DB + Scaffold | Claude Code | 2–3h | Running DB + migrations + seed |
| 2 — Backend Core | Claude Code | 3–4h | Auth + Admin + Config APIs working |
| 3 — Backend Pipeline | Claude Code | 4–6h | Full ingestion → Groq → queue pipeline |
| 4 — Client Portal | **Fable** | 4–6h | Stunning client portal UI |
| 5 — Admin Dashboard | **Fable** | 2–3h | Admin UI complete |
| 6 — Integration | Claude Code | 2–3h | Full e2e flow tested |
| **Total** | | **~20–25h** | **Complete MVP** |

## Critical Path

Phase 3 backend pipeline must complete before Phase 4/5 frontend can integrate real data.
Phases 4 and 5 can run in parallel if needed (mock API responses during development).
Phase 6 is the integration gate — do not call MVP complete until e2e test passes.

## The One Test That Counts

Run `python test_e2e.py` and see 12 PASS, 0 FAIL.
If that passes, the MVP is done.
