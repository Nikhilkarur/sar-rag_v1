from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.tenant import TenantApproveResponse, TenantRejectRequest
from app.services import admin_service
from app.utils.deps import get_super_admin, parse_uuid_or_404
from app.models.user import User
from app.models.tenant import Tenant
from app.models.alert import Alert
from app.models.api_log import APILog
from app.models.llm_config import LLMConfig
from app.models.audit import AuditLog

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])

@router.post("/tenants/{tenant_id}/approve", response_model=TenantApproveResponse)
def approve_tenant(tenant_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_super_admin)):
    return admin_service.approve_tenant(tenant_id, current_user, db)

@router.post("/tenants/{tenant_id}/reject")
def reject_tenant(tenant_id: str, request: TenantRejectRequest, db: Session = Depends(get_db), current_user: User = Depends(get_super_admin)):
    return admin_service.reject_tenant(tenant_id, request, current_user, db)

@router.get("/verifications")
def list_verifications(db: Session = Depends(get_db), current_user: User = Depends(get_super_admin)):
    tenants = db.query(Tenant).filter(Tenant.status == 'PENDING_VERIFICATION').order_by(Tenant.created_at.desc()).all()
    results = []
    for t in tenants:
        user = db.query(User).filter(User.tenant_id == t.id, User.role == 'TENANT_ADMIN').first()
        results.append({
            "id": str(t.id),
            "name": t.name,
            "company_type": t.company_type,
            "cin": t.cin or "—",
            "website": t.website or "—",
            "admin_name": user.full_name if user else "Unknown",
            "admin_email": user.email if user else "unknown@email.com",
            "admin_phone": (user.phone if user and getattr(user, 'phone', None) else "—"),
            "created_at": t.created_at.isoformat() if t.created_at else "",
        })
    return results

def _tenant_or_404(tenant_id: str, db: Session) -> Tenant:
    valid_id = parse_uuid_or_404(tenant_id, "Tenant")
    tenant = db.query(Tenant).filter(Tenant.id == valid_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant

@router.get("/tenants")
def list_customers(db: Session = Depends(get_db), current_user: User = Depends(get_super_admin)):
    tenants = db.query(Tenant).filter(
        Tenant.status.in_(['ACTIVE', 'SUSPENDED'])
    ).order_by(Tenant.created_at.desc()).all()
    if not tenants:
        return []

    ids = [t.id for t in tenants]
    stats = dict()
    rows = db.query(
        Alert.tenant_id,
        func.count(Alert.id),
        func.sum(case((Alert.status == 'APPROVED', 1), else_=0)),
        func.max(Alert.created_at),
    ).filter(Alert.tenant_id.in_(ids), Alert.is_synthetic == False).group_by(Alert.tenant_id).all()
    for tid, total, approved, last in rows:
        stats[tid] = (int(total or 0), int(approved or 0), last)

    admins = {u.tenant_id: u for u in db.query(User).filter(
        User.tenant_id.in_(ids), User.role == 'TENANT_ADMIN').all()}

    results = []
    for t in tenants:
        total, approved, last = stats.get(t.id, (0, 0, None))
        admin = admins.get(t.id)
        results.append({
            "id": str(t.id),
            "name": t.name,
            "tenant_id_public": t.tenant_id_public,
            "company_type": t.company_type,
            "status": t.status,
            "total_alerts": total,
            "approved_sars": approved,
            "joined_at": t.approved_at.isoformat() if t.approved_at else t.created_at.isoformat(),
            "last_active_at": last.isoformat() if last else None,
            "cin": t.cin or "—",
            "website": t.website or "—",
            "admin_email": admin.email if admin else "—",
        })
    return results

@router.post("/tenants/{tenant_id}/suspend")
def suspend_tenant(tenant_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_super_admin)):
    tenant = _tenant_or_404(tenant_id, db)
    if tenant.status != 'ACTIVE':
        raise HTTPException(status_code=400, detail="Only active tenants can be suspended")
    tenant.status = 'SUSPENDED'
    tenant.suspended_at = func.now()
    tenant.suspended_by = current_user.id
    db.add(AuditLog(tenant_id=tenant.id, user_id=current_user.id, action="TENANT_SUSPENDED",
                    entity_type="tenant", entity_id=tenant.id))
    db.commit()
    return {"status": "ok", "tenant_status": tenant.status}

@router.post("/tenants/{tenant_id}/reinstate")
def reinstate_tenant(tenant_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_super_admin)):
    tenant = _tenant_or_404(tenant_id, db)
    if tenant.status != 'SUSPENDED':
        raise HTTPException(status_code=400, detail="Only suspended tenants can be reinstated")
    tenant.status = 'ACTIVE'
    tenant.suspended_at = None
    tenant.suspended_by = None
    db.add(AuditLog(tenant_id=tenant.id, user_id=current_user.id, action="TENANT_REINSTATED",
                    entity_type="tenant", entity_id=tenant.id))
    db.commit()
    return {"status": "ok", "tenant_status": tenant.status}

@router.get("/logs")
def list_api_logs(limit: int = 200, db: Session = Depends(get_db), current_user: User = Depends(get_super_admin)):
    limit = max(1, min(500, limit))
    rows = db.query(APILog, Tenant.name).outerjoin(
        Tenant, Tenant.id == APILog.tenant_id
    ).order_by(APILog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": str(log.id),
            "tenant_name": tenant_name or "—",
            "method": log.method,
            "endpoint": log.endpoint,
            "status_code": log.status_code,
            "latency_ms": log.latency_ms,
            "created_at": log.created_at.isoformat(),
        }
        for log, tenant_name in rows
    ]

# Groq pricing approximation for llama-3.3-70b (USD per 1M tokens, blended)
_USD_PER_MILLION_TOKENS = 0.65

@router.get("/groq-usage")
def groq_usage(db: Session = Depends(get_db), current_user: User = Depends(get_super_admin)):
    rows = db.query(LLMConfig, Tenant).join(Tenant, Tenant.id == LLMConfig.tenant_id).all()
    total_tokens = sum(l.total_tokens_used for l, _ in rows)

    last_actives = dict(db.query(Alert.tenant_id, func.max(Alert.created_at)).group_by(Alert.tenant_id).all())

    per_tenant = [
        {
            "tenant_id": str(t.id),
            "tenant_name": t.name,
            "tokens_this_month": l.total_tokens_used,
            "total_requests": l.total_requests,
            "est_cost": round(l.total_tokens_used / 1_000_000 * _USD_PER_MILLION_TOKENS, 4),
            "last_active": last_actives[t.id].isoformat() if t.id in last_actives else None,
        }
        for l, t in sorted(rows, key=lambda r: r[0].total_tokens_used, reverse=True)
    ]
    return {
        "total_tokens_all_time": total_tokens,
        "total_tokens_this_month": total_tokens,
        "estimated_cost_usd_this_month": round(total_tokens / 1_000_000 * _USD_PER_MILLION_TOKENS, 2),
        "per_tenant": per_tenant,
    }
