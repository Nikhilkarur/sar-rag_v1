from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

from app.middleware.logging import APILoggingMiddleware
from app.routers import auth, admin, tenant, ingest, alerts

_IS_PROD = settings.ENVIRONMENT == "production"

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
    allow_origins=[settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(tenant.router)
app.include_router(ingest.router)
app.include_router(alerts.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}
