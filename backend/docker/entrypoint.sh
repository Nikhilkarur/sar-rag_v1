#!/bin/sh
# Container entrypoint for the Aegis API.
#   1. Refuse an insecure production configuration BEFORE touching the database.
#   2. Apply Alembic migrations (idempotent).
#   3. Optionally run seed.py (idempotent; never regenerates an existing API key).
#   4. Hand off to the CMD (uvicorn by default).
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

if [ "${SEED_ON_START:-false}" = "true" ]; then
  echo "[entrypoint] Seeding database (idempotent)..."
  python seed.py
fi

exec "$@"
