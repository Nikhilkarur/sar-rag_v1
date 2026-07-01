# Evaluation — IR metrics + RAGAS

Two evaluators for the RAG pipeline. Full detail in the root `PROJECT_REFERENCE.md`.

- **`ir_metrics.py`** — retrieval quality: Precision@k, Recall@k, nDCG@k, MRR.
  Deterministic, **no LLM**. Needs a hand-labeled answer key (`eval.json`).
- **`ragas_eval.py`** — generation quality: Faithfulness + Answer Relevancy.
  LLM-judge (Groq) + bge embeddings. **Reference-free** — no answer key needed.

## Table of contents

- [Where the data lives (unified per-client storage)](#where-the-data-lives-unified-per-client-storage)
- [The dummy client = client_0](#the-dummy-client--client_0)
- [Run](#run)
- [IR on a real client (optional, manual)](#ir-on-a-real-client-optional-manual)
- [RAGAS on a real client](#ragas-on-a-real-client)
- [Ground truth (IR only)](#ground-truth-ir-only)
- [Results are written to outputs/](#results-are-written-to-outputs)

---

## Where the data lives (unified per-client storage)

Both evaluators read the SAME folders the live system uses — one folder per client
under `backend/`:

```
backend/storage/clients/<client_id>/
├── policy.pdf          # the client's AML policy (indexed into a temp Chroma collection)
├── alerts/*.json       # {"raw_payload": {...}} — transactions to score
├── sar/*.pdf           # generated SARs (live output; not read by the eval)
└── eval.json           # IR answer key (schema_preset + rule_to_section)  — client_0 only
```

`<client_id>` = `client_0` for the dummy/test client, or the tenant public id
(e.g. `TEN-0002`) for a real client.

## The dummy client = `client_0`

`client_0` is the offline test bench — synthetic policy + 5 labeled alerts + an
answer key. Build / rebuild it with the seed tooling (it does NOT touch real clients):

```bash
python scripts/seed_testing.py     # build client_0 (policy.pdf + alerts + eval.json)
python scripts/reset.py --seed     # wipe runtime + rebuild client_0
```

### Full cycle: delete → reseed → eval (the standard sanity check)

```bash
python scripts/reset.py --barebone --seed   # wipe dummy client_0 + rebuild it (real clients kept)
python eval/ir_metrics.py                    # IR — expect Recall@8 = 1.0
python eval/ragas_eval.py client_0           # RAGAS (needs the Groq key)

# (optional) generate a viewable SAR PDF -> client_0/sar/<sar_id>.pdf
python scripts/generate_sar_report.py        # NOT needed for RAGAS — RAGAS makes its own SARs
```

> RAGAS does **not** read the `sar/` folder — it generates a fresh SAR per alert
> internally (`generate_sar_core`) and judges that. So `--barebone` wiping `sar/` is
> irrelevant to the eval; `generate_sar_report.py` is only for producing a PDF to look at.

## Run

```bash
# IR (needs eval.json → client_0 only)
python eval/ir_metrics.py            # every client that has an eval.json
python eval/ir_metrics.py client_0   # just the dummy

# RAGAS (no answer key → any client)   [requires GROQ_API_KEY in backend/.env]
python eval/ragas_eval.py client_0   # the dummy
python eval/ragas_eval.py TEN-0002   # a real client (after exporting its alerts ↓)
```

## IR on a real client (optional, manual)

IR needs an answer key tied to *that client's* policy section numbers, so it's manual
work you only do if you specifically want to grade their retrieval:

1. Put their `eval.json` in `backend/storage/clients/<id>/` with `schema_preset`,
   `rule_to_section` (their policy's section numbers), and `always_relevant`.
2. Make sure their `policy.pdf` and some `alerts/*.json` are present.
3. `python eval/ir_metrics.py <id>` — it auto-discovers any client with an `eval.json`.

## RAGAS on a real client

A real client's alerts live in the Postgres `alerts` table, not on disk. Export a
sample first, then score. The export also writes the **`normalized_payload` +
`masked_payload` the live system already computed with the client's OWN schema**, and
the eval uses those — so it scores exactly what live produced, no matter which schema
(STANDARD_FINTECH / SEBI_BROKER / PAYMENT_GW) the client uses. See `PROJECT_REFERENCE.md` §21.

```bash
python scripts/export_alerts.py TEN-0002 --limit 20            # latest 20: DB alerts -> folder JSON
python scripts/export_alerts.py TEN-0002 --limit 1 --oldest    # just the client's 1st request
python eval/ragas_eval.py TEN-0002                             # score what was exported
```

The folder for `TEN-0002` is created automatically by the export (and by the live
upload) — you never make it by hand.

## Ground truth (IR only)

For each alert we run the REAL rule engine; every fired rule maps to one correct
section (`rule_to_section`) plus `5.1` (always relevant). The metric checks whether
retrieval surfaced those sections and how highly it ranked them.

## Results are written to `outputs/`

`outputs/ir_metrics.json` and `outputs/ragas_metrics.json` (regeneratable; wiped by
`reset.py`).
