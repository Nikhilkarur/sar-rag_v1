#!/bin/sh
# Container entrypoint for the Aegis API.
#   1. Refuse an insecure production configuration BEFORE touching the database.
#   2. Apply Alembic migrations (idempotent).
#   3. Remove stale sample files an earlier image baked into the storage volume.
#   4. Optionally run seed.py (idempotent; never regenerates an existing API key).
#   5. Hand off to the CMD (uvicorn by default).
set -e

# app/main.py has the same guard, but it only runs once uvicorn imports the app,
# i.e. after migrations and seeding have already written data (encrypted with the
# wrong key, plus public demo logins). Check first, fail closed.
python - <<'PY'
import os, sys
from app.config import settings

errors = settings.production_config_errors()
if settings.ENVIRONMENT == "production":
    if settings.PII_ENCRYPTION_KEY:
        try:
            from cryptography.fernet import Fernet
            Fernet(settings.PII_ENCRYPTION_KEY)
        except Exception:
            errors.append("PII_ENCRYPTION_KEY is not a valid Fernet key.")
    if os.environ.get("SEED_ON_START", "false") == "true":
        for var in ("AEGIS_ADMIN_PASSWORD", "AEGIS_TENANT_ADMIN_PASSWORD"):
            if not os.environ.get(var):
                errors.append(f"SEED_ON_START=true in production requires {var} "
                              "(the built-in demo password is public). Or set SEED_ON_START=false.")
if errors:
    sys.exit("Refusing to start: insecure production configuration:\n  - " + "\n  - ".join(errors))
PY

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "[entrypoint] Applying database migrations..."
  python -m alembic upgrade head
fi

# One-off cleanup: the first Docker image baked the repo's storage/clients/TEN-0003 and
# TEN-0005 sample files into fresh client_storage volumes, where a new tenant receiving that id
# would inherit another organisation's policy. Remove them only while NO tenant with that id
# exists (so nothing there can be real tenant data). Best-effort; never blocks startup.
python - <<'PY' || true
import os, shutil
from app.database import SessionLocal
from app.models.tenant import Tenant
from app.services.client_storage import CLIENTS_ROOT
db = SessionLocal()
try:
    for cid in ("TEN-0003", "TEN-0005"):
        d = os.path.join(CLIENTS_ROOT, cid)
        if os.path.isdir(d) and not db.query(Tenant).filter(Tenant.tenant_id_public == cid).first():
            try:
                shutil.rmtree(d)
                print(f"[entrypoint] Removed stale sample files baked in by an earlier image: {d}")
            except OSError as e:
                print(f"[entrypoint] WARNING: could not remove stale sample files in {d} ({e}); "
                      "delete that folder from the client_storage volume manually.")
except Exception as e:
    print(f"[entrypoint] Skipped stale-storage cleanup: {e}")
finally:
    db.close()
PY

if [ "${SEED_ON_START:-false}" = "true" ]; then
  echo "[entrypoint] Seeding database (idempotent)..."
  python seed.py
fi

exec "$@"
