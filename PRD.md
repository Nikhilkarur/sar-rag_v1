# Aegis AML — Product Requirements Document (PRD)
**Version:** 1.0 — MVP (No RAG)
**Last Updated:** 2026-06-10
**Status:** Active

---

## 1. Product Vision

> **Aegis AML is the compliance infrastructure layer for Indian fintechs and brokers — replacing manual SAR drafting with an AI-assisted pipeline that ingests flagged transaction alerts, analyses them against AML typologies, generates structured SAR drafts, and delivers approved reports back to the regulated entity, all within a single platform.**

The regulated entity (fintech, broker, payment company) remains in full control. Aegis does not file anything autonomously. Every SAR requires explicit human approval before it leaves the system.

---

## 2. The Problem

Indian fintechs and stockbrokers regulated under PMLA and SEBI AML guidelines are legally required to file Suspicious Activity Reports (SARs) with FIU-India through the goAML portal. The current state:

- **Manual and slow.** Compliance officers write SARs by hand from raw transaction data. A single SAR can take 4–8 hours.
- **Inconsistent.** Officer-to-officer quality varies. Regulators flag poorly structured reports.
- **No audit trail.** Most firms keep SAR history in spreadsheets or email threads — impossible to defend during RBI/SEBI inspection.
- **No affordable tooling.** Enterprise options like TCS BaNCS cost crores, take months to deploy, and lock firms into a proprietary ecosystem. There is nothing purpose-built for mid-size fintechs and brokers.

---

## 3. Target Users (Personas)

### Persona 1 — The Fintech Compliance Admin (`TENANT_ADMIN`)
- **Who:** Head of Compliance at a fintech / broker (10–500 person company)
- **Goal:** Get Aegis integrated with their transaction monitoring system, configure it correctly, and hand it to officers
- **Pain:** Spent weeks integrating a legacy compliance tool; it crashed during an audit
- **Needs:** Self-service setup, clear API docs, confidence the system is secure

### Persona 2 — The Compliance Officer (`COMPLIANCE_OFFICER`)
- **Who:** The analyst who reviews flagged transactions daily
- **Goal:** Review AI-generated SAR drafts quickly, edit if needed, approve and dispatch
- **Pain:** Writes 3–5 SARs per week manually; quality suffers under volume
- **Needs:** Everything on one screen, fast review, easy editing, clear audit trail

### Persona 3 — The Aegis Super Admin (`SUPER_ADMIN`)
- **Who:** Nikhil (you) and your team
- **Goal:** Onboard new clients, monitor platform health, debug issues
- **Needs:** Verification queue, customer directory, token usage, API logs

---

## 4. User Stories

### Onboarding Flow
- As a **Compliance Admin**, I can sign up with my company details so I can request access to Aegis.
- As a **Compliance Admin**, I can see a real-time status page showing whether my account is pending, active, or rejected so I know where I stand.
- As a **Super Admin**, I can review company registration details and approve or reject them so only legitimate regulated entities access the platform.
- As a **Super Admin**, when I approve a tenant, the system auto-generates their API key and Tenant ID so they can start integrating immediately.

### Configuration Flow
- As a **Compliance Admin**, I can view and copy my X-API-Key and X-Tenant-ID from a secure credential panel so my developers can integrate the ingestion API.
- As a **Compliance Admin**, I can configure a webhook URL so Aegis can POST approved SARs back to our internal system.
- As a **Compliance Admin**, I can use the built-in webhook test receiver so I can verify the full pipeline without running my own callback server.
- As a **Compliance Admin**, I can select or configure our transaction alert schema (from presets or custom mapping) so the PII masker knows which fields contain sensitive data.
- As a **Compliance Admin**, I can choose "SaaS Managed LLM" (Groq) so I don't need to manage my own model infrastructure.

### Alert Ingestion & Analysis
- As a **developer at the fintech**, I can POST a transaction alert JSON to `/api/v1/alerts/ingest` with our API key so Aegis automatically processes it.
- As a **Compliance Officer**, when an alert is ingested, the system runs AML typology checks against the transaction data so the SAR draft reflects specific rule violations, not a generic narrative.
- As a **Compliance Officer**, I can see a new alert appear in my review queue automatically after ingestion so I don't have to check manually.

### Review & Approval Flow
- As a **Compliance Officer**, I can open an alert and see a 3-panel workspace: transaction data (left), AML rules triggered (centre), AI-generated SAR draft (right) so I have everything to make a decision without switching tabs.
- As a **Compliance Officer**, I can edit the AI-generated SAR draft inline so I can correct errors or add context before approval.
- As a **Compliance Officer**, I can preview the final re-hydrated SAR (with real names/account numbers restored from tokens) before approving.
- As a **Compliance Officer**, I can click "Approve & Send" so the final SAR is signed, packaged as a PDF, and delivered via webhook.
- As a **Compliance Officer**, I can reject an alert with a reason so it's logged and removed from the active queue.

### Audit & Compliance
- As a **Compliance Admin**, I can see a usage dashboard showing total alerts processed, approved SARs, and rejected/false-positive counts so I can report on compliance activity.
- As a **Super Admin**, I can see platform-wide API call volumes, error rates, and per-tenant Groq token usage so I can manage costs and debug issues.
- As a **Super Admin**, I can suspend a tenant's API key instantly so I can cut off a misbehaving client without deleting their data.

### Demo / Testing
- As a **Compliance Officer or Admin**, I can submit a mock test alert from inside the portal so I can verify the full pipeline end-to-end without connecting an external TMS.
- As a **Compliance Admin**, I can activate a built-in test webhook receiver so the complete ingestion → review → delivery loop works entirely within Aegis during development and demos.

---

## 5. Frontend Requirements

### 5.1 Design System

**Philosophy:** Dark-first, precision tooling aesthetic. Think Linear meets Stripe Dashboard meets a Bloomberg terminal. Every pixel earns its place. No marketing fluff inside the app.

**Color Tokens:**
```
--bg-base:       #09090b   (page background)
--bg-surface:    #18181b   (cards, panels)
--bg-elevated:   #27272a   (modals, dropdowns, hover states)
--border:        #3f3f46   (default borders)
--border-subtle: #27272a   (dividers)

--accent:        #6366f1   (indigo — primary CTA, active states)
--accent-glow:   rgba(99,102,241,0.15)  (ambient glow behind accent elements)

--success:       #22c55e
--warning:       #f59e0b
--danger:        #ef4444
--info:          #38bdf8

--text-primary:  #fafafa
--text-secondary: #a1a1aa
--text-muted:    #71717a

--font-sans:     'Inter', system-ui, sans-serif
--font-mono:     'JetBrains Mono', monospace   (API keys, IDs, JSON)
```

**Motion:**
- Page transitions: fade + slight upward slide (150ms ease-out)
- Card entrance: stagger fade-in from bottom (80ms delay between items)
- Status badge changes: crossfade, never jump
- Alert queue: new items slide in from top with a subtle indigo left-border flash
- Approval success: full-screen micro-celebration (particle burst, green glow, then settle)

**Layout:**
- Left sidebar navigation (240px collapsed to 64px icon rail on mobile)
- Content area: max-width 1400px, centered
- 3-panel SAR workspace: fills 100vw with CSS grid, panels resizable via drag handle

---

### 5.2 Pages & Components

#### AUTH PAGES (Unauthenticated)

**`/login`**
- Centered card on dark background with subtle animated noise texture
- Aegis logo + wordmark at top
- Email + password fields
- "Sign in" button (indigo, full-width)
- Link to signup
- On submit: brief loading state, redirect to `/dashboard` (tenant) or `/admin/verifications` (super admin)

**`/signup`**
- 3-step wizard with animated step indicator
- Step 1 — Company Info: Company name, registration type (Fintech / Broker / NBFC / Payment Company / Other), CIN/SEBI reg number, website
- Step 2 — Contact Details: Admin full name, work email, phone, designation
- Step 3 — Confirm: Summary card, Terms checkbox, "Submit for Verification" button
- After submit: redirect to verification status page with PENDING state

---

#### CLIENT PORTAL (Tenant — ADMIN + OFFICER)

**`/dashboard`**
- Greeting header: "Good morning, Nikhil — 3 alerts need your review"
- 4 stat cards (animated count-up on load):
  - Alerts This Month / Pending Review / Approved SARs / Avg. Resolution Time
- Recent Activity feed (last 10 alerts with status badges)
- Quick-action button: "Submit Test Alert"
- If PENDING_VERIFICATION: entire dashboard replaced by a status card (see below)

**`/status` (Verification Status Page)**
- Shown when tenant status is PENDING_VERIFICATION or REJECTED
- Prominent status indicator with animated pulsing dot
- PENDING: "Your account is under review. We verify all entities manually. Typically 1–2 business days."
- REJECTED: Rejection reason shown + contact support CTA
- No other navigation is accessible until ACTIVE

**`/settings/credentials`**
- Section: API Credentials
  - X-Tenant-ID: displayed in monospace, copy button
  - X-API-Key: blurred by default, "Reveal" button (requires password confirm), copy button, "Rotate Key" button (with confirmation modal)
- Section: Integration Guide (collapsible)
  - Code snippet showing how to call `/api/v1/alerts/ingest` with curl and Python
  - Syntax highlighted

**`/settings/webhook`**
- Section: Webhook Configuration
  - URL field: input for their callback endpoint
  - Shared Secret: auto-generated, revealed same as API key
  - Save button
- Section: Test Receiver (toggle)
  - Toggle: "Use Aegis Built-in Test Receiver"
  - When ON: shows the built-in sink URL (read-only), disables the custom URL field
  - "Send Test Payload" button: fires a sample SAR payload to the active receiver
- Section: Webhook Test Console (live, updates via polling every 3s when tab is active)
  - Shows last 10 webhook delivery events
  - Each event: timestamp, status (DELIVERED / FAILED), HTTP response code, expandable payload viewer (JSON syntax highlighted)

**`/settings/schema`**
- Header: "Alert Schema Mapping"
- Subheader: "Tell Aegis which fields in your alert payload contain sensitive data, transaction identifiers, and risk signals."
- Preset Templates (3 cards to select):
  - "Standard Fintech Transaction Alert" (default)
  - "SEBI Stock Broker Trading Alert"
  - "Payment Gateway Alert"
- Custom Mapping accordion (expands when "Custom" is selected):
  - Table with 4 columns: Field Category | Your JSON Key | Sample Value | PII? (toggle)
  - Field categories: account_id, customer_name, customer_id, transaction_amount, transaction_id, timestamp, ip_address, device_id, counterparty_account, counterparty_name, transaction_type, risk_score
  - "Add Custom Field" row at bottom
  - Save button

**`/settings/llm`**
- Section: LLM Provider
  - Radio: "SaaS Managed (Groq)" [selected, locked for MVP]
  - Radio: "Private LLM" [disabled, badge: "Coming Soon"]
- Section: SAR Generation Settings
  - Jurisdiction: India — FIU-India goAML (locked for MVP)
  - Report Language: English (locked for MVP)
  - SAR Template Style: radio — Narrative / Structured Fields / Both

**`/queue`**
- Page title: "Review Queue"
- Filter bar: status chips (All / Pending Review / Approved / Rejected), date range picker, search by transaction ID
- Alert table columns: Alert ID | Transaction ID | Amount | Risk Score | AML Rules Triggered (badges) | Received At | Status | Action
- Each row: clicking anywhere opens `/queue/:alertId`
- Empty state: illustration + "No pending alerts. Submit a test alert to try the pipeline."
- New alerts appear at the top with a brief highlight animation

**`/queue/:alertId` — THE SAR WORKSPACE (Crown Jewel)**

Layout: Full-screen 3-panel CSS grid. Panels are horizontally resizable via drag handles.

**Panel 1 — Transaction Intelligence (left, ~30% width)**
- Header: Alert ID + received timestamp
- Transaction Summary card: Amount, currency, direction (credit/debit), type, risk score (colour-coded gauge)
- Customer Profile section: tokenized name, account ID, device, IP (shown as tokens — the real values are hidden until "Preview Rehydrated" is clicked)
- Counterparty section: counterparty account, institution
- Transaction Timeline: a mini horizontal timeline showing related transactions from the same customer (if available in the payload)
- Raw JSON Viewer: collapsible, syntax-highlighted

**Panel 2 — Compliance Analysis (centre, ~30% width)**
- Header: "AML Typology Analysis"
- Triggered Rules list: each rule shown as a card with:
  - Rule name (e.g., "Structuring / Smurfing Detected")
  - Brief explanation of why it fired
  - Confidence indicator (HIGH / MEDIUM / LOW) with colour coding
  - The specific field values that triggered it
- Rules that did NOT fire: shown collapsed in a "Clean Checks" accordion
- At the bottom: overall risk classification badge (HIGH / MEDIUM / LOW) with a brief rationale

**Panel 3 — SAR Draft (right, ~40% width)**
- Header: "AI-Generated SAR Draft" + "Groq · llama-3.3-70b" badge
- Draft text in a rich inline editor (contenteditable, no toolbar clutter — just clean prose editing)
- Character count, last-edited timestamp
- Floating action bar at bottom:
  - "Preview Rehydrated SAR" button: opens a modal showing the full SAR with real PII restored, formatted as the final document
  - "Reject Alert" button (secondary, red): opens reason input modal
  - "Approve & Send" button (primary, indigo): confirmation modal → success state

Approval success state:
- Modal closes
- Full-screen overlay: particle burst animation + "SAR Approved & Delivered" message + delivery timestamp + webhook status indicator
- Queue row updates to APPROVED status in real time
- Auto-redirect to `/queue` after 3 seconds

**`/usage`**
- 4 stat cards: Alerts This Month / SARs Approved / False Positives Cleared / Avg. Draft Time
- Time-series chart (Recharts): Alerts Ingested per day (last 30 days), line chart, indigo
- Table: Recent 20 approved SARs with download PDF button

---

#### SUPER ADMIN DASHBOARD (SUPER_ADMIN only)

**`/admin/verifications`**
- Table: Company Name | Registration Type | Submitted At | CIN | Contact Email | Action
- Action buttons: "Approve" (green) / "Reject" (red with reason input)
- Approve: confirmation modal, then immediate status update in table

**`/admin/customers`**
- Table: Tenant Name | Status chip | Alerts (total) | SARs Approved | Joined | Actions
- Actions: "Suspend" / "Reinstate" / "View Details"
- Suspend: flips API key to inactive, shown immediately in table

**`/admin/logs`**
- Filter: tenant selector, endpoint filter, status code filter, date range
- Table: Timestamp | Tenant | Method | Endpoint | Status | Latency (ms)
- Expandable row: request headers + body (PII-stripped), response code

**`/admin/groq`**
- Total tokens consumed (all time + this month)
- Per-tenant breakdown table: Tenant | Tokens Used | Approx. Cost ($) | Last Active
- Estimated monthly bill card

---

### 5.3 Global UI Components

**`<CommandPalette>`** — triggered by `Cmd+K` / `Ctrl+K`
- Searches: navigation pages, recent alerts (by ID or amount), tenant name (admin only)
- Keyboard navigable
- Fuzzy match

**`<AlertStatusBadge>`**
- Variants: PENDING_INGESTION (grey) / PROCESSING (blue pulse) / PENDING_REVIEW (amber) / APPROVED (green) / REJECTED (red) / DELIVERED (indigo)
- All transitions animated via CSS

**`<APIKeyReveal>`**
- Default: `sk-aegis-••••••••••••••••••••••••••••••••`
- Reveal: requires clicking "Reveal" → 10-second auto-hide timer with countdown

**`<SplitResizable>`**
- CSS grid-based, drag handle in between panels
- Min panel width: 280px
- Persists panel widths in localStorage

**`<WebhookEventCard>`**
- Expandable card showing webhook delivery details
- Status icon: green check or red X
- Payload JSON viewer with syntax highlighting

**`<SkeletonLoader>`**
- Used on all data-loading states
- Dark-themed placeholder blocks, subtle shimmer animation

**`<ToastNotifications>`**
- Bottom-right stack
- Auto-dismiss after 4s
- Types: success (green), error (red), info (indigo), warning (amber)

---

## 6. Backend Requirements

### 6.1 Core Services

**Authentication Service**
- JWT-based auth for portal users (15-min access token, 7-day refresh token)
- API key auth for headless ingestion (stateless lookup against DB)
- Role enforcement: SUPER_ADMIN, TENANT_ADMIN, COMPLIANCE_OFFICER
- Password hashing: bcrypt

**Tenant Management Service**
- CRUD for tenant records
- Status machine: PENDING_VERIFICATION → ACTIVE | REJECTED → SUSPENDED
- API key generation: cryptographically random 40-char hex, stored as bcrypt hash (full key shown once on activation)
- Auto-provision on approval: generate api_key + tenant_id

**Schema & Config Service**
- Store and retrieve ingestion schemas per tenant
- Preset schemas hardcoded server-side (3 templates)
- Webhook config: store URL and HMAC secret per tenant
- LLM config: store provider choice (Groq only for MVP)

**Alert Ingestion Pipeline**
Each stage is a discrete function, testable independently:

1. **Receive & Validate:** Parse JSON body, authenticate API key, look up tenant
2. **Schema Normalize:** Map raw payload keys to Aegis standard fields using tenant's schema
3. **PII Mask:** Replace sensitive field values with deterministic tokens (`USR_<8hex>`, `ACC_<8hex>`, `TXN_<8hex>`). Store mapping in `pii_maps` table.
4. **Compliance Analyze:** Run 8 deterministic AML checks (see Section 7). Return list of triggered rules with confidence and evidence fields.
5. **Groq Draft Generation:** Construct a structured prompt with masked transaction, triggered rules, and SAR format instructions. Call Groq API (`llama-3.3-70b-versatile`). Parse response. Store draft.
6. **Queue:** Save `Alert` + `SARDraft` records with status `PENDING_REVIEW`. Log to `audit_logs`.

**SAR Review Service**
- Fetch alert + draft for officer
- Patch draft text (inline edits)
- Approve: trigger PII re-hydration + PDF generation + webhook delivery
- Reject: log reason, update status

**PII Re-hydration**
- On approval: retrieve `pii_map` for the alert
- Replace all tokens in the draft text back to real values
- Return the rehydrated text for PDF rendering

**PDF Generation**
- Use `reportlab` to render a formatted SAR document
- Template sections: Header / Reporting Entity / Subject Customer / Transaction Details / AML Analysis / SAR Narrative / Officer Sign-off
- Embed audit metadata in the document footer

**Webhook Delivery Service**
- POST to tenant's configured callback URL (or built-in sink)
- Body: `{ sar_id, approved_at, officer_id, pdf_base64, narrative_text, hmac_signature }`
- HMAC-SHA256 signature over `sar_id + approved_at + pdf_base64` using tenant's webhook secret
- Retry: up to 3 attempts with exponential backoff (5s, 30s, 120s)
- Log all delivery attempts to `webhook_deliveries`

**Built-in Webhook Sink**
- `POST /api/v1/webhooks/sink/{tenant_id}`: receives and stores the payload (verifies HMAC)
- `GET /api/v1/webhooks/sink/{tenant_id}/events`: returns last 10 events
- Fully usable as the tenant's own callback during development/demo

**Simulator**
- `POST /api/v1/simulator/submit-test-alert`: generates a realistic fake alert payload based on the tenant's selected schema template and injects it through the full pipeline
- Returns the created `alert_id` immediately for tracking

---

### 6.2 AML Compliance Analyzer (8 Typology Checks)

Each check is a pure function: `check(normalized_transaction) → { triggered: bool, confidence: str, evidence: dict }`

| # | Rule Name | Detection Logic |
|---|-----------|-----------------|
| 1 | Structuring / Smurfing | Multiple transactions just below reporting threshold (₹10L) within 24h window from same customer |
| 2 | Rapid Fund Movement | Inbound + outbound transaction within 2h, net balance change < 10% of gross |
| 3 | Round-Number Transactions | Amount is an exact multiple of ₹1L, ₹5L, ₹10L with no fractional component |
| 4 | Dormant Account Activation | Account has no prior transaction history, sudden large transaction |
| 5 | High-Risk Transaction Type | Type is one of: crypto_purchase, international_wire, cash_withdrawal > ₹2L |
| 6 | Unusual Velocity | > 5 transactions from same account in any 1h window |
| 7 | Counterparty Risk | Counterparty account is in a known high-risk institution list (hardcoded for MVP) |
| 8 | Risk Score Threshold | Incoming `risk_score` field exceeds configured threshold (default: 75/100) |

For MVP, checks 1, 2, 5, 6, 8 work purely from the single transaction payload. Checks 3, 4, 7 may not fully fire without historical data — they degrade gracefully (fire only if evidence is present in the payload).

---

### 6.3 Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Alert → Draft in queue | < 8 seconds end-to-end |
| API ingestion response | < 500ms (async pipeline, returns `alert_id` immediately) |
| Portal page load | < 1.5s (Vite production build) |
| Uptime | Best effort for MVP; 99.5% target for v1 |
| Multi-tenancy | Row-level isolation via `tenant_id` FK on all data tables |
| Data at rest | PostgreSQL on India-region cloud (AWS Mumbai / Azure Pune) |
| Audit log | Immutable append-only, no delete |

---

## 7. Out of Scope (MVP)

The following are explicitly deferred to post-MVP phases:

| Feature | Reason Deferred |
|---------|-----------------|
| ChromaDB / Vector Store | RAG phase — requires embedding pipeline |
| Compliance manual upload | Depends on vector store |
| Cross-encoder re-ranking | Premature optimization before RAG |
| Private LLM support | No customer demanding it yet |
| IP whitelisting | Adds ops complexity for zero MVP benefit |
| Billing / invoicing | Pre-revenue — adds 2+ weeks for no demo value |
| Rate limit customization | Not needed with 0–3 tenants |
| Real-time telemetry (WebSocket) | Polling is sufficient for demo |
| FIU-India goAML direct submission | Regulatory integration is a separate project |
| Multi-user roles per tenant | Single user per tenant is fine for MVP |
| SEBI-specific SAR templates | Add after first broker customer onboards |
| Email notifications | Nice to have, not critical path |
| Forgot password / 2FA | Post-MVP security hardening |
