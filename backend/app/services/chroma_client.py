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


def replace_tenant_collection(tenant_id: str, ids, documents, embeddings, metadatas) -> int:
    """Atomically swap in a fully-built index as the tenant's whole collection.

    The new chunks are written to a staging collection first and only then renamed
    over the live one, so a failure while writing them (or anything earlier) leaves the
    previous index serving. Reset-then-add would leave the tenant with an empty index."""
    client = get_chroma_client()
    live = collection_name(tenant_id)
    staging_name = f"{live}_staging"
    try:
        client.delete_collection(staging_name)  # leftover from an interrupted swap
    except Exception:
        pass
    staging = client.create_collection(name=staging_name, metadata={"hnsw:space": "cosine"})
    try:
        step = client.get_max_batch_size()
        for i in range(0, len(ids), step):
            staging.add(ids=ids[i:i + step], documents=documents[i:i + step],
                        embeddings=embeddings[i:i + step], metadatas=metadatas[i:i + step])
    except Exception:
        try:
            client.delete_collection(staging_name)
        except Exception:
            pass
        raise
    # Promote. A concurrent reader's get_or_create can re-create an empty live
    # collection between the delete and the rename; drop it and retry once.
    for attempt in range(2):
        try:
            client.delete_collection(live)
        except Exception:
            pass
        try:
            staging.modify(name=live)
            return len(ids)
        except Exception:
            if attempt:
                raise
