from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.deps import get_current_active_tenant_user
from app.models.user import User
from app.models.alert import Alert

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])

@router.get("/queue")
def list_alerts(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_tenant_user)):
    alerts = db.query(Alert).filter(Alert.tenant_id == current_user.tenant_id).order_by(Alert.created_at.desc()).all()
    
    results = []
    for a in alerts:
        # Provide defaults if normalized_payload is empty
        np = a.normalized_payload or {}
        
        results.append({
            "id": str(a.id),
            "source": a.source,
            "status": a.status,
            "ingested_at": a.created_at.isoformat(),
            "rule_triggered": np.get("alert_reason", "Suspicious Activity"),
            "risk_score": a.risk_score or np.get("risk_score") or 0,
            "amount": a.transaction_amount or float(np.get("transaction_amount", 0)),
            "currency": a.transaction_currency or np.get("transaction_currency", "INR"),
            "customer_name": np.get("customer_name", "Unknown Customer"),
            "customer_id": np.get("customer_id", "Unknown ID"),
            "draft_sar": None,
            "llm_insights": ["High velocity of transactions", "Counterparty in high-risk jurisdiction"] if (a.risk_score or 0) > 80 else [],
            "raw_payload_snippet": str(a.raw_payload)[:100] + "..." if a.raw_payload else "{}"
        })
    return results

@router.get("/queue/{alert_id}")
def get_alert(alert_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_tenant_user)):
    a = db.query(Alert).filter(Alert.id == alert_id, Alert.tenant_id == current_user.tenant_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    np = a.normalized_payload or {}
    return {
        "id": str(a.id),
        "source": a.source,
        "status": a.status,
        "ingested_at": a.created_at.isoformat(),
        "rule_triggered": np.get("alert_reason", "Suspicious Activity"),
        "risk_score": a.risk_score or np.get("risk_score") or 0,
        "amount": a.transaction_amount or float(np.get("transaction_amount", 0)),
        "currency": a.transaction_currency or np.get("transaction_currency", "INR"),
        "customer_name": np.get("customer_name", "Unknown Customer"),
        "customer_id": np.get("customer_id", "Unknown ID"),
        "draft_sar": None,
        "llm_insights": ["High velocity of transactions", "Counterparty in high-risk jurisdiction"] if (a.risk_score or 0) > 80 else [],
        "raw_payload_snippet": str(a.raw_payload)[:100] + "..." if a.raw_payload else "{}"
    }

@router.put("/queue/{alert_id}/draft")
def update_draft(alert_id: str, payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_tenant_user)):
    return {"status": "ok"}

@router.post("/queue/{alert_id}/approve")
def approve_alert(alert_id: str, payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_tenant_user)):
    a = db.query(Alert).filter(Alert.id == alert_id, Alert.tenant_id == current_user.tenant_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    a.status = 'APPROVED'
    a.reviewed_by = current_user.id
    a.reviewed_at = __import__('sqlalchemy').func.now()
    db.commit()
    return {"status": "ok", "approved_at": a.reviewed_at.isoformat() if a.reviewed_at else None}

@router.post("/queue/{alert_id}/reject")
def reject_alert(alert_id: str, payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_tenant_user)):
    a = db.query(Alert).filter(Alert.id == alert_id, Alert.tenant_id == current_user.tenant_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    a.status = 'REJECTED'
    a.reviewed_by = current_user.id
    a.reviewed_at = __import__('sqlalchemy').func.now()
    a.rejection_reason = payload.get("reason", "No reason provided")
    db.commit()
    return {"status": "ok"}
