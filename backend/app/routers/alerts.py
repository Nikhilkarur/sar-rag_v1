from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.deps import get_current_active_tenant_user, get_compliance_user, parse_uuid_or_404
from app.models.user import User
from app.models.alert import Alert
from app.models.schema import IngestionSchema
from app.models.pii_map import PIIMap
from app.models.compliance import ComplianceMatch
from app.models.sar import SARDraft
from app.models.webhook import WebhookConfig, WebhookSinkEvent
from app.services.pii_masker import mask_payload, rehydrate_text
from app.services.compliance_analyzer import analyze
from app.services.risk_scoring import compute_composite_risk, warrants_sar
from app.services.goaml_builder import build_goaml_str
from app.services.sar_delivery import finalize_and_deliver
from app.routers.ingest import process_alert_background
from app.config import settings
from app.models.tenant import Tenant
from app.utils.security import decrypt_json, validate_webhook_url
from datetime import datetime
from typing import Any
import secrets

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])

# Backend pipeline statuses → the statuses the portal filters/renders on
_STATUS_MAP = {
    "PROCESSING_COMPLETED": "PENDING_REVIEW",
    "PENDING_INGESTION": "PROCESSING",
}

def _public_status(status: str) -> str:
    return _STATUS_MAP.get(status, status)

def _summary(a: Alert, rules: list) -> dict:
    np = a.normalized_payload or {}
    return {
        "id": str(a.id),
        "transaction_id": a.transaction_id or str(np.get("transaction_id") or "—"),
        "transaction_amount": float(a.transaction_amount or 0),
        "transaction_currency": a.transaction_currency or str(np.get("transaction_currency") or "INR"),
        "transaction_type": a.transaction_type or str(np.get("transaction_type") or "—"),
        "transaction_direction": str(np.get("transaction_direction") or "DEBIT"),
        "transaction_timestamp": (a.transaction_timestamp or a.created_at).isoformat(),
        "risk_score": a.risk_score or 0,
        "status": _public_status(a.status),
        "triggered_rules": rules,
        "source": a.source,
        "is_synthetic": a.is_synthetic,
        "created_at": a.created_at.isoformat(),
    }

def _rules_by_alert(db: Session, alert_ids: list) -> dict:
    """One query for all alerts' rule ids — avoids N+1 on the queue."""
    if not alert_ids:
        return {}
    rows = db.query(ComplianceMatch.alert_id, ComplianceMatch.rule_id).filter(
        ComplianceMatch.alert_id.in_(alert_ids),
        ComplianceMatch.triggered == True,
    ).all()
    out: dict = {}
    for alert_id, rule_id in rows:
        out.setdefault(alert_id, []).append(rule_id)
    return out

# All rules the analyzer evaluates (for the "clean checks" panel)
_ALL_RULES = [
    ("STRUCTURING", "Structuring / Smurfing"),
    ("RAPID_MOVEMENT", "Rapid Movement of Funds"),
    ("ROUND_NUMBER", "Large Round Number"),
    ("DORMANT_ACTIVATION", "Dormant Account Activation"),
    ("HIGH_RISK_TYPE", "High Risk Transaction Type"),
    ("VELOCITY", "High Velocity"),
    ("COUNTERPARTY_RISK", "High Risk Counterparty"),
    ("RISK_SCORE_THRESHOLD", "Risk Score Threshold Exceeded"),
]

@router.get("/queue")
def list_alerts(include_synthetic: bool = False, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_tenant_user)):
    # Default excludes synthetic (portal-simulator) alerts so a real compliance officer sees
    # only real transactions. The DEV dashboard opts back in (?include_synthetic=true) so the
    # "Submit test alert" button's output is still visible while demoing.
    query = db.query(Alert).filter(Alert.tenant_id == current_user.tenant_id, Alert.is_deleted == False)
    if not include_synthetic:
        # Compliance metrics must be computed over real alerts only
        query = query.filter(Alert.is_synthetic == False)
    alerts = query.order_by(Alert.created_at.desc()).limit(500).all()
    rules_map = _rules_by_alert(db, [a.id for a in alerts])
    return [_summary(a, rules_map.get(a.id, [])) for a in alerts]

def _get_owned_alert(alert_id: str, db: Session, user: User) -> Alert:
    valid_id = parse_uuid_or_404(alert_id, "Alert")
    a = db.query(Alert).filter(Alert.id == valid_id, Alert.tenant_id == user.tenant_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    return a

@router.get("/queue/{alert_id}")
def get_alert(alert_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_tenant_user)):
    a = _get_owned_alert(alert_id, db, current_user)

    matches = db.query(ComplianceMatch).filter(ComplianceMatch.alert_id == a.id).all()
    triggered = [
        {
            "rule_id": m.rule_id,
            "rule_name": m.rule_name,
            "triggered": True,
            "confidence": m.confidence,
            "evidence": m.evidence or {},
        }
        for m in matches if m.triggered
    ]
    triggered_ids = {m.rule_id for m in matches if m.triggered}
    clean_checks = [
        {"rule_id": rid, "rule_name": name, "triggered": False}
        for rid, name in _ALL_RULES if rid not in triggered_ids
    ]
    score = a.risk_score or 0
    overall = "HIGH" if score >= 75 else "MEDIUM" if score >= 50 else "LOW"

    draft = db.query(SARDraft).filter(SARDraft.alert_id == a.id).first()
    sar_draft = None
    if draft:
        sar_draft = {
            "id": str(draft.id),
            "draft_text": draft.draft_text,
            # The structured half of the SAR (key indicators + recommended action).
            # Derived from MASKED data, so it carries no real PII — safe to render.
            "draft_structured": draft.draft_structured,
            "llm_model": draft.llm_model,
            "generation_latency_ms": draft.generation_latency_ms,
            "officer_edit_count": draft.officer_edit_count,
            "last_edited_at": draft.last_edited_at.isoformat() if draft.last_edited_at else None,
            "created_at": draft.created_at.isoformat(),
        }

    rules_map = _rules_by_alert(db, [a.id])
    return {
        **_summary(a, rules_map.get(a.id, [])),
        "masked_payload": a.masked_payload or {},
        "raw_payload": a.raw_payload or {},
        "compliance": {
            "overall_risk": overall,
            "triggered_rules": triggered,
            "clean_checks": clean_checks,
        },
        "sar_draft": sar_draft,
    }

@router.put("/queue/{alert_id}/draft")
def update_draft(alert_id: str, payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_compliance_user)):
    a = _get_owned_alert(alert_id, db, current_user)
    # A finalized SAR has already been rehydrated + delivered to the bank; editing
    # draft_text afterwards would silently diverge from the delivered approved_text.
    if a.status in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=409, detail=f"Alert already {a.status.lower()} — the draft can no longer be edited")
    draft = db.query(SARDraft).filter(SARDraft.alert_id == a.id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="No draft exists for this alert yet")
    text = payload.get("draft_text")
    if not isinstance(text, str) or not text.strip():
        raise HTTPException(status_code=400, detail="draft_text is required")
    draft.draft_text = text[:50000]
    draft.officer_edit_count += 1
    draft.last_edited_by = current_user.id
    draft.last_edited_at = __import__('sqlalchemy').func.now()
    db.commit()
    return {"status": "ok", "officer_edit_count": draft.officer_edit_count}

@router.get("/queue/{alert_id}/preview-rehydrated")
def preview_rehydrated(alert_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_compliance_user)):
    a = _get_owned_alert(alert_id, db, current_user)
    draft = db.query(SARDraft).filter(SARDraft.alert_id == a.id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="No draft exists for this alert yet")
    pii_map = db.query(PIIMap).filter(PIIMap.alert_id == a.id).first()
    text = draft.draft_text
    if pii_map and pii_map.token_map:
        text = rehydrate_text(text, pii_map.token_map)
    return {"rehydrated_text": text}

def _deliver_webhook(callback_url: str, secret_encrypted, payload: dict):
    """POST the approved SAR to the bank's webhook URL, HMAC-signed. A delivery
    failure must NOT fail the approval, so everything is wrapped."""
    import json as _json
    import hmac
    import hashlib
    import httpx
    try:
        # Re-validate at SEND time (DNS rebinding): a URL that was public at
        # registration may now resolve to an internal/metadata address, and this
        # payload carries real rehydrated PII. No-op-safe in development.
        validate_webhook_url(callback_url)
        body = _json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", "X-Aegis-Event": "sar.approved"}
        if secret_encrypted:
            try:
                secret = decrypt_json(secret_encrypted)
                headers["X-Aegis-Signature"] = "sha256=" + hmac.new(
                    str(secret).encode(), body, hashlib.sha256).hexdigest()
            except Exception:
                pass
        httpx.post(callback_url, content=body, headers=headers, timeout=8.0)
    except Exception:
        pass  # network/receiver failure is non-fatal for the demo


@router.post("/queue/{alert_id}/approve")
def approve_alert(alert_id: str, payload: Any = Body(default=None), db: Session = Depends(get_db), current_user: User = Depends(get_compliance_user)):
    a = _get_owned_alert(alert_id, db, current_user)
    if a.status in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=409, detail=f"Alert already {a.status.lower()}")
    # Approving requires a SAR to approve. Without this, a below-threshold
    # (COMPLETED_CLEAN) or still-PROCESSING alert could be marked APPROVED with no
    # draft — finalize_and_deliver would no-op and leave an "approved" SAR that was
    # never generated nor delivered.
    if not db.query(SARDraft.id).filter(SARDraft.alert_id == a.id).first():
        raise HTTPException(status_code=409, detail="No SAR draft exists for this alert — nothing to approve")

    # Officer approval → finalize + deliver (shared with the auto-approve path).
    finalize_and_deliver(a, db, current_user.full_name, current_user.id)

    db.commit()
    db.refresh(a)
    return {"status": "ok", "approved_at": a.reviewed_at.isoformat() if a.reviewed_at else None}

@router.post("/queue/{alert_id}/reject")
def reject_alert(alert_id: str, payload: dict = Body(default={}), db: Session = Depends(get_db), current_user: User = Depends(get_compliance_user)):
    a = _get_owned_alert(alert_id, db, current_user)
    if a.status in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=409, detail=f"Alert already {a.status.lower()}")
    a.status = 'REJECTED'
    a.reviewed_by = current_user.id
    a.reviewed_at = __import__('sqlalchemy').func.now()
    a.rejection_reason = str(payload.get("reason", "No reason provided"))[:2000]
    db.commit()
    return {"status": "ok"}

# --- Simulator: portal "Submit Test Alert" button ---

_SCENARIO_TEMPLATES = {
    "STRUCTURING":   {"transaction_amount": 990000, "transaction_type": "TRANSFER", "risk_score": 60, "alert_reason": "Near-threshold transfer"},
    "RAPID_MOVEMENT": {"transaction_amount": 500000, "transaction_type": "REVERSAL", "risk_score": 65, "alert_reason": "Large reversal shortly after credit"},
    "HIGH_RISK_TYPE": {"transaction_amount": 750000, "transaction_type": "INTERNATIONAL_WIRE", "risk_score": 70, "alert_reason": "High-risk transaction type"},
    "VELOCITY":      {"transaction_amount": 120000, "transaction_type": "TRANSFER", "risk_score": 90, "alert_reason": "High velocity - 8 transactions in 1 hour"},
    "DEFAULT":       {"transaction_amount": 250000, "transaction_type": "TRANSFER", "risk_score": 40, "alert_reason": "Routine review"},
}

@router.post("/simulator/submit-test-alert", status_code=202)
def submit_test_alert(
    payload: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_compliance_user),
):
    scenario = str(payload.get("scenario", "DEFAULT")).upper()
    if scenario not in _SCENARIO_TEMPLATES:
        raise HTTPException(status_code=400, detail=f"Unknown scenario '{scenario}'")

    txn_id = f"TEST-TXN-{datetime.utcnow().strftime('%Y%m%d')}{secrets.randbelow(100000):05d}"
    normalized = {
        "transaction_id": txn_id,
        "transaction_currency": "INR",
        "customer_name": "Test Customer",
        "customer_id": f"CUST-TEST-{secrets.randbelow(10000):04d}",
        "account_id": f"ACC-TEST-{secrets.randbelow(10000):04d}",
        **_SCENARIO_TEMPLATES[scenario],
    }
    if payload.get("custom_risk_score") is not None:
        try:
            normalized["risk_score"] = max(0, min(100, int(payload["custom_risk_score"])))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="custom_risk_score must be an integer between 0 and 100")

    schema = db.query(IngestionSchema).filter(
        IngestionSchema.tenant_id == current_user.tenant_id,
        IngestionSchema.is_active == True
    ).first()
    pii_fields = (schema.pii_fields if schema and schema.pii_fields else ["customer_name", "customer_id", "account_id"])

    masked_payload, token_map = mask_payload(normalized, pii_fields)
    analysis_results = analyze(normalized)

    # Same composite scoring as the live ingest path (single source of truth).
    risk_score = compute_composite_risk(normalized.get("risk_score"), analysis_results)

    alert = Alert(
        tenant_id=current_user.tenant_id,
        schema_id=schema.id if schema else None,
        status="PROCESSING",
        raw_payload=normalized,
        normalized_payload=normalized,
        masked_payload=masked_payload,
        transaction_id=txn_id,
        transaction_amount=normalized.get("transaction_amount"),
        transaction_type=normalized.get("transaction_type"),
        risk_score=risk_score,  # already clamped to 0..100 by compute_composite_risk
        source="SIMULATOR",
        is_synthetic=True,  # never counted in compliance metrics
        processing_started_at=__import__('sqlalchemy').func.now()
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    db.add(PIIMap(alert_id=alert.id, tenant_id=current_user.tenant_id, token_map=token_map))
    for r in analysis_results:
        if r["triggered"]:
            db.add(ComplianceMatch(
                alert_id=alert.id,
                tenant_id=current_user.tenant_id,
                rule_id=r["rule_id"],
                rule_name=r["rule_name"],
                triggered=True,
                confidence=r["confidence"],
                evidence=r["evidence"]
            ))
    db.commit()

    if warrants_sar(alert.risk_score):
        background_tasks.add_task(process_alert_background, alert.id)
    else:
        alert.status = "COMPLETED_CLEAN"
        alert.processing_completed_at = __import__('sqlalchemy').func.now()
        db.commit()

    return {
        "alert_id": str(alert.id),
        "message": "Test alert injected. Check the review queue in ~8 seconds.",
        "scenario_used": scenario,
        "synthetic_transaction_id": txn_id,
    }
