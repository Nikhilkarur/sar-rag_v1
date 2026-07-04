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
from app.models.compliance import ComplianceMatch
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

def _llm_usage_from_drafts(db: Session, tenant_id):
    """(requests, tokens) derived from the SAR drafts — one draft == one SAR == one
    generation. This is authoritative and drift-proof, unlike the mutable llm_config
    counters (which under-counted after a couple of missed increments).
    Synthetic (portal-simulator) drafts are EXCLUDED — like every other customer-facing
    metric, and so the customer is never shown (or billed) usage from our own test button."""
    row = db.query(
        func.count(SARDraft.id),
        func.coalesce(func.sum(func.coalesce(SARDraft.prompt_tokens, 0)
                               + func.coalesce(SARDraft.completion_tokens, 0)), 0),
    ).join(Alert, Alert.id == SARDraft.alert_id).filter(
        SARDraft.tenant_id == tenant_id,
        Alert.is_synthetic == False,  # noqa: E712
    ).first()
    return int(row[0] or 0), int(row[1] or 0)


@router.get("/llm-config")
def get_llm_config(db: Session = Depends(get_db), current_user: User = Depends(get_tenant_admin)):
    llm = db.query(LLMConfig).filter(LLMConfig.tenant_id == current_user.tenant_id).first()
    if not llm:
        raise HTTPException(status_code=404, detail="LLM config not found")
    requests, tokens = _llm_usage_from_drafts(db, current_user.tenant_id)
    return {
        "provider": llm.provider,
        "model_name": llm.model_name,
        "sar_template_style": llm.sar_template_style,
        "total_tokens_used": tokens,
        "total_requests": requests,
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

def _pct_delta(current: int, previous: int) -> int | None:
    # No prior-month baseline -> percent change is undefined (not "+100%"). Return None so the
    # UI can show "new" instead of a misleading number. Both zero -> 0 (genuinely flat).
    if previous <= 0:
        return None if current > 0 else 0
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

    # "Avg review time" is a HUMAN metric: measure only officer-approved alerts
    # (reviewed_by set). Auto-approved SARs have reviewed_at ≈ created_at + pipeline
    # seconds — including them would report the LLM latency as "review time".
    avg_secs = real(db.query(func.avg(func.extract('epoch', Alert.reviewed_at - Alert.created_at)))).filter(
        Alert.status == 'APPROVED', Alert.reviewed_at.isnot(None),
        Alert.reviewed_by.isnot(None)).scalar()
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

    # Monthly alert-outcome stack (last 6 months) — same terminal-status buckets as the admin
    # Overview, scoped to THIS tenant. "cleared" = closed with NO SAR (COMPLETED_CLEAN below
    # threshold, or REJECTED by an officer) — the same definition as the "Cleared — no SAR" KPI
    # above, so the card and the chart segment always agree.
    #   filed = APPROVED · review = drafted/awaiting file · cleared = no SAR · failed = PROCESSING_FAILED
    STATUS_BUCKET = {
        'APPROVED': 'filed',
        'PROCESSING_COMPLETED': 'review',
        'PENDING_REVIEW': 'review',
        'COMPLETED_CLEAN': 'cleared',
        'REJECTED': 'cleared',
        'PROCESSING_FAILED': 'failed',
    }
    MONTH_ABBR = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    keys, yy, mm = [], now.year, now.month
    for _ in range(6):
        keys.append(f"{yy:04d}-{mm:02d}")
        mm -= 1
        if mm == 0:
            mm, yy = 12, yy - 1
    keys = list(reversed(keys))
    buckets = {k: {'filed': 0, 'review': 0, 'cleared': 0, 'failed': 0} for k in keys}
    m_expr = func.to_char(Alert.created_at, 'YYYY-MM')
    outcome_rows = real(db.query(m_expr, Alert.status, func.count(Alert.id))).filter(
        Alert.created_at >= six_months).group_by(m_expr, Alert.status).all()
    for mk, status, cnt in outcome_rows:
        seg = STATUS_BUCKET.get(status)
        if mk in buckets and seg:
            buckets[mk][seg] += int(cnt or 0)
    outcome_monthly = [{"month": k, "label": MONTH_ABBR[int(k.split('-')[1])], **buckets[k]} for k in keys]

    # Typology mix (donut): which AML rules fire most for THIS tenant.
    typ_rows = db.query(
        ComplianceMatch.rule_id, ComplianceMatch.rule_name, func.count(ComplianceMatch.id)
    ).join(Alert, Alert.id == ComplianceMatch.alert_id).filter(
        Alert.tenant_id == tid, Alert.is_synthetic == False, Alert.is_deleted == False,
        ComplianceMatch.triggered == True,  # noqa: E712
    ).group_by(ComplianceMatch.rule_id, ComplianceMatch.rule_name).order_by(
        func.count(ComplianceMatch.id).desc()).all()
    typology = [{"rule_id": rid, "rule_name": rname, "count": int(c or 0)} for rid, rname, c in typ_rows]

    # LLM usage (tokens/requests) + processing failures — surfaced on the central dashboard.
    # Derived from SAR drafts (one draft == one generation) so "requests" can never be less
    # than "SARs filed".
    total_requests, tokens_used = _llm_usage_from_drafts(db, tid)
    failed_count = real(db.query(func.count(Alert.id))).filter(
        Alert.status == 'PROCESSING_FAILED').scalar() or 0

    # Amount screened vs flagged (this month, INR). Screened = value of every alert we assessed;
    # flagged = value of the alerts that escalated to a SAR (filed or in review).
    ESCALATED = ['APPROVED', 'PROCESSING_COMPLETED', 'PENDING_REVIEW']
    amount_screened = real(db.query(func.coalesce(func.sum(Alert.transaction_amount), 0))).filter(
        Alert.created_at >= month_start).scalar() or 0
    amount_flagged = real(db.query(func.coalesce(func.sum(Alert.transaction_amount), 0))).filter(
        Alert.created_at >= month_start, Alert.status.in_(ESCALATED)).scalar() or 0

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
        "outcome_monthly": outcome_monthly,
        "typology": typology,
        "tokens_used": tokens_used,
        "total_requests": total_requests,
        "failed_count": failed_count,
        "amount_screened_inr": float(amount_screened),
        "amount_flagged_inr": float(amount_flagged),
    }


# ── Billing ──────────────────────────────────────────────────────────
# Usage-based pricing: the first FREE_SARS SARs each month (~FREE_TOKENS tokens) are free;
# beyond that each SAR is billed per report. Two drafting tiers:
#   Standard drafting  = PRICE_PER_SAR_INR        (Sonnet 4.6)
#   Premium drafting   = PREMIUM_PRICE_PER_SAR_INR (Opus 4.8 — highest-quality narratives)
# Metered on the actual SAR drafts, so the amount due is computed from real usage.
FREE_SARS = 36
FREE_TOKENS = 100_000
PRICE_PER_SAR_INR = 5           # Standard drafting tier
PREMIUM_PRICE_PER_SAR_INR = 10  # Premium drafting tier
# Drafting-tier labels shown to customers. We deliberately do NOT expose the underlying
# third-party model (Aegis-managed, chosen by plan) — the product is the tier, not the vendor.
STANDARD_MODEL = "Standard"
PREMIUM_MODEL = "Premium"

# Comped tenants — billed Rs.0 regardless of usage (our own test/partner banks). Keyed by
# the public tenant id. TEN-0005 (Meridian) is the live integration/demo tenant.
FREE_ACCESS_TENANTS = {"TEN-0005"}
FREE_ACCESS_LABEL = "Your bank has special free access — all SARs are free."

# Committed-volume plans have a price DERIVED from the standard per-SAR rate — a plan just
# prepays a monthly SAR allotment at PRICE_PER_SAR_INR (the FREE_SARS are still on the house),
# so the landing page and the dashboard can never quote a number the billing engine wouldn't.
# monthly_inr = (included_sars - FREE_SARS) * PRICE_PER_SAR_INR ; None = per-SAR / custom.
def _plan_price(included: int | None) -> int | None:
    if included is None:
        return None
    return max(0, included - FREE_SARS) * PRICE_PER_SAR_INR


def billing_plans() -> list[dict]:
    # (id, name, included_sars, monthly_inr, per_sar_inr, model, description, features)
    tiers = [
        ("standard", "Standard Drafting", FREE_SARS, _plan_price(FREE_SARS), PRICE_PER_SAR_INR, STANDARD_MODEL,
         "Start here - 36 SARs free each month, then pay per report.",
         [f"{FREE_SARS} SARs / month free", f"Then Rs.{PRICE_PER_SAR_INR} per SAR", f"{STANDARD_MODEL} narratives", "1 officer seat"]),
        ("premium", "Premium Drafting", None, None, PREMIUM_PRICE_PER_SAR_INR, PREMIUM_MODEL,
         "Highest-quality narratives on our most capable model.",
         [f"Rs.{PREMIUM_PRICE_PER_SAR_INR} per SAR", f"{PREMIUM_MODEL} narratives", "Deeper policy citations", "Priority support"]),
        ("growth", "Growth", 500, _plan_price(500), PRICE_PER_SAR_INR, STANDARD_MODEL,
         "For teams filing regularly.",
         ["500 SARs / month", "5 officer seats", "Webhook delivery", "Email support"]),
        ("scale", "Scale", 2000, _plan_price(2000), PRICE_PER_SAR_INR, STANDARD_MODEL,
         "The full engine, around the clock.",
         ["2,000 SARs / month", "Unlimited seats", "HMAC-signed delivery", "Priority support"]),
        ("enterprise", "Enterprise", None, None, None, "Custom",
         "Dedicated infrastructure and custom typologies.",
         ["Unlimited SARs", "Custom rule packs", "Dedicated infrastructure", "SLA & onboarding"]),
    ]
    return [
        {
            "id": pid,
            "name": name,
            "included_sars": included,        # None = unlimited / per-SAR
            "monthly_inr": monthly,           # None = per-SAR / custom
            "per_sar_inr": per_sar,           # None = custom
            "effective_per_sar_inr": PRICE_PER_SAR_INR,
            "model": model,
            "description": desc,
            "features": feats,
        }
        for (pid, name, included, monthly, per_sar, model, desc, feats) in tiers
    ]


@router.get("/billing")
def get_billing(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_tenant_user)):
    tid = current_user.tenant_id
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Synthetic (simulator) drafts are never billable — a bank testing the pipeline with
    # the portal's own test button must not be charged for those SARs.
    row = db.query(
        func.count(SARDraft.id),
        func.coalesce(func.sum(func.coalesce(SARDraft.prompt_tokens, 0)
                               + func.coalesce(SARDraft.completion_tokens, 0)), 0),
    ).join(Alert, Alert.id == SARDraft.alert_id).filter(
        SARDraft.tenant_id == tid,
        SARDraft.created_at >= month_start,
        Alert.is_synthetic == False,  # noqa: E712
    ).first()
    sars_cycle = int(row[0] or 0)
    tokens_cycle = int(row[1] or 0)

    billable_sars = max(0, sars_cycle - FREE_SARS)
    amount_due = billable_sars * PRICE_PER_SAR_INR  # metered at the standard rate

    # Comped tenants (e.g. TEN-0005 / Meridian) never owe anything, regardless of usage.
    tenant = db.query(Tenant).filter(Tenant.id == tid).first()
    special_free_access = bool(tenant and tenant.tenant_id_public in FREE_ACCESS_TENANTS)
    if special_free_access:
        amount_due = 0

    # No per-tenant plan column yet — everyone is on standard drafting until they upgrade.
    plans = billing_plans()
    current_plan = "standard"
    # Suggest the smallest committed-VOLUME plan (growth/scale/enterprise) covering this cycle.
    # Comped tenants have free access, so never nudge them to a paid plan.
    recommended_plan = None if special_free_access else next(
        (p["id"] for p in plans
         if p["id"] in ("growth", "scale", "enterprise")
         and (p["included_sars"] is None or sars_cycle <= p["included_sars"])),
        "enterprise",
    )

    return {
        "cycle_start": month_start.isoformat(),
        "sars_this_cycle": sars_cycle,
        "tokens_this_cycle": tokens_cycle,
        "free_sars": FREE_SARS,
        "free_tokens": FREE_TOKENS,
        "price_per_sar_inr": PRICE_PER_SAR_INR,
        "premium_price_per_sar_inr": PREMIUM_PRICE_PER_SAR_INR,
        "standard_model": STANDARD_MODEL,
        "premium_model": PREMIUM_MODEL,
        "billable_sars": billable_sars,
        "amount_due_inr": amount_due,
        "within_free_tier": special_free_access or billable_sars == 0,
        "special_free_access": special_free_access,
        "special_access_label": FREE_ACCESS_LABEL if special_free_access else None,
        "currency": "INR",
        "plans": plans,
        "current_plan": current_plan,
        "recommended_plan": recommended_plan,
    }

# ── Approved SARs ────────────────────────────────────────────────────

@router.get("/sars")
def list_approved_sars(db: Session = Depends(get_db), current_user: User = Depends(get_compliance_user)):
    # Real filings only: synthetic (simulator) and soft-deleted alerts are excluded,
    # matching the usage KPIs so the history list and the "SARs approved" number agree.
    rows = db.query(Alert, SARDraft, User).join(
        SARDraft, SARDraft.alert_id == Alert.id
    ).outerjoin(
        User, User.id == Alert.reviewed_by
    ).filter(
        Alert.tenant_id == current_user.tenant_id,
        Alert.status == 'APPROVED',
        Alert.is_synthetic == False,  # noqa: E712
        Alert.is_deleted == False,  # noqa: E712
    ).order_by(Alert.reviewed_at.desc()).limit(100).all()

    return [
        {
            "sar_id": str(d.id),
            "transaction_id": a.transaction_id,
            "amount": float(a.transaction_amount or 0),
            # reviewed_by is NULL for the auto-approve path — label it honestly
            "approved_by": u.full_name if u else ("Auto-approved" if a.reviewed_by is None else "—"),
            "approved_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
        }
        for a, d, u in rows
    ]
