"""
RAG retrieval (Phase 2) — triggered rules -> sub-queries -> per-query cosine
search -> merge/dedupe -> top-K chunks.

We never embed the raw transaction JSON (masked tokens + numbers are semantic
noise). Instead each rule that fired maps to a regulation-worded sub-query, plus
one generic fallback from the transaction type.

RULE_TO_QUERY keys use the EXACT rule_name strings emitted by
compliance_analyzer.py (the original handoff's keys were wrong).
"""
from typing import List, Optional

from app.services import embeddings
from app.services.chroma_client import get_tenant_collection

try:
    from app.config import settings
    TOP_K = getattr(settings, "RAG_TOP_K_CHUNKS", 8)
except Exception:
    TOP_K = 8

PER_QUERY_N = 5

# Keyed on the real rule_name values from compliance_analyzer.py
RULE_TO_QUERY = {
    "Structuring / Smurfing":
        "structuring smurfing transactions just below the reporting threshold STR PMLA obligation",
    "Rapid Movement of Funds":
        "rapid movement of funds layering reversal refund pass-through suspicious transaction",
    "Large Round Number":
        "large round number transactions exact multiples unusual amount AML red flag",
    "Dormant Account Activation":
        "dormant account sudden activation large transaction suspicious activity reporting",
    "High Risk Transaction Type":
        "high risk transaction type cryptocurrency international wire forex hawala enhanced scrutiny",
    "High Velocity":
        "high velocity multiple transactions short period layering mule account indicators",
    "High Risk Counterparty":
        "high risk counterparty shell bank offshore anonymous institution enhanced due diligence",
    "Risk Score Threshold Exceeded":
        "high composite risk score suspicious transaction report filing obligation FIU-India goAML",
}


def build_sub_queries(masked_payload: dict, compliance_results: List[dict]) -> List[str]:
    queries: List[str] = []
    for r in compliance_results:
        if r.get("triggered") and r.get("rule_name") in RULE_TO_QUERY:
            queries.append(RULE_TO_QUERY[r["rule_name"]])
    # generic fallback from the transaction type so we always have at least one query
    txn_type = (masked_payload or {}).get("transaction_type")
    if txn_type:
        queries.append(f"{str(txn_type).replace('_', ' ').lower()} "
                       "AML reporting obligations suspicious transaction red flags")
    # de-dup while preserving order
    seen = set()
    deduped = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            deduped.append(q)
    return deduped


def retrieve_regulatory_context(
    tenant_id: str,
    masked_payload: dict,
    compliance_results: List[dict],
    top_k: Optional[int] = None,
) -> List[dict]:
    """Return up to top_k chunks: [{document, metadata, distance, matched_query}]."""
    top_k = top_k or TOP_K
    sub_queries = build_sub_queries(masked_payload, compliance_results)
    if not sub_queries:
        return []

    collection = get_tenant_collection(tenant_id)
    merged: dict = {}  # chunk_id -> hit (keep best/lowest distance)

    for q in sub_queries:
        qvec = embeddings.embed_query(q)
        res = collection.query(query_embeddings=[qvec], n_results=PER_QUERY_N,
                               include=["documents", "metadatas", "distances"])
        ids = (res.get("ids") or [[]])[0]
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        for cid, doc, meta, dist in zip(ids, docs, metas, dists):
            if cid not in merged or dist < merged[cid]["distance"]:
                merged[cid] = {"id": cid, "document": doc, "metadata": meta,
                               "distance": dist, "matched_query": q}

    ranked = sorted(merged.values(), key=lambda h: h["distance"])
    return ranked[:top_k]
