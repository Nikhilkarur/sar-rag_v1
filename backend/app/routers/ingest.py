from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.deps import authenticate_api_key
from app.models.tenant import Tenant
from app.models.schema import IngestionSchema
from app.models.alert import Alert
from app.models.pii_map import PIIMap
from app.models.compliance import ComplianceMatch
from app.services.schema_normalizer import normalize_payload
from app.services.pii_masker import mask_payload
from app.services.compliance_analyzer import analyze
from app.services.llm_agent import generate_sar
import uuid

router = APIRouter(prefix="/api/v1/ingest", tags=["Ingestion Pipeline"])

def process_alert_background(alert_id: str, db: Session):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        return
        
    try:
        # 4. Generate SAR Narrative
        sar = generate_sar(alert.id, db)
        
        # 5. Mark Complete
        alert.status = "PROCESSING_COMPLETED"
        alert.processing_completed_at = __import__('sqlalchemy').func.now()
        db.commit()
    except Exception as e:
        alert.status = "PROCESSING_FAILED"
        alert.processing_error = str(e)
        db.commit()

@router.post("/")
async def ingest_payload(
    request: Request, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db), 
    tenant: Tenant = Depends(authenticate_api_key)
):
    try:
        raw_payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
    schema_key = request.headers.get("X-Schema-Key")
    schema = None
    if schema_key:
        schema = db.query(IngestionSchema).filter(
            IngestionSchema.tenant_id == tenant.id,
            IngestionSchema.template_key == schema_key
        ).first()
        
    if not schema:
        # Default to first active schema if not provided
        schema = db.query(IngestionSchema).filter(
            IngestionSchema.tenant_id == tenant.id,
            IngestionSchema.is_active == True
        ).first()
        if not schema:
            raise HTTPException(status_code=400, detail="No active schema found for tenant")
            
    # 1. Normalize
    normalized = normalize_payload(raw_payload, schema.field_map)
    
    # 2. Mask PII
    masked_payload, token_map = mask_payload(normalized, schema.pii_fields)
    
    # 3. Compliance Analysis
    analysis_results = analyze(normalized)
    
    # Determine base risk score from payload or rules
    risk_score = int(normalized.get("risk_score", 0))
    for r in analysis_results:
        if r["triggered"]:
            if r["confidence"] == "HIGH": risk_score += 20
            elif r["confidence"] == "MEDIUM": risk_score += 10
    
    # Create Alert
    alert = Alert(
        tenant_id=tenant.id,
        schema_id=schema.id,
        status="PROCESSING",
        raw_payload=raw_payload,
        normalized_payload=normalized,
        masked_payload=masked_payload,
        transaction_id=str(normalized.get("transaction_id", uuid.uuid4())),
        transaction_amount=normalized.get("transaction_amount"),
        transaction_type=normalized.get("transaction_type"),
        risk_score=min(100, risk_score),
        processing_started_at=__import__('sqlalchemy').func.now()
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    # Save PII Map
    pii = PIIMap(alert_id=alert.id, tenant_id=tenant.id, token_map=token_map)
    db.add(pii)
    
    # Save Compliance Matches
    for r in analysis_results:
        if r["triggered"]:
            match = ComplianceMatch(
                alert_id=alert.id,
                tenant_id=tenant.id,
                rule_id=r["rule_id"],
                rule_name=r["rule_name"],
                triggered=True,
                confidence=r["confidence"],
                evidence=r["evidence"]
            )
            db.add(match)
            
    db.commit()
    
    if alert.risk_score >= 75:
        # Threshold met, trigger SAR generation
        background_tasks.add_task(process_alert_background, alert.id, db)
    else:
        alert.status = "COMPLETED_CLEAN"
        alert.processing_completed_at = __import__('sqlalchemy').func.now()
        db.commit()
        
    return {
        "status": "success",
        "alert_id": alert.id,
        "risk_score": alert.risk_score,
        "message": "Ingested successfully. SAR generation triggered." if alert.risk_score >= 75 else "Ingested successfully. No SAR required."
    }
