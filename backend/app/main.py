from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

from app.middleware.logging import APILoggingMiddleware
from app.routers import auth, admin, tenant, ingest, alerts

app = FastAPI(title="Aegis AML", version="1.0.0")

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
