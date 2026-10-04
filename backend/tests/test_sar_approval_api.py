"""SAR approval → PDF download → webhook delivery, end to end through the API.

DB-backed: runs against DATABASE_URL (tables created if missing) and is skipped when that
database is unreachable. Each test seeds its own tenant, so no cleanup between tests is needed.
A local HTTP server stands in for the bank's webhook receiver.
"""
import base64
import hashlib
import hmac
import json
import socket
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from sqlalchemy import create_engine

from app.config import settings


def _db_reachable() -> bool:
    try:
        engine = create_engine(settings.DATABASE_URL, connect_args={"connect_timeout": 3})
        with engine.connect():
            pass
        engine.dispose()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_reachable(), reason="DATABASE_URL database is unreachable")

HINDI = "राजेश कुमार शर्मा"
ARABIC = "شركة الأفق الخليجي"


# ── Fake bank receiver ───────────────────────────────────────────────

class _Receiver:
    """Records every POST; responds with the status scripted for its path (default 200)."""

    def __init__(self):
        self.requests = []
        self.script = {}  # path -> list of status codes, consumed per request
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                receiver.requests.append({"path": self.path, "headers": dict(self.headers), "body": body})
                codes = receiver.script.get(self.path) or [200]
                code = codes.pop(0) if len(codes) > 1 else codes[0]
                self.send_response(code)
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def to(self, path):
        return [r for r in self.requests if r["path"] == path]


@pytest.fixture(scope="module")
def receiver():
    r = _Receiver()
    yield r
    r.server.shutdown()


# ── App + seed data ──────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.database import engine
    from app.models import Base
    from app.main import app
    Base.metadata.create_all(engine)
    return TestClient(app)


@pytest.fixture
def db():
    from app.database import SessionLocal
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture(autouse=True)
def fast_retries(monkeypatch):
    from app.services import sar_delivery
    monkeypatch.setattr(sar_delivery, "WEBHOOK_RETRY_BACKOFF_SECONDS", 0.05)


def _auth(user):
    from app.utils.security import create_access_token
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


class Tenancy:
    """One tenant with an officer, an admin and a webhook config."""

    def __init__(self, db, callback_url=None):
        from app.models.tenant import Tenant
        from app.models.user import User
        from app.models.webhook import WebhookConfig
        from app.utils.security import encrypt_json, hash_api_key
        tag = uuid.uuid4().hex[:8]
        self.db = db
        self.tenant = Tenant(name=f"Test Bank {tag}", slug=f"test-{tag}", company_type="BANK",
                             status="ACTIVE", tenant_id_public=f"TST-{tag}")
        db.add(self.tenant)
        db.flush()
        self.officer = User(tenant_id=self.tenant.id, email=f"officer-{tag}@test.local", password_hash="x",
                            full_name="Priya Nair", role="COMPLIANCE_OFFICER")
        self.admin = User(tenant_id=self.tenant.id, email=f"admin-{tag}@test.local", password_hash="x",
                          full_name="Triage Admin", role="TENANT_ADMIN")
        self.secret = "s3cret-" + tag
        self.webhook = WebhookConfig(tenant_id=self.tenant.id, callback_url=callback_url,
                                     use_internal_sink=callback_url is None,
                                     secret_encrypted=encrypt_json(self.secret),
                                     secret_hash=hash_api_key(self.secret), secret_prefix=self.secret[:12])
        db.add_all([self.officer, self.admin, self.webhook])
        db.commit()

    def alert(self, status="PROCESSING_COMPLETED", synthetic=False, customer="Rohan Mehta",
              counterparty="Global Holdings"):
        """An alert with a generated (masked) SAR draft awaiting review."""
        from app.models.alert import Alert
        from app.models.compliance import ComplianceMatch
        from app.models.pii_map import PIIMap
        from app.models.sar import SARDraft
        norm = {"transaction_id": f"TXN-{uuid.uuid4().hex[:6]}", "transaction_type": "INTERNATIONAL_WIRE",
                "transaction_amount": 990000, "customer_name": customer, "customer_id": "CUST-1",
                "account_id": "9988-7766-5544", "counterparty_name": counterparty,
                "counterparty_institution": "Emirates NBD"}
        a = Alert(tenant_id=self.tenant.id, status=status, raw_payload=norm, normalized_payload=norm,
                  masked_payload={"customer_name": "USR_aaaa"}, transaction_id=norm["transaction_id"],
                  transaction_amount=990000, transaction_type="INTERNATIONAL_WIRE", risk_score=88,
                  is_synthetic=synthetic, source="SIMULATOR" if synthetic else "API")
        self.db.add(a)
        self.db.flush()
        draft = SARDraft(alert_id=a.id, tenant_id=self.tenant.id,
                         draft_text="USR_aaaa wired INR 9,90,000 to a high-risk counterparty.",
                         draft_structured={"key_indicators": [{"indicator": "Structuring"}]})
        self.db.add_all([
            draft,
            PIIMap(alert_id=a.id, tenant_id=self.tenant.id, token_map={"USR_aaaa": customer}),
            ComplianceMatch(alert_id=a.id, tenant_id=self.tenant.id, rule_id="RISK_SCORE_THRESHOLD",
                            rule_name="Risk Score Threshold Exceeded", triggered=True, confidence=0.9),
        ])
        self.db.commit()
        return a, draft

    def set_callback(self, url):
        self.db.refresh(self.webhook)
        self.webhook.callback_url = url
        self.webhook.use_internal_sink = url is None
        self.db.commit()


def _wait_for_delivery(db, draft_id, timeout=15):
    """Block until the draft's webhook delivery has a final status; return the row."""
    from app.models.delivery import WebhookDelivery
    deadline = time.time() + timeout
    while time.time() < deadline:
        db.expire_all()
        d = db.query(WebhookDelivery).filter(WebhookDelivery.sar_draft_id == draft_id).first()
        if d is not None and d.status not in ("PENDING", "RETRYING"):
            return d
        time.sleep(0.05)
    raise AssertionError(f"delivery for {draft_id} did not finish")


def _approve(client, t, alert):
    return client.post(f"/api/v1/alerts/queue/{alert.id}/approve", json={}, headers=_auth(t.officer))


def _events(client, t):
    r = client.get("/api/v1/tenant/webhook/events", headers=_auth(t.admin))
    assert r.status_code == 200, r.text
    return r.json()


def _pdf_text(pdf: bytes) -> str:
    fitz = pytest.importorskip("fitz")
    return "\n".join(p.get_text() for p in fitz.open(stream=pdf, filetype="pdf"))


# ── SAR PDF download ─────────────────────────────────────────────────

class TestSarPdfDownload:
    def test_pending_or_rejected_draft_is_not_served(self, client, db):
        t = Tenancy(db)
        _, pending = t.alert()
        rejected_alert, rejected = t.alert()
        assert client.post(f"/api/v1/alerts/queue/{rejected_alert.id}/reject", json={"reason": "fp"},
                           headers=_auth(t.officer)).status_code == 200
        for draft in (pending, rejected):
            r = client.get(f"/files/sar/{draft.id}.pdf", headers=_auth(t.officer))
            assert r.status_code == 404 and r.json()["detail"] == "SAR PDF not found"

    def test_other_tenants_sar_is_indistinguishable_from_missing(self, client, db):
        owner, other = Tenancy(db), Tenancy(db)
        alert, draft = owner.alert()
        assert _approve(client, owner, alert).status_code == 200
        r = client.get(f"/files/sar/{draft.id}.pdf", headers=_auth(other.officer))
        assert r.status_code == 404 and r.json()["detail"] == "SAR PDF not found"

    def test_approved_pdf_shows_real_approver(self, client, db):
        t = Tenancy(db)
        alert, draft = t.alert()
        assert _approve(client, t, alert).status_code == 200
        r = client.get(f"/files/sar/{draft.id}.pdf", headers=_auth(t.officer))
        assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
        text = _pdf_text(r.content)
        assert "Priya Nair - " in text and "APPROVED" in text
        assert "Automated compliance review" not in text
        assert "APPROVED & FILED" not in text and "Filed to FIU-IND" not in text

    def test_download_matches_the_delivered_pdf(self, client, db, receiver):
        t = Tenancy(db, callback_url=f"{receiver.base}/match")
        alert, draft = t.alert()
        r = _approve(client, t, alert)
        assert r.status_code == 200
        _wait_for_delivery(db, draft.id)
        delivered = json.loads(receiver.to("/match")[-1]["body"])
        db.refresh(alert)
        from app.services.sar_delivery import format_approved_at
        assert delivered["approved_at"] == format_approved_at(alert.reviewed_at) == r.json()["approved_at"]
        assert delivered["goaml_str"]["report"]["submission_date"] == delivered["approved_at"]
        download = client.get(f"/files/sar/{draft.id}.pdf", headers=_auth(t.officer)).content
        assert base64.b64decode(delivered["pdf_base64"]) == download


# ── Webhook delivery outcome ─────────────────────────────────────────

class TestWebhookDelivery:
    def test_success_is_recorded_with_real_status(self, client, db, receiver):
        t = Tenancy(db, callback_url=f"{receiver.base}/ok")
        alert, draft = t.alert()
        assert _approve(client, t, alert).status_code == 200
        d = _wait_for_delivery(db, draft.id)
        assert (d.status, d.http_status_code, d.attempt_number) == ("DELIVERED", 200, 1)
        [evt] = _events(client, t)
        assert evt["status"] == "DELIVERED" and evt["http_status"] == 200
        assert evt["destination"] == f"{receiver.base}/ok" and evt["attempts"] == 1

    def test_receiver_error_is_retried_then_reported_failed(self, client, db, receiver):
        receiver.script["/down"] = [503]
        t = Tenancy(db, callback_url=f"{receiver.base}/down")
        alert, draft = t.alert()
        assert _approve(client, t, alert).status_code == 200  # approval itself still succeeds
        d = _wait_for_delivery(db, draft.id)
        from app.services.sar_delivery import WEBHOOK_MAX_ATTEMPTS
        assert (d.status, d.http_status_code, d.attempt_number) == ("FAILED", 503, WEBHOOK_MAX_ATTEMPTS)
        assert len(receiver.to("/down")) == WEBHOOK_MAX_ATTEMPTS
        [evt] = _events(client, t)
        assert (evt["status"], evt["http_status"], evt["error"]) == ("FAILED", 503, "Receiver responded 503")

    def test_transient_failure_recovers_on_retry(self, client, db, receiver):
        receiver.script["/flaky"] = [500, 200]
        t = Tenancy(db, callback_url=f"{receiver.base}/flaky")
        alert, draft = t.alert()
        assert _approve(client, t, alert).status_code == 200
        d = _wait_for_delivery(db, draft.id)
        assert (d.status, d.http_status_code, d.attempt_number) == ("DELIVERED", 200, 2)

    def test_client_error_is_not_retried(self, client, db, receiver):
        receiver.script["/gone"] = [410]
        t = Tenancy(db, callback_url=f"{receiver.base}/gone")
        alert, draft = t.alert()
        assert _approve(client, t, alert).status_code == 200
        d = _wait_for_delivery(db, draft.id)
        assert (d.status, d.http_status_code, d.attempt_number) == ("FAILED", 410, 1)

    def test_unreachable_receiver_is_reported_failed(self, client, db):
        with socket.socket() as s:  # a port nothing listens on
            s.bind(("127.0.0.1", 0))
            dead = f"http://127.0.0.1:{s.getsockname()[1]}/dead"
        t = Tenancy(db, callback_url=dead)
        alert, draft = t.alert()
        assert _approve(client, t, alert).status_code == 200
        d = _wait_for_delivery(db, draft.id)
        assert d.status == "FAILED" and d.http_status_code is None and "ConnectError" in d.error_message
        [evt] = _events(client, t)
        assert (evt["status"], evt["http_status"], evt["destination"]) == ("FAILED", None, dead)

    def test_destination_is_the_one_used_at_delivery_time(self, client, db, receiver):
        receiver.script["/old-dead"] = [500]
        t = Tenancy(db, callback_url=f"{receiver.base}/old-dead")
        failed_alert, failed_draft = t.alert()
        assert _approve(client, t, failed_alert).status_code == 200
        _wait_for_delivery(db, failed_draft.id)
        t.set_callback(f"{receiver.base}/new")
        ok_alert, ok_draft = t.alert()
        assert _approve(client, t, ok_alert).status_code == 200
        _wait_for_delivery(db, ok_draft.id)
        t.set_callback(None)  # switch to the built-in sink afterwards

        by_sar = {e["payload"]["sar_id"]: e for e in _events(client, t)}
        assert by_sar[str(failed_draft.id)]["destination"] == f"{receiver.base}/old-dead"
        assert by_sar[str(failed_draft.id)]["status"] == "FAILED"
        assert by_sar[str(ok_draft.id)]["destination"] == f"{receiver.base}/new"
        assert by_sar[str(ok_draft.id)]["status"] == "DELIVERED"

    def test_internal_sink_delivery(self, client, db):
        t = Tenancy(db)  # built-in sink
        alert, draft = t.alert()
        assert _approve(client, t, alert).status_code == 200
        [evt] = _events(client, t)
        assert (evt["status"], evt["http_status"], evt["destination"]) == ("DELIVERED", None, "internal-sink")
        assert evt["hmac_valid"] is True and "pdf_base64" not in evt["payload"]

    def test_legacy_event_without_delivery_record_is_unknown(self, client, db):
        from app.models.webhook import WebhookSinkEvent
        t = Tenancy(db)
        db.add(WebhookSinkEvent(tenant_id=t.tenant.id, payload={"event": "sar.approved"},
                                headers={"X-Aegis-Event": "sar.approved"}, hmac_valid=True,
                                source_ip="internal-sink"))
        db.commit()
        [evt] = _events(client, t)
        assert evt["status"] == "UNKNOWN" and evt["http_status"] is None and evt["destination"] is None


# ── Auto-approve path (routers/ingest.py background task) ────────────

class TestAutoApprovePath:
    def test_auto_approved_download_matches_delivered(self, client, db, receiver):
        from app.models.alert import Alert
        from app.services.sar_delivery import AUTO_APPROVER_NAME, finalize_and_deliver
        t = Tenancy(db, callback_url=f"{receiver.base}/auto")
        alert, draft = t.alert()
        a = db.get(Alert, alert.id)
        finalize_and_deliver(a, db, "Automated compliance review (auto-approved)")  # as ingest.py does
        db.commit()
        _wait_for_delivery(db, draft.id)
        delivered = json.loads(receiver.to("/auto")[-1]["body"])
        assert delivered["approved_by"] == AUTO_APPROVER_NAME
        download = client.get(f"/files/sar/{draft.id}.pdf", headers=_auth(t.officer)).content
        assert base64.b64decode(delivered["pdf_base64"]) == download

    def test_rolled_back_approval_is_never_sent(self, db, receiver):
        from app.models.alert import Alert
        from app.services.sar_delivery import finalize_and_deliver
        t = Tenancy(db, callback_url=f"{receiver.base}/rolled-back")
        alert, draft = t.alert()
        finalize_and_deliver(db.get(Alert, alert.id), db, "Priya Nair", t.officer.id)
        db.rollback()
        db.commit()  # a later commit on the same session (ingest.py's failure path does this)
        time.sleep(0.5)
        assert receiver.to("/rolled-back") == []


# ── Concurrency ──────────────────────────────────────────────────────

class TestConcurrentApprove:
    def test_parallel_approvals_file_and_deliver_once(self, client, db, receiver, monkeypatch):
        from app.models.delivery import WebhookDelivery
        from app.models.webhook import WebhookSinkEvent
        from app.services import sar_delivery
        real_render = sar_delivery.render_sar_pdf

        def slow_render(*args, **kwargs):  # widen the check-then-act window
            time.sleep(0.3)
            return real_render(*args, **kwargs)
        monkeypatch.setattr(sar_delivery, "render_sar_pdf", slow_render)

        t = Tenancy(db, callback_url=f"{receiver.base}/race")
        alert, draft = t.alert()
        # resolve ORM attributes up front: the threads must not share the test's session
        url, headers = f"/api/v1/alerts/queue/{alert.id}/approve", _auth(t.officer)
        n = 5
        barrier, codes = threading.Barrier(n), []

        def approve():
            barrier.wait()
            codes.append(client.post(url, json={}, headers=headers).status_code)
        threads = [threading.Thread(target=approve) for _ in range(n)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        assert sorted(codes) == [200] + [409] * (n - 1)
        _wait_for_delivery(db, draft.id)
        time.sleep(0.3)  # let any (wrong) extra deliveries land
        assert len(receiver.to("/race")) == 1
        assert db.query(WebhookDelivery).filter(WebhookDelivery.sar_draft_id == draft.id).count() == 1
        assert db.query(WebhookSinkEvent).filter(WebhookSinkEvent.tenant_id == t.tenant.id).count() == 1


# ── Simulator (synthetic) alerts ─────────────────────────────────────

class TestSyntheticAlert:
    def test_bank_payload_is_marked_test(self, client, db, receiver):
        t = Tenancy(db, callback_url=f"{receiver.base}/synthetic")
        alert, draft = t.alert(synthetic=True)
        assert _approve(client, t, alert).status_code == 200
        _wait_for_delivery(db, draft.id)
        req = receiver.to("/synthetic")[-1]
        payload = json.loads(req["body"])
        assert payload["test"] is True and payload["event"] == "sar.approved.test"
        assert req["headers"]["X-Aegis-Event"] == "sar.approved.test"
        assert "TEST ALERT" in _pdf_text(base64.b64decode(payload["pdf_base64"]))

    def test_real_alert_payload_is_not_test(self, client, db, receiver):
        t = Tenancy(db, callback_url=f"{receiver.base}/real")
        alert, draft = t.alert()
        assert _approve(client, t, alert).status_code == 200
        _wait_for_delivery(db, draft.id)
        req = receiver.to("/real")[-1]
        payload = json.loads(req["body"])
        assert payload["test"] is False and payload["event"] == "sar.approved"
        assert req["headers"]["X-Aegis-Event"] == "sar.approved"


# ── Webhook secret + sink URL ────────────────────────────────────────

class TestWebhookSecret:
    def test_rotate_returns_full_secret_once_and_signs_deliveries(self, client, db, receiver):
        from app.models.audit import AuditLog
        from app.utils.security import decrypt_json, verify_api_key
        t = Tenancy(db, callback_url=f"{receiver.base}/signed")
        r = client.post("/api/v1/tenant/webhook/secret/rotate", headers=_auth(t.admin))
        assert r.status_code == 200
        secret = r.json()["secret"]
        assert len(secret) == 64 and r.json()["secret_prefix"] == secret[:12]

        cfg = client.get("/api/v1/tenant/webhook", headers=_auth(t.admin)).json()
        assert cfg["secret_prefix"] == secret[:12] and secret not in json.dumps(cfg)
        db.refresh(t.webhook)
        assert decrypt_json(t.webhook.secret_encrypted) == secret
        assert verify_api_key(secret, t.webhook.secret_hash)
        assert db.query(AuditLog).filter(AuditLog.tenant_id == t.tenant.id,
                                         AuditLog.action == "WEBHOOK_SECRET_ROTATED").count() == 1

        alert, draft = t.alert()
        assert _approve(client, t, alert).status_code == 200
        _wait_for_delivery(db, draft.id)
        req = receiver.to("/signed")[-1]
        expected = "sha256=" + hmac.new(secret.encode(), req["body"], hashlib.sha256).hexdigest()
        assert hmac.compare_digest(req["headers"]["X-Aegis-Signature"], expected)

    def test_rotate_requires_tenant_admin(self, client, db):
        t = Tenancy(db)
        assert client.post("/api/v1/tenant/webhook/secret/rotate", headers=_auth(t.officer)).status_code == 403
        assert client.post("/api/v1/tenant/webhook/secret/rotate").status_code == 401

    def test_no_internal_sink_url_is_advertised(self, client, db):
        t = Tenancy(db)
        cfg = client.get("/api/v1/tenant/webhook", headers=_auth(t.admin)).json()
        assert "internal_sink_url" not in cfg
        assert "webhooks/sink" not in json.dumps(_events(client, t))
