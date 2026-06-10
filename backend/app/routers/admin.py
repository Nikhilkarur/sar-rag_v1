from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.tenant import TenantApproveRequest, TenantApproveResponse, TenantRejectRequest, TenantResponse
from app.services import admin_service
from app.utils.deps import get_super_admin
from app.models.user import User

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])

@router.post("/tenants/{tenant_id}/approve", response_model=TenantApproveResponse)
def approve_tenant(tenant_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_super_admin)):
    return admin_service.approve_tenant(tenant_id, current_user, db)

@router.post("/tenants/{tenant_id}/reject")
def reject_tenant(tenant_id: str, request: TenantRejectRequest, db: Session = Depends(get_db), current_user: User = Depends(get_super_admin)):
    return admin_service.reject_tenant(tenant_id, request, current_user, db)

@router.get("/verifications")
def list_verifications(db: Session = Depends(get_db), current_user: User = Depends(get_super_admin)):
    from app.models.tenant import Tenant
    tenants = db.query(Tenant).filter(Tenant.status == 'PENDING_VERIFICATION').all()
    results = []
    for t in tenants:
        user = db.query(User).filter(User.tenant_id == t.id, User.role == 'TENANT_ADMIN').first()
        results.append({
            "id": str(t.id),
            "companyName": t.name,
            "companyType": t.company_type,
            "applicantName": user.full_name if user else "Unknown",
            "email": user.email if user else "unknown@email.com",
            "submittedAt": t.created_at.isoformat() if t.created_at else "",
            "status": "PENDING"
        })
    return results
