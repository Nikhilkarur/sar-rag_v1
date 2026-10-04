"""
APILoggingMiddleware: unhandled exceptions are logged as 500 (and still raised), the
log write runs off the event loop and can't break a request, and the client IP reaches
AuditLog.actor_ip through the request context (sync/threadpool and async endpoints).

The first group is DB-free (the log writer is replaced by a recorder). The DB-backed
group runs against DATABASE_URL and is skipped when that DB (with migrations applied)
is unreachable.
"""
import threading
import uuid

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, get_db
from app.middleware import logging as api_logging
from app.middleware.logging import APILoggingMiddleware
from app.utils import request_context


def _app(state: dict) -> FastAPI:
    app = FastAPI()
    app.add_middleware(APILoggingMiddleware)

    @app.get("/ok")
    def ok():
        return {"ok": True}

    @app.get("/boom/{tag}")
    def boom(tag: str):
        raise RuntimeError("unhandled " + tag)

    @app.get("/ip-sync")
    def ip_sync():
        return {"ip": request_context.client_ip.get()}

    @app.get("/ip-async")
    async def ip_async():
        state["loop_thread"] = threading.get_ident()
        return {"ip": request_context.client_ip.get()}

    def ip_dep():
        return request_context.client_ip.get()

    @app.get("/ip-dep")
    def ip_from_sync_dependency(ip=Depends(ip_dep)):
        return {"ip": ip}

    return app


@pytest.fixture
def recorded(monkeypatch):
    calls = []

    def record(**kw):
        kw["thread"] = threading.get_ident()
        calls.append(kw)
    monkeypatch.setattr(api_logging, "_write_api_log", record)
    return calls


def test_unhandled_exception_is_logged_as_500(recorded):
    client = TestClient(_app({}), raise_server_exceptions=False)
    r = client.get("/boom/x")
    assert r.status_code == 500
    assert [(c["endpoint"], c["status_code"]) for c in recorded] == [("/boom/x", 500)]
    assert recorded[0]["request_ip"] == "testclient"


def test_exception_still_propagates_after_logging(recorded):
    client = TestClient(_app({}))  # re-raises server exceptions
    with pytest.raises(RuntimeError, match="unhandled y"):
        client.get("/boom/y")
    assert [c["status_code"] for c in recorded] == [500]


def test_success_is_logged_with_its_status(recorded):
    client = TestClient(_app({}))
    assert client.get("/ok").status_code == 200
    assert client.get("/nope").status_code == 404
    assert [(c["endpoint"], c["status_code"]) for c in recorded] == [("/ok", 200), ("/nope", 404)]


def test_log_write_runs_off_the_event_loop(recorded):
    state = {}
    client = TestClient(_app(state))
    assert client.get("/ip-async").status_code == 200
    assert recorded and recorded[0]["thread"] != state["loop_thread"]


def test_logging_failure_never_breaks_the_request(monkeypatch):
    def broken(**kw):
        raise RuntimeError("log db down")
    monkeypatch.setattr(api_logging, "_write_api_log", broken)
    client = TestClient(_app({}))
    assert client.get("/ok").json() == {"ok": True}
    # ...and doesn't mask the original exception on the error path
    with pytest.raises(RuntimeError, match="unhandled z"):
        client.get("/boom/z")


@pytest.mark.parametrize("path", ["/ip-sync", "/ip-async", "/ip-dep"])
def test_client_ip_reaches_handlers(recorded, path):
    client = TestClient(_app({}))
    assert client.get(path).json() == {"ip": "testclient"}


# --- DB-backed --------------------------------------------------------------
@pytest.fixture(scope="module")
def db_ready():
    try:
        with engine.connect():
            pass
        insp = sa_inspect(engine)
        if not (insp.has_table("api_logs") and insp.has_table("audit_logs")):
            pytest.skip("database schema not migrated")
    except Exception as e:  # unreachable DB -> skip, don't fail the suite
        pytest.skip(f"database unavailable: {e.__class__.__name__}")


def test_500_is_persisted_to_api_logs(db_ready):
    from app.models.api_log import APILog
    tag = uuid.uuid4().hex
    client = TestClient(_app({}), raise_server_exceptions=False)
    assert client.get(f"/boom/{tag}").status_code == 500
    db = SessionLocal()
    try:
        rows = db.query(APILog).filter(APILog.endpoint == f"/boom/{tag}").all()
        assert [(r.status_code, r.method, r.request_ip) for r in rows] == [(500, "GET", "testclient")]
        for r in rows:
            db.delete(r)
        db.commit()
    finally:
        db.close()


def test_audit_log_actor_ip_filled_from_request(db_ready):
    from app.models.audit import AuditLog
    action = f"TEST_ACTOR_IP_{uuid.uuid4().hex[:8]}"
    app = FastAPI()
    app.add_middleware(APILoggingMiddleware)

    # Mirrors the real call sites: sync endpoints that db.add(AuditLog(...)) without an IP
    @app.post("/sync-audit")
    def sync_audit(db: Session = Depends(get_db)):
        db.add(AuditLog(action=action, details={"via": "sync"}))
        db.commit()
        return {}

    @app.post("/async-audit")
    async def async_audit():
        db = SessionLocal()
        try:
            db.add(AuditLog(action=action, details={"via": "async"}))
            db.add(AuditLog(action=action, details={"via": "explicit"}, actor_ip="10.9.9.9"))
            db.commit()
        finally:
            db.close()
        return {}

    client = TestClient(app)
    assert client.post("/sync-audit").status_code == 200
    assert client.post("/async-audit").status_code == 200

    db = SessionLocal()
    try:
        # Outside any request there is no caller IP to record
        db.add(AuditLog(action=action, details={"via": "script"}))
        db.commit()
        rows = db.query(AuditLog).filter(AuditLog.action == action).all()
        got = {r.details["via"]: r.actor_ip for r in rows}
        assert got == {"sync": "testclient", "async": "testclient",
                       "explicit": "10.9.9.9", "script": None}
        for r in rows:
            db.delete(r)
        db.commit()
        db.query(api_logging.APILog).filter(
            api_logging.APILog.endpoint.in_(["/sync-audit", "/async-audit"])).delete(
            synchronize_session=False)
        db.commit()
    finally:
        db.close()
