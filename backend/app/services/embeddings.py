"""
Embedding interface — the ONLY place that knows which encoder is in use.

Swap providers via the EMBEDDING_PROVIDER setting ("local" | "openai") without
touching ingestion or retrieval. Dimension is never hardcoded: Chroma infers it
from the first vectors written, so 384-dim (local bge) and 1536-dim (OpenAI) both
work. The one rule: don't mix providers in a single collection — re-index if you
switch.

Default: BAAI/bge-small-en-v1.5 via sentence-transformers (SBERT) — local, free,
384-dim, 512-token max, asymmetric (query gets an instruction prefix; chunks raw).
"""
import os

# Stabilize the native ML stack BEFORE torch/sentence-transformers ever load.
# The ragas/langchain install bumped numpy/torch, which causes intermittent
# segfaults on this Windows/CPU env. Set centrally here so every consumer is safe.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from functools import lru_cache
from typing import List

try:
    from app.config import settings
    _PROVIDER = getattr(settings, "EMBEDDING_PROVIDER", "local")
    _LOCAL_MODEL_NAME = getattr(settings, "LOCAL_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    _OPENAI_MODEL = getattr(settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    _OPENAI_KEY = getattr(settings, "OPENAI_API_KEY", "")
except Exception:  # allow standalone use without the app package importable
    _PROVIDER = "local"
    _LOCAL_MODEL_NAME = "BAAI/bge-small-en-v1.5"
    _OPENAI_MODEL = "text-embedding-3-small"
    _OPENAI_KEY = ""

# bge wants this prefix on the QUERY ONLY (asymmetric retrieval). Chunks go in raw.
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def _local_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(_LOCAL_MODEL_NAME)


@lru_cache(maxsize=1)
def _openai_client():
    from openai import OpenAI
    return OpenAI(api_key=_OPENAI_KEY)


def embed_documents(texts: List[str]) -> List[List[float]]:
    """Embed chunk texts for storage. No query prefix."""
    if not texts:
        return []
    if _PROVIDER == "openai":
        resp = _openai_client().embeddings.create(model=_OPENAI_MODEL, input=texts)
        return [d.embedding for d in resp.data]
    model = _local_model()
    return model.encode(texts, normalize_embeddings=True, convert_to_numpy=True).tolist()


def embed_query(text: str) -> List[float]:
    """Embed a single search query. Local provider prepends the bge instruction."""
    if _PROVIDER == "openai":
        resp = _openai_client().embeddings.create(model=_OPENAI_MODEL, input=[text])
        return resp.data[0].embedding
    model = _local_model()
    vec = model.encode([QUERY_INSTRUCTION + text], normalize_embeddings=True,
                        convert_to_numpy=True)[0]
    return vec.tolist()


def count_tokens(text: str) -> int:
    """Token count using the active model's own tokenizer (local provider).

    Used by the chunker to stay under the encoder's 512-token window. For the
    OpenAI provider we approximate, since its limit (8191) is far larger than any
    chunk we produce."""
    if _PROVIDER == "openai":
        return max(1, len(text) // 4)  # rough; OpenAI's window is not a constraint here
    tok = _local_model().tokenizer
    return len(tok.encode(text, add_special_tokens=False))


def provider() -> str:
    return _PROVIDER


def model_name() -> str:
    return _OPENAI_MODEL if _PROVIDER == "openai" else _LOCAL_MODEL_NAME
