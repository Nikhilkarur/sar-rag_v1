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

Per-client, like ir_metrics.py. MOCK (testing/clients) by default; --prod for real.
  python eval/ragas_eval.py             # all MOCK clients
  python eval/ragas_eval.py client_0    # one mock client
  python eval/ragas_eval.py --prod      # all REAL clients (production/clients)
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

MOCK_DIR = os.path.join(ROOT, "testing", "clients")
PROD_DIR = os.path.join(ROOT, "production", "clients")
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


def answer_relevancy(question, answer, n=3):
    qs = _parse_json(_judge(
        f"Based ONLY on the ANSWER below, write {n} distinct questions that this answer "
        f"directly and fully addresses. Output ONLY a JSON array of {n} question strings.\n\n"
        f"ANSWER:\n{answer}"))
    if not isinstance(qs, list) or not qs:
        return None
    qv = embeddings.embed_query(question)               # bge vectors are unit-normalized
    sims = [sum(a * b for a, b in zip(qv, embeddings.embed_query(str(gq)))) for gq in qs]
    return sum(sims) / len(sims)


def evaluate_client(client_dir):
    cfg = json.load(open(os.path.join(client_dir, "config.json"), encoding="utf-8"))
    tid = cfg["tenant_id"]
    policy = os.path.join(client_dir, cfg["policy_pdf"])
    preset = SCHEMA_PRESETS[cfg["schema_preset"]]
    fm, pii_fields = preset["field_map"], preset["pii_fields"]
    alerts = sorted(glob.glob(os.path.join(client_dir, "alerts", "*.json")))

    chunks = dis.build_chunks(policy, cfg.get("display_name", tid), cfg["policy_pdf"], f"{tid}-p")
    dis.index_document(f"ragas-{tid}", chunks)
    print(f"\n######## CLIENT: {tid} ({len(alerts)} alerts) ########")

    rows = []
    for path in alerts:
        raw = json.load(open(path, encoding="utf-8"))
        norm = normalize_payload(raw, fm)
        masked, _ = mask_payload(norm, pii_fields)
        fired = [r for r in analyze(norm) if r["triggered"]]
        base = max(0, min(100, int(float(norm.get("risk_score") or 0))))
        score = min(100, base + sum(20 if r["confidence"] == "HIGH" else 10 for r in fired))

        # Wrap the Groq-dependent work so one transient API hiccup skips this alert
        # instead of crashing the whole run.
        try:
            comp = [{"rule_name": r["rule_name"], "triggered": True} for r in fired]
            hits = retrieve_regulatory_context(f"ragas-{tid}", {"transaction_type": norm.get("transaction_type")}, comp)
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
    print(f"  >> {tid} MEAN: faithfulness={agg['faithfulness']:.3f} "
          f"answer_relevancy={agg['answer_relevancy']:.3f}"
          if fa and re_ else f"  >> {tid} MEAN: n/a")
    return {"tenant_id": tid, "per_alert": rows, "aggregate": agg}


def main():
    prod = "--prod" in sys.argv
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    only = positional[0] if positional else None
    base = PROD_DIR if prod else MOCK_DIR
    print(f"Evaluating {'PRODUCTION' if prod else 'MOCK (testing)'} clients in "
          f"{os.path.relpath(base, ROOT)}  (Groq judge + bge)")

    client_dirs = sorted(d for d in glob.glob(os.path.join(base, "*"))
                         if os.path.isfile(os.path.join(d, "config.json")))
    if only:
        client_dirs = [d for d in client_dirs if os.path.basename(d) == only]
    if not client_dirs:
        print(f"No clients found in {os.path.relpath(base, ROOT)}"
              + (f" matching '{only}'" if only else "")
              + (". (production/ is empty until you add real clients.)" if prod else ""))
        return

    results = [evaluate_client(d) for d in client_dirs]

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
