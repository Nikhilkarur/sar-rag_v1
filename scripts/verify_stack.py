"""
verify_stack.py - Phase 5.5 acceptance battery.

Hits the live backend and asserts the auth/API contract end to end:
health, admin + tenant login, /auth/me, refresh ROTATION (old token must
die, new must work), and every auth edge case that used to risk a 500
(bad password, unknown email, malformed/expired tokens, garbage UUIDs,
wrong API keys, replayed payloads).

    python scripts/verify_stack.py
"""
import sys
import uuid

import httpx

BASE = "http://localhost:8000"
API = f"{BASE}/api/v1"

ADMIN = {"email": "admin@aegis-aml.com", "password": "AegisAdmin2026!"}
TENANT_ADMIN = {"email": "admin@testfintech.in", "password": "TestFintech2026!"}

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    mark = "PASS" if condition else "FAIL"
    if condition:
        passed += 1
    else:
        failed += 1
    print(f"  [{mark}] {name}" + (f"  - {detail}" if detail and not condition else ""))


def cleanup_probe_tenants():
    """Best-effort: remove the throwaway 'Probe Fintech' tenants this battery signs up, so they
    don't accumulate as junk in the admin Verification Queue. Purely housekeeping — it prints an
    info line and NEVER affects the pass/fail count (or raises)."""
    import os
    backend = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)
    try:
        from app.database import SessionLocal
        from app.models.tenant import Tenant
        from app.models.user import User
        db = SessionLocal()
        try:
            probes = db.query(Tenant).filter(Tenant.name == "Probe Fintech").all()
            for t in probes:
                for u in db.query(User).filter(User.tenant_id == t.id).all():
                    db.delete(u)
                db.delete(t)  # alerts/matches cascade
            db.commit()
            print(f"  [info] cleaned up {len(probes)} probe tenant(s)")
        finally:
            db.close()
    except Exception as e:  # noqa: BLE001 — housekeeping must never break the run
        print(f"  [info] probe cleanup skipped ({e.__class__.__name__})")


def main() -> int:
    c = httpx.Client(timeout=30.0)

    print("\n-- Health --")
    r = c.get(f"{BASE}/health")
    check("GET /health -> 200", r.status_code == 200, str(r.status_code))

    print("\n-- JWT: login --")
    r = c.post(f"{API}/auth/login", json=ADMIN)
    check("admin login -> 200", r.status_code == 200, r.text[:200])
    admin_tokens = r.json() if r.status_code == 200 else {}
    check("admin role is SUPER_ADMIN", admin_tokens.get("user", {}).get("role") == "SUPER_ADMIN")

    r = c.post(f"{API}/auth/login", json=TENANT_ADMIN)
    check("tenant admin login -> 200", r.status_code == 200, r.text[:200])
    tenant_tokens = r.json() if r.status_code == 200 else {}
    t_user = tenant_tokens.get("user", {})
    check("tenant attached and ACTIVE", (t_user.get("tenant") or {}).get("status") == "ACTIVE")

    access = tenant_tokens.get("access_token", "")
    refresh = tenant_tokens.get("refresh_token", "")
    auth = {"Authorization": f"Bearer {access}"}

    print("\n-- JWT: /me + token-type confusion --")
    r = c.get(f"{API}/auth/me", headers=auth)
    check("/auth/me with access token -> 200", r.status_code == 200, str(r.status_code))
    r = c.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {refresh}"})
    check("refresh token rejected as access token -> 401", r.status_code == 401, str(r.status_code))

    print("\n-- JWT: refresh rotation --")
    r = c.post(f"{API}/auth/refresh", json={"refresh_token": refresh})
    check("refresh -> 200 + new pair", r.status_code == 200 and "refresh_token" in r.json(), r.text[:200])
    new_refresh = r.json().get("refresh_token", "") if r.status_code == 200 else ""
    r = c.post(f"{API}/auth/refresh", json={"refresh_token": refresh})
    check("OLD refresh token re-use -> 401 (rotation enforced)", r.status_code == 401, str(r.status_code))
    r = c.post(f"{API}/auth/refresh", json={"refresh_token": new_refresh})
    check("NEW refresh token works -> 200", r.status_code == 200, str(r.status_code))

    print("\n-- Auth edge cases (must be 4xx, never 500) --")
    r = c.post(f"{API}/auth/login", json={"email": TENANT_ADMIN["email"], "password": "wrong-password"})
    check("wrong password -> 401", r.status_code == 401, str(r.status_code))
    r = c.post(f"{API}/auth/login", json={"email": "ghost@nowhere.in", "password": "whatever123"})
    check("unknown email -> 401", r.status_code == 401, str(r.status_code))
    r = c.post(f"{API}/auth/login", json={"email": "not-an-email", "password": "x"})
    check("malformed email -> 422", r.status_code == 422, str(r.status_code))
    r = c.post(f"{API}/auth/refresh", json={"refresh_token": "garbage.token.here"})
    check("garbage refresh token -> 401", r.status_code == 401, str(r.status_code))
    r = c.get(f"{API}/auth/me", headers={"Authorization": "Bearer nonsense"})
    check("garbage access token -> 401", r.status_code == 401, str(r.status_code))
    r = c.get(f"{API}/alerts/queue/not-a-uuid", headers=auth)
    check("garbage UUID path -> 404 (was 500)", r.status_code == 404, str(r.status_code))
    r = c.get(f"{API}/alerts/queue/{uuid.uuid4()}", headers=auth)
    check("unknown-but-valid UUID -> 404", r.status_code == 404, str(r.status_code))

    print("\n-- Signup --")
    probe_email = f"probe-{uuid.uuid4().hex[:8]}@example.in"
    signup_body = {
        "company_name": "Probe Fintech",
        "company_type": "FINTECH",
        "admin_email": probe_email,
        "admin_password": "ProbePass2026!",
        "admin_name": "Probe Admin",
    }
    r = c.post(f"{API}/auth/signup", json=signup_body)
    check("signup -> 200 + tokens", r.status_code == 200 and "access_token" in r.json(), r.text[:200])
    r = c.post(f"{API}/auth/signup", json=signup_body)
    check("duplicate signup -> 400", r.status_code == 400, str(r.status_code))
    r = c.post(f"{API}/auth/login", json={"email": probe_email, "password": "ProbePass2026!"})
    probe_user = r.json().get("user", {}) if r.status_code == 200 else {}
    check("new tenant is PENDING_VERIFICATION", (probe_user.get("tenant") or {}).get("status") == "PENDING_VERIFICATION")

    print("\n-- API-key ingest auth --")
    body = {"txn": {"ref_id": "X", "amount": 1}}
    r = c.post(f"{API}/ingest/", json=body, headers={"X-API-Key": "sk-ae-wrong", "X-Tenant-ID": "TEN-0001"})
    check("wrong API key -> 401", r.status_code == 401, str(r.status_code))
    r = c.post(f"{API}/ingest/", json=body, headers={"X-API-Key": "sk-ae-wrong", "X-Tenant-ID": "TEN-9999"})
    check("unknown tenant id -> 401 (no enumeration)", r.status_code == 401, str(r.status_code))
    r = c.post(f"{API}/ingest/", json=body)
    check("missing headers -> 422", r.status_code == 422, str(r.status_code))

    print("\n-- Admin authorization --")
    r = c.get(f"{API}/admin/verifications", headers=auth)
    check("tenant admin blocked from admin API -> 403", r.status_code == 403, str(r.status_code))
    admin_auth = {"Authorization": f"Bearer {admin_tokens.get('access_token', '')}"}
    r = c.get(f"{API}/admin/verifications", headers=admin_auth)
    check("super admin sees verifications -> 200", r.status_code == 200, str(r.status_code))
    if r.status_code == 200:
        names = [v.get("name") for v in r.json()]
        check("probe signup awaiting verification", "Probe Fintech" in names)
    r = c.post(f"{API}/admin/tenants/not-a-uuid/approve", headers=admin_auth)
    check("admin garbage UUID -> 404 (was 500)", r.status_code == 404, str(r.status_code))

    print("\n-- Cleanup --")
    cleanup_probe_tenants()

    print(f"\n{'=' * 48}\nRESULT: {passed} passed, {failed} failed\n{'=' * 48}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
