from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import tenant_service
from app.utils.deps import get_tenant_admin, get_current_active_tenant_user
from app.utils.security import validate_webhook_url
from app.models.user import User
from app.models.webhook import WebhookConfig
from app.models.audit import AuditLog
from app.schemas.tenant import TenantResponse

router = APIRouter(prefix="/api/v1/tenant", tags=["Tenant"])

@router.get("/profile", response_model=TenantResponse)
def get_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_tenant_user)):
    return tenant_service.get_profile(current_user, db)

@router.get("/credentials")
def get_credentials(db: Session = Depends(get_db), current_user: User = Depends(get_tenant_admin)):
    return tenant_service.get_credentials(current_user, db)

@router.get("/webhook")
def get_webhook(db: Session = Depends(get_db), current_user: User = Depends(get_tenant_admin)):
    return tenant_service.get_webhook(current_user, db)

@router.put("/webhook")
def update_webhook(payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_tenant_admin)):
    webhook = db.query(WebhookConfig).filter(WebhookConfig.tenant_id == current_user.tenant_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook config not found")

    use_internal_sink = bool(payload.get("use_internal_sink", webhook.use_internal_sink))
    callback_url = payload.get("callback_url", webhook.callback_url)

    if not use_internal_sink:
        if not callback_url:
            raise HTTPException(status_code=400, detail="callback_url is required when not using the internal sink")
        try:
            # SSRF guard: refuse URLs resolving to loopback/RFC1918/link-local
            # (cloud metadata), reserved or multicast ranges
            validate_webhook_url(callback_url)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    webhook.use_internal_sink = use_internal_sink
    webhook.callback_url = callback_url

    db.add(AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="WEBHOOK_CONFIG_UPDATED",
        entity_type="webhook_config",
        entity_id=webhook.id,
        details={"use_internal_sink": use_internal_sink}
    ))
    db.commit()
    db.refresh(webhook)
    return webhook

@router.get("/llm-config")
def get_llm_config(db: Session = Depends(get_db), current_user: User = Depends(get_tenant_admin)):
    return tenant_service.get_llm_config(current_user, db)

@router.get("/schemas")
def get_schemas(db: Session = Depends(get_db), current_user: User = Depends(get_tenant_admin)):
    return tenant_service.get_schemas(current_user, db)
