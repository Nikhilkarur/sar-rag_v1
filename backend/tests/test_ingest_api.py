"""POST /api/v1/ingest/ against a real Postgres: bad typed fields are 422s (never a
500 or a half-written alert), a missing ref_id gets a generated id, failed auth never
spends the tenant's quota, and alerts can't be left stuck in PROCESSING.

Needs DATABASE_URL to point at a migrated database whose name contains "test"
(these tests insert and delete tenants); skipped otherwise.
"""
import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect as sa_inspect
from sqlalchemy.engine import make_url
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

from app.config import settings
from app.routers import ingest


def _db_skip_reason():
    try:
        url = make_url(settings.DATABASE_URL)
    except Exception:
        return "DATABASE_URL is not a valid URL"
    if "test" not in (url.database or ""):
        return "DATABASE_URL does not point at a *test* database"
    try:
        engine = create_engine(url, connect_args={"connect_timeout": 3})
        try:
            with engine.connect() as conn:
                if not sa_inspect(conn).has_table("alerts"):
                    return "test database is not migrated (alembic upgrade head)"
        finally:
            engine.dispose()
    except Exception as e:
        return f"test database unreachable ({e.__class__.__name__})"
    return None


_SKIP_REASON = _db_skip_reason()
pytestmark = pytest.mark.skipif(_SKIP_REASON is not None, reason=f"DB-backed ingest tests: {_SKIP_REASON}")

if _SKIP_REASON is None:
    from app.data.schema_presets import SCHEMA_PRESETS
    from app.database import SessionLocal
    from app.models.alert import Alert
    from app.models.compliance import ComplianceMatch
    from app.models.pii_map import PIIMap
    from app.models.schema import IngestionSchema
    from app.models.tenant import Tenant
    from app.utils.security import hash_api_key

URL = "/api/v1/ingest/"


@pytest.fixture
def ctx(monkeypatch):
    suffix = uuid.uuid4().hex[:8]
    api_key = f"sk-ae-{uuid.uuid4().hex}"
    db = SessionLocal()
    tenant = Tenant(
        name=f"Ingest Test {suffix}", slug=f"ingest-test-{suffix}", company_type="FINTECH",
        status="ACTIVE", api_key_hash=hash_api_key(api_key), tenant_id_public=f"TST-{suffix}",
    )
    db.add(tenant)
    db.flush()
    preset = SCHEMA_PRESETS["STANDARD_FINTECH"]
    db.add(IngestionSchema(
        tenant_id=tenant.id, name=preset["name"], template_key="STANDARD_FINTECH", is_active=True,
        field_map=preset["field_map"], pii_fields=preset["pii_fields"],
    ))
    db.commit()
    tenant_id, public_id = tenant.id, tenant.tenant_id_public

    # SAR generation needs an LLM: record what would be queued instead
    submitted = []
    monkeypatch.setattr(ingest, "_sar_executor", SimpleNamespace(submit=lambda fn, *a: submitted.append(a)))
    monkeypatch.setattr(ingest, "_ip_rate_limiter", ingest._SlidingWindowLimiter())
    monkeypatch.setattr(ingest, "_tenant_rate_limiter", ingest._SlidingWindowLimiter())

    app = FastAPI()
    app.include_router(ingest.router)

    def alerts():
        db.expire_all()
        return db.query(Alert).filter(Alert.tenant_id == tenant_id).all()

    yield SimpleNamespace(
        client=TestClient(app), db=db, tenant_id=tenant_id, submitted=submitted, alerts=alerts,
        headers={"X-API-Key": api_key, "X-Tenant-ID": public_id},
        bad_headers={"X-API-Key": "attacker-garbage", "X-Tenant-ID": public_id},
    )

    db.rollback()
    db.query(Tenant).filter(Tenant.id == tenant_id).delete()  # cascades alerts, schema, maps
    db.commit()
    db.close()


def _payload(txn=None, risk=None, **sections):
    body = {
        "customer": {"full_name": "Rajesh Kumar Sharma", "id": "CUST-98271"},
        "account": {"number": "HDFC-00123456789"},
        "txn": {
            "ref_id": f"TXN-{uuid.uuid4().hex[:12]}", "amount": 990000.00, "currency": "INR",
            "type": "NEFT_TRANSFER", "direction": "DEBIT", "timestamp": "2026-06-10T09:30:00+05:30",
        },
        "counterparty": {"account": "ICICI-00987654321", "name": "Priya Enterprises", "bank": "ICICI Bank"},
        "metadata": {"ip": "103.27.9.44", "device_id": "MOB-a1b2c3d4e5f6"},
        "risk": {"score": 87, "reason": "Near reporting threshold"},
    }
    if isinstance(txn, dict):
        body["txn"].update(txn)
    elif txn is not None:
        body["txn"] = txn
    if risk:
        body["risk"].update(risk)
    body.update(sections)
    return body


class TestValidPayload:
    def test_stores_typed_columns_atomically(self, ctx):
        r = ctx.client.post(URL, json=_payload(), headers=ctx.headers)
        assert r.status_code == 200, r.text
        assert r.json()["message"].endswith("SAR generation triggered.")
        [alert] = ctx.alerts()
        assert alert.status == "PROCESSING"
        assert alert.transaction_id.startswith("TXN-")
        assert alert.transaction_amount == Decimal("990000.0000")
        assert alert.transaction_currency == "INR" and alert.transaction_type == "NEFT_TRANSFER"
        assert alert.transaction_timestamp == datetime(2026, 6, 10, 4, 0, tzinfo=timezone.utc)
        assert ctx.db.query(PIIMap).filter(PIIMap.alert_id == alert.id).count() == 1
        assert ctx.db.query(ComplianceMatch).filter(ComplianceMatch.alert_id == alert.id).count() >= 1
        assert ctx.submitted == [(alert.id,)]

    def test_low_risk_is_completed_clean(self, ctx):
        r = ctx.client.post(URL, json=_payload(txn={"amount": "1234.5"}, risk={"score": 10}), headers=ctx.headers)
        assert r.status_code == 200, r.text
        [alert] = ctx.alerts()
        assert alert.status == "COMPLETED_CLEAN"
        assert alert.transaction_amount == Decimal("1234.5")
        assert ctx.submitted == []


class TestInvalidFieldsAre422:
    @pytest.mark.parametrize("payload,field", [
        # The original repro: every typed field garbage at once; amount is reported first
        (_payload(txn={"amount": "N/A", "timestamp": "yesterday"}, risk={"score": "high"}), "transaction_amount"),
        (_payload(txn={"amount": 1e308}), "transaction_amount"),
        (_payload(txn={"amount": "Infinity"}), "transaction_amount"),
        (_payload(txn={"ref_id": "R" * 5007}), "transaction_id"),
        (_payload(txn={"ref_id": {"nested": "object"}}), "transaction_id"),
        (_payload(txn={"currency": "RUPEES-LONG-CURRENCY-CODE"}), "transaction_currency"),
        (_payload(txn={"type": "T" * 300}), "transaction_type"),
        (_payload(txn={"timestamp": "yesterday"}), "transaction_timestamp"),
    ])
    def test_named_field(self, ctx, payload, field):
        r = ctx.client.post(URL, json=payload, headers=ctx.headers)
        assert r.status_code == 422, r.text
        assert r.json()["detail"].startswith(f"{field} (")
        assert ctx.alerts() == []

    @pytest.mark.parametrize("old,new,expected", [
        ('"score": 87', '"score": 1e400', "risk_score"),
        ('"amount": 990000.0', '"amount": NaN', "transaction_amount"),
        ('"bank": "ICICI Bank"', '"bank": Infinity', "non-finite"),
    ])
    def test_non_finite_json_numbers(self, ctx, old, new, expected):
        body = json.dumps(_payload())
        assert old in body
        r = ctx.client.post(URL, content=body.replace(old, new),
                            headers={**ctx.headers, "Content-Type": "application/json"})
        assert r.status_code == 422, r.text
        assert expected in r.json()["detail"]
        assert ctx.alerts() == []

    def test_db_rejection_is_422_and_leaves_nothing_behind(self, ctx):
        # JSONB refuses \u0000: caught as DataError on the single commit, so neither
        # a 500 nor an orphaned PROCESSING alert without its PII map
        payload = _payload(counterparty={"account": "A-1", "name": "N", "bank": "ICICI\u0000Bank"})
        r = ctx.client.post(URL, json=payload, headers=ctx.headers)
        assert r.status_code == 422, r.text
        assert ctx.alerts() == []


class TestMissingRefIdGetsGeneratedId:
    @pytest.mark.parametrize("payload", [
        _payload(txn="not-an-object"),
        {"triage": "empty-1"},
        _payload(txn={"ref_id": None}),
    ])
    def test_auto_id_never_literal_none(self, ctx, payload):
        r = ctx.client.post(URL, json=payload, headers=ctx.headers)
        assert r.status_code == 200, r.text
        [alert] = ctx.alerts()
        assert alert.transaction_id != "None"
        assert alert.transaction_id.startswith("AUTO-")
        uuid.UUID(alert.transaction_id[len("AUTO-"):])

    def test_generated_ids_are_unique(self, ctx):
        for i in range(2):
            assert ctx.client.post(URL, json={"triage": f"empty-{i}"}, headers=ctx.headers).status_code == 200
        ids = {a.transaction_id for a in ctx.alerts()}
        assert len(ids) == 2


class TestQuotaAfterAuth:
    def test_unauthenticated_flood_cannot_exhaust_tenant_quota(self, ctx, monkeypatch):
        monkeypatch.setattr(settings, "RATE_LIMIT_INGEST_PER_MINUTE", 2)
        monkeypatch.setattr(settings, "RATE_LIMIT_INGEST_PER_IP_PER_MINUTE", 1000)
        for _ in range(5):
            assert ctx.client.post(URL, json=_payload(), headers=ctx.bad_headers).status_code == 401
        codes = [ctx.client.post(URL, json=_payload(), headers=ctx.headers).status_code for _ in range(3)]
        # the real tenant still gets its full quota, then is limited
        assert codes == [200, 200, 429]

    def test_ip_limit_applies_before_auth(self, ctx, monkeypatch):
        monkeypatch.setattr(settings, "RATE_LIMIT_INGEST_PER_IP_PER_MINUTE", 3)
        codes = [ctx.client.post(URL, json=_payload(), headers=ctx.bad_headers).status_code for _ in range(4)]
        assert codes == [401, 401, 401, 429]


def _stuck_alert(db, tenant_id, started_at):
    alert = Alert(tenant_id=tenant_id, status="PROCESSING", raw_payload={}, processing_started_at=started_at)
    db.add(alert)
    db.commit()
    return alert.id


class TestStuckProcessing:
    def test_sweep_fails_only_old_processing_alerts(self, ctx):
        now = datetime.now(timezone.utc)
        old_id = _stuck_alert(ctx.db, ctx.tenant_id, now - timedelta(hours=1))
        fresh_id = _stuck_alert(ctx.db, ctx.tenant_id, now)
        assert ingest.fail_stuck_processing_alerts(now - timedelta(minutes=15)) >= 1
        ctx.db.expire_all()
        old, fresh = ctx.db.get(Alert, old_id), ctx.db.get(Alert, fresh_id)
        assert old.status == "PROCESSING_FAILED" and "interrupted" in old.processing_error
        assert fresh.status == "PROCESSING" and fresh.processing_error is None

    def test_background_task_failing_to_load_alert_marks_it_failed(self, ctx, monkeypatch):
        # The burst left an alert in PROCESSING forever because the task's very
        # first query hit a pool timeout outside its error handling
        alert_id = _stuck_alert(ctx.db, ctx.tenant_id, datetime.now(timezone.utc))
        real_session = ingest.SessionLocal

        def session_whose_first_query_times_out():
            session = real_session()
            real_query = session.query
            calls = []

            def query(*args, **kwargs):
                calls.append(1)
                if len(calls) == 1:
                    raise PoolTimeoutError("QueuePool limit of size 10 overflow 20 reached")
                return real_query(*args, **kwargs)

            session.query = query
            return session

        monkeypatch.setattr(ingest, "SessionLocal", session_whose_first_query_times_out)
        ingest.process_alert_background(alert_id)
        ctx.db.expire_all()
        alert = ctx.db.get(Alert, alert_id)
        assert alert.status == "PROCESSING_FAILED"
        assert "QueuePool" in alert.processing_error

    def test_generation_failure_still_marks_failed(self, ctx, monkeypatch):
        alert_id = _stuck_alert(ctx.db, ctx.tenant_id, datetime.now(timezone.utc))
        monkeypatch.setattr(settings, "SAR_GENERATION_MAX_ATTEMPTS", 1)
        monkeypatch.setattr(ingest, "retrieve_regulatory_context", lambda *a, **k: None)

        def boom(*args, **kwargs):
            raise RuntimeError("both LLM providers down")

        monkeypatch.setattr(ingest, "generate_sar", boom)
        ingest.process_alert_background(alert_id)
        ctx.db.expire_all()
        alert = ctx.db.get(Alert, alert_id)
        assert alert.status == "PROCESSING_FAILED"
        assert alert.processing_error == "both LLM providers down"


class TestNoConnectionHeldAcrossThreadHops:
    """The 40-ingest burst timed out because request sessions kept a pooled
    connection checked out between threadpool hops (API-key lookup -> bcrypt ->
    handler -> get_db teardown): threads waited on connections whose owners were
    waiting for a thread. Each DB-touching step must hand its connection back."""

    def _request(self):
        from starlette.requests import Request
        return Request({
            "type": "http", "method": "POST", "path": URL, "query_string": b"",
            "headers": [], "client": ("127.0.0.1", 50000),
        })

    def _tenant(self, ctx):
        from app.utils.deps import authenticate_api_key
        return authenticate_api_key(ctx.headers["X-API-Key"], ctx.headers["X-Tenant-ID"], ctx.db)

    def test_api_key_auth_releases_connection(self, ctx):
        tenant = self._tenant(ctx)
        assert not ctx.db.in_transaction()
        assert tenant.id == ctx.tenant_id and tenant.status == "ACTIVE"  # still usable

    def test_handler_releases_connection_on_success_and_error(self, ctx):
        tenant = self._tenant(ctx)
        result = ingest.ingest_payload(self._request(), ctx.db, tenant, json.dumps(_payload()).encode())
        assert result["status"] == "success"
        assert not ctx.db.in_transaction()

        bad = json.dumps(_payload(txn={"amount": "N/A"})).encode()
        with pytest.raises(Exception) as exc:
            ingest.ingest_payload(self._request(), ctx.db, tenant, bad)
        assert getattr(exc.value, "status_code", None) == 422
        assert not ctx.db.in_transaction()
