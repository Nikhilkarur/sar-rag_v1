from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.tenant import Tenant
from app.models.webhook import WebhookConfig
from app.models.llm_config import LLMConfig
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.tenant import TenantApproveRequest, TenantApproveResponse, TenantRejectRequest
from app.utils.security import generate_api_key, hash_api_key
import secrets

def generate_tenant_id_public(db: Session) -> str:
    count = db.query(Tenant).count()
    return f"TEN-{count+1:04d}"

def approve_tenant(tenant_id: str, current_user: User, db: Session) -> TenantApproveResponse:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    if tenant.status != 'PENDING_VERIFICATION':
        raise HTTPException(status_code=400, detail="Tenant is not pending verification")
        
    plaintext_key = generate_api_key()
    key_hash = hash_api_key(plaintext_key)
    prefix = plaintext_key[:12]
    
    tenant_id_public = generate_tenant_id_public(db)
    
    tenant.status = 'ACTIVE'
    tenant.api_key_hash = key_hash
    tenant.api_key_prefix = prefix
    tenant.tenant_id_public = tenant_id_public
    tenant.approved_at = __import__('sqlalchemy').func.now()
    tenant.approved_by = current_user.id
    
    # Create Webhook Config
    webhook = WebhookConfig(
        tenant_id=tenant.id,
        use_internal_sink=True,
        secret_hash=hash_api_key(secrets.token_hex(32)),
        secret_prefix=secrets.token_hex(6)
    )
    db.add(webhook)
    
    # Create LLM Config
    llm = LLMConfig(
        tenant_id=tenant.id,
        provider="GROQ",
        model_name="llama-3.3-70b-versatile"
    )
    db.add(llm)
    
    # Audit Logs
    audit1 = AuditLog(tenant_id=tenant.id, user_id=current_user.id, action="TENANT_APPROVED", entity_type="tenant", entity_id=tenant.id)
    audit2 = AuditLog(tenant_id=tenant.id, user_id=current_user.id, action="API_KEY_GENERATED", entity_type="tenant", entity_id=tenant.id)
    db.add(audit1)
    db.add(audit2)
    
    db.commit()
    
    return TenantApproveResponse(
        tenant_id=tenant.id,
        status=tenant.status,
        api_key=plaintext_key
    )

def reject_tenant(tenant_id: str, request: TenantRejectRequest, current_user: User, db: Session):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    if tenant.status != 'PENDING_VERIFICATION':
        raise HTTPException(status_code=400, detail="Tenant is not pending verification")
        
    tenant.status = 'REJECTED'
    tenant.rejection_reason = request.reason
    
    audit = AuditLog(tenant_id=tenant.id, user_id=current_user.id, action="TENANT_REJECTED", entity_type="tenant", entity_id=tenant.id)
    db.add(audit)
    db.commit()
    
    return {"status": "success", "tenant_id": tenant.id}
