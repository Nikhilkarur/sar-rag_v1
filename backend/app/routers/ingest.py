from fastapi import APIRouter, Depends, HTTPException, Request
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
from app.services.risk_scoring import compute_composite_risk, warrants_sar
from app.services.llm_agent import generate_sar
from app.services.rag_retrieval_service import retrieve_regulatory_context
import hashlib
import ipaddress
import json
import math
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal, DecimalException, ROUND_HALF_UP
from collections import defaultdict, deque
from sqlalchemy import func
from sqlalchemy.exc import DataError, IntegrityError


# Plausible transaction years. Anything outside is a placeholder (.NET's
# DateTime.MinValue serializes as 0001-01-01T00:00:00) or a unit mix-up, not a
# real transaction date to put on a SAR. The bound also keeps the stored value
# loadable: Postgres keeps timestamptz in UTC, so a value Python parses fine but
# whose UTC instant falls outside years 1-9999 (9999-12-31T23:00:00-05:00,
# 0001-01-01T00:00:00+05:30) used to commit and then fail every read of the
# alert, which took down the tenant's whole review queue.
_TXN_TIMESTAMP_YEARS = (1900, 2100)

class _TimestampOutOfRange(ValueError):
    pass

def _parse_txn_timestamp(value):
    """Parse a payload transaction_timestamp (ISO 8601) into a datetime.
    Missing -> None (the summary/goAML then fall back to the row's created_at).
    Present but unparseable -> ValueError, which the handler turns into a 422:
    silently dropping it put the ingest time on the report as the txn date.
    Outside _TXN_TIMESTAMP_YEARS (checked in UTC) -> _TimestampOutOfRange."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, datetime):
        ts = value
    elif not isinstance(value, str):
        raise ValueError("not a string")
    else:
        ts = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    # Check the UTC instant Postgres will store, not the local wall-clock time
    try:
        year = ts.astimezone(timezone.utc).year if ts.tzinfo else ts.year
    except OverflowError:
        year = None
    low, high = _TXN_TIMESTAMP_YEARS
    if year is None or not low <= year <= high:
        raise _TimestampOutOfRange(f"year outside {low}-{high}")
    return ts

# --- Typed-column validation ---
# The normalizer is deliberately tolerant (a missing path is just None), but these
# values land in fixed-width / Numeric(20, 4) columns, where a bad one used to
# surface as a psycopg2 DataError (500). Reject them up front with a 422 that
# names the field and the payload path it came from.
_TEXT_COLUMN_LIMITS = {"transaction_id": 255, "transaction_currency": 10, "transaction_type": 50}
_AMOUNT_LIMIT = Decimal(10) ** 16  # Numeric(20, 4) leaves 16 integer digits
_AMOUNT_QUANTUM = Decimal("0.0001")

def _field_error(field: str, field_map: dict, message: str) -> HTTPException:
    path = field_map.get(field)
    where = f"{field} ({path})" if path else field
    return HTTPException(status_code=422, detail=f"{where} {message}")

def _blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())

def _clean_text_field(normalized: dict, field_map: dict, field: str):
    value = normalized.get(field)
    if _blank(value):
        return None
    # Numbers are accepted and stored as text (e.g. a numeric ref_id); objects,
    # arrays and booleans are a mapping mistake, not a value
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise _field_error(field, field_map, "must be a string")
    value = str(value)
    limit = _TEXT_COLUMN_LIMITS[field]
    if len(value) > limit:
        raise _field_error(field, field_map, f"must be at most {limit} characters")
    if "\x00" in value:
        raise _field_error(field, field_map, "must not contain NUL characters")
    if not _encodes_as_utf8(value):
        raise _field_error(field, field_map, "must not contain unpaired UTF-16 surrogates")
    return value

def _parse_amount(normalized: dict, field_map: dict):
    value = normalized.get("transaction_amount")
    if _blank(value):
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise _field_error("transaction_amount", field_map, "must be a number")
    try:
        amount = Decimal(str(value).strip())
    except DecimalException:
        raise _field_error("transaction_amount", field_map, "must be a number")
    if not amount.is_finite():
        raise _field_error("transaction_amount", field_map, "must be a finite number")
    out_of_range = _field_error(
        "transaction_amount", field_map, "is out of range (at most 16 integer digits)"
    )
    # Range check before quantize (which raises on huge exponents) and again
    # after it, since rounding to 4 places can carry into a 17th digit
    if amount.copy_abs() >= _AMOUNT_LIMIT:
        raise out_of_range
    amount = amount.quantize(_AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)
    if amount.copy_abs() >= _AMOUNT_LIMIT:
        raise out_of_range
    return amount

def _check_risk_score(normalized: dict, field_map: dict) -> None:
    # clamp_score()/the analyzer collapse non-numeric garbage to 0 by design, but
    # int(float(x)) raises OverflowError on inf/huge values, so reject those here
    value = normalized.get("risk_score")
    if value is None or isinstance(value, bool):
        return
    try:
        finite = math.isfinite(float(value))
    except (TypeError, ValueError):
        return
    except OverflowError:
        finite = False
    if not finite:
        raise _field_error("risk_score", field_map, "must be a finite number")

def _loads_payload(body: bytes):
    """json.loads that also reports whether any number in the payload is non-finite.
    JSON has no NaN/Infinity, but Python's parser accepts those literals and turns
    overflowing numbers (1e400) into inf: JSONB rejects them on insert and the
    alert detail endpoint could never serialize the stored raw payload again."""
    non_finite = []

    def _float(text):
        number = float(text)
        if not math.isfinite(number):
            non_finite.append(text)
        return number

    def _constant(text):
        non_finite.append(text)
        return float(text)

    payload = json.loads(body, parse_float=_float, parse_constant=_constant)
    return payload, bool(non_finite)

def _encodes_as_utf8(value) -> bool:
    """False if any string in value (keys included) holds an unpaired surrogate.
    json.loads turns a lone \\ud800-\\udfff escape into a str that has no UTF-8
    form, so psycopg2 and the PII tokenizer raised UnicodeEncodeError (a 500).
    Properly paired escapes (e.g. emoji) are joined by json.loads and pass."""
    try:
        json.dumps(value, ensure_ascii=False).encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True

# --- Rate limiting (sliding window, in-process) ---
# Two layers, so a caller without the API key can never spend a tenant's quota:
#   1. pre-auth, per client IP (router dependency): sheds floods before the bcrypt
#      API-key check. Keyed on request.client.host, never on a header the client
#      controls: behind nginx it is the real client IP (uvicorn only trusts
#      X-Forwarded-For from the proxy IP, see FORWARDED_ALLOW_IPS in docker-compose).
#   2. per tenant (RATE_LIMIT_INGEST_PER_MINUTE), counted only after the API key
#      checks out. It used to be keyed on the unauthenticated X-Tenant-ID header
#      before auth: anyone could exhaust a bank's quota with its (public,
#      sequential) tenant ID, or dodge the limit by sending a fresh ID each time.
# NOTE: state is per worker process; for multi-instance deployments move the
# windows to Redis, but the contract (429 + Retry-After) stays the same.
_RATE_WINDOW_SECONDS = 60.0
_RATE_MAX_BUCKETS = 10_000  # bound limiter memory against floods from many sources

class _SlidingWindowLimiter:
    def __init__(self, max_buckets: int = _RATE_MAX_BUCKETS):
        self._lock = threading.Lock()
        self._buckets: dict = defaultdict(deque)
        self._max_buckets = max_buckets

    def _prune(self, now: float) -> None:
        # Caller must hold _lock. Drop buckets with no traffic in the window so
        # sources that come and go cannot grow memory forever.
        stale = [k for k, b in self._buckets.items() if not b or now - b[-1] > _RATE_WINDOW_SECONDS]
        for k in stale:
            del self._buckets[k]

    def hit(self, key: str, limit: int) -> None:
        """Count one request for key; raise 429 if it is over limit per window."""
        now = time.monotonic()
        with self._lock:
            if len(self._buckets) >= self._max_buckets and key not in self._buckets:
                self._prune(now)
                if len(self._buckets) >= self._max_buckets:
                    # Table still full of active keys: shed load instead of growing
                    raise HTTPException(status_code=429, detail="Server busy. Try again later.",
                                        headers={"Retry-After": "30"})
            bucket = self._buckets[key]
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

_ip_rate_limiter = _SlidingWindowLimiter()
_tenant_rate_limiter = _SlidingWindowLimiter()

def _client_ip_key(request: Request) -> str:
    host = request.client.host if request.client else "unknown"
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return host[:128]
    if ip.version == 6:
        if ip.ipv4_mapped:
            return str(ip.ipv4_mapped)
        # One host usually owns a whole /64, so per-address buckets would be
        # trivially rotated around
        return str(ipaddress.ip_network(f"{ip}/64", strict=False))
    return str(ip)

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

    _ip_rate_limiter.hit(_client_ip_key(request), settings.RATE_LIMIT_INGEST_PER_IP_PER_MINUTE)

def enforce_tenant_ingest_quota(tenant: Tenant = Depends(authenticate_api_key)) -> Tenant:
    # Runs only after authenticate_api_key succeeded: failed auth never counts here
    _tenant_rate_limiter.hit(str(tenant.id), settings.RATE_LIMIT_INGEST_PER_MINUTE)
    return tenant

async def _read_ingest_body(request: Request) -> bytes:
    # The handler is a plain def so its blocking DB work runs in the threadpool
    # instead of on the event loop; the body still has to be awaited, so it is
    # read here (declared after the tenant dependency, i.e. only once authed).
    return await request.body()

# SAR generation for API ingests runs on its own small pool instead of as a
# Starlette BackgroundTask. Each generation holds a DB connection for the whole
# LLM call, and a burst of ingests used to start one task per alert at once,
# draining the connection pool and the shared request threadpool so concurrent
# requests failed with pool timeouts. Extra alerts wait here in PROCESSING.
_sar_executor = ThreadPoolExecutor(
    max_workers=settings.SAR_GENERATION_CONCURRENCY, thread_name_prefix="sar-gen"
)

router = APIRouter(
    prefix="/api/v1/ingest",
    tags=["Ingestion Pipeline"],
    dependencies=[Depends(enforce_ingest_rate_limit)],
)

def _mark_processing_failed(db: Session, alert_id, error: Exception) -> None:
    # Nothing may escape the task with the alert still PROCESSING: it would have no
    # draft, could never be reviewed, and nothing retries it.
    try:
        db.rollback()
        db.query(Alert).filter(Alert.id == alert_id).update(
            {"status": "PROCESSING_FAILED", "processing_error": str(error)},
            synchronize_session=False,
        )
        db.commit()
    except Exception as mark_err:
        db.rollback()
        # Stays PROCESSING; fail_stuck_processing_alerts() catches it after a restart
        print(f"Failed to mark alert {alert_id} PROCESSING_FAILED: {mark_err}")

def process_alert_background(alert_id: str):
    # Runs after the request-scoped session is returned to the pool (as a
    # BackgroundTask, or on _sar_executor for API ingests), so this task must own
    # its session (and connection) end to end.
    db = SessionLocal()
    try:
        try:
            alert = db.query(Alert).filter(Alert.id == alert_id).first()
        except Exception as e:
            # e.g. a pool timeout under load: this used to leave the alert stuck
            _mark_processing_failed(db, alert_id, e)
            return
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

            # 4b. Generate SAR Narrative (with the tenant's policy context, if retrieved).
            #     Bounded in-process retry: the LLM providers already fail over Groq->Gemini,
            #     but a transient blip on BOTH would otherwise strand the alert as FAILED with
            #     no SAR — a regulatory gap. Retry a few times with short backoff before giving
            #     up. (A durable retry queue is the production-scale upgrade; this covers blips.)
            last_err = None
            for attempt in range(settings.SAR_GENERATION_MAX_ATTEMPTS):
                try:
                    sar = generate_sar(alert.id, db, retrieved_chunks=retrieved_chunks)
                    last_err = None
                    break
                except Exception as e:  # noqa: BLE001 — retry on any generation failure
                    last_err = e
                    db.rollback()
                    if attempt + 1 < settings.SAR_GENERATION_MAX_ATTEMPTS:
                        time.sleep(settings.SAR_GENERATION_RETRY_BACKOFF_SECONDS * (attempt + 1))
            if last_err is not None:
                raise last_err

            # 5. Finalize. When AUTO_APPROVE_SARS is on, skip manual officer review and
            #    deliver the finished report straight to the bank (the bank's admin makes
            #    the final file-with-FIU call). Otherwise leave it pending officer review.
            if settings.AUTO_APPROVE_SARS:
                from app.services.sar_delivery import finalize_and_deliver
                finalize_and_deliver(alert, db, "Automated compliance review (auto-approved)")
            else:
                alert.status = "PROCESSING_COMPLETED"
                alert.processing_completed_at = __import__('sqlalchemy').func.now()
            db.commit()
        except Exception as e:
            _mark_processing_failed(db, alert_id, e)
    finally:
        db.close()

def fail_stuck_processing_alerts(started_before: datetime) -> int:
    """Mark alerts left in PROCESSING since before `started_before` as PROCESSING_FAILED.

    SAR generation runs in-process, so an alert whose worker died mid-generation
    (crash, restart, OOM) would sit in PROCESSING forever with no draft. Called
    from the startup sweep in main.py; uses the same failure state as
    process_alert_background so it shows up as failed in the queue and metrics."""
    db = SessionLocal()
    try:
        count = db.query(Alert).filter(
            Alert.status == "PROCESSING",
            func.coalesce(Alert.processing_started_at, Alert.created_at) < started_before,
        ).update(
            {
                "status": "PROCESSING_FAILED",
                "processing_error": "SAR generation was interrupted: the API worker stopped before it finished.",
            },
            synchronize_session=False,
        )
        db.commit()
        return count
    finally:
        db.close()

@router.post("/")
def ingest_payload(
    request: Request,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(enforce_tenant_ingest_quota),
    body: bytes = Depends(_read_ingest_body),
):
    try:
        return _ingest_payload(request, db, tenant, body)
    finally:
        # Return the pooled connection before leaving this worker thread. get_db
        # only closes the session in a later threadpool hop; under a burst, every
        # thread ended up waiting for a connection held by a request that was
        # itself waiting for a thread, and all of them hit pool_timeout.
        db.close()

def _ingest_payload(request: Request, db: Session, tenant: Tenant, body: bytes):
    # Content-Length was checked pre-auth, but a chunked/lying client can send
    # more bytes than declared — enforce against what actually arrived
    if len(body) > settings.MAX_INGEST_PAYLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Payload exceeds the maximum allowed size")

    try:
        raw_payload, has_non_finite = _loads_payload(body)
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

    # 1b. Validate what lands in typed columns (422 naming the field, never a 500).
    # A missing ref_id is not an error: schemas without one (SEBI_BROKER,
    # PAYMENT_GW) and payloads that omit it get a generated, clearly-marked id.
    # It used to store the literal 'None' (the normalizer maps a missing path to None).
    field_map = schema.field_map or {}
    transaction_id = (
        _clean_text_field(normalized, field_map, "transaction_id") or f"AUTO-{uuid.uuid4()}"
    )
    transaction_amount = _parse_amount(normalized, field_map)
    transaction_currency = _clean_text_field(normalized, field_map, "transaction_currency")
    transaction_type = _clean_text_field(normalized, field_map, "transaction_type")
    try:
        transaction_timestamp = _parse_txn_timestamp(normalized.get("transaction_timestamp"))
    except _TimestampOutOfRange:
        low, high = _TXN_TIMESTAMP_YEARS
        raise _field_error("transaction_timestamp", field_map, f"is out of range (years {low}-{high} UTC)")
    except ValueError:
        raise _field_error("transaction_timestamp", field_map, "must be an ISO 8601 datetime")
    _check_risk_score(normalized, field_map)
    if has_non_finite:
        raise HTTPException(
            status_code=422,
            detail="Payload contains a non-finite number (NaN, Infinity or out of range)",
        )
    if not _encodes_as_utf8(raw_payload):
        raise HTTPException(
            status_code=422,
            detail="Payload contains an unpaired UTF-16 surrogate (a lone \\ud800-\\udfff escape)",
        )

    # 2. Mask PII
    masked_payload, token_map = mask_payload(normalized, schema.pii_fields)
    
    # 3. Compliance Analysis
    analysis_results = analyze(normalized)
    
    # Composite risk = bank's own score (base) + Aegis's triggered typology rules.
    # See services/risk_scoring.py for the model and why RISK_SCORE_THRESHOLD scores 0.
    risk_score = compute_composite_risk(normalized.get("risk_score"), analysis_results)

    # Create Alert
    alert = Alert(
        tenant_id=tenant.id,
        schema_id=schema.id,
        status="PROCESSING",
        raw_payload=raw_payload,
        normalized_payload=normalized,
        masked_payload=masked_payload,
        transaction_id=transaction_id,
        transaction_amount=transaction_amount,
        # Persist the payload's real currency/timestamp into the typed columns.
        # When absent, leave them NULL (the summary falls back to the tenant default /
        # created_at) rather than letting the column's 'INR'/NULL default masquerade as
        # a real value — a USD txn was previously always shown as INR.
        transaction_currency=transaction_currency,
        transaction_type=transaction_type,
        transaction_timestamp=transaction_timestamp,
        risk_score=risk_score,  # already clamped to 0..100 by compute_composite_risk
        is_synthetic=False,
        idempotency_key=idempotency_key,
        ingested_from_ip=request.client.host if request.client else None,
        processing_started_at=__import__('sqlalchemy').func.now()
    )
    db.add(alert)
    try:
        # Flush (not commit) to get the server-generated id, so the alert, its PII
        # map and its matches commit together: a failure part-way can no longer
        # leave a half-written alert stuck in PROCESSING
        db.flush()

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
    except IntegrityError:
        # Two identical requests raced past the SELECT: the unique constraint
        # on (tenant_id, idempotency_key) is the authoritative guard
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate submission rejected (idempotency key already processed)")
    except DataError as e:
        # Last line of defence behind the validation above (e.g. a \u0000 in a
        # mapped field, which JSONB refuses): the client's data, not a server fault
        db.rollback()
        # Error class only: the DB message can quote the offending payload value
        print(f"Ingest rejected by the database for tenant {tenant.id}: {type(e.orig).__name__}")
        raise HTTPException(
            status_code=422,
            detail="Payload contains a value that cannot be stored (invalid or out-of-range field)",
        )
    db.refresh(alert)

    # NOTE: the alert is now persisted in Postgres (alerts table) — the source of
    # truth for live transactions. We deliberately do NOT mirror it to the per-client
    # folder here; for offline eval, export a sample from the DB on demand instead.

    if warrants_sar(alert.risk_score):
        # Threshold met, trigger SAR generation
        _sar_executor.submit(process_alert_background, alert.id)
    else:
        alert.status = "COMPLETED_CLEAN"
        alert.processing_completed_at = __import__('sqlalchemy').func.now()
        db.commit()

    return {
        "status": "success",
        "alert_id": alert.id,
        "risk_score": alert.risk_score,
        "message": "Ingested successfully. SAR generation triggered." if warrants_sar(alert.risk_score) else "Ingested successfully. No SAR required."
    }
