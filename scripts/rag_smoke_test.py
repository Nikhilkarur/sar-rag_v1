"""
End-to-end RAG smoke test WITHOUT the DB, router, or Groq.

  1. Index backend/storage/clients/client_0/policy.pdf into a temp Chroma dir
  2. Take a mock alert, run the REAL normalizer + analyzer to get triggered rules
  3. Run retrieval and print which policy sections came back

Pass criteria are documented in mock_inputs/README.md (the test oracle).

Run from the repo root:  python scripts/rag_smoke_test.py
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND)

# Use a throwaway Chroma dir so the smoke test never touches real data
os.environ.setdefault("CHROMA_PERSIST_DIR", tempfile.mkdtemp(prefix="chroma_smoke_"))
# chroma_client reads settings.CHROMA_PERSIST_DIR; patch the module default too
import app.services.chroma_client as cc  # noqa: E402
cc._PERSIST_DIR = os.environ["CHROMA_PERSIST_DIR"]

from app.services.schema_normalizer import normalize_payload          # noqa: E402
from app.services.compliance_analyzer import analyze                   # noqa: E402
from app.data.schema_presets import SCHEMA_PRESETS                     # noqa: E402
from app.services import document_ingestion_service as dis             # noqa: E402
from app.services.rag_retrieval_service import (                       # noqa: E402
    retrieve_regulatory_context, build_sub_queries,
)

PDF = os.path.join(ROOT, "backend", "storage", "clients", "client_0", "policy.pdf")
MOCK = os.path.join(ROOT, "backend", "storage", "clients", "client_0", "alerts", "01_structuring_intlwire.json")
TENANT = "client_0"   # dummy/test client (real clients start at client_1)


def main():
    print("=" * 70)
    print("STEP 1 — Index the Aegis Bank policy PDF")
    print("=" * 70)
    chunks = dis.build_chunks(PDF, doc_title="Aegis Bank AML/CFT Policy",
                              filename="aegis_bank_aml_policy.pdf", doc_id="aegis-policy-1")
    print(f"Built {len(chunks)} chunks from the PDF. Sections detected:")
    seen = []
    for c in chunks:
        h = c.metadata["section_heading"]
        if h not in seen:
            seen.append(h)
    for h in seen:
        print(f"   - {h}")
    n = dis.index_document(TENANT, chunks)
    print(f"Indexed {n} chunks into Chroma collection for tenant '{TENANT}'.")

    print()
    print("=" * 70)
    print("STEP 2 — Run mock alert through the REAL rule engine")
    print("=" * 70)
    _rec = json.load(open(MOCK, encoding="utf-8"))
    raw = _rec.get("raw_payload", _rec)
    fm = SCHEMA_PRESETS["STANDARD_FINTECH"]["field_map"]
    norm = normalize_payload(raw, fm)
    results = analyze(norm)
    triggered = [r for r in results if r["triggered"]]
    print("Triggered rules:")
    for r in triggered:
        print(f"   [{r['confidence']:6}] {r['rule_name']}")

    # masked_payload stand-in: retrieval only reads transaction_type from it
    masked = {"transaction_type": norm.get("transaction_type")}
    compliance_results = [{"rule_name": r["rule_name"], "triggered": True} for r in triggered]

    print()
    print("Sub-queries built:")
    for q in build_sub_queries(masked, compliance_results):
        print(f"   * {q}")

    print()
    print("=" * 70)
    print("STEP 3 — Retrieve regulatory context")
    print("=" * 70)
    hits = retrieve_regulatory_context(TENANT, masked, compliance_results)
    print(f"Top {len(hits)} chunks (cosine distance, lower = closer):\n")
    for i, h in enumerate(hits, 1):
        m = h["metadata"]
        preview = h["document"].split("\n", 1)[-1][:90].replace("\n", " ")
        print(f"{i:2}. dist={h['distance']:.3f}  [{m['section_heading']}] p{m['page_number']}")
        print(f"      {preview}...")

    print()
    print("=" * 70)
    print("ORACLE CHECK (see mock_inputs/README.md)")
    print("=" * 70)
    want = ["Structuring", "High-Risk Transaction Types", "Composite Risk", "Obligation to Report"]
    got_sections = " | ".join(h["metadata"]["section_heading"] for h in hits)
    for w in want:
        ok = w.lower() in got_sections.lower()
        print(f"   [{'PASS' if ok else 'MISS'}] expected a section matching '{w}'")


if __name__ == "__main__":
    main()
