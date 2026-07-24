from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

from app.middleware.logging import APILoggingMiddleware
from app.routers import auth, admin, tenant, ingest, alerts, files, documents

_IS_PROD = settings.ENVIRONMENT == "production"

# Fail closed: refuse to boot a production instance whose security-critical secrets
# are still defaults (unset PII key / default JWT secret). Dev is unaffected.
_config_errors = settings.production_config_errors()
if _config_errors:
    raise RuntimeError(
        "Refusing to start: insecure production configuration:\n  - "
        + "\n  - ".join(_config_errors)
    )

app = FastAPI(
    title="Aegis AML",
    version="1.0.0",
    # Don't hand attackers a complete API map in production
    docs_url=None if _IS_PROD else "/docs",
    redoc_url=None if _IS_PROD else "/redoc",
    openapi_url=None if _IS_PROD else "/openapi.json",
)

app.add_middleware(APILoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(tenant.router)
app.include_router(ingest.router)
app.include_router(alerts.router)
app.include_router(files.router)
app.include_router(documents.router)

@app.on_event("startup")
def _warm_embeddings():
    # The embedding model loads lazily on first use (see services/embeddings.py, which also
    # sets the OMP/torch env guards at import). An earlier build eagerly warmed it here to
    # sidestep a torch/DB init-order segfault on this env; that no longer reproduces, so warmup
    # is left off to keep startup fast. Kept as a single hook so eager warmup can be re-enabled
    # in one place if a deployment ever needs it.
    try:
        pass
    except Exception:
        pass  # never block startup on optional warmup


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}
