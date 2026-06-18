"""
ChromaDB access — one persistent client, one collection per tenant.

Collections are named `tenant_{tenant_id}_docs` so every tenant's regulatory
chunks are fully isolated. Cosine space matches the normalized embeddings from
embeddings.py.

Dev uses a local persistent directory. For production, switch to Chroma server
mode or migrate to pgvector — the call sites here are the only thing that changes.
"""
from functools import lru_cache

try:
    from app.config import settings
    _PERSIST_DIR = getattr(settings, "CHROMA_PERSIST_DIR", "./chroma_data")
except Exception:
    _PERSIST_DIR = "./chroma_data"


@lru_cache(maxsize=1)
def get_chroma_client():
    import chromadb
    return chromadb.PersistentClient(path=_PERSIST_DIR)


def collection_name(tenant_id: str) -> str:
    return f"tenant_{tenant_id}_docs"


def get_tenant_collection(tenant_id: str):
    """Get or create the tenant's isolated, cosine-space collection."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=collection_name(tenant_id),
        metadata={"hnsw:space": "cosine"},
    )


def reset_tenant_collection(tenant_id: str):
    """Drop and recreate a tenant collection (used when re-indexing)."""
    client = get_chroma_client()
    try:
        client.delete_collection(collection_name(tenant_id))
    except Exception:
        pass
    return get_tenant_collection(tenant_id)
