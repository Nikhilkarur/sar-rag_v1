"""
SAR finalization + delivery — shared by the manual approve endpoint (routers/alerts.py)
and the auto-approve path (routers/ingest.py background task).

Given an alert whose SAR draft exists, this rehydrates the PII into the bank-facing text,
builds the goAML STR, renders the PDF, marks the alert APPROVED, and delivers the finished
report to the tenant's webhook (real HTTP if a callback URL is set, plus an internal sink
event for audit). It does NOT commit — the caller owns the transaction.
"""
from datetime import datetime

import sqlalchemy
from sqlalchemy.orm import Session

from app.config import settings
from app.models.sar import SARDraft
from app.models.pii_map import PIIMap
from app.models.compliance import ComplianceMatch
from app.models.tenant import Tenant
from app.models.webhook import WebhookConfig, WebhookSinkEvent
from app.services.pii_masker import rehydrate_text
from app.services.goaml_builder import build_goaml_str, build_goaml_xml
from app.services.sar_pdf import render_sar_pdf
from app.utils.security import decrypt_json, validate_webhook_url


def _triggered_rule_ids(db: Session, alert_id) -> list:
    rows = db.query(ComplianceMatch.rule_id).filter(
        ComplianceMatch.alert_id == alert_id,
        ComplianceMatch.triggered == True,  # noqa: E712
    ).all()
    return [r[0] for r in rows]


def build_draft_pdf_bytes(db: Session, draft) -> bytes | None:
    """Re-render an approved SAR's PDF from stored data — in memory, never persisted.
    Used by the officer's on-demand download (/files/sar). Returns None if unresolved."""
    from app.models.alert import Alert
    from app.models.user import User
    alert = db.query(Alert).filter(Alert.id == draft.alert_id).first()
    if not alert:
        return None
    tenant = db.query(Tenant).filter(Tenant.id == draft.tenant_id).first()
    rule_ids = _triggered_rule_ids(db, alert.id)
    approver = db.query(User).filter(User.id == alert.reviewed_by).first() if alert.reviewed_by else None
    approver_name = approver.full_name if approver else "Automated compliance review"
    approved_at_iso = alert.reviewed_at.isoformat() if alert.reviewed_at else datetime.utcnow().isoformat() + "Z"
    goaml = build_goaml_str(alert, draft, rule_ids, tenant, approver_name, approved_at_iso)
    return render_sar_pdf(str(draft.id), alert, draft, goaml, approver_name, approved_at_iso)


def _deliver_webhook(callback_url: str, secret_encrypted, payload: dict) -> None:
    """POST the approved SAR to the bank's webhook, HMAC-signed. Non-fatal on failure."""
    import json as _json
    import hmac
    import hashlib
    import httpx
    try:
        # Re-validate at SEND time, not just at registration: a tenant can register a
        # public URL and later re-point its DNS at an internal/metadata address (DNS
        # rebinding). This payload carries real rehydrated PII, so refuse a target that
        # now resolves to a private/internal IP. (No-op-safe in development.)
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
        pass  # network/receiver failure is non-fatal


def finalize_and_deliver(alert, db: Session, approver_name: str, approver_user_id=None) -> dict:
    """Mark APPROVED, rehydrate PII, build goAML + PDF, deliver the webhook.
    `approver_name` is stamped into the goAML reporting_person + the webhook `approved_by`.
    `approver_user_id` is the reviewing user's id (None for auto-approval). Caller commits.
    """
    alert.status = "APPROVED"
    alert.reviewed_by = approver_user_id
    alert.reviewed_at = sqlalchemy.func.now()

    draft = db.query(SARDraft).filter(SARDraft.alert_id == alert.id).first()
    if not draft:
        return {}

    pii_map = db.query(PIIMap).filter(PIIMap.alert_id == alert.id).first()
    rehydrated = (rehydrate_text(draft.draft_text, pii_map.token_map)
                  if pii_map and pii_map.token_map else draft.draft_text)
    draft.approved_text = rehydrated
    draft.rehydrated_text = rehydrated
    if pii_map:
        pii_map.rehydrated_at = sqlalchemy.func.now()

    approved_at_iso = datetime.utcnow().isoformat() + "Z"
    rule_ids = _triggered_rule_ids(db, alert.id)
    tenant = db.query(Tenant).filter(Tenant.id == alert.tenant_id).first()
    goaml = build_goaml_str(alert, draft, rule_ids, tenant, approver_name, approved_at_iso)
    # goAML-aligned XML filing (well-formed; XSD certification pending). Delivered alongside
    # the JSON so the bank receives an actual submission-ready STR document, not just a struct.
    try:
        goaml_xml = build_goaml_xml(goaml)
    except Exception:
        goaml_xml = None

    # The SAR PDF carries REAL (rehydrated) PII, so it is NOT written to Aegis's disk. Render it
    # in memory: base64 it into the webhook (the bank keeps its OWN copy) and re-render on demand
    # for the officer's /files/sar download. Nothing PII-bearing is persisted to the filesystem.
    pdf_base64 = None
    try:
        import base64 as _b64
        pdf_bytes = render_sar_pdf(str(draft.id), alert, draft, goaml, approver_name, approved_at_iso)
        pdf_base64 = _b64.b64encode(pdf_bytes).decode("ascii")
        draft.pdf_generated_at = sqlalchemy.func.now()
    except Exception:
        pdf_base64 = None  # PDF render failure must not block approval/delivery
    pdf_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/files/sar/{draft.id}.pdf"

    delivery_payload = {
        "event": "sar.approved",
        "sar_id": str(draft.id),
        "alert_id": str(alert.id),
        "approved_at": approved_at_iso,
        "approved_by": approver_name,
        "goaml_str": goaml,
        "goaml_xml": goaml_xml,
        "pdf_url": pdf_url,
        "pdf_base64": pdf_base64,
        "pdf_filename": f"SAR-{draft.id}.pdf",
        "compliance_rules_triggered": rule_ids,
    }

    webhook = db.query(WebhookConfig).filter(WebhookConfig.tenant_id == alert.tenant_id).first()
    if webhook and webhook.is_active:
        if webhook.callback_url and not webhook.use_internal_sink:
            _deliver_webhook(webhook.callback_url, webhook.secret_encrypted, delivery_payload)
        # Audit copy WITHOUT the base64 blob — storing the whole PDF in the
        # webhook_sink_events JSONB on every approval would bloat the audit trail.
        sink_payload = {k: v for k, v in delivery_payload.items() if k != "pdf_base64"}
        db.add(WebhookSinkEvent(
            tenant_id=alert.tenant_id,
            payload=sink_payload,
            headers={"X-Aegis-Event": "sar.approved"},
            hmac_valid=True,
            source_ip="internal-sink",
        ))
    return delivery_payload
