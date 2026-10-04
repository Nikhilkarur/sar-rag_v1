"""
SAR finalization + delivery — shared by the manual approve endpoint (routers/alerts.py)
and the auto-approve path (routers/ingest.py background task).

Given an alert whose SAR draft exists, this rehydrates the PII into the bank-facing text,
builds the goAML STR, renders the PDF, marks the alert APPROVED, and records the delivery of
the finished report to the tenant's webhook: a webhook_deliveries row (the real outcome) plus
an audit copy in webhook_sink_events. It does NOT commit — the caller owns the transaction;
the HTTP POST to an external callback is only sent once that transaction commits, from a
background thread that retries with backoff and writes every attempt's result to the row.
"""
import base64
import hashlib
import hmac
import json
import logging
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import sqlalchemy
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.sar import SARDraft
from app.models.pii_map import PIIMap
from app.models.compliance import ComplianceMatch
from app.models.tenant import Tenant
from app.models.delivery import WebhookDelivery
from app.models.webhook import WebhookConfig, WebhookSinkEvent
from app.services.pii_masker import rehydrate_text
from app.services.goaml_builder import build_goaml_str, build_goaml_xml
from app.services.sar_pdf import render_sar_pdf
from app.utils.security import decrypt_json, validate_webhook_url

logger = logging.getLogger(__name__)

# Approver stamped on SARs finalized without an officer (AUTO_APPROVE_SARS). Must match the
# name routers/ingest.py passes, so the re-rendered download matches the delivered PDF.
AUTO_APPROVER_NAME = "Automated compliance review (auto-approved)"
# destination_url recorded for deliveries to the built-in sink (no HTTP involved)
INTERNAL_SINK_DESTINATION = "internal-sink"

# Outbound delivery: bounded in-process retry with exponential backoff (2s, 4s, ...). Not
# durable across a restart — such a delivery stays PENDING/RETRYING, never "DELIVERED".
WEBHOOK_MAX_ATTEMPTS = 3
WEBHOOK_RETRY_BACKOFF_SECONDS = 2.0
WEBHOOK_TIMEOUT_SECONDS = 8.0


def format_approved_at(dt: datetime) -> str:
    """The one serialization of an approval time (UTC, ISO-8601, 'Z'), used by the delivered
    payload/goAML/PDF and by the officer's re-rendered download, so the two copies match."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(tzinfo=None).isoformat(timespec="microseconds") + "Z"


def _triggered_rule_ids(db: Session, alert_id) -> list:
    rows = db.query(ComplianceMatch.rule_id).filter(
        ComplianceMatch.alert_id == alert_id,
        ComplianceMatch.triggered == True,  # noqa: E712
    ).all()
    return [r[0] for r in rows]


def build_draft_pdf_bytes(db: Session, draft) -> bytes | None:
    """Re-render an approved SAR's PDF from stored data — in memory, never persisted.
    Used by the officer's on-demand download (/files/sar). Returns None unless the alert is
    APPROVED: a pending or rejected draft is not a filing and must not render as one."""
    from app.models.alert import Alert
    from app.models.user import User
    alert = db.query(Alert).filter(Alert.id == draft.alert_id).first()
    if not alert or alert.status != "APPROVED":
        return None
    tenant = db.query(Tenant).filter(Tenant.id == draft.tenant_id).first()
    rule_ids = _triggered_rule_ids(db, alert.id)
    # Same approver + approval time finalize_and_deliver stamped (reviewed_at is stored from
    # that exact value). reviewed_by is unset only on the auto-approve path.
    if alert.reviewed_by:
        approver = db.query(User).filter(User.id == alert.reviewed_by).first()
        approver_name = approver.full_name if approver else "Unknown officer"
    else:
        approver_name = AUTO_APPROVER_NAME
    approved_at_iso = format_approved_at(alert.reviewed_at) if alert.reviewed_at else None
    goaml = build_goaml_str(alert, draft, rule_ids, tenant, approver_name, approved_at_iso)
    return render_sar_pdf(str(draft.id), alert, draft, goaml, approver_name, approved_at_iso)


def _signature(secret_encrypted, body: bytes) -> str | None:
    """X-Aegis-Signature for `body`, or None if the tenant has no usable secret."""
    if not secret_encrypted:
        logger.warning("Webhook has no signing secret; delivering unsigned")
        return None
    try:
        secret = decrypt_json(secret_encrypted)
    except Exception:
        logger.exception("Webhook signing secret could not be decrypted; delivering unsigned")
        return None
    return "sha256=" + hmac.new(str(secret).encode(), body, hashlib.sha256).hexdigest()


def _post_once(url: str, body: bytes, headers: dict) -> tuple:
    """One POST attempt. Returns (ok, retryable, http_status, error)."""
    try:
        # Re-validate at SEND time, not just at registration: a tenant can register a
        # public URL and later re-point its DNS at an internal/metadata address (DNS
        # rebinding). This payload carries real rehydrated PII, so refuse a target that
        # now resolves to a private/internal IP. (No-op-safe in development.)
        validate_webhook_url(url)
    except ValueError as e:
        return False, False, None, f"Destination rejected: {e}"
    try:
        r = httpx.post(url, content=body, headers=headers, timeout=WEBHOOK_TIMEOUT_SECONDS)
    except Exception as e:  # network failure: connection refused, timeout, TLS, ...
        return False, True, None, f"{type(e).__name__}: {e}"[:500]
    if 200 <= r.status_code < 300:
        return True, False, r.status_code, None
    # A 4xx other than timeout/rate-limit is the receiver rejecting this exact request;
    # resending it unchanged won't help. 5xx/408/429 are transient.
    retryable = r.status_code >= 500 or r.status_code in (408, 429)
    return False, retryable, r.status_code, f"Receiver responded {r.status_code}"


def _record_attempt(delivery_id, attempt: int, status: str, http_status, error,
                    retry_in: float | None) -> None:
    db = SessionLocal()
    try:
        d = db.get(WebhookDelivery, delivery_id)
        if d is None:
            return
        now = datetime.now(timezone.utc)
        d.attempt_number = attempt
        d.attempted_at = now
        d.status = status
        d.http_status_code = http_status
        d.error_message = error
        d.delivered_at = now if status == "DELIVERED" else None
        d.next_retry_at = now + timedelta(seconds=retry_in) if retry_in else None
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Could not record webhook delivery %s attempt %d", delivery_id, attempt)
    finally:
        db.close()


def deliver_webhook(delivery_id, url: str, body: bytes, headers: dict) -> str | None:
    """POST a recorded delivery to the bank, retrying transient failures with exponential
    backoff, and write each attempt's real outcome to its webhook_deliveries row.
    Returns the final status, or None if the delivery is gone/already handled."""
    db = SessionLocal()
    try:
        d = db.get(WebhookDelivery, delivery_id)
        # Missing = the approving transaction rolled back; never send that SAR.
        if d is None or d.status != "PENDING":
            return None
    finally:
        db.close()

    for attempt in range(1, WEBHOOK_MAX_ATTEMPTS + 1):
        ok, retryable, http_status, error = _post_once(url, body, headers)
        final = ok or not retryable or attempt == WEBHOOK_MAX_ATTEMPTS
        backoff = WEBHOOK_RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
        status = "DELIVERED" if ok else ("FAILED" if final else "RETRYING")
        _record_attempt(delivery_id, attempt, status, http_status, error, None if final else backoff)
        if ok:
            logger.info("Webhook delivery %s to %s delivered (HTTP %s, attempt %d)",
                        delivery_id, url, http_status, attempt)
            return status
        if final:
            logger.error("Webhook delivery %s to %s FAILED after %d attempt(s): %s",
                         delivery_id, url, attempt, error)
            return status
        logger.warning("Webhook delivery %s to %s attempt %d/%d failed: %s; retrying in %.1fs",
                       delivery_id, url, attempt, WEBHOOK_MAX_ATTEMPTS, error, backoff)
        time.sleep(backoff)
    return None


def _deliver_after_commit(db: Session, delivery_id, url: str, body: bytes, headers: dict) -> None:
    """Send only once the approval is committed: a rolled-back approval must never reach the
    bank, and the HTTP round-trips/backoff must hold neither the request nor the row lock."""
    def _start(_session):
        threading.Thread(target=deliver_webhook, args=(delivery_id, url, body, headers),
                         name=f"webhook-delivery-{delivery_id}", daemon=True).start()
    event.listen(db, "after_commit", _start, once=True)


def _record_delivery(db: Session, alert, draft, webhook: WebhookConfig, payload: dict) -> None:
    """Record the delivery and its audit event; schedule the POST for an external callback."""
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "X-Aegis-Event": payload["event"]}
    signature = _signature(webhook.secret_encrypted, body)
    if signature:
        headers["X-Aegis-Signature"] = signature
    external = bool(webhook.callback_url and not webhook.use_internal_sink)
    now = datetime.now(timezone.utc)

    # The built-in sink is in-process: storing the event below IS the delivery.
    delivery = WebhookDelivery(
        id=uuid.uuid4(),
        sar_draft_id=draft.id,
        tenant_id=alert.tenant_id,
        destination_url=webhook.callback_url if external else INTERNAL_SINK_DESTINATION,
        is_internal_sink=not external,
        status="PENDING" if external else "DELIVERED",
        attempt_number=0 if external else 1,
        max_attempts=WEBHOOK_MAX_ATTEMPTS if external else 1,
        request_headers=headers,
        request_body_hash=hashlib.sha256(body).hexdigest(),
        hmac_signature=signature,
        attempted_at=now,
        delivered_at=None if external else now,
    )
    db.add(delivery)
    db.flush()  # the audit event below references the delivery row

    # Audit copy WITHOUT the base64 blob — storing the whole PDF in the
    # webhook_sink_events JSONB on every approval would bloat the audit trail.
    sink_payload = {k: v for k, v in payload.items() if k != "pdf_base64"}
    db.add(WebhookSinkEvent(
        tenant_id=alert.tenant_id,
        payload=sink_payload,
        headers={"X-Aegis-Event": payload["event"]},
        hmac_valid=signature is not None,
        source_ip="internal-sink",
        delivery_id=delivery.id,
    ))
    if external:
        _deliver_after_commit(db, delivery.id, webhook.callback_url, body, headers)


def finalize_and_deliver(alert, db: Session, approver_name: str, approver_user_id=None) -> dict:
    """Mark APPROVED, rehydrate PII, build goAML + PDF, record + schedule the webhook delivery.
    `approver_name` is stamped into the goAML reporting_person + the webhook `approved_by`.
    `approver_user_id` is the reviewing user's id (None for auto-approval). Caller commits.
    """
    # One approval timestamp, taken here and stored as reviewed_at (not func.now(), which is
    # the DB clock): the payload, goAML, PDF and the officer's later re-render all use it.
    approved_at = datetime.now(timezone.utc)
    alert.status = "APPROVED"
    alert.reviewed_by = approver_user_id
    alert.reviewed_at = approved_at

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

    approved_at_iso = format_approved_at(approved_at)
    rule_ids = _triggered_rule_ids(db, alert.id)
    tenant = db.query(Tenant).filter(Tenant.id == alert.tenant_id).first()
    goaml = build_goaml_str(alert, draft, rule_ids, tenant, approver_name, approved_at_iso)
    # goAML-aligned XML filing (well-formed; XSD certification pending). Delivered alongside
    # the JSON so the bank receives an actual submission-ready STR document, not just a struct.
    try:
        goaml_xml = build_goaml_xml(goaml)
    except Exception:
        logger.exception("goAML XML build failed for SAR %s", draft.id)
        goaml_xml = None

    # The SAR PDF carries REAL (rehydrated) PII, so it is NOT written to Aegis's disk. Render it
    # in memory: base64 it into the webhook (the bank keeps its OWN copy) and re-render on demand
    # for the officer's /files/sar download. Nothing PII-bearing is persisted to the filesystem.
    pdf_base64 = None
    try:
        pdf_bytes = render_sar_pdf(str(draft.id), alert, draft, goaml, approver_name, approved_at_iso)
        pdf_base64 = base64.b64encode(pdf_bytes).decode("ascii")
        draft.pdf_generated_at = sqlalchemy.func.now()
    except Exception:
        # PDF render failure must not block approval/delivery
        logger.exception("SAR PDF render failed for SAR %s", draft.id)
        pdf_base64 = None
    pdf_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/files/sar/{draft.id}.pdf"

    # Simulator alerts are synthetic: mark them like the /tenant/webhook/test ping (test: true)
    # and under their own event name, so the bank can never file one as a real STR.
    is_test = bool(alert.is_synthetic)
    delivery_payload = {
        "event": "sar.approved.test" if is_test else "sar.approved",
        "test": is_test,
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
        _record_delivery(db, alert, draft, webhook, delivery_payload)
    return delivery_payload
