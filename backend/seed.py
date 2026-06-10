import os
import sys
from app.database import SessionLocal, engine, Base
from app.models.tenant import Tenant
from app.models.user import User
from app.models.schema import IngestionSchema
from app.models.webhook import WebhookConfig
from app.models.llm_config import LLMConfig
from app.utils.security import hash_password, hash_api_key
from app.data.schema_presets import SCHEMA_PRESETS

# Ensure tables are created (in a real app, use Alembic)
Base.metadata.create_all(bind=engine)

def seed():
    db = SessionLocal()
    try:
        # 1. Super Admin
        admin = db.query(User).filter_by(email="admin@aegis-aml.com").first()
        if not admin:
            admin = User(
                email="admin@aegis-aml.com",
                password_hash=hash_password("AegisAdmin2026!"),
                full_name="Aegis Super Admin",
                role="SUPER_ADMIN"
            )
            db.add(admin)
            db.commit()
            print("Created Super Admin user")
        
        # 2. Demo Tenant
        tenant = db.query(Tenant).filter_by(slug="demofintech").first()
        if not tenant:
            demo_key = "sk-ae-demo"
            tenant = Tenant(
                name="DemoFintech Pvt Ltd",
                slug="demofintech",
                company_type="FINTECH",
                status="ACTIVE",
                api_key_hash=hash_api_key(demo_key),
                api_key_prefix="sk-ae-demo",
                tenant_id_public="TEN-DEMO",
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            print("Created Demo Tenant")
        
        # 3. Demo User
        user = db.query(User).filter_by(email="demo@demofintech.com").first()
        if not user:
            user = User(
                tenant_id=tenant.id,
                email="demo@demofintech.com",
                password_hash=hash_password("Demo2026!"),
                full_name="Demo User",
                role="TENANT_ADMIN"
            )
            db.add(user)
            db.commit()
            print("Created Demo User")
        
        # 4. Ingestion Schema
        schema = db.query(IngestionSchema).filter_by(tenant_id=tenant.id).first()
        if not schema:
            preset = SCHEMA_PRESETS["STANDARD_FINTECH"]
            schema = IngestionSchema(
                tenant_id=tenant.id,
                name=preset["name"],
                template_key="STANDARD_FINTECH",
                field_map=preset["field_map"],
                pii_fields=preset["pii_fields"]
            )
            db.add(schema)
            db.commit()
            print("Created Ingestion Schema")
        
        # 5. Webhook Config
        webhook = db.query(WebhookConfig).filter_by(tenant_id=tenant.id).first()
        if not webhook:
            webhook = WebhookConfig(
                tenant_id=tenant.id,
                use_internal_sink=True
            )
            db.add(webhook)
            db.commit()
            print("Created Webhook Config")
            
        # 6. LLM Config
        llm = db.query(LLMConfig).filter_by(tenant_id=tenant.id).first()
        if not llm:
            llm = LLMConfig(
                tenant_id=tenant.id,
                provider="GROQ",
                model_name="llama-3.3-70b-versatile",
                sar_template_style="BOTH"
            )
            db.add(llm)
            db.commit()
            print("Created LLM Config")
            
    finally:
        db.close()

if __name__ == "__main__":
    print("Seeding database...")
    seed()
    print("Seeding complete.")
