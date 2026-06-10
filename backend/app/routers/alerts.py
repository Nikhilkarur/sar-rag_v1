from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.deps import get_current_active_tenant_user, get_compliance_user
from app.models.user import User
from app.models.alert import Alert
from app.models.schema import IngestionSchema
from app.models.pii_map import PIIMap
from app.models.compliance import ComplianceMatch
from app.services.pii_masker import mask_payload
from app.services.compliance_analyzer import analyze
from app.routers.ingest import process_alert_background
from datetime import datetime
import secrets

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])

@router.get("/queue")
def list_alerts(include_synthetic: bool = True, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_tenant_user)):
    query = db.query(Alert).filter(Alert.tenant_id == current_user.tenant_id)
    if not include_synthetic:
        # Compliance metrics must be computed over real alerts only
        query = query.filter(Alert.is_synthetic == False)
    alerts = query.order_by(Alert.created_at.desc()).all()

    results = []
    for a in alerts:
        # Provide defaults if normalized_payload is empty
        np = a.normalized_payload or {}
        
        results.append({
            "id": str(a.id),
            "source": a.source,
            "is_synthetic": a.is_synthetic,
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
        "is_synthetic": a.is_synthetic,
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

# --- Simulator: portal "Submit Test Alert" button ---

_SCENARIO_TEMPLATES = {
    "STRUCTURING":   {"transaction_amount": 990000, "transaction_type": "TRANSFER", "risk_score": 60, "alert_reason": "Near-threshold transfer"},
    "RAPID_MOVEMENT": {"transaction_amount": 500000, "transaction_type": "REVERSAL", "risk_score": 65, "alert_reason": "Large reversal shortly after credit"},
    "HIGH_RISK_TYPE": {"transaction_amount": 750000, "transaction_type": "INTERNATIONAL_WIRE", "risk_score": 70, "alert_reason": "High-risk transaction type"},
    "VELOCITY":      {"transaction_amount": 120000, "transaction_type": "TRANSFER", "risk_score": 90, "alert_reason": "High velocity - 8 transactions in 1 hour"},
    "DEFAULT":       {"transaction_amount": 250000, "transaction_type": "TRANSFER", "risk_score": 40, "alert_reason": "Routine review"},
}

@router.post("/simulator/submit-test-alert", status_code=202)
def submit_test_alert(
    payload: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_compliance_user),
):
    scenario = str(payload.get("scenario", "DEFAULT")).upper()
    if scenario not in _SCENARIO_TEMPLATES:
        raise HTTPException(status_code=400, detail=f"Unknown scenario '{scenario}'")

    txn_id = f"TEST-TXN-{datetime.utcnow().strftime('%Y%m%d')}{secrets.randbelow(100000):05d}"
    normalized = {
        "transaction_id": txn_id,
        "transaction_currency": "INR",
        "customer_name": "Test Customer",
        "customer_id": f"CUST-TEST-{secrets.randbelow(10000):04d}",
        "account_id": f"ACC-TEST-{secrets.randbelow(10000):04d}",
        **_SCENARIO_TEMPLATES[scenario],
    }
    if payload.get("custom_risk_score") is not None:
        try:
            normalized["risk_score"] = max(0, min(100, int(payload["custom_risk_score"])))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="custom_risk_score must be an integer between 0 and 100")

    schema = db.query(IngestionSchema).filter(
        IngestionSchema.tenant_id == current_user.tenant_id,
        IngestionSchema.is_active == True
    ).first()
    pii_fields = (schema.pii_fields if schema and schema.pii_fields else ["customer_name", "customer_id", "account_id"])

    masked_payload, token_map = mask_payload(normalized, pii_fields)
    analysis_results = analyze(normalized)

    risk_score = int(normalized.get("risk_score", 0))
    for r in analysis_results:
        if r["triggered"]:
            if r["confidence"] == "HIGH": risk_score += 20
            elif r["confidence"] == "MEDIUM": risk_score += 10

    alert = Alert(
        tenant_id=current_user.tenant_id,
        schema_id=schema.id if schema else None,
        status="PROCESSING",
        raw_payload=normalized,
        normalized_payload=normalized,
        masked_payload=masked_payload,
        transaction_id=txn_id,
        transaction_amount=normalized.get("transaction_amount"),
        transaction_type=normalized.get("transaction_type"),
        risk_score=min(100, risk_score),
        source="SIMULATOR",
        is_synthetic=True,  # never counted in compliance metrics
        processing_started_at=__import__('sqlalchemy').func.now()
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    db.add(PIIMap(alert_id=alert.id, tenant_id=current_user.tenant_id, token_map=token_map))
    for r in analysis_results:
        if r["triggered"]:
            db.add(ComplianceMatch(
                alert_id=alert.id,
                tenant_id=current_user.tenant_id,
                rule_id=r["rule_id"],
                rule_name=r["rule_name"],
                triggered=True,
                confidence=r["confidence"],
                evidence=r["evidence"]
            ))
    db.commit()

    if alert.risk_score >= 75:
        background_tasks.add_task(process_alert_background, alert.id)
    else:
        alert.status = "COMPLETED_CLEAN"
        alert.processing_completed_at = __import__('sqlalchemy').func.now()
        db.commit()

    return {
        "alert_id": str(alert.id),
        "message": "Test alert injected. Check the review queue in ~8 seconds.",
        "scenario_used": scenario,
        "synthetic_transaction_id": txn_id,
    }
