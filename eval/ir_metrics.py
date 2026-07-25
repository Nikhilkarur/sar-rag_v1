"""
Deterministic retrieval evaluation — Precision@k, Recall@k, nDCG@k, MRR.
NO LLM. Pure arithmetic against ground-truth labels we control.

Reads the UNIFIED per-client storage: backend/storage/clients/<client_id>/
  ├── policy.pdf          (indexed into a temp collection for scoring)
  ├── alerts/*.json       ({"raw_payload": {...}} — mock seeds + live-logged requests)
  └── eval.json           (answer key: schema_preset, rule_to_section, always_relevant)

A client is scored only if it has an eval.json (IR needs the answer key). Real clients
get scored once you add their eval.json. Mock client_0 ships with one.

  python eval/ir_metrics.py            # all clients that have an eval.json
  python eval/ir_metrics.py client_0   # one client
"""
import glob
import json
import math
import os
import re
import sys
import tempfile

# Stabilize the native ML stack BEFORE torch/sentence-transformers load (mirrors
# embeddings.py / ragas_eval.py). Without these — KMP_DUPLICATE_LIB_OK especially —
# loading torch after chromadb segfaults on this Windows/CPU env.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

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

CLIENTS_DIR = os.path.join(BACKEND, "storage", "clients")
KS = [3, 5, 8]
_SEC_NUM = re.compile(r"^\s*(\d+(?:\.\d+)?)")


def section_number(h):
    m = _SEC_NUM.match(h or "")
    return m.group(1) if m else h


def precision_at_k(r, rel, k):
    return sum(1 for s in r[:k] if s in rel) / k if k else 0.0

def recall_at_k(r, rel, k):
    return sum(1 for s in r[:k] if s in rel) / len(rel) if rel else 0.0

def ndcg_at_k(r, rel, k):
    dcg = sum((1.0 if r[i] in rel else 0.0) / math.log2(i + 2) for i in range(min(k, len(r))))
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(k, len(rel))))
    return dcg / ideal if ideal else 0.0

def mrr(r, rel):
    for i, s in enumerate(r):
        if s in rel:
            return 1.0 / (i + 1)
    return 0.0

def dedup(seq):
    seen, out = set(), []
    for s in seq:
        if s not in seen:
            seen.add(s); out.append(s)
    return out


def evaluate_client(client_dir):
    cfg = json.load(open(os.path.join(client_dir, "eval.json"), encoding="utf-8"))
    cid = os.path.basename(client_dir)
    policy = os.path.join(client_dir, "policy.pdf")
    fm = SCHEMA_PRESETS[cfg["schema_preset"]]["field_map"]
    rule_to_section = cfg["rule_to_section"]
    always = set(cfg.get("always_relevant", []))
    alerts = sorted(glob.glob(os.path.join(client_dir, "alerts", "*.json")))
    if not os.path.isfile(policy) or not alerts:
        print(f"\n#### {cid}: missing policy.pdf or alerts — skipped"); return None

    dis.index_document(cid, dis.build_chunks(policy, f"{cid} policy", "policy.pdf", "policy.pdf"))
    print(f"\n######## CLIENT: {cid} ({len(alerts)} alerts) ########")
    rows, means = [], {f"P@{k}": [] for k in KS}
    means.update({f"nDCG@{k}": [] for k in KS}); means["Recall@8"] = []; means["MRR"] = []

    for path in alerts:
        rec = json.load(open(path, encoding="utf-8"))
        raw = rec.get("raw_payload", rec)
        # Prefer the live-computed normalized payload (exported from the DB with the
        # tenant's OWN schema). Only client_0 fixtures lack it → normalize with the preset.
        norm = rec.get("normalized_payload") or normalize_payload(raw, fm)
        fired = [r for r in analyze(norm) if r["triggered"]]
        relevant = {rule_to_section[r["rule_name"]] for r in fired
                    if r["rule_name"] in rule_to_section} | always
        comp = [{"rule_name": r["rule_name"], "triggered": True} for r in fired]
        hits = retrieve_regulatory_context(cid, {"transaction_type": norm.get("transaction_type")}, comp, top_k=8)
        retrieved = dedup([section_number(h["metadata"]["section_heading"]) for h in hits])
        row = {"alert": os.path.basename(path), "relevant": sorted(relevant), "retrieved": retrieved[:8]}
        for k in KS:
            row[f"P@{k}"] = precision_at_k(retrieved, relevant, k)
            row[f"nDCG@{k}"] = ndcg_at_k(retrieved, relevant, k)
            means[f"P@{k}"].append(row[f"P@{k}"]); means[f"nDCG@{k}"].append(row[f"nDCG@{k}"])
        row["Recall@8"] = recall_at_k(retrieved, relevant, 8); row["MRR"] = mrr(retrieved, relevant)
        means["Recall@8"].append(row["Recall@8"]); means["MRR"].append(row["MRR"])
        rows.append(row)
        print(f"--- {row['alert']} ---  relevant={row['relevant']}  P@3={row['P@3']:.2f} "
              f"Recall@8={row['Recall@8']:.2f} nDCG@8={row['nDCG@8']:.2f} MRR={row['MRR']:.2f}")

    agg = {m: (sum(v) / len(rows) if rows else 0.0) for m, v in means.items()}
    print(f"  >> {cid} MEAN: P@3={agg['P@3']:.3f} nDCG@8={agg['nDCG@8']:.3f} "
          f"Recall@8={agg['Recall@8']:.3f} MRR={agg['MRR']:.3f}")
    return {"client_id": cid, "per_alert": rows, "aggregate": agg}


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    dirs = sorted(d for d in glob.glob(os.path.join(CLIENTS_DIR, "*"))
                  if os.path.isfile(os.path.join(d, "eval.json")))
    if only:
        dirs = [d for d in dirs if os.path.basename(d) == only]
    if not dirs:
        print(f"No clients with eval.json in {os.path.relpath(CLIENTS_DIR, ROOT)}"
              + (f" matching '{only}'" if only else "")
              + ". (Add an eval.json answer key to score a client.)")
        return

    results = [r for r in (evaluate_client(d) for d in dirs) if r]
    print("\n" + "=" * 56 + "\nOVERALL (mean across clients)\n" + "=" * 56)
    metrics = ["P@3", "P@5", "P@8", "nDCG@3", "nDCG@5", "nDCG@8", "Recall@8", "MRR"]
    overall = {m: (sum(r["aggregate"][m] for r in results) / len(results) if results else 0.0) for m in metrics}
    for m in metrics:
        print(f"  {m:9} = {overall[m]:.3f}")
    out = os.path.join(ROOT, "outputs", "ir_metrics.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({"clients": results, "overall": overall}, open(out, "w", encoding="utf-8"), indent=2)
    print(f"\nSaved -> {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
