"""
Deterministic retrieval evaluation — Precision@k, Recall@k, nDCG@k, MRR.
NO LLM. Pure arithmetic against ground-truth labels we control.

PER-CLIENT: each client has its OWN policy.pdf, alerts, and answer key
(config.json -> rule_to_section), because section numbers differ between clients'
policy documents. Mock clients live in testing/clients/, real clients in
production/clients/. Retrieval is already isolated per tenant (separate Chroma
collections); this harness keeps the labels isolated too.

  python eval/ir_metrics.py             # all MOCK clients (testing/) + overall
  python eval/ir_metrics.py client_0    # one mock client
  python eval/ir_metrics.py --prod      # all REAL clients (production/)
"""
import glob
import json
import math
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND)

os.environ.setdefault("CHROMA_PERSIST_DIR", tempfile.mkdtemp(prefix="chroma_ir_"))
import app.services.chroma_client as cc  # noqa: E402
cc._PERSIST_DIR = os.environ["CHROMA_PERSIST_DIR"]

from app.services.schema_normalizer import normalize_payload          # noqa: E402
from app.services.compliance_analyzer import analyze                  # noqa: E402
from app.data.schema_presets import SCHEMA_PRESETS                    # noqa: E402
from app.services import document_ingestion_service as dis            # noqa: E402
from app.services.rag_retrieval_service import retrieve_regulatory_context  # noqa: E402

# Mock clients live in testing/clients; real clients in production/clients.
# Default = mock (testing). Pass --prod to evaluate real clients instead.
MOCK_DIR = os.path.join(ROOT, "testing", "clients")
PROD_DIR = os.path.join(ROOT, "production", "clients")
KS = [3, 5, 8]
_SEC_NUM = re.compile(r"^\s*(\d+(?:\.\d+)?)")


def section_number(heading):
    m = _SEC_NUM.match(heading or "")
    return m.group(1) if m else heading


# ---- pure-math metrics (binary relevance) ----
def precision_at_k(retrieved, relevant, k):
    return sum(1 for s in retrieved[:k] if s in relevant) / k if k else 0.0

def recall_at_k(retrieved, relevant, k):
    return sum(1 for s in retrieved[:k] if s in relevant) / len(relevant) if relevant else 0.0

def ndcg_at_k(retrieved, relevant, k):
    dcg = sum((1.0 if retrieved[i] in relevant else 0.0) / math.log2(i + 2)
              for i in range(min(k, len(retrieved))))
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(k, len(relevant))))
    return dcg / ideal if ideal else 0.0

def mrr(retrieved, relevant):
    for i, s in enumerate(retrieved):
        if s in relevant:
            return 1.0 / (i + 1)
    return 0.0

def dedup(seq):
    seen, out = set(), []
    for s in seq:
        if s not in seen:
            seen.add(s); out.append(s)
    return out


def evaluate_tenant(tenant_dir):
    cfg = json.load(open(os.path.join(tenant_dir, "config.json"), encoding="utf-8"))
    tid = cfg["tenant_id"]
    policy = os.path.join(tenant_dir, cfg["policy_pdf"])
    field_map = SCHEMA_PRESETS[cfg["schema_preset"]]["field_map"]
    rule_to_section = cfg["rule_to_section"]
    always = set(cfg.get("always_relevant", []))
    alerts = sorted(glob.glob(os.path.join(tenant_dir, "alerts", "*.json")))

    # index THIS tenant's policy into ITS OWN collection
    chunks = dis.build_chunks(policy, cfg.get("display_name", tid),
                              cfg["policy_pdf"], f"{tid}-policy")
    dis.index_document(tid, chunks)

    print(f"\n############ TENANT: {tid} "
          f"({len(alerts)} alerts, {len(chunks)} chunks) ############")
    rows = []
    means = {f"P@{k}": [] for k in KS}
    means.update({f"nDCG@{k}": [] for k in KS})
    means["Recall@8"] = []; means["MRR"] = []

    for path in alerts:
        raw = json.load(open(path, encoding="utf-8"))
        norm = normalize_payload(raw, field_map)
        fired = [r for r in analyze(norm) if r["triggered"]]
        relevant = {rule_to_section[r["rule_name"]] for r in fired
                    if r["rule_name"] in rule_to_section} | always

        masked = {"transaction_type": norm.get("transaction_type")}
        comp = [{"rule_name": r["rule_name"], "triggered": True} for r in fired]
        hits = retrieve_regulatory_context(tid, masked, comp, top_k=8)
        retrieved = dedup([section_number(h["metadata"]["section_heading"]) for h in hits])

        row = {"alert": os.path.basename(path), "relevant": sorted(relevant),
               "retrieved": retrieved[:8]}
        for k in KS:
            row[f"P@{k}"] = precision_at_k(retrieved, relevant, k)
            row[f"nDCG@{k}"] = ndcg_at_k(retrieved, relevant, k)
            means[f"P@{k}"].append(row[f"P@{k}"]); means[f"nDCG@{k}"].append(row[f"nDCG@{k}"])
        row["Recall@8"] = recall_at_k(retrieved, relevant, 8)
        row["MRR"] = mrr(retrieved, relevant)
        means["Recall@8"].append(row["Recall@8"]); means["MRR"].append(row["MRR"])
        rows.append(row)

        print(f"--- {row['alert']} ---")
        print(f"  relevant : {row['relevant']}")
        print(f"  retrieved: {row['retrieved']}")
        print(f"  P@3={row['P@3']:.2f} P@5={row['P@5']:.2f} P@8={row['P@8']:.2f} "
              f"Recall@8={row['Recall@8']:.2f} nDCG@8={row['nDCG@8']:.2f} MRR={row['MRR']:.2f}")

    agg = {m: (sum(v) / len(rows) if rows else 0.0) for m, v in means.items()}
    print(f"  >> {tid} MEAN: P@3={agg['P@3']:.3f} nDCG@8={agg['nDCG@8']:.3f} "
          f"Recall@8={agg['Recall@8']:.3f} MRR={agg['MRR']:.3f}")
    return {"tenant_id": tid, "per_alert": rows, "aggregate": agg}


def main():
    # python eval/ir_metrics.py [client_id] [--prod]
    prod = "--prod" in sys.argv
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    only = positional[0] if positional else None
    base = PROD_DIR if prod else MOCK_DIR
    print(f"Evaluating {'PRODUCTION' if prod else 'MOCK (testing)'} clients in {os.path.relpath(base, ROOT)}")
    tenant_dirs = sorted(d for d in glob.glob(os.path.join(base, "*"))
                         if os.path.isfile(os.path.join(d, "config.json")))
    if only:
        tenant_dirs = [d for d in tenant_dirs if os.path.basename(d) == only]
    if not tenant_dirs:
        print(f"No clients found in {os.path.relpath(base, ROOT)}"
              + (f" matching '{only}'" if only else "")
              + (". (production/ is empty until you add real clients.)" if prod else ""))
        return

    results = [evaluate_tenant(d) for d in tenant_dirs]

    # overall = mean of each tenant's mean (so every client weighs equally)
    print("\n" + "=" * 60 + "\nOVERALL (mean across tenants)\n" + "=" * 60)
    metrics = ["P@3", "P@5", "P@8", "nDCG@3", "nDCG@5", "nDCG@8", "Recall@8", "MRR"]
    overall = {}
    for m in metrics:
        vals = [r["aggregate"][m] for r in results]
        overall[m] = sum(vals) / len(vals) if vals else 0.0
        print(f"  {m:9} = {overall[m]:.3f}")

    out = os.path.join(ROOT, "outputs", "ir_metrics.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({"tenants": results, "overall": overall},
              open(out, "w", encoding="utf-8"), indent=2)
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()
