from app.database import SessionLocal, engine
from app.models.tenant import Tenant
from app.models.user import User
from app.models.alert import Alert
from app.models.sar import SARDraft
from app.models.compliance import ComplianceMatch
from app.models.pii_map import PIIMap
from app.models.schema import IngestionSchema
from app.models.webhook import WebhookConfig, WebhookSinkEvent
from app.models.llm_config import LLMConfig
from app.models.api_log import APILog
from app.models.audit import AuditLog
from app.models.delivery import WebhookDelivery

def clear_db():
    db = SessionLocal()
    try:
        # First, detach Super Admins from any tenant so they aren't cascaded
        super_admins = db.query(User).filter(User.role == 'SUPER_ADMIN').all()
        for admin in super_admins:
            admin.tenant_id = None
        db.commit()

        # Delete dependent tables first to avoid FK constraint errors
        db.query(APILog).delete()
        db.query(AuditLog).delete()
        db.query(WebhookDelivery).delete()
        db.query(WebhookSinkEvent).delete()
        db.query(WebhookConfig).delete()
        db.query(LLMConfig).delete()
        db.query(PIIMap).delete()
        db.query(ComplianceMatch).delete()
        db.query(SARDraft).delete()
        db.query(Alert).delete()
        db.query(IngestionSchema).delete()

        # Delete all non-super-admin users AFTER alerts to avoid reviewed_by FK error
        db.query(User).filter(User.role != 'SUPER_ADMIN').delete()
        db.query(AuditLog).delete()
        db.query(APILog).delete()
        
        # Finally delete tenants
        db.query(Tenant).delete()
        
        db.commit()
        
        print("Database cleared. Super Admins preserved:", len(super_admins))
        
    except Exception as e:
        db.rollback()
        print("Error clearing DB:", e)
    finally:
        db.close()

if __name__ == "__main__":
    clear_db()
