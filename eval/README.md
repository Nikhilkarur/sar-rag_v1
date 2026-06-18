# Retrieval Evaluation (per-tenant)

Deterministic IR metrics (Precision@k, Recall@k, nDCG@k, MRR) — **no LLM**.
Full detail in the root `RAG_MASTER.md`.

## Structure

Per-tenant, because ground-truth labels are document-specific. The dummy/test
client is **`client_0`** (named 0 so real clients start at `client_1`).

```
eval/
├── ir_metrics.py
└── tenants/
    └── client_0/                 # DUMMY test client (synthetic Aegis)
        ├── config.json           # policy + schema + rule->section answer key
        ├── policy.pdf            # this client's AML policy
        └── alerts/*.json         # this client's test alerts
```

## Run

```bash
python eval/ir_metrics.py            # all tenants, per-tenant + overall
python eval/ir_metrics.py client_0   # just the dummy client
```

## Add a real client (e.g. client_1)

1. `mkdir eval/tenants/client_1/alerts`
2. Drop their policy as `eval/tenants/client_1/policy.pdf`
3. Add `eval/tenants/client_1/config.json` with *their* `rule_to_section`
   (section numbers as they appear in *their* policy) + `schema_preset`.
4. Add test alerts in `eval/tenants/client_1/alerts/`.
5. Re-run `python eval/ir_metrics.py` — it auto-discovers the new tenant.

## Ground truth

For each alert we run the REAL rule engine; every fired rule has one correct
section (`rule_to_section` in that tenant's config) + `5.1` always. The metric
checks whether retrieval surfaced those sections and how highly it ranked them.

## Reset

`python scripts/reset.py` clears runtime artifacts; `--barebone` removes all dummy
data (incl. `client_0`). See `RAG_MASTER.md` §9.
