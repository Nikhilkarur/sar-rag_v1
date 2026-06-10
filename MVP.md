# Aegis AML — MVP Definition
**Version:** 1.0
**Last Updated:** 2026-06-10

---

## 1. The MVP Thesis

**One sentence:** A compliance officer at a fintech can go from a raw transaction alert to an approved, delivered SAR — entirely inside Aegis — in under 10 minutes.

That is the only thing the MVP has to prove.

Everything else (RAG, private LLMs, billing, multi-user tenants, goAML direct submission) is a distraction until this loop works end-to-end and someone finds it valuable.

---

## 2. The Critical User Journey (The Demo Loop)

This is the exact flow the MVP must execute flawlessly. Every feature decision is subordinate to making this work.

```
Step 1  →  Fintech signs up on Client Portal
Step 2  →  Super Admin approves via Admin Dashboard (30 seconds)
Step 3  →  Fintech sees their API Key and Tenant ID
Step 4  →  Fintech activates the built-in Test Webhook Receiver
Step 5  →  Fintech clicks "Submit Test Alert" (or POSTs to /alerts/ingest)
Step 6  →  System runs PII masking + AML typology checks
Step 7  →  Groq generates SAR draft (< 8s)
Step 8  →  Draft appears in Review Queue with pending badge
Step 9  →  Officer opens the 3-panel SAR Workspace
Step 10 →  Officer reads transaction data, sees which AML rules fired, reviews the draft
Step 11 →  Officer makes a small edit to the narrative
Step 12 →  Officer clicks "Preview Rehydrated SAR" → sees the final document with real names
Step 13 →  Officer clicks "Approve & Send"
Step 14 →  PDF is generated, HMAC signed, POSTed to the test webhook receiver
Step 15 →  Webhook Test Console shows the received payload
Step 16 →  Queue row flips to APPROVED
```

**This loop must work in a live demo. If it breaks at any step, the MVP is not done.**

---

## 3. Feature Matrix

### IN — Core Pipeline (Must Work)

| Feature | Notes |
|---------|-------|
| Tenant signup (3-step form) | Captures company info + contact |
| Verification status page | Blocks access until ACTIVE |
| Super Admin approval queue | Approve/Reject with one click |
| API key + Tenant ID generation on approval | Auto-provisioned, shown once |
| Credential panel (view/copy/rotate API key) | Blur-reveal pattern for security feel |
| Webhook URL config | Store + validate URL format |
| Built-in webhook test receiver | POST sink + event console |
| Schema preset selection (3 templates) | No custom mapper required for MVP |
| Alert ingestion endpoint (`POST /api/v1/alerts/ingest`) | API key auth, JSON body |
| Schema normalization | Map raw payload to Aegis standard fields |
| PII masking (field-level tokenization) | Based on selected schema |
| AML typology analysis (8 checks) | Deterministic rule engine, no ML |
| Groq SAR draft generation | llama-3.3-70b-versatile |
| Review queue (inbox view) | Status filter, alert table |
| 3-panel SAR Workspace | Transaction / AML analysis / SAR draft |
| Inline draft editing | contenteditable rich text |
| Rehydrated SAR preview modal | Real PII restored for review |
| Approve & Send flow | Re-hydrate → PDF → HMAC → webhook |
| Reject with reason | Logged, removed from active queue |
| PDF SAR generation | reportlab, formatted document |
| HMAC-SHA256 webhook signing | SHA256 over sar_id + approved_at + pdf |
| Webhook delivery (with 3-retry) | Exponential backoff |
| Webhook delivery log | Per-event status in console |
| Submit Test Alert (portal button) | Injects synthetic alert through full pipeline |
| Basic usage dashboard | Counts: alerts, approved, rejected |
| Super Admin: customer directory | Status, suspend, view |
| Super Admin: API logs | Endpoint + status + latency |
| Immutable audit log | All actions recorded |

### OUT — Explicitly Deferred

| Feature | When |
|---------|------|
| ChromaDB / RAG pipeline | Phase 2 (RAG phase) |
| Compliance manual upload + embedding | Phase 2 |
| Cross-encoder re-ranking | Phase 2 |
| Private LLM support | Only when a customer signs an NDA demanding it |
| IP whitelisting | Phase 2 security hardening |
| Billing + invoicing | When first paying customer onboards |
| Per-tenant rate limiting | When managing > 5 tenants |
| Custom JSON schema mapper (UI) | After validating 3 presets are sufficient |
| Email notifications (new alert) | Post-MVP |
| Forgot password / 2FA | Post-MVP |
| SEBI-specific SAR templates | After first broker customer |
| Direct goAML portal submission | Separate regulatory integration project |
| Multi-user per tenant (role management) | Phase 2 |
| Real-time WebSocket updates | Polling at 5s interval is fine for MVP |
| Super Admin telemetry charts | Simple counts only for MVP |
| Groq token usage per-tenant breakdown | Aggregate only for MVP |

---

## 4. The Built-in Webhook Test System

**The problem it solves:** During a demo, you have no external server receiving webhook payloads. Without this, the most impressive part of the flow (Step 14–15 above) is invisible.

**How it works:**

```
Tenant activates "Use Aegis Test Receiver" toggle in Settings → Webhook
        ↓
Backend stores webhook_url = "internal://sink/{tenant_id}" in webhook_configs
        ↓
On SAR approval, WebhookDispatcher detects "internal://" prefix
        ↓
Instead of HTTP POST, it writes the payload directly to webhook_sink_events table
        ↓
Client Portal polls GET /api/v1/webhooks/sink/{tenant_id}/events every 3s
        ↓
New event appears in Webhook Test Console with full JSON payload
```

**Additionally:**
- "Send Test Payload" button: fires a dummy SAR payload (no real alert needed) to validate the sink is working
- Each event in the console is expandable: shows headers, body, timestamp, HMAC verification status

**Why this is important for demo:** The investor or prospect sees a complete, closed-loop system. Alert goes in, SAR comes out, webhook fires, console lights up. No "you'd need to set up a server to see the rest" handwave.

---

## 5. Demo Script (5-Minute Version)

**Minute 0–1 — The Problem**
- "Indian fintechs have to file SARs with FIU-India. A single one takes 4–8 hours manually. We automate the draft and cut that to 10 minutes."

**Minute 1–2 — Onboarding**
- Show signup form (don't complete it live — have a pre-approved demo tenant)
- Open Super Admin → Approvals tab → Show approval queue → Click Approve
- "That's the 60-second onboarding."

**Minute 2–3 — Integration**
- Open Credentials panel. Show API key reveal.
- Open Webhook settings. Toggle built-in test receiver.
- Click "Submit Test Alert". "That's the bank's TMS sending us a flagged transaction."

**Minute 3–4 — The SAR Workspace**
- Open Queue → Click the alert that just appeared
- Walk through the 3 panels: "Here's the transaction, here are the 3 AML rules that fired, here's what Groq drafted."
- Make a 2-word edit to the draft. "Officers can adjust anything."
- Click "Preview Rehydrated SAR". "Real names come back from our tokenization vault."

**Minute 4–5 — Approval & Delivery**
- Click "Approve & Send."
- Show the success animation.
- Navigate to Webhook Test Console. "The SAR just arrived at the bank's system — HMAC verified."
- Open the payload. Show the SAR narrative + PDF base64.
- "That took 4 minutes. The bank's officer would have spent 6 hours."

---

## 6. Success Criteria for MVP

The MVP is complete when all of the following are true:

- [ ] The full demo loop (Steps 1–16) executes without errors
- [ ] Groq draft generation completes in < 8 seconds from alert submission
- [ ] At least 2 of the 8 AML rules fire on the default test alert
- [ ] The rehydrated SAR preview shows real PII values (not tokens)
- [ ] The PDF SAR can be downloaded and opened
- [ ] The webhook test console shows the delivery event within 5 seconds of approval
- [ ] HMAC signature verification passes on the received payload
- [ ] Super Admin can approve and suspend tenants
- [ ] A rotated API key invalidates previous key immediately
- [ ] All actions appear in the audit log

---

## 7. Honest Risks & Assumptions to Validate

**Risk 1 — Groq draft quality may need tuning**
The SAR narrative from a generic LLM prompt may not match RBI FIU-India's expected format precisely. Mitigation: invest time in the system prompt during testing. The RAG phase will fix this structurally.

**Risk 2 — Schema preset may not match real transaction payloads**
Your first real customer's payload might not fit the 3 presets. Mitigation: the custom schema mapper is listed as deferred, but keep the DB model flexible enough to add it in < 2 days when needed.

**Risk 3 — PDF generation on the server**
`reportlab` works well but the SAR template needs careful design to look credible. A poorly formatted PDF undermines the demo. Allocate explicit time to the PDF template.

**Risk 4 — Fintechs want webhook delivery, not portal review**
Some prospects may want the SAR delivered to their system without any officer intervention. For MVP, officer approval is mandatory (it's a legal requirement — SARs cannot be fully automated). But we may need to surface this clearly in sales conversations.

**Risk 5 — Multi-tenancy isolation assumption**
We use row-level tenant_id isolation in a single DB. This is fine for 0–10 tenants. For > 10, revisit with read replicas or schema-per-tenant. Not a blocker.

---

## 8. Technology Choices (Final)

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | React 18 + Vite + TypeScript | Fast build, excellent Claude Code/Fable support |
| Styling | Tailwind CSS v3 + custom CSS variables | Dark theme tokens, utility-first |
| State | Zustand (global) + React Query (server state) | Minimal boilerplate, excellent cache management |
| Routing | React Router v6 | Mature, nested routes for portals |
| Charts | Recharts | Lightest option, integrates with Tailwind |
| Backend | FastAPI + Python 3.11 | Async, fast, great for AI pipelines |
| ORM | SQLAlchemy 2.0 + Alembic | Type-safe, migrations |
| Database | PostgreSQL 15 | Multi-tenant row isolation, JSONB for schema maps |
| LLM | Groq API (llama-3.3-70b-versatile) | Fastest inference, generous free tier for MVP |
| PDF | reportlab | No OS-level dependencies, reliable |
| Auth | python-jose (JWT) + passlib/bcrypt | Standard, well-tested |
| HTTP client | httpx (async) | For webhook delivery |
| Background tasks | FastAPI BackgroundTasks | Sufficient for MVP (no Celery overhead) |
| Dev server | Uvicorn | FastAPI standard |
