from datetime import datetime, timezone, timedelta
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
from app.models.sar import SARDraft
from app.models.audit import AuditLog
from app.models.compliance import ComplianceMatch

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

# Blended token cost (USD per 1M tokens) for the internal all-in usage estimate. Not shown to
# customers and deliberately vendor-agnostic — we never surface the underlying model.
_USD_PER_MILLION_TOKENS = 0.65

def _month_start(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _draft_usage(db: Session, since: datetime | None = None) -> dict:
    """Tokens + request counts per tenant from sar_drafts (one draft == one generation).
    Authoritative and drift-proof. Pass `since` to scope to a time window (e.g. this month).
    Synthetic (portal-simulator) drafts are excluded — the overview promises all metrics
    exclude synthetic, and these numbers must reconcile with the tenant-facing usage/billing."""
    q = db.query(
        SARDraft.tenant_id,
        func.count(SARDraft.id),
        func.coalesce(func.sum(func.coalesce(SARDraft.prompt_tokens, 0)
                               + func.coalesce(SARDraft.completion_tokens, 0)), 0),
    ).join(Alert, Alert.id == SARDraft.alert_id).filter(Alert.is_synthetic == False)  # noqa: E712
    if since is not None:
        q = q.filter(SARDraft.created_at >= since)
    return {tid: (int(c or 0), int(tok or 0)) for tid, c, tok in q.group_by(SARDraft.tenant_id).all()}


@router.get("/groq-usage")
def groq_usage(db: Session = Depends(get_db), current_user: User = Depends(get_super_admin)):
    rows = db.query(LLMConfig, Tenant).join(Tenant, Tenant.id == LLMConfig.tenant_id).all()

    month_start = _month_start()
    all_time = _draft_usage(db)            # {tenant_id: (requests, tokens)} — all time
    this_month = _draft_usage(db, month_start)  # {tenant_id: (requests, tokens)} — current month

    reqs_all = lambda t: all_time.get(t.id, (0, 0))[0]
    toks_all = lambda t: all_time.get(t.id, (0, 0))[1]
    reqs_mo = lambda t: this_month.get(t.id, (0, 0))[0]
    toks_mo = lambda t: this_month.get(t.id, (0, 0))[1]

    total_tokens_all = sum(toks_all(t) for _, t in rows)
    total_tokens_mo = sum(toks_mo(t) for _, t in rows)
    last_actives = dict(db.query(Alert.tenant_id, func.max(Alert.created_at)).group_by(Alert.tenant_id).all())

    per_tenant = [
        {
            "tenant_id": str(t.id),
            "tenant_name": t.name,
            "tokens_this_month": toks_mo(t),
            "tokens_all_time": toks_all(t),
            "total_requests": reqs_mo(t),
            "requests_all_time": reqs_all(t),
            "est_cost": round(toks_mo(t) / 1_000_000 * _USD_PER_MILLION_TOKENS, 4),
            "last_active": last_actives[t.id].isoformat() if t.id in last_actives else None,
        }
        # Sort by this-month usage so the "This Month" chart/table are consistent
        for _, t in sorted(rows, key=lambda r: toks_mo(r[1]), reverse=True)
    ]
    return {
        "total_tokens_all_time": total_tokens_all,
        "total_tokens_this_month": total_tokens_mo,
        "estimated_cost_usd_this_month": round(total_tokens_mo / 1_000_000 * _USD_PER_MILLION_TOKENS, 2),
        "per_tenant": per_tenant,
    }


@router.get("/billing")
def platform_billing(db: Session = Depends(get_db), current_user: User = Depends(get_super_admin)):
    """Platform billing: each active/suspended client's bill this cycle + the overall total
    (sum of clients). Comped clients (e.g. TEN-0005, our free test tenant on free-tier keys)
    bill Rs.0. Uses the same rules as the tenant-facing /tenant/billing, so the numbers reconcile."""
    from app.routers.tenant import FREE_SARS, PRICE_PER_SAR_INR, FREE_ACCESS_TENANTS
    from app.services.model_router import resolve_plan

    month_start = _month_start()
    tenants = db.query(Tenant).filter(Tenant.status.in_(['ACTIVE', 'SUSPENDED'])).order_by(
        Tenant.created_at.desc()).all()

    # SAR drafts this cycle, per tenant (one draft == one billable SAR).
    # Synthetic (simulator) drafts are excluded — never billable, and this must
    # reconcile with the tenant-facing /tenant/billing numbers.
    cycle_counts = dict(
        db.query(SARDraft.tenant_id, func.count(SARDraft.id)).join(
            Alert, Alert.id == SARDraft.alert_id
        ).filter(
            SARDraft.created_at >= month_start,
            Alert.is_synthetic == False,  # noqa: E712
        ).group_by(SARDraft.tenant_id).all()
    )

    clients = []
    total_amount = 0
    total_sars = 0
    billable_clients = 0
    for t in tenants:
        sars = int(cycle_counts.get(t.id, 0))
        comped = t.tenant_id_public in FREE_ACCESS_TENANTS
        billable = max(0, sars - FREE_SARS)
        amount = 0 if comped else billable * PRICE_PER_SAR_INR
        if amount > 0:
            billable_clients += 1
        total_amount += amount
        total_sars += sars
        clients.append({
            "tenant_id": str(t.id),
            "tenant_id_public": t.tenant_id_public,
            "name": t.name,
            "status": t.status,
            "plan": resolve_plan(t),
            "sars_this_cycle": sars,
            "billable_sars": billable,
            "amount_due_inr": amount,
            "special_free_access": comped,
            "note": "Free test client — free-tier keys, not charged" if comped else None,
        })

    # Comped clients first is confusing for a bill; sort by amount desc, then SARs desc.
    clients.sort(key=lambda c: (c["amount_due_inr"], c["sars_this_cycle"]), reverse=True)
    return {
        "currency": "INR",
        "cycle_start": month_start.isoformat(),
        "free_sars": FREE_SARS,
        "price_per_sar_inr": PRICE_PER_SAR_INR,
        "total_amount_due_inr": total_amount,
        "total_sars_this_cycle": total_sars,
        "client_count": len(clients),
        "billable_client_count": billable_clients,
        "comped_client_count": sum(1 for c in clients if c["special_free_access"]),
        "clients": clients,
    }


def _last_n_month_keys(n: int, now: datetime | None = None) -> list[str]:
    """['2026-02', ..., '2026-07'] — n calendar months ending with the current one."""
    now = now or datetime.now(timezone.utc)
    keys, y, m = [], now.year, now.month
    for _ in range(n):
        keys.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(keys))


@router.get("/overview")
def platform_overview(db: Session = Depends(get_db), current_user: User = Depends(get_super_admin)):
    """Platform-wide super-admin dashboard: KPIs, monthly alert-outcome stack, typology mix,
    and recent API-log traffic. All metrics exclude synthetic (portal-simulator) alerts."""
    now = datetime.now(timezone.utc)
    month_start = _month_start(now)
    real = Alert.is_synthetic == False  # noqa: E712

    # ── Tenant counts ──
    status_counts = dict(
        db.query(Tenant.status, func.count(Tenant.id)).group_by(Tenant.status).all()
    )
    active = int(status_counts.get("ACTIVE", 0))
    suspended = int(status_counts.get("SUSPENDED", 0))
    pending = int(status_counts.get("PENDING_VERIFICATION", 0))

    # ── Alert / SAR counts ──
    total_alerts = db.query(func.count(Alert.id)).filter(real).scalar() or 0
    alerts_this_month = db.query(func.count(Alert.id)).filter(real, Alert.created_at >= month_start).scalar() or 0
    total_sars = db.query(func.count(Alert.id)).filter(real, Alert.status == "APPROVED").scalar() or 0
    sars_this_month = db.query(func.count(Alert.id)).filter(
        real, Alert.status == "APPROVED", Alert.created_at >= month_start
    ).scalar() or 0
    failed_total = db.query(func.count(Alert.id)).filter(real, Alert.status == "PROCESSING_FAILED").scalar() or 0

    # ── LLM usage (this month) ──
    month_usage = _draft_usage(db, month_start)
    tokens_this_month = sum(v[1] for v in month_usage.values())
    llm_cost_this_month = round(tokens_this_month / 1_000_000 * _USD_PER_MILLION_TOKENS, 2)

    # ── Monthly alert-outcome stack (last 6 months) ──
    # Each segment is counted from its ACTUAL terminal status (not a remainder), so an
    # escalated-but-unfiled SAR is never miscounted as "cleared":
    #   filed   = APPROVED (SAR filed)
    #   review  = PROCESSING_COMPLETED / PENDING_REVIEW (SAR drafted, awaiting officer file)
    #   cleared = closed with NO SAR — COMPLETED_CLEAN (auto, below threshold) or REJECTED
    #             (an officer reviewed the draft and dismissed it as not suspicious)
    #   failed  = PROCESSING_FAILED
    # Transient states (PENDING_INGESTION / PROCESSING) are out of scope here. This "cleared"
    # definition matches the tenant dashboard's "Cleared — no SAR" KPI (COMPLETED_CLEAN + REJECTED).
    STATUS_BUCKET = {
        "APPROVED": "filed",
        "PROCESSING_COMPLETED": "review",
        "PENDING_REVIEW": "review",
        "COMPLETED_CLEAN": "cleared",
        "REJECTED": "cleared",
        "PROCESSING_FAILED": "failed",
    }
    month_keys = _last_n_month_keys(6, now)
    m_expr = func.to_char(Alert.created_at, "YYYY-MM")
    since_6mo = datetime(now.year, now.month, 1, tzinfo=timezone.utc) - timedelta(days=190)
    m_rows = db.query(m_expr, Alert.status, func.count(Alert.id)).filter(
        real, Alert.created_at >= since_6mo
    ).group_by(m_expr, Alert.status).all()
    buckets = {k: {"filed": 0, "review": 0, "cleared": 0, "failed": 0} for k in month_keys}
    for mk, status, cnt in m_rows:
        if mk not in buckets:
            continue
        seg = STATUS_BUCKET.get(status)
        if seg:
            buckets[mk][seg] += int(cnt or 0)
    MONTH_ABBR = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly = [
        {"month": k, "label": MONTH_ABBR[int(k.split("-")[1])], **buckets[k]}
        for k in month_keys
    ]

    # ── Typology mix (donut): triggered compliance rules across real alerts ──
    t_rows = db.query(
        ComplianceMatch.rule_id, ComplianceMatch.rule_name, func.count(ComplianceMatch.id)
    ).join(Alert, Alert.id == ComplianceMatch.alert_id).filter(
        real, ComplianceMatch.triggered == True  # noqa: E712
    ).group_by(ComplianceMatch.rule_id, ComplianceMatch.rule_name).order_by(
        func.count(ComplianceMatch.id).desc()
    ).all()
    typology = [
        {"rule_id": rid, "rule_name": rname, "count": int(c or 0)}
        for rid, rname, c in t_rows
    ]

    # ── API traffic (last 7 days): daily volume + status split ──
    since_7d = now - timedelta(days=7)
    d_expr = func.to_char(APILog.created_at, "YYYY-MM-DD")
    a_rows = db.query(
        d_expr,
        func.count(APILog.id),
        func.sum(case((APILog.status_code < 400, 1), else_=0)),
        func.sum(case((APILog.status_code.between(400, 499), 1), else_=0)),
        func.sum(case((APILog.status_code >= 500, 1), else_=0)),
    ).filter(APILog.created_at >= since_7d).group_by(d_expr).order_by(d_expr).all()
    api_daily = [
        {
            "date": d,
            "label": d[5:],  # MM-DD
            "total": int(tot or 0),
            "ok": int(ok or 0),
            "client_err": int(c4 or 0),
            "server_err": int(c5 or 0),
        }
        for d, tot, ok, c4, c5 in a_rows
    ]
    total_reqs_7d = sum(r["total"] for r in api_daily)
    err_reqs_7d = sum(r["client_err"] + r["server_err"] for r in api_daily)
    error_rate_7d = round(err_reqs_7d / total_reqs_7d * 100, 1) if total_reqs_7d else 0.0

    # Real EXTERNAL API usage = successful ingestion calls (tenants pushing flagged txns).
    # The raw request total above is dominated by the dashboards polling themselves, so it's a
    # misleading "API usage" figure — this is the honest one.
    ingest_7d = db.query(func.count(APILog.id)).filter(
        APILog.created_at >= since_7d,
        APILog.endpoint.like("%/ingest/%"),
        APILog.status_code < 400,
    ).scalar() or 0

    return {
        "kpis": {
            "tenants_active": active,
            "tenants_suspended": suspended,
            "tenants_pending": pending,
            "total_alerts": int(total_alerts),
            "alerts_this_month": int(alerts_this_month),
            "total_sars": int(total_sars),
            "sars_this_month": int(sars_this_month),
            "failed_total": int(failed_total),
            "tokens_this_month": int(tokens_this_month),
            "llm_cost_this_month": llm_cost_this_month,
            "api_requests_7d": total_reqs_7d,
            "api_error_rate_7d": error_rate_7d,
            "ingest_requests_7d": int(ingest_7d),
        },
        "monthly": monthly,
        "typology": typology,
        "api_daily": api_daily,
    }
