"""
P1.2 — Index a tenant's AML policy PDF into THEIR Chroma collection, so live alerts
have policy context to retrieve.

The live ingest path (ingest.py) retrieves from collection `tenant_{alert.tenant_id}_docs`,
where `alert.tenant_id` is the tenant's DB UUID. So we look the tenant up by its public
id, then index the policy under that UUID — into the SAME chroma_data the backend uses
(backend/chroma_data, because both this script and uvicorn run from backend/).

Requires the DB to be reachable and the tenant to exist (seed the DB first — P4.1).

Run from repo root:
  python scripts/seed_policy.py                         # TEN-0001 + the Aegis policy
  python scripts/seed_policy.py TEN-0001 path/to/policy.pdf
"""
import os
import sys

# Stabilize the native ML stack before torch loads (belt-and-suspenders; also set in embeddings.py).
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)  # so CHROMA_PERSIST_DIR=./chroma_data == backend/chroma_data (same as uvicorn)

_ARG_PDF = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else None  # resolve before chdir-relative use

# Load the ML model FIRST — before psycopg2/SQLAlchemy. Loading torch AFTER a DB
# connection segfaults intermittently on this env, so we warm it up here.
from app.services import embeddings                                     # noqa: E402
from app.services import document_ingestion_service as dis              # noqa: E402
from app.services.chroma_client import reset_tenant_collection, collection_name  # noqa: E402
embeddings._local_model()  # force-load the encoder now, before the DB

from app.database import SessionLocal                                   # noqa: E402
from app.models.tenant import Tenant                                    # noqa: E402

PUBLIC_ID = sys.argv[1] if len(sys.argv) > 1 else "TEN-0001"
POLICY = _ARG_PDF or os.path.join(ROOT, "backend", "storage", "clients", "client_0", "policy.pdf")


def main():
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.tenant_id_public == PUBLIC_ID).first()
        if not tenant:
            print(f"No tenant with public id '{PUBLIC_ID}'. Seed the DB first (P4.1).")
            return
        tid = str(tenant.id)
        print(f"Tenant {PUBLIC_ID} -> uuid {tid}")
        print(f"Policy: {POLICY}")

        reset_tenant_collection(tid)  # clean re-index (drop any stale chunks first)
        # doc_id = filename, SAME convention as the upload endpoint (documents.py),
        # so seeding and uploading the same file replace cleanly instead of duplicating.
        fname = os.path.basename(POLICY)
        chunks = dis.build_chunks(POLICY, f"{PUBLIC_ID} AML Policy", fname, fname)
        n = dis.index_document(tid, chunks)
        print(f"Indexed {n} chunks into collection '{collection_name(tid)}' "
              f"(chroma_data at {os.path.abspath(os.environ.get('CHROMA_PERSIST_DIR', './chroma_data'))}).")
        print("Done — live alerts for this tenant will now retrieve policy context.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
