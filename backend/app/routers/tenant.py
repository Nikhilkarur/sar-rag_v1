import hashlib
import hmac as hmac_mod
import json
import secrets as pysecrets
import time
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import tenant_service
from app.utils.deps import get_tenant_admin, get_current_active_tenant_user, get_compliance_user
from app.utils.security import (
    validate_webhook_url, encrypt_json, decrypt_json,
    generate_api_key, hash_api_key,
)
from app.models.user import User
from app.models.tenant import Tenant
from app.models.alert import Alert
from app.models.sar import SARDraft
from app.models.llm_config import LLMConfig
from app.models.schema import IngestionSchema
from app.models.webhook import WebhookConfig, WebhookSinkEvent
from app.models.audit import AuditLog
from app.data.schema_presets import SCHEMA_PRESETS
from app.schemas.tenant import TenantResponse

router = APIRouter(prefix="/api/v1/tenant", tags=["Tenant"])

@router.get("/profile", response_model=TenantResponse)
def get_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_tenant_user)):
    return tenant_service.get_profile(current_user, db)

# ── Credentials ──────────────────────────────────────────────────────

@router.get("/credentials")
def get_credentials(db: Session = Depends(get_db), current_user: User = Depends(get_tenant_admin)):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    return {
        "tenant_id_public": tenant.tenant_id_public,
        "api_key_prefix": tenant.api_key_prefix,
        "api_key_last_rotated": tenant.api_key_last_rotated.isoformat() if tenant.api_key_last_rotated else None,
    }

@router.get("/credentials/reveal")
def reveal_api_key(db: Session = Depends(get_db), current_user: User = Depends(get_tenant_admin)):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant.api_key_encrypted:
        raise HTTPException(
            status_code=409,
            detail="This key predates reveal support and cannot be recovered. Rotate to get a new revealable key."
        )
    db.add(AuditLog(tenant_id=tenant.id, user_id=current_user.id, action="API_KEY_REVEALED",
                    entity_type="tenant", entity_id=tenant.id))
    db.commit()
    return {"api_key": decrypt_json(tenant.api_key_encrypted)}

@router.post("/credentials/rotate")
def rotate_api_key(db: Session = Depends(get_db), current_user: User = Depends(get_tenant_admin)):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    new_key = generate_api_key()
    tenant.api_key_hash = hash_api_key(new_key)
    tenant.api_key_encrypted = encrypt_json(new_key)
    tenant.api_key_prefix = new_key[:12]
    tenant.api_key_last_rotated = func.now()
    db.add(AuditLog(tenant_id=tenant.id, user_id=current_user.id, action="API_KEY_ROTATED",
                    entity_type="tenant", entity_id=tenant.id))
    db.commit()
    return {"new_api_key": new_key, "api_key_prefix": tenant.api_key_prefix}

# ── Webhook ──────────────────────────────────────────────────────────

def _webhook_dict(w: WebhookConfig, tenant: Tenant) -> dict:
    return {
        "callback_url": w.callback_url,
        "use_internal_sink": w.use_internal_sink,
        "internal_sink_url": f"/api/v1/webhooks/sink/{tenant.tenant_id_public}",
        "secret_prefix": w.secret_prefix,
        "last_tested_at": w.last_tested_at.isoformat() if w.last_tested_at else None,
        "last_test_status": w.last_test_status,
    }

def _get_webhook(db: Session, user: User) -> tuple:
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    webhook = db.query(WebhookConfig).filter(WebhookConfig.tenant_id == user.tenant_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook config not found")
    return webhook, tenant

@router.get("/webhook")
def get_webhook(db: Session = Depends(get_db), current_user: User = Depends(get_tenant_admin)):
    webhook, tenant = _get_webhook(db, current_user)
    return _webhook_dict(webhook, tenant)

@router.put("/webhook")
def update_webhook(payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_tenant_admin)):
    webhook, tenant = _get_webhook(db, current_user)

    use_internal_sink = bool(payload.get("use_internal_sink", webhook.use_internal_sink))
    callback_url = payload.get("callback_url", webhook.callback_url)

    if not use_internal_sink:
        if not callback_url:
            raise HTTPException(status_code=400, detail="callback_url is required when not using the internal sink")
        try:
            # SSRF guard: refuse URLs resolving to loopback/RFC1918/link-local
            # (cloud metadata), reserved or multicast ranges
            validate_webhook_url(callback_url)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    webhook.use_internal_sink = use_internal_sink
    webhook.callback_url = callback_url

    db.add(AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="WEBHOOK_CONFIG_UPDATED",
        entity_type="webhook_config",
        entity_id=webhook.id,
        details={"use_internal_sink": use_internal_sink}
    ))
    db.commit()
    db.refresh(webhook)
    return _webhook_dict(webhook, tenant)

def _ensure_webhook_secret(webhook: WebhookConfig) -> str:
    """Secrets created before encrypted storage are unrecoverable (bcrypt) —
    rotate transparently so signing works."""
    if webhook.secret_encrypted:
        return decrypt_json(webhook.secret_encrypted)
    secret = pysecrets.token_hex(32)
    webhook.secret_encrypted = encrypt_json(secret)
    webhook.secret_prefix = secret[:12]
    webhook.secret_hash = hash_api_key(secret)
    return secret

@router.post("/webhook/test")
def test_webhook(db: Session = Depends(get_db), current_user: User = Depends(get_tenant_admin)):
    webhook, tenant = _get_webhook(db, current_user)
    secret = _ensure_webhook_secret(webhook)

    sample = {
        "event": "sar.approved",
        "test": True,
        "sar_id": "00000000-0000-0000-0000-000000000000",
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "narrative_text": "TEST PAYLOAD — Aegis AML webhook connectivity check.",
        "compliance_rules_triggered": ["STRUCTURING"],
    }
    body = json.dumps(sample, separators=(",", ":")).encode("utf-8")
    signature = hmac_mod.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-Aegis-Signature": f"sha256={signature}",
        "X-Aegis-Event": "webhook.test",
    }

    start = time.monotonic()
    if webhook.use_internal_sink or not webhook.callback_url:
        db.add(WebhookSinkEvent(
            tenant_id=current_user.tenant_id,
            payload=sample,
            headers=headers,
            hmac_valid=True,
            source_ip="internal-sink",
        ))
        status, message = "SUCCESS", "Delivered to the built-in sink."
        latency_ms = max(1, int((time.monotonic() - start) * 1000))
    else:
        try:
            validate_webhook_url(webhook.callback_url)  # re-check at send time (DNS rebinding)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        try:
            r = httpx.post(webhook.callback_url, content=body, headers=headers, timeout=6.0)
            latency_ms = int((time.monotonic() - start) * 1000)
            ok = 200 <= r.status_code < 300
            status = "SUCCESS" if ok else "FAILED"
            message = f"Receiver responded {r.status_code}."
        except Exception as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            status, message = "FAILED", f"Delivery failed: {type(e).__name__}"

    webhook.last_tested_at = func.now()
    webhook.last_test_status = status
    db.commit()
    return {"status": status, "latency_ms": latency_ms, "message": message}

@router.get("/webhook/events")
def webhook_events(db: Session = Depends(get_db), current_user: User = Depends(get_tenant_admin)):
    webhook, tenant = _get_webhook(db, current_user)
    events = db.query(WebhookSinkEvent).filter(
        WebhookSinkEvent.tenant_id == current_user.tenant_id
    ).order_by(WebhookSinkEvent.received_at.desc()).limit(10).all()
    return [
        {
            "id": str(e.id),
            "received_at": e.received_at.isoformat(),
            "hmac_valid": bool(e.hmac_valid),
            "status": "DELIVERED",
            "http_status": 200,
            "destination": webhook.callback_url if not webhook.use_internal_sink and webhook.callback_url
                           else f"/api/v1/webhooks/sink/{tenant.tenant_id_public}",
            "payload": e.payload,
        }
        for e in events
    ]

# ── Ingestion schemas ────────────────────────────────────────────────

def _schema_dict(s: IngestionSchema) -> dict:
    return {
        "id": str(s.id),
        "name": s.name,
        "template_key": s.template_key,
        "is_active": s.is_active,
        "field_map": s.field_map,
        "pii_fields": s.pii_fields,
    }

@router.get("/schemas")
def get_schemas(db: Session = Depends(get_db), current_user: User = Depends(get_tenant_admin)):
    schemas = db.query(IngestionSchema).filter(IngestionSchema.tenant_id == current_user.tenant_id).all()
    return [_schema_dict(s) for s in schemas]

@router.post("/schemas/select-preset")
def select_schema_preset(payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_tenant_admin)):
    key = str(payload.get("template_key", "")).upper()
    preset = SCHEMA_PRESETS.get(key)
    if not preset:
        raise HTTPException(status_code=400, detail=f"Unknown schema preset '{key}'")

    db.query(IngestionSchema).filter(
        IngestionSchema.tenant_id == current_user.tenant_id
    ).update({IngestionSchema.is_active: False})

    existing = db.query(IngestionSchema).filter(
        IngestionSchema.tenant_id == current_user.tenant_id,
        IngestionSchema.template_key == key,
    ).first()
    if existing:
        existing.is_active = True
        existing.field_map = preset["field_map"]
        existing.pii_fields = preset["pii_fields"]
        schema = existing
    else:
        schema = IngestionSchema(
            tenant_id=current_user.tenant_id,
            name=preset["name"],
            template_key=key,
            is_active=True,
            field_map=preset["field_map"],
            pii_fields=preset["pii_fields"],
        )
        db.add(schema)

    db.add(AuditLog(tenant_id=current_user.tenant_id, user_id=current_user.id, action="SCHEMA_UPDATED",
                    entity_type="ingestion_schema", details={"template_key": key}))
    db.commit()
    db.refresh(schema)
    return _schema_dict(schema)

# ── LLM config ───────────────────────────────────────────────────────

@router.get("/llm-config")
def get_llm_config(db: Session = Depends(get_db), current_user: User = Depends(get_tenant_admin)):
    llm = db.query(LLMConfig).filter(LLMConfig.tenant_id == current_user.tenant_id).first()
    if not llm:
        raise HTTPException(status_code=404, detail="LLM config not found")
    return {
        "provider": llm.provider,
        "model_name": llm.model_name,
        "sar_template_style": llm.sar_template_style,
        "total_tokens_used": llm.total_tokens_used,
        "total_requests": llm.total_requests,
    }

@router.put("/llm-config")
def update_llm_config(payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_tenant_admin)):
    llm = db.query(LLMConfig).filter(LLMConfig.tenant_id == current_user.tenant_id).first()
    if not llm:
        raise HTTPException(status_code=404, detail="LLM config not found")
    style = str(payload.get("sar_template_style", "")).upper()
    if style not in ("NARRATIVE", "STRUCTURED", "BOTH"):
        raise HTTPException(status_code=400, detail="sar_template_style must be NARRATIVE, STRUCTURED or BOTH")
    llm.sar_template_style = style
    db.commit()
    return get_llm_config(db=db, current_user=current_user)

# ── Usage analytics (synthetic test alerts excluded) ─────────────────

def _pct_delta(current: int, previous: int) -> int:
    if previous <= 0:
        return 100 if current > 0 else 0
    return round((current - previous) / previous * 100)

@router.get("/usage")
def get_usage(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_tenant_user)):
    tid = current_user.tenant_id
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

    real = lambda q: q.filter(Alert.tenant_id == tid, Alert.is_synthetic == False, Alert.is_deleted == False)

    alerts_this = real(db.query(func.count(Alert.id))).filter(Alert.created_at >= month_start).scalar() or 0
    alerts_prev = real(db.query(func.count(Alert.id))).filter(
        Alert.created_at >= prev_month_start, Alert.created_at < month_start).scalar() or 0

    sars_this = real(db.query(func.count(Alert.id))).filter(
        Alert.status == 'APPROVED', Alert.reviewed_at >= month_start).scalar() or 0
    sars_prev = real(db.query(func.count(Alert.id))).filter(
        Alert.status == 'APPROVED', Alert.reviewed_at >= prev_month_start, Alert.reviewed_at < month_start).scalar() or 0

    pending = real(db.query(func.count(Alert.id))).filter(
        Alert.status.in_(['PROCESSING_COMPLETED', 'PENDING_REVIEW'])).scalar() or 0
    cleared = real(db.query(func.count(Alert.id))).filter(
        Alert.status.in_(['REJECTED', 'COMPLETED_CLEAN']), Alert.created_at >= month_start).scalar() or 0

    avg_secs = real(db.query(func.avg(func.extract('epoch', Alert.reviewed_at - Alert.created_at)))).filter(
        Alert.status == 'APPROVED', Alert.reviewed_at.isnot(None)).scalar()
    avg_review_minutes = round(float(avg_secs) / 60, 1) if avg_secs else 0

    # Daily breakdown — last 30 days
    since = now - timedelta(days=30)
    day_rows = real(db.query(
        func.date_trunc('day', Alert.created_at).label('d'),
        func.count(Alert.id),
        func.sum(case((Alert.status == 'APPROVED', 1), else_=0)),
    )).filter(Alert.created_at >= since).group_by('d').order_by('d').all()
    daily = [
        {"date": d.strftime('%Y-%m-%d'), "alerts": int(c or 0), "approved": int(ap or 0)}
        for d, c, ap in day_rows
    ]

    # Monthly SARs — last 6 months
    six_months = (month_start - timedelta(days=185)).replace(day=1)
    month_rows = real(db.query(
        func.date_trunc('month', Alert.reviewed_at).label('m'),
        func.count(Alert.id),
    )).filter(Alert.status == 'APPROVED', Alert.reviewed_at >= six_months).group_by('m').order_by('m').all()
    monthly = [{"month": m.strftime('%b'), "sars": int(c or 0)} for m, c in month_rows]

    return {
        "alerts_ingested": alerts_this,
        "delta_alerts": _pct_delta(alerts_this, alerts_prev),
        "sars_approved": sars_this,
        "delta_sars": _pct_delta(sars_this, sars_prev),
        "pending_review": pending,
        "false_positives_cleared": cleared,
        "avg_review_time_minutes": avg_review_minutes,
        "daily_breakdown": daily,
        "monthly_sars": monthly,
    }

# ── Approved SARs ────────────────────────────────────────────────────

@router.get("/sars")
def list_approved_sars(db: Session = Depends(get_db), current_user: User = Depends(get_compliance_user)):
    rows = db.query(Alert, SARDraft, User).join(
        SARDraft, SARDraft.alert_id == Alert.id
    ).outerjoin(
        User, User.id == Alert.reviewed_by
    ).filter(
        Alert.tenant_id == current_user.tenant_id,
        Alert.status == 'APPROVED',
    ).order_by(Alert.reviewed_at.desc()).limit(100).all()

    return [
        {
            "sar_id": str(d.id),
            "transaction_id": a.transaction_id,
            "amount": float(a.transaction_amount or 0),
            "approved_by": u.full_name if u else "—",
            "approved_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
        }
        for a, d, u in rows
    ]
