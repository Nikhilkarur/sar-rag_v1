#!/bin/sh
# Container entrypoint for the Aegis API.
#   1. Apply Alembic migrations (idempotent).
#   2. Optionally run seed.py (idempotent; never regenerates an existing API key).
#   3. Hand off to the CMD (uvicorn by default).
set -e

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "[entrypoint] Applying database migrations..."
  python -m alembic upgrade head
fi

if [ "${SEED_ON_START:-false}" = "true" ]; then
  echo "[entrypoint] Seeding database (idempotent)..."
  python seed.py
fi

exec "$@"
