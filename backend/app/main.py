import threading
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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


@app.exception_handler(UnicodeEncodeError)
async def _lone_surrogate_is_a_bad_request(request: Request, exc: UnicodeEncodeError):
    # JSON allows "\ud800" escapes that no UTF-8 text can hold; psycopg2 raises when such a
    # string reaches the DB (draft edits, reject reasons, webhook URLs...). That's the
    # client's input, not a server fault. Any other encode error is still a 500.
    if exc.reason != "surrogates not allowed":
        raise exc
    return JSONResponse(status_code=422,
                        content={"detail": "Request contains an unpaired UTF-16 surrogate (a lone \\ud800-\\udfff escape)"})


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


@app.on_event("startup")
def _sweep_stuck_processing_alerts():
    # SAR generation runs in-process, so alerts a previous worker left in PROCESSING
    # (it died mid-generation) would never finish. Fail those already past the grace
    # period now, and the rest of the pre-boot ones once they pass it too: nothing
    # ingested after this boot is touched. Runs off-thread so a slow or unreachable
    # DB never blocks startup.
    boot = datetime.now(timezone.utc)
    grace = timedelta(minutes=settings.STUCK_PROCESSING_TIMEOUT_MINUTES)

    def sweep(started_before):
        try:
            count = ingest.fail_stuck_processing_alerts(started_before)
            if count:
                print(f"Marked {count} alert(s) stuck in PROCESSING as PROCESSING_FAILED")
        except Exception as e:
            print(f"Stuck-alert sweep failed: {e}")

    threading.Thread(target=sweep, args=(boot - grace,), daemon=True).start()
    later = threading.Timer(grace.total_seconds(), sweep, args=(boot,))
    later.daemon = True
    later.start()


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}
