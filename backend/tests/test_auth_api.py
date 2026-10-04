"""End-to-end auth/tenant checks against a real Postgres (FastAPI TestClient).

Runs only when DATABASE_URL points at a reachable database whose name contains "test"
(it migrates the schema and writes users/tenants); otherwise the module is skipped, so the
suite still passes without a database and never touches a dev/prod database. E.g.:

  docker run -d --name pg-test -e POSTGRES_PASSWORD=pw -e POSTGRES_DB=aegis_test \\
      -p 127.0.0.1:55433:5432 postgres:16-alpine
  DATABASE_URL=postgresql+psycopg2://postgres:pw@127.0.0.1:55433/aegis_test pytest tests
"""
import itertools
import os
import re
import threading
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.config import settings

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _db_unavailable_reason():
    try:
        if "test" not in (make_url(settings.DATABASE_URL).database or ""):
            return "DATABASE_URL does not point at a *test* database"
        engine = create_engine(settings.DATABASE_URL, connect_args={"connect_timeout": 3})
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        finally:
            engine.dispose()
    except Exception as e:  # unreachable, bad URL, missing driver...
        return f"test database unavailable ({type(e).__name__})"
    return None


_SKIP_REASON = _db_unavailable_reason()
pytestmark = pytest.mark.skipif(_SKIP_REASON is not None, reason=_SKIP_REASON or "")

PASSWORD = "correct-horse-battery"


@pytest.fixture(scope="module")
def client():
    from alembic import command
    from alembic.config import Config
    from fastapi.testclient import TestClient
    from app.main import app

    cfg = Config()  # no ini file: env.py then leaves the test run's logging alone
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    command.upgrade(cfg, "head")
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    from app.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _uid() -> str:
    return uuid.uuid4().hex[:10]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _signup(client, email=None):
    email = email or f"user-{_uid()}@bank.example.com"
    r = client.post("/api/v1/auth/signup", json={
        "company_name": f"Test Bank {_uid()}", "company_type": "BANK",
        "admin_email": email, "admin_password": PASSWORD, "admin_name": "Test Admin",
    })
    return r


def _login(client, email, password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def _refresh(client, token):
    return client.post("/api/v1/auth/refresh", json={"refresh_token": token})


def _make_user(db, email, role="SUPER_ADMIN"):
    from app.models.user import User
    from app.utils.security import hash_password

    user = User(email=email, password_hash=hash_password(PASSWORD), full_name="Ops", role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="module")
def super_admin(client):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        user = _make_user(db, f"root-{_uid()}@aegis.example.com")
        user_id = user.id
        email = user.email
    finally:
        db.close()
    r = _login(client, email)
    assert r.status_code == 200, r.text
    return SimpleNamespace(id=user_id, token=r.json()["access_token"])


def _pending_tenant(client):
    """Sign up a new applicant; returns (signup json, tenant uuid)."""
    r = _signup(client)
    assert r.status_code == 200, r.text
    body = r.json()
    return body, body["user"]["tenant"]["id"]


def _approve(client, super_admin, tenant_uuid):
    return client.post(f"/api/v1/admin/tenants/{tenant_uuid}/approve", headers=_auth(super_admin.token))


# ── Case-insensitive email ────────────────────────────────────────────

def test_login_and_signup_treat_email_case_insensitively(client):
    email = f"Case-{_uid()}@Example.COM"
    r = _signup(client, email)
    assert r.status_code == 200, r.text
    assert r.json()["user"]["email"] == email.lower()

    for variant in (email, email.lower(), email.upper()):
        assert _login(client, variant).status_code == 200, variant

    for variant in (email.lower(), email.upper(), f"  {email.swapcase()} "):
        dup = _signup(client, variant)
        assert dup.status_code == 400, variant
        assert dup.json()["detail"] == "Email already registered"


def test_concurrent_signups_with_same_email_never_500(client):
    from app.database import SessionLocal
    from app.schemas.auth import UserSignup
    from app.services import auth_service

    # Equal once normalized, so all of them pass the pre-check before any commits
    email = f"Race-{_uid()}@Bank.example.com"
    variants = [email, email.lower(), email.upper(), email.swapcase()]
    barrier = threading.Barrier(len(variants))
    statuses, errors = [], []

    def signup(variant):
        session = SessionLocal()
        try:
            data = UserSignup(company_name=f"Race Bank {_uid()}", company_type="BANK",
                              admin_email=variant, admin_password=PASSWORD, admin_name="Racer")
            barrier.wait()
            auth_service.signup_tenant_admin(data, session)
            statuses.append(200)
        except HTTPException as e:
            statuses.append((e.status_code, e.detail))
        except Exception as e:  # the losers used to hit UniqueViolation at flush -> 500
            errors.append(repr(e))
        finally:
            session.close()

    threads = [threading.Thread(target=signup, args=(v,)) for v in variants]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert errors == []
    assert sorted(statuses, key=str) == sorted(
        [200] + [(400, "Email already registered")] * (len(variants) - 1), key=str)
    assert _login(client, email).status_code == 200


def test_concurrent_signups_with_same_company_name_never_500(client):  # client: migrated DB
    from app.database import SessionLocal
    from app.schemas.auth import UserSignup
    from app.services import auth_service

    # Same new name -> same slug for all of them (the pre-check sees it free)
    name = f"Slug Race Bank {_uid()}"
    barrier = threading.Barrier(3)
    statuses, errors = [], []

    def signup():
        session = SessionLocal()
        try:
            data = UserSignup(company_name=name, company_type="BANK",
                              admin_email=f"slug-{_uid()}@bank.example.com",
                              admin_password=PASSWORD, admin_name="Racer")
            barrier.wait()
            auth_service.signup_tenant_admin(data, session)
            statuses.append(200)
        except HTTPException as e:
            statuses.append(e.status_code)
        except Exception as e:
            errors.append(repr(e))
        finally:
            session.close()

    threads = [threading.Thread(target=signup) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert errors == []
    assert 200 in statuses and set(statuses) <= {200, 409}


def test_legacy_mixed_case_account_still_logs_in(client, db):
    email = f"Legacy-{_uid()}@Example.com"
    _make_user(db, email, role="COMPLIANCE_OFFICER")  # stored as-is, like pre-fix rows

    assert _login(client, email.lower()).status_code == 200
    assert _login(client, email).status_code == 200
    assert _login(client, email.lower(), password="wrong-password").status_code == 401
    assert _signup(client, email.lower()).status_code == 400


# ── Per-session refresh tokens ────────────────────────────────────────

def test_second_login_does_not_kill_first_session(client):
    email = _signup(client).json()["user"]["email"]
    rt1 = _login(client, email).json()["refresh_token"]
    rt2 = _login(client, email).json()["refresh_token"]

    r1 = _refresh(client, rt1)
    assert r1.status_code == 200, r1.text
    assert set(r1.json()) == {"access_token", "refresh_token", "token_type"}
    assert _refresh(client, rt2).status_code == 200


def test_replayed_refresh_token_revokes_its_session(client, db):
    from app.models.audit import AuditLog

    signup = _signup(client).json()
    email = signup["user"]["email"]
    other_session = _login(client, email).json()["refresh_token"]

    rt = _login(client, email).json()["refresh_token"]
    rotated = _refresh(client, rt)
    assert rotated.status_code == 200
    rt_new = rotated.json()["refresh_token"]

    # Replaying the already-rotated token is rejected AND kills the session...
    assert _refresh(client, rt).status_code == 401
    assert _refresh(client, rt_new).status_code == 401
    # ...but only that session: other logins of the same user keep working
    assert _refresh(client, other_session).status_code == 200
    assert _refresh(client, signup["refresh_token"]).status_code == 200

    assert db.query(AuditLog).filter(
        AuditLog.user_id == uuid.UUID(signup["user"]["id"]),
        AuditLog.action == "REFRESH_TOKEN_REUSE",
    ).count() == 1


def test_logout_revokes_only_that_session(client):
    email = _signup(client).json()["user"]["email"]
    rt1 = _login(client, email).json()["refresh_token"]
    rt2 = _login(client, email).json()["refresh_token"]

    assert client.post("/api/v1/auth/logout", json={"refresh_token": rt1}).json() == {"status": "ok"}
    assert _refresh(client, rt1).status_code == 401
    assert _refresh(client, rt2).status_code == 200
    # Idempotent and non-revealing for junk tokens
    assert client.post("/api/v1/auth/logout", json={"refresh_token": rt1}).status_code == 200
    assert client.post("/api/v1/auth/logout", json={"refresh_token": "garbage"}).status_code == 200


def test_refresh_rejects_access_tokens_and_sessionless_tokens(client):
    from app.utils.security import create_refresh_token

    body = _signup(client).json()
    assert _refresh(client, body["access_token"]).status_code == 401
    # Pre-upgrade style refresh token (no session id)
    legacy = create_refresh_token(data={"sub": body["user"]["id"]})
    assert _refresh(client, legacy).status_code == 401


# ── Role guards ───────────────────────────────────────────────────────

@pytest.mark.parametrize("method,path", [
    ("GET", "/api/v1/tenant/profile"),
    ("GET", "/api/v1/tenant/credentials"),
    ("GET", "/api/v1/tenant/credentials/reveal"),
    ("POST", "/api/v1/tenant/credentials/rotate"),
    ("GET", "/api/v1/tenant/webhook"),
    ("GET", "/api/v1/tenant/llm-config"),
    ("GET", "/api/v1/tenant/schemas"),
    ("GET", "/api/v1/tenant/usage"),
    ("GET", "/api/v1/tenant/billing"),
    ("GET", "/api/v1/tenant/sars"),
    ("GET", "/api/v1/alerts/queue"),
    ("GET", "/api/v1/documents/"),
])
def test_super_admin_gets_403_on_tenant_scoped_endpoints(client, super_admin, method, path):
    r = client.request(method, path, headers=_auth(super_admin.token))
    assert r.status_code == 403, r.text
    assert r.json()["detail"] == "Tenant context required"


def test_super_admin_keeps_platform_access(client, super_admin):
    assert client.get("/api/v1/admin/verifications", headers=_auth(super_admin.token)).status_code == 200
    # SAR PDFs stay readable platform-wide (404 = got past the guard, no such SAR)
    r = client.get(f"/files/sar/{uuid.uuid4()}.pdf", headers=_auth(super_admin.token))
    assert r.status_code == 404


def test_missing_token_is_401(client):
    r = client.get("/api/v1/tenant/profile")
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


# ── Tenant profile / approval ─────────────────────────────────────────

def test_tenant_profile_and_me_after_approval(client, super_admin):
    signup, tenant_uuid = _pending_tenant(client)
    token = signup["access_token"]
    assert client.get("/api/v1/tenant/profile", headers=_auth(token)).status_code == 403  # not active yet
    assert client.get("/api/v1/auth/me", headers=_auth(token)).json()["tenant"]["status"] == "PENDING_VERIFICATION"

    approved = _approve(client, super_admin, tenant_uuid)
    assert approved.status_code == 200, approved.text

    r = client.get("/api/v1/tenant/profile", headers=_auth(token))
    assert r.status_code == 200, r.text
    assert r.json()["id"] == tenant_uuid
    assert r.json()["status"] == "ACTIVE"
    assert r.json()["tenant_id_public"] == approved.json()["tenant_id"]
    # What the status page polls to leave "Under Review" without re-login
    assert client.get("/api/v1/auth/me", headers=_auth(token)).json()["tenant"]["status"] == "ACTIVE"


def test_approve_returns_the_id_ingest_accepts(client, super_admin, db):
    from app.utils.deps import authenticate_api_key

    _, tenant_uuid = _pending_tenant(client)
    r = _approve(client, super_admin, tenant_uuid)
    assert r.status_code == 200, r.text
    body = r.json()
    assert re.fullmatch(r"TEN-\d{4,}", body["tenant_id"]), body
    assert body["id"] == tenant_uuid

    tenant = authenticate_api_key(x_api_key=body["api_key"], x_tenant_id=body["tenant_id"], db=db)
    assert str(tenant.id) == tenant_uuid
    with pytest.raises(HTTPException) as exc:
        authenticate_api_key(x_api_key=body["api_key"], x_tenant_id=tenant_uuid, db=db)
    assert exc.value.status_code == 401

    # Approving twice is a clean 400, not a second key
    assert _approve(client, super_admin, tenant_uuid).status_code == 400


@pytest.mark.parametrize("reason", ["", "   ", "no"])
def test_reject_requires_a_reason(client, super_admin, reason):
    _, tenant_uuid = _pending_tenant(client)
    r = client.post(f"/api/v1/admin/tenants/{tenant_uuid}/reject", json={"reason": reason},
                    headers=_auth(super_admin.token))
    assert r.status_code == 422


def test_reject_stores_trimmed_reason(client, super_admin):
    signup, tenant_uuid = _pending_tenant(client)
    r = client.post(f"/api/v1/admin/tenants/{tenant_uuid}/reject",
                    json={"reason": "  Unable to verify CIN.  "}, headers=_auth(super_admin.token))
    assert r.status_code == 200, r.text
    me = client.get("/api/v1/auth/me", headers=_auth(signup["access_token"])).json()
    assert me["tenant"]["status"] == "REJECTED"
    assert me["tenant"]["rejectionReason"] == "Unable to verify CIN."


def test_concurrent_approvals_get_distinct_public_ids(client, super_admin):
    from app.database import SessionLocal
    from app.services import admin_service

    tenant_uuids = [_pending_tenant(client)[1] for _ in range(6)]
    barrier = threading.Barrier(len(tenant_uuids))
    results, errors = {}, []

    def approve(tid):
        session = SessionLocal()
        try:
            barrier.wait()
            results[tid] = admin_service.approve_tenant(tid, super_admin, session).tenant_id
        except Exception as e:  # the old count-based allocation raised UniqueViolation here
            errors.append(repr(e))
        finally:
            session.close()

    threads = [threading.Thread(target=approve, args=(t,)) for t in tenant_uuids]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert errors == []
    assert len(set(results.values())) == len(tenant_uuids)


def test_public_ids_assigned_outside_the_sequence_are_skipped(client, super_admin, db):
    from app.models.tenant import Tenant

    # The shared test DB may already hold ids ahead of the sequence; derive the
    # expectation from what is taken instead of assuming n+1, n+2 are free.
    taken = {t for (t,) in db.query(Tenant.tenant_id_public).filter(Tenant.tenant_id_public.isnot(None))}
    n = db.execute(text("SELECT nextval('tenant_public_id_seq')")).scalar_one()
    free_after = lambda k: next(f"TEN-{i:04d}" for i in itertools.count(k + 1) if f"TEN-{i:04d}" not in taken)

    seeded = free_after(n)  # the id the sequence would hand out next
    db.add(Tenant(name="Seeded", slug=f"seeded-{_uid()}", company_type="BANK",
                  status="ACTIVE", tenant_id_public=seeded))
    db.commit()

    _, tenant_uuid = _pending_tenant(client)
    r = _approve(client, super_admin, tenant_uuid)
    assert r.status_code == 200, r.text
    assert r.json()["tenant_id"] == free_after(int(seeded[4:]))


# ── Comped tenants come from configuration ────────────────────────────

def test_comped_tenants_follow_configuration(client, super_admin, monkeypatch):
    import app.routers.tenant as tenant_router

    comped_signup, comped_uuid = _pending_tenant(client)
    paying_signup, paying_uuid = _pending_tenant(client)
    comped_public = _approve(client, super_admin, comped_uuid).json()["tenant_id"]
    _approve(client, super_admin, paying_uuid)

    monkeypatch.setattr(tenant_router, "FREE_ACCESS_TENANTS", frozenset({comped_public}))

    def billing(signup):
        return client.get("/api/v1/tenant/billing", headers=_auth(signup["access_token"])).json()

    assert billing(comped_signup)["special_free_access"] is True
    assert billing(paying_signup)["special_free_access"] is False

    admin_rows = client.get("/api/v1/admin/billing", headers=_auth(super_admin.token)).json()["clients"]
    flags = {c["tenant_id"]: c["special_free_access"] for c in admin_rows}
    assert flags[comped_uuid] is True
    assert flags[paying_uuid] is False
