from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import tenant_service
from app.utils.deps import get_tenant_admin, get_current_active_tenant_user
from app.models.user import User
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

@router.get("/llm-config")
def get_llm_config(db: Session = Depends(get_db), current_user: User = Depends(get_tenant_admin)):
    return tenant_service.get_llm_config(current_user, db)

@router.get("/schemas")
def get_schemas(db: Session = Depends(get_db), current_user: User = Depends(get_tenant_admin)):
    return tenant_service.get_schemas(current_user, db)
