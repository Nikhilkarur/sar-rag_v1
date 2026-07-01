from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db, SessionLocal
from app.utils.deps import authenticate_api_key
from app.models.tenant import Tenant
from app.models.schema import IngestionSchema
from app.models.alert import Alert
from app.models.pii_map import PIIMap
from app.models.compliance import ComplianceMatch
from app.services.schema_normalizer import normalize_payload
from app.services.pii_masker import mask_payload
from app.services.compliance_analyzer import analyze
from app.services.llm_agent import generate_sar
from app.services.rag_retrieval_service import retrieve_regulatory_context
import hashlib
import json
import threading
import time
import uuid
from collections import defaultdict, deque
from sqlalchemy.exc import IntegrityError

# --- Rate limiting (sliding window, per tenant-or-IP, in-process) ---
# Runs as a router dependency BEFORE API-key verification, so unauthenticated
# floods are rejected without paying a bcrypt round per request.
# NOTE: state is per worker process; for multi-instance deployments move the
# window to Redis, but the contract (429 + Retry-After) stays the same.
_RATE_WINDOW_SECONDS = 60.0
_RATE_MAX_BUCKETS = 10_000  # bound limiter memory against random-key floods
_rate_lock = threading.Lock()
_rate_buckets: dict = defaultdict(deque)

def _prune_rate_buckets(now: float) -> None:
    # Caller must hold _rate_lock. Drop buckets with no traffic in the window
    # so attackers spraying random X-Tenant-ID values cannot grow memory forever.
    stale = [k for k, b in _rate_buckets.items() if not b or now - b[-1] > _RATE_WINDOW_SECONDS]
    for k in stale:
        del _rate_buckets[k]

def enforce_ingest_rate_limit(request: Request):
    # Reject oversized bodies before auth (bcrypt) or body buffering.
    # Content-Length is verified against actual bytes again in the handler.
    content_length = request.headers.get("Content-Length")
    if content_length is None:
        raise HTTPException(status_code=411, detail="Content-Length header is required")
    try:
        if int(content_length) > settings.MAX_INGEST_PAYLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Payload exceeds the maximum allowed size")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Content-Length header")

    # Untrusted header is the bucket key: cap its length so it can't be abused
    key = (request.headers.get("X-Tenant-ID") or (
        request.client.host if request.client else "unknown"
    ))[:128]
    limit = settings.RATE_LIMIT_INGEST_PER_MINUTE
    now = time.monotonic()
    with _rate_lock:
        if len(_rate_buckets) >= _RATE_MAX_BUCKETS and key not in _rate_buckets:
            _prune_rate_buckets(now)
            if len(_rate_buckets) >= _RATE_MAX_BUCKETS:
                # Table still full of active keys: shed load instead of growing
                raise HTTPException(status_code=429, detail="Server busy. Try again later.",
                                    headers={"Retry-After": "30"})
        bucket = _rate_buckets[key]
        while bucket and now - bucket[0] > _RATE_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= limit:
            retry_after = max(1, int(_RATE_WINDOW_SECONDS - (now - bucket[0])) + 1)
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again later.",
                headers={"Retry-After": str(retry_after)},
            )
        bucket.append(now)

router = APIRouter(
    prefix="/api/v1/ingest",
    tags=["Ingestion Pipeline"],
    dependencies=[Depends(enforce_ingest_rate_limit)],
)

def process_alert_background(alert_id: str):
    # Background tasks run after the request-scoped session is returned to the
    # pool, so this task must own its session (and connection) end to end.
    db = SessionLocal()
    try:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return

        try:
            # 4a. RAG retrieval (best-effort). A failure here must NOT fail the alert —
            #     we degrade to generating without policy context (general AML knowledge).
            retrieved_chunks = None
            try:
                matches = db.query(ComplianceMatch).filter(
                    ComplianceMatch.alert_id == alert_id,
                    ComplianceMatch.triggered == True
                ).all()
                compliance_results = [
                    {"rule_name": m.rule_name, "triggered": True} for m in matches
                ]
                retrieved_chunks = retrieve_regulatory_context(
                    str(alert.tenant_id), alert.masked_payload or {}, compliance_results
                )
            except Exception:
                retrieved_chunks = None  # RAG unavailable → fall back to no-context generation

            # 4b. Generate SAR Narrative (with the tenant's policy context, if retrieved)
            sar = generate_sar(alert.id, db, retrieved_chunks=retrieved_chunks)

            # 5. Mark Complete
            alert.status = "PROCESSING_COMPLETED"
            alert.processing_completed_at = __import__('sqlalchemy').func.now()
            db.commit()
        except Exception as e:
            db.rollback()
            alert.status = "PROCESSING_FAILED"
            alert.processing_error = str(e)
            db.commit()
    finally:
        db.close()

@router.post("/")
async def ingest_payload(
    request: Request, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db), 
    tenant: Tenant = Depends(authenticate_api_key)
):
    body = await request.body()
    # Content-Length was checked pre-auth, but a chunked/lying client can send
    # more bytes than declared — enforce against what actually arrived
    if len(body) > settings.MAX_INGEST_PAYLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Payload exceeds the maximum allowed size")

    try:
        raw_payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    if not isinstance(raw_payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")

    # Replay protection: explicit Idempotency-Key header, falling back to a
    # hash of the exact body so byte-identical resubmissions are caught too
    idempotency_key = request.headers.get("Idempotency-Key")
    if idempotency_key:
        idempotency_key = idempotency_key.strip()[:255]
    else:
        idempotency_key = f"sha256:{hashlib.sha256(body).hexdigest()}"

    existing = db.query(Alert).filter(
        Alert.tenant_id == tenant.id,
        Alert.idempotency_key == idempotency_key
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Duplicate submission rejected (idempotency key already processed)",
                "original_alert_id": str(existing.id),
            },
        )

    schema_key = request.headers.get("X-Schema-Key")
    schema = None
    if schema_key:
        schema = db.query(IngestionSchema).filter(
            IngestionSchema.tenant_id == tenant.id,
            IngestionSchema.template_key == schema_key
        ).first()
        
    if not schema:
        # Default to first active schema if not provided
        schema = db.query(IngestionSchema).filter(
            IngestionSchema.tenant_id == tenant.id,
            IngestionSchema.is_active == True
        ).first()
        if not schema:
            raise HTTPException(status_code=400, detail="No active schema found for tenant")
            
    # 1. Normalize
    normalized = normalize_payload(raw_payload, schema.field_map)
    
    # 2. Mask PII
    masked_payload, token_map = mask_payload(normalized, schema.pii_fields)
    
    # 3. Compliance Analysis
    analysis_results = analyze(normalized)
    
    # Determine base risk score from payload or rules.
    # Clamp to 0-100: a crafted negative/huge/non-numeric risk_score must not
    # crash the pipeline or drag the final score below the SAR threshold.
    try:
        risk_score = int(float(normalized.get("risk_score") or 0))
    except (TypeError, ValueError):
        risk_score = 0
    risk_score = max(0, min(100, risk_score))
    for r in analysis_results:
        if r["triggered"]:
            if r["confidence"] == "HIGH": risk_score += 20
            elif r["confidence"] == "MEDIUM": risk_score += 10
    
    # Create Alert
    alert = Alert(
        tenant_id=tenant.id,
        schema_id=schema.id,
        status="PROCESSING",
        raw_payload=raw_payload,
        normalized_payload=normalized,
        masked_payload=masked_payload,
        transaction_id=str(normalized.get("transaction_id", uuid.uuid4())),
        transaction_amount=normalized.get("transaction_amount"),
        transaction_type=normalized.get("transaction_type"),
        risk_score=min(100, risk_score),
        is_synthetic=False,
        idempotency_key=idempotency_key,
        ingested_from_ip=request.client.host if request.client else None,
        processing_started_at=__import__('sqlalchemy').func.now()
    )
    db.add(alert)
    try:
        db.commit()
    except IntegrityError:
        # Two identical requests raced past the SELECT: the unique constraint
        # on (tenant_id, idempotency_key) is the authoritative guard
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate submission rejected (idempotency key already processed)")
    db.refresh(alert)
    
    # Save PII Map
    pii = PIIMap(alert_id=alert.id, tenant_id=tenant.id, token_map=token_map)
    db.add(pii)
    
    # Save Compliance Matches
    for r in analysis_results:
        if r["triggered"]:
            match = ComplianceMatch(
                alert_id=alert.id,
                tenant_id=tenant.id,
                rule_id=r["rule_id"],
                rule_name=r["rule_name"],
                triggered=True,
                confidence=r["confidence"],
                evidence=r["evidence"]
            )
            db.add(match)
            
    db.commit()

    # NOTE: the alert is now persisted in Postgres (alerts table) — the source of
    # truth for live transactions. We deliberately do NOT mirror it to the per-client
    # folder here; for offline eval, export a sample from the DB on demand instead.

    if alert.risk_score >= 75:
        # Threshold met, trigger SAR generation
        background_tasks.add_task(process_alert_background, alert.id)
    else:
        alert.status = "COMPLETED_CLEAN"
        alert.processing_completed_at = __import__('sqlalchemy').func.now()
        db.commit()
        
    return {
        "status": "success",
        "alert_id": alert.id,
        "risk_score": alert.risk_score,
        "message": "Ingested successfully. SAR generation triggered." if alert.risk_score >= 75 else "Ingested successfully. No SAR required."
    }
