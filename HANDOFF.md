# Aegis — Handoff (2026-07-05)

Short continuity note. Full history: `IMPROVEMENTS_LOG.md`. Run everything: `DEMO_GUIDE.md`.

## State
All 4 services run (Aegis API :8000, dashboard :5173, bank API :8001, bank UI :5174). Backend runs
**without `--reload`** — restart after any `backend/` edit (`unset GEMINI_API_KEY` first). Finish
frontend changes with `npx tsc --noEmit`. Only live tenant is **TEN-0005 (Meridian, comped/free)**
+ `client_0` (eval fixture). Logins in `DEMO_GUIDE.md`.

## Just fixed (context)
- **SAR PDFs no longer persisted to disk.** They carry real PII; now rendered in-memory, base64'd to
  the webhook, and re-rendered on demand for `/files/sar`. Deleted leaked PDFs under `TEN-0005/`.
- Clarified: **live alerts live ONLY in Postgres** (`alerts` table). `storage/clients/<id>/` is an
  EVAL-only folder; alert JSONs there come from the manual `scripts/export_alerts.py`, not the live
  path. That's why TEN-0005 had 8 alert files but 16 SAR PDFs.
- Also this session: purged vendor model names from dashboards; fixed risk-score double-counting;
  fixed false "+100% vs last month"; comped-tenant billing; new admin Billing page.

## Next agent — DO THIS
1. **Hunt for more issues like the PII-on-disk leak and logical/math edge cases** across the app
   (data written to disk, masked-vs-rehydrated confusion, stats/billing arithmetic, empty/zero/negative
   states, cross-dashboard inconsistencies). **When you find one, DO NOT just fix it — surface it to the
   user and ask how they want it solved.** Known-but-deferred: officer Review Queue shows synthetic
   test alerts by default (`/alerts/queue?include_synthetic=true`).
2. **Then: the RAG experiment.** Run different transaction types through ingest (clean/below-threshold,
   borderline, clearly-suspicious, each typology) and observe how the SAR generation behaves — is it
   grounded/correct or hallucinating? Non-suspicious (<75) txns bypass RAG+LLM entirely (deterministic
   `COMPLETED_CLEAN`), so focus on whether the suspicious-path narratives stay faithful to the retrieved
   policy + rule evidence. Use the portal simulator or `POST /api/v1/ingest/` (see `MOCKBANK_INTEGRATION.md`).
