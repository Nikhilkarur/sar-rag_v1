"""
Phase 3 — full RAG-augmented SAR generation (uses the Groq key from backend/.env).
Still DB-free and HTTP-free: indexes the policy PDF, runs the mock alert through
the REAL normalize + mask + analyze, retrieves chunks, then calls Groq.

Shows: triggered rules -> retrieved sections -> cited SAR narrative + structured
JSON -> PII rehydration. Also prints a no-context baseline for contrast.

Run from repo root:  python scripts/rag_generate_test.py
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND)
# load backend/.env (GROQ key) regardless of cwd
os.chdir(BACKEND)

os.environ.setdefault("CHROMA_PERSIST_DIR", tempfile.mkdtemp(prefix="chroma_gen_"))
import app.services.chroma_client as cc  # noqa: E402
cc._PERSIST_DIR = os.environ["CHROMA_PERSIST_DIR"]

from app.config import settings                                       # noqa: E402
from app.services.schema_normalizer import normalize_payload          # noqa: E402
from app.services.pii_masker import mask_payload                      # noqa: E402
from app.services.compliance_analyzer import analyze                  # noqa: E402
from app.data.schema_presets import SCHEMA_PRESETS                    # noqa: E402
from app.services import document_ingestion_service as dis            # noqa: E402
from app.services.rag_retrieval_service import retrieve_regulatory_context  # noqa: E402
from app.services.llm_agent import generate_sar_core                  # noqa: E402

PDF = os.path.join(ROOT, "testing", "corpus", "aegis_bank_aml_policy.pdf")
MOCK = os.path.join(ROOT, "testing", "inputs", "alert_structuring_intlwire.json")
TENANT = "client_0"   # dummy/test client (real clients start at client_1)


def hr(t):
    print("\n" + "=" * 70 + f"\n{t}\n" + "=" * 70)


def main():
    hr("Index policy PDF")
    chunks = dis.build_chunks(PDF, "Aegis Bank AML/CFT Policy",
                              "aegis_bank_aml_policy.pdf", "aegis-policy-1")
    dis.index_document(TENANT, chunks)
    print(f"Indexed {len(chunks)} chunks.")

    hr("Mock alert -> normalize -> mask -> analyze")
    raw = json.load(open(MOCK, encoding="utf-8"))
    preset = SCHEMA_PRESETS["STANDARD_FINTECH"]
    norm = normalize_payload(raw, preset["field_map"])
    masked, token_map = mask_payload(norm, preset["pii_fields"])
    results = [r for r in analyze(norm) if r["triggered"]]

    base = max(0, min(100, int(float(norm.get("risk_score") or 0))))
    score = base
    for r in results:
        score += 20 if r["confidence"] == "HIGH" else (10 if r["confidence"] == "MEDIUM" else 0)
    score = min(100, score)

    print("Triggered:", ", ".join(r["rule_name"] for r in results))
    print("Composite risk score:", score)
    print("Masked payload (what RAG + Groq see):")
    print(json.dumps(masked, indent=2)[:600])

    hr("Retrieve regulatory context")
    compliance_results = [{"rule_name": r["rule_name"], "triggered": True} for r in results]
    hits = retrieve_regulatory_context(TENANT, masked, compliance_results)
    for i, h in enumerate(hits, 1):
        print(f"{i:2}. [{h['metadata']['section_heading']}]  dist={h['distance']:.3f}")

    hr(f"Groq generation WITH RAG context  (model={settings.GROQ_MODEL})")
    out = generate_sar_core(masked, score, settings.GROQ_MODEL, retrieved_chunks=hits)
    print("\n--- NARRATIVE (masked) ---\n")
    print(out["narrative"])
    print("\n--- STRUCTURED JSON ---\n")
    print(json.dumps(out["structured"], indent=2))
    print("\n--- SOURCES USED ---")
    for c in out["used_chunks"]:
        print(f"   - {c['section']}")
    print(f"\ntokens: prompt={out['prompt_tokens']} completion={out['completion_tokens']} "
          f"latency={out['latency_ms']}ms")

    hr("PII rehydration (bank-facing version)")
    rehydrated = out["narrative"]
    for token, original in token_map.items():
        rehydrated = rehydrated.replace(token, str(original))
    print("token_map:", json.dumps(token_map, indent=2)[:400])
    changed = rehydrated != out["narrative"]
    print(f"\nRehydration changed the text: {changed}")
    if changed:
        print("\n--- NARRATIVE (rehydrated, real PII) ---\n")
        print(rehydrated)

    hr("Baseline: Groq WITHOUT RAG context (for contrast)")
    base_out = generate_sar_core(masked, score, settings.GROQ_MODEL, retrieved_chunks=None)
    print(base_out["narrative"][:900])
    print("\n(Compare: the RAG version above should cite specific policy sections; "
          "this baseline cannot.)")


if __name__ == "__main__":
    main()
