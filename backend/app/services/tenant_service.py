from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.tenant import Tenant
from app.models.webhook import WebhookConfig
from app.models.llm_config import LLMConfig
from app.models.schema import IngestionSchema
from app.models.user import User

def get_profile(current_user: User, db: Session):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    return tenant

def get_credentials(current_user: User, db: Session):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    return {
        "tenant_id_public": tenant.tenant_id_public,
        "api_key_prefix": tenant.api_key_prefix
    }

def get_webhook(current_user: User, db: Session):
    webhook = db.query(WebhookConfig).filter(WebhookConfig.tenant_id == current_user.tenant_id).first()
    return webhook

def get_llm_config(current_user: User, db: Session):
    llm = db.query(LLMConfig).filter(LLMConfig.tenant_id == current_user.tenant_id).first()
    return llm

def get_schemas(current_user: User, db: Session):
    schemas = db.query(IngestionSchema).filter(IngestionSchema.tenant_id == current_user.tenant_id).all()
    return schemas
