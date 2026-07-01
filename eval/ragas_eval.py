"""
Generation-quality evaluation — RAGAS-methodology, implemented natively.

WHY native: the `ragas` pip package (0.4.x) imports a langchain_community path that
was removed in LangChain 1.x, so it won't import on this env. These two metrics are
well-defined LLM-judge procedures, so we implement them directly using OUR stack —
Groq as the judge LLM + bge for embeddings (exactly the components RAGAS would use).

Metrics (both reference-free):
  * Faithfulness     — does the SAR stick to its sources, or hallucinate?
      extract atomic claims from the SAR (Groq) -> for each, is it supported by the
      grounding = (transaction data + retrieved policy chunks)? (Groq) ->
      score = supported / total claims.
  * Answer Relevancy — is the SAR on-topic for the alert?
      generate questions the SAR answers (Groq) -> embed them + the real question
      (bge) -> score = mean cosine similarity to the real question.

Per-client, like ir_metrics.py. Reads the UNIFIED per-client storage:
  backend/storage/clients/<client_id>/
    ├── policy.pdf        (indexed into a temp collection for scoring)
    └── alerts/*.json     ({"raw_payload": {...}} — mock seeds + live-logged requests)

RAGAS is reference-free, so it needs NO answer key — any client with a policy.pdf +
alerts/ is scored (mock client_0 and real TEN-xxxx alike). schema_preset is read from
eval.json if present, else defaults to STANDARD_FINTECH.

  python eval/ragas_eval.py             # all clients with policy.pdf + alerts
  python eval/ragas_eval.py client_0    # one client
"""
import glob
import json
import os
import re
import sys
import tempfile

# Stabilize the native ML stack — the ragas/langchain install bumped numpy/torch,
# which causes intermittent segfaults on this Windows/CPU env. Force single-threaded
# OpenMP + disable tokenizer parallelism BEFORE torch/sentence-transformers load.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)  # load backend/.env (GROQ key)

os.environ.setdefault("CHROMA_PERSIST_DIR", tempfile.mkdtemp(prefix="chroma_ragas_"))
import app.services.chroma_client as cc  # noqa: E402
cc._PERSIST_DIR = os.environ["CHROMA_PERSIST_DIR"]

from functools import lru_cache                                       # noqa: E402
from groq import Groq                                                 # noqa: E402
from app.config import settings                                       # noqa: E402
from app.services.schema_normalizer import normalize_payload          # noqa: E402
from app.services.pii_masker import mask_payload                      # noqa: E402
from app.services.compliance_analyzer import analyze                  # noqa: E402
from app.data.schema_presets import SCHEMA_PRESETS                    # noqa: E402
from app.services import document_ingestion_service as dis            # noqa: E402
from app.services import embeddings                                   # noqa: E402
from app.services.rag_retrieval_service import retrieve_regulatory_context  # noqa: E402
from app.services.llm_agent import generate_sar_core                  # noqa: E402

CLIENTS_DIR = os.path.join(ROOT, "backend", "storage", "clients")
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


# Lazy Groq client: creating it at import time (before torch loads) segfaults here.
@lru_cache(maxsize=1)
def _groq():
    return Groq(api_key=settings.GROQ_API_KEY)


def _judge(prompt, system="You are a strict, precise evaluation assistant. Output ONLY what is asked, no preamble."):
    r = _groq().chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        temperature=0.0, max_tokens=1024)
    return r.choices[0].message.content


def _parse_json(text):
    t = _FENCE.sub("", (text or "").strip()).strip()
    m = re.search(r"(\[.*\]|\{.*\})", t, re.DOTALL)
    try:
        return json.loads(m.group(1) if m else t)
    except Exception:
        return None


def faithfulness(answer, contexts):
    ctx = "\n\n".join(contexts)
    claims = _parse_json(_judge(
        "Break the following Suspicious Activity Report into a JSON array of atomic, "
        "verifiable factual claims (each a short standalone sentence). Output ONLY the "
        f"JSON array.\n\nSAR:\n{answer}"))
    if not isinstance(claims, list) or not claims:
        return None, 0
    verdicts = _parse_json(_judge(
        "For each CLAIM, decide if it is directly supported by the CONTEXT below. "
        "Output ONLY a JSON array of booleans (true/false) in the SAME order as the claims.\n\n"
        f"CONTEXT:\n{ctx}\n\nCLAIMS:\n{json.dumps(claims)}"))
    if not isinstance(verdicts, list) or not verdicts:
        return None, len(claims)
    verdicts = verdicts[:len(claims)]
    supported = sum(1 for v in verdicts if v is True or str(v).strip().lower() == "true")
    return supported / len(verdicts), len(claims)


def answer_relevancy(question, answer, n=5):
    qs = _parse_json(_judge(
        f"Based ONLY on the ANSWER below, write {n} distinct questions that this answer "
        f"directly and fully addresses. Output ONLY a JSON array of {n} question strings.\n\n"
        f"ANSWER:\n{answer}"))
    if not isinstance(qs, list) or not qs:
        return None
    # Question<->question is SYMMETRIC similarity, not retrieval, so embed WITHOUT bge's
    # query-instruction prefix (embed_documents, not embed_query) on BOTH sides — same space,
    # no shared-prefix confound. Vectors are unit-normalized, so dot product == cosine.
    qv = embeddings.embed_documents([question])[0]
    gen_vecs = embeddings.embed_documents([str(gq) for gq in qs])
    sims = [sum(a * b for a, b in zip(qv, gv)) for gv in gen_vecs]
    return sum(sims) / len(sims)


def evaluate_client(client_dir):
    cid = os.path.basename(client_dir)
    policy = os.path.join(client_dir, "policy.pdf")
    alerts = sorted(glob.glob(os.path.join(client_dir, "alerts", "*.json")))
    if not os.path.isfile(policy) or not alerts:
        print(f"\n#### {cid}: missing policy.pdf or alerts — skipped"); return None

    # schema_preset from eval.json if the client has one, else the default fintech preset.
    # RAGAS is reference-free, so no other answer-key fields are needed.
    eval_cfg_path = os.path.join(client_dir, "eval.json")
    schema_preset = "STANDARD_FINTECH"
    if os.path.isfile(eval_cfg_path):
        schema_preset = json.load(open(eval_cfg_path, encoding="utf-8")).get("schema_preset", schema_preset)
    preset = SCHEMA_PRESETS[schema_preset]
    fm, pii_fields = preset["field_map"], preset["pii_fields"]

    chunks = dis.build_chunks(policy, f"{cid} AML Policy", "policy.pdf", "policy.pdf")
    dis.index_document(f"ragas-{cid}", chunks)
    print(f"\n######## CLIENT: {cid} ({len(alerts)} alerts) ########")

    rows = []
    for path in alerts:
        rec = json.load(open(path, encoding="utf-8"))
        raw = rec.get("raw_payload", rec)
        # Prefer the live-computed normalized/masked payloads (exported from the DB with
        # the tenant's OWN schema) so we score EXACTLY what live produced. Only client_0
        # fixtures lack them → fall back to normalizing/masking with the preset.
        norm = rec.get("normalized_payload") or normalize_payload(raw, fm)
        masked = rec.get("masked_payload") or mask_payload(norm, pii_fields)[0]
        fired = [r for r in analyze(norm) if r["triggered"]]
        base = max(0, min(100, int(float(norm.get("risk_score") or 0))))
        score = min(100, base + sum(20 if r["confidence"] == "HIGH" else 10 for r in fired))

        # Wrap the Groq-dependent work so one transient API hiccup skips this alert
        # instead of crashing the whole run.
        try:
            comp = [{"rule_name": r["rule_name"], "triggered": True} for r in fired]
            hits = retrieve_regulatory_context(f"ragas-{cid}", {"transaction_type": norm.get("transaction_type")}, comp)
            out = generate_sar_core(masked, score, settings.GROQ_MODEL, retrieved_chunks=hits)
            answer = out["narrative"]

            # Faithfulness grounding = SAR's ACTUAL sources: transaction data + policy chunks.
            txn_context = ("TRANSACTION UNDER REVIEW (the alert the SAR is based on): "
                           + json.dumps(masked) + f" | composite_risk_score={score} | "
                           + "triggered_indicators=" + ", ".join(r["rule_name"] for r in fired))
            contexts = [txn_context] + [h["document"].split("\n", 1)[-1] for h in hits]

            question = (f"Assess this transaction for money-laundering suspicion and cite the "
                        f"applicable AML policy sections. Transaction type: {norm.get('transaction_type')}; "
                        f"amount: INR {norm.get('transaction_amount')}; "
                        f"triggered indicators: {', '.join(r['rule_name'] for r in fired)}.")

            faith, n_claims = faithfulness(answer, contexts)
            rel = answer_relevancy(question, answer)
            rows.append({"alert": os.path.basename(path), "faithfulness": faith,
                         "answer_relevancy": rel, "n_claims": n_claims})
            f_s = f"{faith:.3f} ({n_claims} claims)" if faith is not None else "n/a"
            r_s = f"{rel:.3f}" if rel is not None else "n/a"
            print(f"--- {os.path.basename(path)} ---  faithfulness={f_s}  answer_relevancy={r_s}")
        except Exception as e:
            rows.append({"alert": os.path.basename(path), "faithfulness": None,
                         "answer_relevancy": None, "n_claims": 0, "error": str(e)[:150]})
            print(f"--- {os.path.basename(path)} ---  SKIPPED (transient error: {str(e)[:80]})")

    fa = [r["faithfulness"] for r in rows if r["faithfulness"] is not None]
    re_ = [r["answer_relevancy"] for r in rows if r["answer_relevancy"] is not None]
    agg = {"faithfulness": (sum(fa) / len(fa) if fa else None),
           "answer_relevancy": (sum(re_) / len(re_) if re_ else None)}
    print(f"  >> {cid} MEAN: faithfulness={agg['faithfulness']:.3f} "
          f"answer_relevancy={agg['answer_relevancy']:.3f}"
          if fa and re_ else f"  >> {cid} MEAN: n/a")
    return {"client_id": cid, "per_alert": rows, "aggregate": agg}


def main():
    only = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else None

    # RAGAS uses Groq as the judge LLM — fail early with a clear message if no key.
    key = (settings.GROQ_API_KEY or "").strip()
    if not key or "placeholder" in key.lower() or key.lower() in ("changeme", "your-key-here"):
        print("GROQ_API_KEY is not set in backend/.env — RAGAS needs a real Groq key to run.\n"
              "(IR metrics need no key: python eval/ir_metrics.py)")
        return

    print(f"Evaluating clients in {os.path.relpath(CLIENTS_DIR, ROOT)}  (Groq judge + bge)")

    # RAGAS needs no answer key: score any client with a policy.pdf + alerts/.
    client_dirs = sorted(d for d in glob.glob(os.path.join(CLIENTS_DIR, "*"))
                         if os.path.isfile(os.path.join(d, "policy.pdf"))
                         and os.path.isdir(os.path.join(d, "alerts")))
    if only:
        client_dirs = [d for d in client_dirs if os.path.basename(d) == only]
    if not client_dirs:
        print(f"No clients with policy.pdf + alerts/ in {os.path.relpath(CLIENTS_DIR, ROOT)}"
              + (f" matching '{only}'" if only else "")
              + ".  (Seed client_0 with scripts/seed_testing.py, or export a real "
                "client's alerts into its folder.)")
        return

    results = [r for r in (evaluate_client(d) for d in client_dirs) if r]
    if not results:
        print("No clients had both a policy.pdf and alerts to score."); return

    print("\n" + "=" * 56 + "\nOVERALL (mean across clients)\n" + "=" * 56)
    fa = [r["aggregate"]["faithfulness"] for r in results if r["aggregate"]["faithfulness"] is not None]
    re_ = [r["aggregate"]["answer_relevancy"] for r in results if r["aggregate"]["answer_relevancy"] is not None]
    print(f"  Faithfulness     = {sum(fa)/len(fa):.3f}" if fa else "  Faithfulness     = n/a")
    print(f"  Answer Relevancy = {sum(re_)/len(re_):.3f}" if re_ else "  Answer Relevancy = n/a")

    out_path = os.path.join(ROOT, "outputs", "ragas_metrics.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump({"clients": results,
               "overall": {"faithfulness": (sum(fa)/len(fa) if fa else None),
                           "answer_relevancy": (sum(re_)/len(re_) if re_ else None)}},
              open(out_path, "w", encoding="utf-8"), indent=2)
    print(f"\nSaved -> {os.path.relpath(out_path, ROOT)}")


if __name__ == "__main__":
    main()
