from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.tenant import Tenant
from app.models.webhook import WebhookConfig
from app.models.llm_config import LLMConfig
from app.models.audit import AuditLog
from app.models.user import User
from app.models.schema import IngestionSchema
from app.data.schema_presets import SCHEMA_PRESETS
from app.schemas.tenant import TenantApproveRequest, TenantApproveResponse, TenantRejectRequest
from app.utils.deps import parse_uuid_or_404
from app.utils.security import generate_api_key, hash_api_key, encrypt_json
import secrets

# Default ingestion schema a tenant starts with at approval, so ingest works out of the box
# (without this, the first transaction is rejected with "No active schema found" until the
# tenant manually picks a preset). The tenant can switch presets in Settings → Ingestion Schema.
_DEFAULT_SCHEMA_KEY = "STANDARD_FINTECH"

def generate_tenant_id_public(db: Session) -> str:
    # Count-based ids collide after rejections/deletions (count shrinks while
    # the high ids remain taken) — walk forward until a free id is found.
    n = db.query(Tenant).count() + 1
    while db.query(Tenant).filter(Tenant.tenant_id_public == f"TEN-{n:04d}").first():
        n += 1
    return f"TEN-{n:04d}"

def approve_tenant(tenant_id: str, current_user: User, db: Session) -> TenantApproveResponse:
    valid_id = parse_uuid_or_404(tenant_id, "Tenant")
    tenant = db.query(Tenant).filter(Tenant.id == valid_id).first()
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
    # Encrypted copy enables the portal's "reveal key" (hash remains the verifier)
    tenant.api_key_encrypted = encrypt_json(plaintext_key)
    tenant.api_key_last_rotated = __import__('sqlalchemy').func.now()
    tenant.tenant_id_public = tenant_id_public
    tenant.approved_at = __import__('sqlalchemy').func.now()
    tenant.approved_by = current_user.id

    # Create Webhook Config — secret stored encrypted so deliveries can be HMAC-signed
    webhook_secret = secrets.token_hex(32)
    webhook = WebhookConfig(
        tenant_id=tenant.id,
        use_internal_sink=True,
        secret_hash=hash_api_key(webhook_secret),
        secret_encrypted=encrypt_json(webhook_secret),
        secret_prefix=webhook_secret[:12]
    )
    db.add(webhook)
    
    # Create LLM Config
    llm = LLMConfig(
        tenant_id=tenant.id,
        provider="GROQ",
        model_name="llama-3.3-70b-versatile"
    )
    db.add(llm)

    # Provision a default ACTIVE ingestion schema so the tenant can ingest transactions
    # immediately after approval — no hidden manual step before the pipeline works.
    preset = SCHEMA_PRESETS.get(_DEFAULT_SCHEMA_KEY)
    if preset:
        db.add(IngestionSchema(
            tenant_id=tenant.id,
            name=preset["name"],
            template_key=_DEFAULT_SCHEMA_KEY,
            is_active=True,
            field_map=preset["field_map"],
            pii_fields=preset["pii_fields"],
        ))

    # Audit Logs
    audit1 = AuditLog(tenant_id=tenant.id, user_id=current_user.id, action="TENANT_APPROVED", entity_type="tenant", entity_id=tenant.id)
    audit2 = AuditLog(tenant_id=tenant.id, user_id=current_user.id, action="API_KEY_GENERATED", entity_type="tenant", entity_id=tenant.id)
    db.add(audit1)
    db.add(audit2)
    
    db.commit()
    
    return TenantApproveResponse(
        tenant_id=str(tenant.id),
        status=tenant.status,
        api_key=plaintext_key
    )

def reject_tenant(tenant_id: str, request: TenantRejectRequest, current_user: User, db: Session):
    valid_id = parse_uuid_or_404(tenant_id, "Tenant")
    tenant = db.query(Tenant).filter(Tenant.id == valid_id).first()
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
