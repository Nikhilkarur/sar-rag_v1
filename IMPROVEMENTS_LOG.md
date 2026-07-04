# Aegis — Improvements Log (integration + hardening phase)

A running log of iterative changes made while integrating the mock bank and hardening the
demo. Newest first. Companion to `MOCKBANK_INTEGRATION.md` (the integration runbook).

## Open / planned (not yet done)

- **Production hardening for the (now byte-pushed) PDF delivery.** The bank now keeps its own
  PDF copy (see 2026-07-04 entry below), so the remaining items are production-only: HTTPS
  everywhere, and the bank must **verify the `X-Aegis-Signature` HMAC** on the webhook (the demo
  still skips verification). goAML JSON is the real filing; the base64 PDF rides inside the signed
  JSON over HTTPS — a valid, standard transport.
- **No AML-policy-upload button in the Aegis dashboard** — the bank uploads its policy via the API
  (`POST /api/v1/documents/upload`) only; add a Settings → Documents upload page.
- **Session-auth stricter options** (optional) — in-memory (logout on every reload) or idle timeout.
- **Deferred (from before):** LLM-outage retry queue (Celery/Redis); async webhook delivery.

---

## 2026-07-05 — PII leak fix: SAR PDFs no longer persisted to disk; alerts-vs-SARs mismatch explained

User spotted, in `storage/clients/TEN-0005/`, more SAR PDFs (16) than alert JSONs (8), and that the
SAR PDFs held **unmasked (real) PII**. Root-caused and fixed.

- **Root cause.** `storage/clients/<id>/` is an EVAL construct (for the synthetic `client_0`). But
  the LIVE approval path (`sar_delivery.finalize_and_deliver` -> `sar_pdf.render_sar_pdf`) was writing
  the **rehydrated (real-PII) SAR PDF** into `storage/clients/<tenant>/sar/<id>.pdf` on every approval —
  a plaintext PII-at-rest leak in the eval folder. The `alerts/` JSONs, by contrast, are ONLY written
  by the manual `scripts/export_alerts.py` eval tool (never the live path — ingest deliberately does not
  mirror alerts). So the two folders came from different sources at different times → **16 SARs > 8
  alerts** was an artefact, not a data-integrity bug.
- **Fix — SAR PDF is never persisted to Aegis disk now.** `render_sar_pdf` renders to an in-memory
  `BytesIO` and returns **bytes** (no `client_id`/path). `finalize_and_deliver` base64's those bytes
  straight into the `sar.approved` webhook (the bank keeps its own copy, unchanged) — no file write, no
  `draft.pdf_path`. `/files/sar/{id}.pdf` (the officer's own download) now **re-renders on demand** in
  memory from stored data via new `sar_delivery.build_draft_pdf_bytes(db, draft)`, JWT-gated to the
  owning tenant. Nothing PII-bearing is written to the filesystem in the live path.
- **Verified:** `/files/sar` returns a valid PDF **after** the on-disk copies were deleted (re-render
  from DB), and rendering writes nothing back to disk. Removed a stale unused `render_sar_pdf` import in
  `alerts.py`.
- **Cleanup.** Deleted the leaked artefacts under `storage/clients/TEN-0005/` (`sar/` 16 PDFs +
  `alerts/` 8 JSONs); kept `policy.pdf`. `client_0` (synthetic eval fixture) untouched.
- **Noted (dev-only, not a live leak):** `scripts/export_alerts.py` writes `raw_payload` (real PII) to
  `storage/clients/<id>/alerts/` because the IR eval (`eval/ir_metrics.py`) re-normalizes it — it's a
  manual developer/eval tool against a local folder, not the production path. Left functional.

---

## 2026-07-05 — Purge vendor model names, clarify "rule fires", fix risk-score double-count

- **Removed all third-party model names from the dashboards** (we don't advertise the vendor).
  Billing tiers are now generic ("Standard" / "Premium", `STANDARD_MODEL`/`PREMIUM_MODEL` in tenant.py);
  the Billing copy dropped the "(Sonnet 4.6)" / "(Opus 4.8)" parentheticals; the SAR Workspace footer
  now says "AI-generated" / "Aegis AI" instead of the raw `llm_model` (llama-3.3-70b). Purged the dead
  model-pricing catalog (Opus/Sonnet/Gemini/GPT) + token-split fields from the `/admin/groq-usage`
  response and `GroqUsage`/`ModelPricing` types (they only fed the removed projector). LLM Config was
  already generic ("Aegis-managed model"). NOTE: the **Landing page still names models** — left for the
  separate landing pass. `model_router.py` keeps the real Opus/Sonnet ids internally (config/placeholder,
  never shown).
- **Clarified the typology "fires" count.** "74 fires" was confusing next to ~17 alerts; subtitle now
  reads "Which AML rules fire most — one alert can trigger several rules" and the donut centre label is
  "rule fires" (both client dashboard + admin Overview).
- **Fixed risk-score double-counting.** The composite used the bank's own `risk_score` as the BASE and
  then `RISK_SCORE_THRESHOLD` re-added +20/+10 on top → the bank score was counted twice and the number
  inflated (often clamping at 100). Both scoring paths (`ingest.py`, `alerts.py`) now skip
  `RISK_SCORE_THRESHOLD` in the additive loop; it still fires as an indicator (evidence/typology) but
  scores 0. **Verified offline: SAR decisions (>=75) are unchanged in every case** — the bonus only ever
  applied once the base already crossed 75 — while the displayed score is now truthful (e.g. bank 80 on
  an otherwise-clean txn: 90 -> 80).

---

## 2026-07-04 (dashboard edge-case audit) — comped-tenant billing, empty states, subtitle fixes

Section-by-section correctness pass across both dashboards. Fixes:

- **Comped tenants no longer get upsell nudges.** `get_billing` returns `recommended_plan = None` for
  comped tenants (was suggesting "Growth Rs.2,320/mo" to TEN-0005, which contradicts free access).
  `Billing` type -> `recommended_plan: string | null`.
- **Comped client Billing shows a flat "free access" state** instead of the 36-SAR free-tier meter (the
  meter implied a cap/consumption that doesn't apply to a free tenant). Non-comped tenants keep the meter.
- **Admin Billing empty-state fixed.** With zero clients the "all free" note claimed "every current client
  is a free/test tenant" — now gated on `client_count > 0`.
- **Admin Overview subtitle fixed.** "LLM tokens this month" showed the *all-time* SAR count as its
  sub-label; now shows this-month SARs.
- **Delta wording.** `deltaLabel` now says "no change vs last month" for 0 (was "+0%").
- Reviewed core review flow (queue/approve/reject/draft-edit): approve/reject are idempotent-guarded (409
  on repeat), draft edits bump an edit counter, PII rehydration is on-demand — no issues found.
- **Deferred (needs product call, see chat):** the composite `risk_score` double-counts the bank's own
  score (used as the base AND as the `RISK_SCORE_THRESHOLD` rule bonus, then clamped to 100); and the
  officer Review Queue shows simulator/synthetic alerts by default.

---

## 2026-07-04 (stats audit + icon colours) — fix false "+100%", restore KPI icon colour

- **Bug fixed — false "+100% vs last month".** `_pct_delta` (tenant.py) returned `100` whenever the
  prior month had **zero** activity, so a first-month tenant (e.g. TEN-0005, onboarded this month with
  no June data) saw a bogus "+100% vs last month". Percent change from a zero baseline is undefined, so
  it now returns `None`; the client dashboard renders **"new this month"** instead. `UsageStats.delta_*`
  typed `number | null`; `deltaLabel()` helper added in `Usage.tsx`.
- **Restored KPI icon colour.** Kept the sticker *tiles* removed (per earlier), but the icon glyphs are
  colourful again (plain coloured icons, no filled square) on the client dashboard, admin Overview, and
  the new admin Billing cards — shared palette `#8b5cf6 / #ec4899 / #10b981 / #6366f1 / #f59e0b`.
- **Audit notes (reviewed, not bugs under current config):** admin "SARs this month" buckets by
  `created_at` while the tenant dashboard uses `reviewed_at` — identical while `AUTO_APPROVE_SARS=True`
  (created≈reviewed), worth aligning if manual review is ever enabled. "Ingestion API · 7d" counts raw
  successful `/ingest/` POSTs (7-day window, includes simulator + retries) so it is deliberately not
  equal to "Alerts this month" (real, calendar month). Billing meters on **SAR drafts** (generation =
  cost) not approvals — correct while auto-approve is on. No divide-by-zero paths found.

---

## 2026-07-04 (UI/UX pass) — de-stickered cards, client charts, admin Billing, printable tech handoff

User-driven UI/UX round.

- **Removed the "sticker" icon-tiles** (colored rounded-square icons) from the KPI cards on both the
  client dashboard (`portal/Usage.tsx`) and admin Overview (`admin/Overview.tsx`). Cards are now clean
  typographic stat cards with a small muted inline icon. (Charts stay colorful; only the card tiles went.)
- **Client dashboard — more "normal" stat charts** below the existing ones: **Daily alert volume**
  (30-day area), **SARs filed** (6-month bar), and a **Value screened vs flagged** card (total value
  assessed this month + the share that escalated to a SAR, with a proportion bar). Backend `/tenant/usage`
  gained `amount_screened_inr` + `amount_flagged_inr`; `UsageStats` type extended.
- **Admin Billing page (NEW)** — `admin/Billing.tsx`, nav item + route `/admin/billing`. Shows **overall
  billing = sum of every client's bill**, a per-client breakdown table (plan, SARs, billable, amount due),
  and headline totals. Comped clients (TEN-0005) render a **FREE** chip and Rs.0 with the note "Free test
  client — free-tier keys, not charged". Backend `/admin/billing` aggregates per-tenant billing using the
  same constants as `/tenant/billing` (reconciles) + `model_router.resolve_plan`. **Removed the model-cost
  projector** from LLM Usage (`admin/GroqUsage.tsx`) per user — model is chosen by each client's plan, not
  an admin toggle; LLM Usage keeps only the real token stats + free-tier note (which now points to Billing).
- **Consolidated printable technical handoff page** — the Ingestion Schema page (`settings/Schema.tsx`) no
  longer shows the PII field **table**; it now embeds a single **Technical Integration Reference** document
  (new `settings/techDoc.ts`) rendered in an isolated iframe, with **Print / Save-as-PDF** and **Download
  (HTML)** buttons — one artifact the bank hands to its engineering team. The doc is built from the REAL
  contract (fixed the stale snippet): `POST /api/v1/ingest/`, headers `X-API-Key` / `X-Tenant-ID` /
  `Idempotency-Key` / `Content-Length`, the full six-section STANDARD_FINTECH body (customer/account/txn/
  counterparty/metadata/risk) as a described document (not a table), the 200/4xx responses, and the
  `sar.approved` HMAC-signed webhook with `pdf_base64`. The old Integration Guide accordion was **removed
  from Credentials** (`settings/Credentials.tsx`) and replaced with a link to this one reference, so all
  technical detail lives in exactly one place. API key is never printed (points to Credentials to reveal).
- Verified: `/admin/billing` (total Rs.0, TEN-0005 free), `/tenant/usage` amount fields, `npx tsc --noEmit`
  clean, all 4 services healthy.

---

## 2026-07-04 (late) — Colored client dashboard, TEN-0005 comp, LLM projector, cleared-clarity, plan→model router

Session picking up the (now-deleted) HANDOFF.md pending list, then a round of user-driven fixes.

- **Client dashboard colored stats** (`portal/Usage.tsx`) — rebuilt with the admin Overview's
  visual language: 5 colored KPI cards (colored icon tiles) + the stacked **Alert outcomes** bar +
  **Typology mix** donut, shared palette (`#ec4899 / #6366f1 / #10b981 / #f59e0b / #8b5cf6`).
  Backend `/tenant/usage` (`tenant.py get_usage`) now returns tenant-scoped `outcome_monthly`
  (6-month filed/review/cleared/failed stack) + `typology` (rule fires), mirroring `/admin/overview`
  but filtered to the caller. `UsageStats` type extended.
- **TEN-0005 special free access** — `tenant.py`: `FREE_ACCESS_TENANTS = {"TEN-0005"}`; `get_billing`
  now returns `amount_due_inr=0`, `within_free_tier=True`, `special_free_access`, `special_access_label`
  for comped tenants. `Billing.tsx`: green gift banner when comped; `Billing` type extended.
- **Admin LLM Usage — free-tier note + model cost projector** (`admin/GroqUsage.tsx`) — explicit
  "running on free-tier / rotating keys → ₹0 billed; token counts are real (metered off sar_drafts)"
  note, plus a **model selector** (Opus 4.8 / Sonnet 4.6 / Gemini 2.5 Flash / GPT-4o) that projects the
  INR cost of THIS month's real token split. Backend `admin.py groq_usage` now returns
  `total_prompt_tokens_this_month`, `total_completion_tokens_this_month`, `sar_count_this_month`,
  `usd_to_inr` (86), and a `MODEL_PRICING` catalog. Verified off real usage: Opus ≈ ₹2.13/SAR,
  Sonnet ≈ ₹1.28/SAR (matches earlier cost analysis).
- **"Cleared" clarified + made consistent** — user asked what "cleared" means. Canonical taxonomy now
  documented and identical on both dashboards: **Cleared = closed with NO SAR = COMPLETED_CLEAN (auto,
  below threshold) + REJECTED (officer dismissed)**. Added `REJECTED → cleared` to the monthly-outcome
  `STATUS_BUCKET` in BOTH `admin.py` and `tenant.py` so the "Cleared — no SAR" KPI card and the chart
  segment always agree. Frontend legends/subtitles/tooltips relabeled "Cleared" → "Cleared · no SAR" /
  "Cleared (no SAR needed)" in `Overview.tsx` + `Usage.tsx`. (Current data: 15 filed, 1 failed, 0
  cleared — accurate; the fix was clarity + definition-consistency, not a number bug.)
- **Minimal plan→model→key router** (`services/model_router.py`, NEW) — single source of truth mapping
  **plan → tier → provider/model/API-key**. **FREE tier** = the live path today (Groq → Gemini failover,
  real keys). **PRO tier** = Anthropic Opus/Sonnet **PLACEHOLDER** (`ANTHROPIC_API_KEY` empty in config
  → `is_placeholder`). `TENANT_PLAN_OVERRIDES` pins **TEN-0005 to free-access-only** (can never be
  routed to a paid model); `resolve_plan()` defaults everyone to free with a documented TODO hook for a
  future `tenants.plan` column. `generate_sar` now selects provider chain + model via
  `resolve_drafting(tenant)` (behavior-preserving — every tenant still resolves to Groq→Gemini);
  `_chat_completion` takes an optional `provider_chain`; `_call_provider` gains an **anthropic** branch
  that raises a clear "paid tier not enabled" error until a key is set. Config + `.env.example` gained
  the empty `ANTHROPIC_API_KEY` / `PRO_MODEL` / `PRO_MODEL_STANDARD` placeholders. This is the *minimal*
  scaffold only — the full plan-driven billing rework is intentionally NOT built.
- **Deleted `HANDOFF.md`** (superseded; continuity now lives in this log + `MOCKBANK_INTEGRATION.md`).
- Verified: backend restart clean, `npx tsc --noEmit` clean, offline SAR generation through the new
  router chain produces a narrative, all 4 services healthy.

---

## 2026-07-04 — Repricing (₹5 + Premium Drafting ₹10) + delete TEN-0001

Per user (Sonnet 4.6 is enough for standard SARs; ₹50 was too high):

- **Per-SAR price ₹50 → ₹5** (Standard Drafting, Sonnet 4.6) and a new **Premium Drafting ₹10/SAR**
  (Opus 4.8, highest-quality narratives). `tenant.py`: `PRICE_PER_SAR_INR=5`,
  `PREMIUM_PRICE_PER_SAR_INR=10`, `STANDARD_MODEL`/`PREMIUM_MODEL`. Committed-volume plans recomputed
  from ₹5 (**Growth 500 → ₹2,320**, **Scale 2,000 → ₹9,820**). `/tenant/billing` now returns
  `premium_price_per_sar_inr`, `standard_model`, `premium_model`, and each plan carries `per_sar_inr`
  + `model`; plan ids: `standard` (was payg) · `premium` · growth · scale · enterprise.
- **Client dashboard Billing** (`Billing.tsx`): header "Plans & drafting tiers", per-SAR cards render
  `₹x / SAR` with a model chip, Premium card + "Switch to Premium" CTA, "How billing works" gains a
  Premium Drafting line. **Landing** (`Landing.tsx`): ₹50→₹5 throughout, added a **Premium Drafting
  ₹10** card, recomputed Growth/Scale, updated the pricing subtext (Standard Sonnet 4.6 / Premium
  Opus 4.8).
- **Deleted seed tenant TEN-0001** (Test Fintech Pvt Ltd) entirely — new `scripts/delete_tenant.py`
  (dry-run default, `--confirm`, TEN-0005 protected) removed 1 user + 22 alerts + 11 SARs + 48
  compliance matches + 189 api_logs (all ON DELETE CASCADE), plus its `storage/clients/TEN-0001/`
  folder (policy + 4 SAR PDFs). Rationale: `client_0` covers eval fixtures and TEN-0005 is the live
  demo; TEN-0001 was redundant.
- **Stats now reflect only TEN-0005** (verified live): overview tenants **2→1**, alerts **38→16**,
  SARs **20→15**, failed **7→1**; Customers shows just Meridian; billing quotes std ₹5 / premium ₹10
  with amount due ₹0 (15 SARs < 36 free). Future stats stay correct — everything is metered from live
  `sar_drafts` / `alerts`, not static counters. `tsc` clean; all 4 services healthy.

---

## 2026-07-04 — Admin Overview follow-ups: layout gap, outcome-bucket fix, honest usage stats

Fixes after reviewing the live Overview:

- **Sidebar/content double-margin gap.** `AppLayout` applied `ml-[232px]` for BOTH sidebars, but
  `AdminSidebar` is `position: sticky` (in-flow flex child) so it already reserves its width — the
  margin double-offset it (~232px empty column). Now the margin is `showSidebar && !admin` only.
- **"Cleared" alert-outcome bucket was overcounting.** It was a remainder (`total − filed − failed`),
  which lumped 6 escalated-but-unfiled SARs (`PROCESSING_COMPLETED`) into "cleared" (showed 11, true
  5). Rewrote the monthly stack to count each segment from its ACTUAL status —
  **filed=APPROVED · review=PROCESSING_COMPLETED/PENDING_REVIEW · cleared=COMPLETED_CLEAN ·
  failed=PROCESSING_FAILED** — segments now sum to total (20/6/5/7 = 38). Added the honest
  **"In review"** series (indigo) to the chart; this also explains the LLM-Usage-26 vs
  filed-20 gap (the 6 in review).
- **Removed meaningless LLM $ cost** (free-tier / rotating keys) from the Overview KPI and the
  LLM Usage page (cost stat card + per-tenant Est. Cost column + pricing footnote). Overview KPI is
  now **LLM tokens this month**; LLM Usage keeps token/request columns only.
- **"API requests · 7d" (783) was noise** — mostly the dashboards polling themselves
  (`/alerts/queue`, `/auth/login`, `/admin/verifications` @10s…); real external `/ingest/` traffic
  was tiny. Replaced with **"Ingestion API · 7d" = successful `/ingest/` calls (28)** — the honest
  external-API-usage figure (`ingest_requests_7d` in `/admin/overview`).
- **Verified:** `tsc` clean; live overview reconciles (38 alerts = 20+6+5+7; ingest 28 vs raw 783).

---

## 2026-07-04 — Admin dashboard: Overview page + colorful live charts + data-hygiene fixes

Full admin-console pass. New **Platform Overview** home, the landing's colorful charts wired to
LIVE data, and three real data bugs fixed.

- **New `/admin/overview` page (now the admin default landing).** Added as the first sidebar item
  (`LayoutDashboard` icon); `/admin`, both router guards, and `Login` redirect here now (was
  `/admin/verifications`). TopBar title "Platform Overview". Renders a **KPI row** (active tenants ·
  alerts this month · SARs filed this month · LLM cost · API requests 7d + error rate), a
  **stacked color bar** "Alert outcomes — last 6 months" (Filed pink / Cleared violet / Failed
  amber), a **typology donut** (which AML rules fire most), and an **API-traffic** stacked bar
  (2xx/4xx/5xx over 7 days — the "live logs as charts" the user asked for). Palette mirrors the
  landing "Usage & reports" visual.
- **New backend `GET /api/v1/admin/overview`** (`admin.py`) — one call returns `kpis`, `monthly`
  (6-month filed/cleared/failed from alerts, cleared = total − filed − failed), `typology`
  (triggered `compliance_matches` joined to non-synthetic alerts), and `api_daily` (api_logs status
  split). All metrics exclude `is_synthetic` alerts. Live now: 8 typologies, Jun/Jul stacks, 672
  API reqs/7d @ 14.1% err.
- **Data bug — "Tokens This Month" was actually all-time.** `groq_usage` set
  `total_tokens_this_month = all_time`; now a real month filter (`_draft_usage(db, month_start)`),
  keeps all-time separate, per-tenant rows carry both. Verified: 58,751 this month vs 64,368 all-time.
- **Data bug — two tenants both named "Meridian Bank Limited"** (TEN-0001 seed + TEN-0005 real bank)
  → ambiguous in Customers/Logs/LLM-Usage. Renamed **TEN-0001 → "Test Fintech Pvt Ltd"**.
- **Data bug — "Probe Fintech" junk in the Verification Queue.** `verify_stack.py` signed up a
  throwaway probe tenant every run and never cleaned up (2 had piled up). **Purged** them + made
  `verify_stack.py` **self-clean** its probe at the end (best-effort, never affects the 27/27 count).
  Both one-off fixes live in new **`scripts/admin_hygiene.py`** (`--dry-run` supported, idempotent).
- **LLM Usage alignment** — widened the bar-chart tenant labels (170px, truncate at 26 not 17 → no
  more "Meridian Bank Lim…"), tighter bar spacing (`barCategoryGap`, taller bars).
- **Verified:** `tsc --noEmit` clean; `verify_stack.py` **27/27** + self-cleanup; Verification Queue
  now **0 pending**; Customers shows the two distinctly-named tenants; all 4 services healthy.
  (Encoding note still applies — backend serialized strings kept ASCII; charts render ₹/labels
  frontend-side.)

---

## 2026-07-04 — Align landing pricing with dashboard billing + "Upgrade to a plan" cards

Per user: the landing pricing tiers didn't match the dashboard's live billing, and the dashboard had
no way to surface the plans. Made everything **derive from one source** so they can't drift.

- **Single source of truth (backend `tenant.py`).** New `billing_plans()` derives every tier price from
  the pay-as-you-go constants: `monthly_inr = (included_sars - FREE_SARS) * PRICE_PER_SAR_INR`. So a
  plan is just a prepaid monthly SAR allotment at the same ₹50/SAR (the 36 free SARs still on the house).
  Tiers: **Pay-as-you-go** (36 free, ₹0), **Growth** (500 → **₹23,200**), **Scale** (2,000 → **₹98,200**),
  **Enterprise** (unlimited/custom, `null`). `/tenant/billing` now also returns `plans`, `current_plan`
  (`"payg"` — no per-tenant plan column yet), and `recommended_plan` (smallest tier that covers this
  cycle's usage; Meridian at 15 SARs → `growth`).
- **Dashboard (`settings/Billing.tsx`).** New **"Upgrade to a plan"** card grid under the usage meter —
  renders the backend `plans`, tags the CURRENT plan and a SUGGESTED one, uses the real `Button`
  component, and Upgrade/Talk-to-sales opens a `mailto:sales@`. Pay-as-you-go meter kept as-is.
- **Landing (`Landing.tsx`).** Growth **₹24k → ₹23,200**, Scale **₹58k → ₹98,200** (now exactly the
  derived numbers), added "500/2,000 SARs at ₹50 each" to the descs. Pay-as-you-go line in the section
  subtext kept. Card layout/CSS untouched.
- **Current per-SAR rate:** ₹50/SAR, first 36 SARs/month free (~100k tokens) — unchanged.
- **Encoding gotcha (fits the ASCII-strings rule):** the running backend decodes `tenant.py` as cp1252,
  not UTF-8, so `₹`/`—` in *serialized* plan strings came out mojibake in the JSON. Fixed by keeping the
  plan `description`/`features` **ASCII-only** and letting the frontend render currency via `formatINR`.
- **Verified:** `tsc --noEmit` clean; live `/tenant/billing` returns Growth ₹23,200 / Scale ₹98,200 with
  no mojibake; all 4 services healthy (Aegis :8000, bank :8001, FEs :5173/:5174). Backend restarted
  (no `--reload`) to pick up the change.

---

## 2026-07-04 — Dead-control fixes: SAR Template Style, Queue tabs

- **SAR Template Style was a non-functional control.** `sar_template_style` (Narrative/Structured/Both)
  is stored + updated but **never read during generation** (`llm_agent` always emits both). Since goAML
  filing structurally needs BOTH the narrative (reason + PDF) and the structured fields (indicators),
  "Both" is the only valid mode — so `settings/LLMConfig.tsx` now shows it **locked ("Locked for MVP")**,
  matching Jurisdiction/Report Language on the same page. Removed the dead radios + handler.
- **Review Queue tabs cleaned up for auto-approve.** Removed the **Pending** tab (nothing is ever
  pending under auto-approve); renamed **Rejected → "Rejected / Not approved"** and its filter now
  matches `REJECTED` OR `PROCESSING_FAILED` (so a failed generation shows there). Header no longer says
  "N pending / Nothing pending" — shows `N alerts · M not approved`. Removed the sidebar's pending badge.
- **Landing pricing** confirmed live (36 SARs ~100k tokens free · ₹50/SAR) with the card design intact.

Verified `tsc --noEmit` clean; no backend change (frontend hot-reloads).

---

## 2026-07-04 — Usage-based billing (client Settings → Billing + landing pricing)

Per user: add a **Billing** section (100k tokens / ~36 SARs free per month, then per-SAR charge) and
mirror the logic on the landing pricing — without touching the landing design.

- **Pricing model (user chose per-SAR):** first **36 SARs (~100,000 tokens) / month free → ₹0**, then
  **₹50 per SAR**. Constants in `tenant.py` (`FREE_SARS=36`, `FREE_TOKENS=100_000`, `PRICE_PER_SAR_INR=50`)
  — trivially tunable.
- **Backend:** new `GET /api/v1/tenant/billing` — meters the current calendar month's SAR drafts
  (count + tokens), computes `billable_sars = max(0, sars - 36)` and `amount_due = billable × ₹50`.
  Metered on real drafts, so **it actually works off live usage** (Meridian: 15/36 SARs → ₹0, within
  free tier).
- **Frontend:** new `settings/Billing.tsx` — amount due, a free-tier progress bar (SARs used / 36),
  tokens this cycle, and a "how billing works" explainer. Wired into the router, the Settings sidebar
  ("Billing"), and the TopBar title. New `Billing` type + `getBilling()` API.
- **Landing pricing:** reframed `PLANS` from alerts → SAR/token allowances (Free ₹0 = 36 SARs ~100k
  tokens · Growth ₹24k = 500 · Scale ₹58k = 2,000 · Enterprise = unlimited) and added the free-tier +
  ₹50/SAR line to the section subtext. **Card layout/CSS untouched** — content/logic only.
- Verified: `tsc` clean, backend compiles, `/tenant/billing` returns the live figures.

---

## 2026-07-04 — Fix LLM-request undercount (logical inconsistency)

User spotted it: dashboard showed **15 SARs filed but only 13 LLM requests** — impossible, since each
SAR is exactly one generation. Root cause: `llm_configs.total_requests`/`total_tokens_used` are
**mutable counters** incremented in `generate_sar`, and 2 increments had been missed at some point
(DB truth: 15 sar_drafts summing 41,056 tokens, counter said 13 / 35,545) — a drift-prone design.

- **Fix:** derive tokens/requests from the **`sar_drafts` table** (one draft == one SAR == one
  generation) instead of the counters. New `_llm_usage_from_drafts(db, tenant_id)` in `tenant.py`,
  used by both `/tenant/usage` and `/tenant/llm-config`; `admin.py`'s `/groq-usage` now aggregates
  `sar_drafts` per tenant the same way. Drift-proof, and `requests` can never be < `SARs filed`.
- **Verified:** all endpoints now report **15 requests · 41,056 tokens** (matching the 15 drafts).
  Story is clean: 16 alerts → 15 SARs (15 requests) + 1 failed. The mutable counters are left in place
  (still incremented) but no longer read for display.

Answer to the user's question: yes — every SAR uses its own single LLM request; the count now
reflects that exactly.

---

## 2026-07-04 — Client portal: merge dashboards, SAR-PDF in workspace, collapsible sidebar

Per user, a batch of client-side (tenant portal) changes — content/representation, no visual redesign:

- **Merged Dashboard + Usage into one central dashboard.** `/dashboard` now renders the Usage view;
  `/usage` redirects to it; the "Usage" sidebar item is removed; the old `Dashboard.tsx` is left in
  place but no longer routed (no code deleted). The central dashboard = 4 headline stats + the two
  charts (Monthly SAR Approvals, Daily Alert Volume) + a new **Pipeline usage** strip
  (**LLM tokens used · requests · failed-to-process**, the last tinted red when >0). The SAR-audit
  table was dropped (not needed here). Backend `/tenant/usage` now also returns `tokens_used`,
  `total_requests`, `failed_count` (from `llm_configs` + a PROCESSING_FAILED count).
- **Download PDF in the SAR Workspace.** A "Download PDF" action now sits in the workspace header
  (shown once the alert is APPROVED, i.e. the PDF exists) — fetches the tenant-auth'd
  `/files/sar/<id>.pdf` blob via `downloadSarPdf`. Same secure path as the Usage/bank download.
- **Collapsible sidebar.** `AppLayout` holds a `collapsed` state (persisted in localStorage);
  a toggle button in the `TopBar` shows/hides the sidebar and drops the content's left margin —
  standard open/close behaviour.
- **Dev-gated the "Submit test alert" affordance on the Queue** too (header button + empty-state
  action), matching the dashboard — hidden in production builds, visible in the demo (`npm run dev`).

**Logical inconsistency surfaced (no code fix — it's a workflow truth):** the DB has 15 APPROVED,
1 FAILED, **0 REJECTED** for TEN-0005. Under `AUTO_APPROVE_SARS`, an alert is APPROVED before any human
can act, so **reject/pending are unreachable** → the Queue's "Pending" and "Rejected" tabs are always
empty. The "rejected SAR not showing" was not a bug — nothing was rejected. (Left the tabs since they
work if auto-approve is turned off.)

Verified: `tsc --noEmit` clean, backend compiles, `/tenant/usage` returns the new fields
(tokens_used 35545 · requests 13 · failed 1).

---

## 2026-07-04 — Customer dashboard: content-representation pass (roadmap #4, design untouched)

Per user — fix how the tenant `/dashboard` represents content, without changing the UI design, and
only where it helps. Five changes, no layout/styling changes:

- **Greeting subline** no longer assumes manual review (auto-approve keeps "pending" ~0). Shows real
  activity: *"N SARs filed · M alerts screened this month"* (or *"N alerts awaiting review"* in
  manual mode / *"No alerts yet this month"* when empty).
- **"Submit test alert" button** is a dev/demo affordance, now `import.meta.env.DEV`-gated: visible in
  the demo (runs `npm run dev`), never in a production build.
- **Stat band:** replaced the "Pending review" cell (≈0 under auto-approve) with **"Cleared — no SAR"**
  (`false_positives_cleared`) — meaningful in both modes; pending is surfaced in the subline instead.
- **Trend chart** was a duplicate of Usage's daily-alerts area. Differentiated it: retitled
  *"Activity — last 14 days"* and overlaid a second series **SARs filed** (`approved`, already in the
  data) with a legend + two-series tooltip — now an activity view, not a clone.
- **Rule pills** rendered raw ids in mono (`STRUCTURING`, `HIGH_RISK_TYPE`). Added `prettyRule()` in
  `components/ui/Badge.tsx` → human labels ("Structuring", "High-risk type", …) in a readable sans
  pill. Shared component, so it also cleans up the Queue.

Verified `tsc --noEmit` clean. Frontend hot-reloads.

---

## 2026-07-04 — Portal fallacy fixes (roadmap #4, layouts untouched)

Per user: fix the logical fallacies on the tenant portal but do NOT change the dashboard's
basic design. (The dashboard/usage pages share ~3 stats + the daily-alerts chart, but removing
that overlap is a layout change, so it was deliberately left alone.)

- **Usage "PDF" button was fake** — it toasted *"PDF generation ... available after integration"*
  though SAR PDFs are fully integrated. Now it really downloads: new `downloadSarPdf(sarId)` in
  `api/tenant.ts` fetches `/files/sar/<id>.pdf` (tenant-authenticated, absolute URL through the
  same axios client so the JWT is attached) as a blob and saves `SAR-<id>.pdf`. Verified: authed
  200 application/pdf, unauth 401.
- **"Avg. review time" → "Avg. processing time"** on both Dashboard and Usage. The metric is
  `avg(reviewed_at - created_at)` over approved alerts; under `AUTO_APPROVE_SARS` that's the ~8s
  ingest→finalize pipeline turnaround, not human review time — the old label implied a human step
  that doesn't happen. (Metric unchanged; label made honest and mode-agnostic.)

Deliberately left (would change the design / are actually accurate): the duplicated daily-alerts
chart across both pages, the "Pending review" stat (genuinely 0 under auto-approve), and the
"False Positives Cleared" wording. Revisit if a fuller dashboard/usage redesign is wanted.

---

## 2026-07-04 — SAR narrative polish + Groq/Gemini provider switch (roadmap #1)

**Narrative quality (applied + verified live).** Three prompt fixes in `llm_agent.build_sar_prompt`:
(1) a mandatory NARRATIVE STYLE rule — masked placeholder tokens (USR_/ACC_/CID_/IP_/DEV_) must
NEVER appear in prose; refer to parties by role; (2) `recommended_action` must be specific and
CITE policy sections (§5.4 timeliness, §5.2 escalation, EDD) instead of a generic one-liner;
(3) trim opening redundancy. Verified: a live SAR now reads *"The customer initiated an outbound
international wire transfer of INR 945,000 to a counterparty at an unknown institution..."* — zero
masked tokens, 5 correctly-cited indicators, an actioned+cited recommendation.

**Provider failover (Groq primary → Gemini fallback).** Free-tier caps kept blocking generation, so
the LLM call now retries across providers: `LLM_PROVIDER` (primary, default "groq") →
`LLM_FALLBACK_PROVIDER` (e.g. "gemini") if the primary raises (rate/token cap, error, empty reply).
`llm_agent._call_provider` does one provider (Groq SDK vs Gemini REST with
`thinkingConfig.thinkingBudget=0` so 2.5-flash doesn't spend the output budget on hidden reasoning);
`_chat_completion` runs the primary→fallback chain; `eval/ragas_eval._judge` mirrors it. The SAR
record stores the provider/model that ACTUALLY generated it (so a failover is visible in the audit).

- **Verified:** unit test — primary → `groq/llama-3.3-70b`; force Groq to fail → falls over to
  `gemini/gemini-2.5-flash`. Live SAR → Groq primary, APPROVED, no masked tokens, 5 cited indicators.
  **RAGAS ran FULLY with failover — 8-alert set, 0 skips: Faithfulness 0.880, Answer Relevancy 0.727**
  (earlier single-provider runs stalled at 1/8 on rate limits).
- **Gotcha found:** this machine has a stale/invalid `GEMINI_API_KEY=AIza…` **OS env var** (from the
  shell profile) that pydantic reads BEFORE `.env`, shadowing the good key → `400 "API key not valid"`.
  Launch the backend / run scripts with `unset GEMINI_API_KEY` so the `.env` value wins.
- **.env:** `LLM_PROVIDER=groq`, `LLM_FALLBACK_PROVIDER=gemini`, plus both keys + `GEMINI_MODEL`.

---

## 2026-07-04 — Enriched, regenerable Meridian AML policy (roadmap #2)

The Meridian policy was already solid (sections 4.1-4.8 mapped to the engine with exact thresholds)
but was a static, source-less 6-page PDF with a mojibake bullet glyph. Enriched it and made it
regenerable.

- **New build script `scripts/build_meridian_policy.py`** (reportlab) — the policy is now generated
  from versioned source, not a black-box PDF. Re-run + re-index anytime.
- **Content (v3.2 → v4.0, 6 → 9 pages):** every typology 4.1-4.8 now has a **"Red-flag indicators"
  bullet list + a "Detection threshold" + an "Illustrative example" + its goAML indicator code**
  (STRUCTURING_BELOW_THRESHOLD … HIGH_COMPOSITE_RISK_SCORE, matching `goaml_builder.INDICATOR_MAP`).
  Added §2.3 model governance, §3.6 sanctions/watchlist screening, §4.9 mule accounts, and an
  **Appendix A** typology→goAML reference table. The exact rule thresholds are unchanged, so the
  engine/citation mapping still holds.
- **Encoding fixed:** amounts use "Rs." (core PDF fonts lack a ₹ glyph) and bullets use an ASCII
  marker (reportlab's "•" embeds without a ToUnicode map → mojibake in extracted chunks). Verified:
  zero mojibake/PUA chars in the extracted text.
- **Re-indexed via the live upload endpoint** (not `seed_policy.py`, to avoid a 2nd process touching
  the Chroma DB the backend holds open): **28 → 32 chunks**. Old policy backed up to
  `policy_v3.2_backup.pdf`.
- **Verified:** a fresh SAR over the 32-chunk doc → 5/5 indicators, correct sections
  (4.1/4.5/4.6/4.7/4.8), no parse error, no "Aegis". To regenerate: `python
  scripts/build_meridian_policy.py` then re-upload (portal) or `seed_policy.py TEN-0005 <pdf>`.

---

## 2026-07-04 — SAR quality: feed fired rules to the LLM + harden JSON parsing (roadmap #1)

Two coupled generation-quality fixes.

**(a) Pass the deterministic rule-engine findings into generation.** Previously `generate_sar_core`
got only the masked payload + risk score, so the LLM *re-derived* which indicators applied — and
occasionally mislabeled/mis-cited them (seen: composite-risk-score cited §4.6 instead of §4.8).
Now the fired `compliance_matches` (rule name + confidence + evidence) are formatted into a trusted
**"DETECTED COMPLIANCE INDICATORS"** block, injected AFTER `<<END DATA>>` (they're rule-engine
output, not attacker payload). The prompt instructs the model to report EXACTLY those indicators,
one per fired rule, each matched to its section.
- Threaded through `llm_agent._format_compliance_evidence` → `build_sar_prompt(..., compliance_evidence)`
  → `generate_sar_core(..., compliance_results=None)` → `generate_sar` (queries ComplianceMatch) and
  `eval/ragas_eval.py` (passes `fired`). All new params default-safe; other callers unaffected.

**(b) Harden the structured-JSON parser.** The richer output surfaced a latent fragility: LLMs
intermittently emit JSON with trailing prose / a closing note / trailing commas / ``` fences, and
the strict `json.loads` in `_parse_response` failed on them — silently dropping the ENTIRE
structured SAR (`{"error":"Failed to parse structured output"}`, empty indicators in the UI). New
`_parse_json_lenient` isolates the outermost `{...}` object and tolerates fences + trailing commas.
Unit-checked against clean/fenced/trailing-prose/trailing-comma/preamble/₹-symbol/empty inputs — all parse.

**Verified live:** 3 fresh SARs → indicator count == fired-rule count (4/4, 5/5, 5/5), **zero parse
errors**, every indicator cited to the correct section (4.1/4.3/4.5/4.6/4.7/**4.8** — the §4.8
composite-risk-score mapping now correct). A clean RAGAS re-run afterward (new Groq
key, enriched v4.0 policy, 8-alert sample, 7 scored / 1 throttled) gave **Faithfulness 0.977,
Answer Relevancy 0.735** (faithfulness range 0.91-1.00 — a credible spread, not a flat 1.0). (Note:
RAGAS makes ~4 Groq calls/alert, so large sets can throttle — a known high-volume caveat.)

---

## 2026-07-04 — SAR quality: fix hardcoded "Aegis Bank" citation (roadmap #1)

The SAR citations always read *"Aegis Bank AML Policy, Section 4.1"* regardless of tenant. Root
cause was NOT the policy PDF (the Meridian policy is correctly branded — 0 "aegis" / 10
"meridian", clean 4.1–5.5 sections) but a **hardcoded example in the generation prompt**
(`llm_agent.build_sar_prompt`, the `regulation` field example literally showed
`'Aegis Bank AML Policy, Section 4.1'`).

- **Fix:** citations are now **section-based**, taken from the retrieved context — e.g.
  `"Section 4.1 (Structuring and Smurfing)"`. The prompt instructs the model to use the exact
  section number + heading from the REGULATORY CONTEXT and to refer to the source only as "the
  AML/CFT Policy" — never inventing a bank/document name. (Deliberately no bank name injected: the
  policy's running header carrying the bank name is stripped during ingestion, so asserting
  "Meridian Bank" could read as an ungrounded claim and hurt faithfulness. Section numbers +
  headings ARE in the chunks, so they stay fully grounded.)
- **Verified live:** a fresh SAR cites `Section 4.1/4.5/4.7…`, zero "Aegis" in narrative or
  citations. **RAGAS on TEN-0005 (6 alerts): Faithfulness 0.981, Answer Relevancy 0.765** (was
  1.000/0.740 on 3) — grounding held, relevancy up, and the spread (one SAR at 0.889) shows the
  metric discriminates.

> Residual SAR-quality item (next lever): the model doesn't receive the deterministically-fired
> compliance rules — it re-derives indicators from the raw masked payload, so a citation is
> occasionally mis-mapped (seen: the composite-risk-score indicator cited §4.6 High-Velocity
> instead of §4.8 Composite Risk Scoring). Fix = pass the fired `compliance_matches` (rule names +
> evidence) into `generate_sar_core` as trusted evidence so indicators/citations match the engine.

---

## 2026-07-04 — SAR Workspace shows a proper, read-only SAR (Aegis frontend + 1 backend field)

The officer workspace right panel used to render **only the masked narrative paragraph** — the
structured half of the SAR (cited indicators + recommended action) was generated and stored in
`sar_drafts.draft_structured` but never sent to the UI, so it read like a wall of text. And since
`AUTO_APPROVE_SARS` is on, the edit/approve/reject affordances were dead controls.

- **Backend:** `routers/alerts.py` queue-detail now includes `sar_draft.draft_structured`
  (`{key_indicators:[{indicator, regulation, description}], recommended_action}`; derived from
  masked data → no real PII). One-line add; requires an Aegis backend restart.
- **Frontend (`SARWorkspace.tsx`):** the panel now renders a proper report — a
  **"Suspicious Transaction Report" title + STR badge**, the **Narrative**, a **Key indicators**
  list (each with its cited policy section as a mono chip), and **Recommended action**. The
  narrative stays editable **only** while an officer review is genuinely pending (manual mode);
  once APPROVED it's fully read-only and **Approve/Reject are hidden** (Preview — real PII behind
  the confidential gate — stays). Older drafts with null/malformed `draft_structured` degrade
  gracefully (narrative only). `types.ts` gains `SARStructured` / `SARKeyIndicator`.
- Verified: `tsc --noEmit` clean (Aegis frontend), and the live API returns `draft_structured`
  with 3 cited indicators for the sample alert.

> Noted for later (roadmap #2, policy PDF): the LLM cites *"Aegis Bank AML Policy, Section 4.x"*
> — the Meridian tenant's policy/citations should be branded "Meridian" for a fully consistent demo.

---

## 2026-07-04 — Secure PDF delivery: bank keeps its own copy (Aegis + bank)

Per user: *"do the secure pdf thing so that the bank is not dependent on Aegis for the pdf."*
The bank no longer hot-links Aegis's PDF; the bytes are pushed to it and it self-serves.

**Aegis (backend).**
- `app/services/sar_delivery.py::finalize_and_deliver` now base64-encodes the rendered PDF and
  adds **`pdf_base64`** (+ `pdf_filename`) to the approval webhook payload, alongside the existing
  `goaml_str` / `pdf_url`. The **audit-sink copy strips `pdf_base64`** so the whole PDF isn't
  duplicated into the `webhook_sink_events` JSONB on every approval.
- `app/routers/files.py` — `GET /files/sar/<id>.pdf` is **no longer open**: it now requires a
  tenant JWT (`get_compliance_user`) and only serves a SAR belonging to the caller's tenant
  (super-admin may fetch any; cross-tenant → 404). Safe because the Aegis dashboard never used
  this URL — only the bank did, and the bank no longer does.

**Bank (backend).**
- Flyway `V5__report_pdf.sql` adds `sar_reports.pdf_bytes BYTEA`; `SarReport` gains `pdfBytes`.
- `ReportService.storeWebhook` decodes `pdf_base64` → `pdfBytes` (defensive: bad/missing base64
  just stores null, never throws). `ReportView` gains a `hasPdf` flag.
- New endpoint `GET /api/admin/reports/{id}/pdf` (admin-only) serves the bank's **own** stored
  PDF bytes as `application/pdf`.

**Bank (frontend).** `InboxPage.tsx` + `MonitoringPage.tsx` Download/Open now fetch the blob from
the bank's own `/api/admin/reports/{id}/pdf` (auth'd) instead of Aegis's URL, gated on `hasPdf`.
`api.ts` gains `reportPdfBlob(id)` + `ReportView.hasPdf`.

**Also fixed (pre-existing, unblocked test suite):** `AegisClientTest` still called the old
1-arg `AegisClient(props)` constructor — broken since the Content-Length/411 fix added the
`ObjectMapper` param; updated both call sites. Bank suite now green: **29 → 31 tests pass**
(added 2 for the `pdf_base64` decode round-trip).

**To activate:** restart the **Aegis backend** (no `--reload`) and the **bank backend** (Flyway
applies V5). Reports received *before* this change have `pdf_bytes = NULL` → show "PDF
unavailable"; every new report carries its PDF. Verified: py-compile (Aegis), `mvn test` 31/31
(bank), `tsc --noEmit` clean (bank frontend).

---

## 2026-07-04 — Split monitoring: Alert Transactions vs General (bank frontend)

Per user (a real bank wouldn't surface *every* txn to the compliance queue):
- **Alert Transactions** (`/admin`) — only escalated txns (`status ∈ SENT/PROCESSING/
  REPORT_RECEIVED/SEND_FAILED`); the AML queue, with inline **View report** + **Download PDF**.
- **General Transaction Monitoring** (`/admin/all`) — every customer txn + its risk-check outcome.
- One `MonitoringPage` with a `mode: "alerts" | "all"` prop; routes in `App.tsx`; nav in
  `AdminLayout.tsx`. Verified: 23 total / 13 alerts.

Also added **`DEMO_GUIDE.md`** (Aegis side) — how to start all 4 services, all logins, the live
demo flow, **and the eval tests** (`ir_metrics.py` top-k / Recall@8=1.0 · `ragas_eval.py`
Faithfulness≈0.89) to demonstrate RAG quality when presenting.

**PDF storage (answer to a question):** SAR PDFs live on the **Aegis** side
(`backend/storage/clients/<tenant>/sar/<id>.pdf`, served at `/files/sar/<id>.pdf`). The bank stores
only the goAML JSON + `pdf_url` in its `mockbank` DB; Download fetches from Aegis on demand.

---

## 2026-07-04 — Reports inline in Transaction Monitoring (bank frontend)

Per user: surface the finished report **inside the monitoring rows** instead of a separate tab.
- `mock-bank .../admin/MonitoringPage.tsx` now fetches both `/admin/monitoring` and
  `/admin/reports`, matches them by `alertId`, and for each `report received` row shows a
  **"View report"** button (opens a modal with narrative + goAML fields + indicators + raw JSON,
  a **Download PDF ↓** button, and **File with FIU**) plus an inline **Download PDF ↓**.
- `mock-bank .../admin/AdminLayout.tsx` — removed the **"Report Inbox"** nav tab (the route/page
  still exist, just not linked). Verified: all 6 report-received rows matched a report.

---

## 2026-07-04 — Auto-approve SARs + downloadable PDF on the bank inbox

**Auto-approve (Aegis backend).** Per the product decision that the *bank's* admin makes the
final file-with-FIU call, the Aegis compliance-officer approval step is now automatic: a
generated SAR is finalized (rehydrate PII → goAML → PDF) and delivered to the bank webhook
immediately, without a manual click on the Aegis side.
- New setting `AUTO_APPROVE_SARS: bool = True` in `config.py` (set `False` to restore manual
  officer review).
- New shared service `app/services/sar_delivery.py` — `finalize_and_deliver(alert, db,
  approver_name, approver_user_id=None)` holds the finalize+deliver logic.
- `routers/alerts.py` `approve_alert` (manual endpoint) and `routers/ingest.py`
  `process_alert_background` (auto path) both call it — no duplicated logic.
- Auto-approved reports are stamped `approved_by = "Automated compliance review (auto-approved)"`
  and `reviewed_by = NULL`.
- Verified: a bank transaction reaches the bank inbox as `REPORT_RECEIVED` in ~8s with **no
  manual approval**. Backend security (JWT, PII masking, rate limiting, etc.) unchanged.

**Downloadable PDF (bank frontend).** The mock-bank Report inbox now has a **"Download PDF ↓"**
button (plus "Open ↗") — `admin/InboxPage.tsx` fetches the PDF from Aegis as a blob and saves it
as `SAR-<sarId>.pdf`. Works cross-origin because Aegis CORS already allows `http://localhost:5174`
(verified: GET returns 200 + `Access-Control-Allow-Origin: http://localhost:5174`).

---

## 2026-07-04 — Session-scoped login on the Aegis dashboard (frontend only)

**Problem:** the dashboard login was persisted in **`localStorage`**, so once you signed in,
the session survived closing the tab/browser — the dashboard (client *or* admin) could be
reached again without re-entering the password. Not safe for a shared/demo machine.

**Change (frontend only — backend security untouched):** moved the auth session from
`localStorage` to **`sessionStorage`**.
- `frontend/src/store/auth.ts` — zustand `persist` now uses
  `createJSONStorage(() => sessionStorage)`; the refresh token is stored in `sessionStorage`.
- `frontend/src/api/client.ts` — the silent-refresh reads/writes the refresh token from
  `sessionStorage`.

**Result:** closing the tab/browser **clears the session**, so returning to the dashboard
requires signing in again. Navigating/refreshing *within* the same tab keeps you logged in
(normal UX). No backend change — JWT (access/refresh), refresh-token rotation, rate limiting,
PII handling, etc. are all unchanged.

**To apply:** hard-refresh the dashboard tab (Ctrl+Shift+R) once (the store re-reads from the
new storage). Any stale `localStorage` entry is simply ignored.

**Stricter options available if wanted (not yet done):**
- *In-memory only* → logged out on every full page reload (harsher UX, max strictness).
- *Idle timeout* → auto-logout after N minutes of inactivity.

---

## Earlier work (see `MOCKBANK_INTEGRATION.md` for detail)

- **2026-07-04** — Mock bank integrated end-to-end; onboarded Meridian Bank as its own Aegis
  tenant **TEN-0005** via the real signup → super-admin-approve flow; fixed the bank's
  `AegisClient` Content-Length (411) bug; installed portable Maven; created the `mockbank` DB;
  uploaded a rebranded Meridian AML policy; wired the webhook; verified the full loop.
- **Earlier** — goAML indicator mapping fix; answer-relevancy prompt-scoping + metric fix
  (Faithfulness ≈0.89); RAG_MASTER.md deleted; MOCKBANK_BRIEF.md written. See
  `PROJECT_REFERENCE.md` §18 change log.
