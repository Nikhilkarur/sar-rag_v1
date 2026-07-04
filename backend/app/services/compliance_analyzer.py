from typing import Any, Dict, List

def _safe_float(value) -> Any:
    """Coerce to float, returning None for garbage. A payload like
    {"transaction_amount": "N/A"} must not 500 the whole ingest request."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _safe_int(value) -> Any:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None

def check_structuring(normalized: dict) -> dict:
    amount = normalized.get("transaction_amount")
    
    triggered = amount is not None and 800000 <= float(amount) <= 999999
    confidence = "HIGH" if amount and 900000 <= float(amount) <= 999999 else "MEDIUM"
    
    evidence = {}
    if triggered:
        evidence = {
            "field": "transaction_amount",
            "value": str(amount),
            "explanation": f"Transaction of ₹{float(amount):,.0f} is near but below the ₹10,00,000 reporting threshold — a common structuring indicator."
        }
        
    return {
        "rule_id": "STRUCTURING",
        "rule_name": "Structuring / Smurfing",
        "triggered": bool(triggered),
        "confidence": confidence,
        "evidence": evidence
    }

def check_rapid_movement(normalized: dict) -> dict:
    amount = normalized.get("transaction_amount")
    txn_type = normalized.get("transaction_type")
    
    triggered = txn_type in ["REVERSAL", "REFUND"] and amount and float(amount) > 100000
    confidence = "MEDIUM"
    
    evidence = {}
    if triggered:
        evidence = {
            "explanation": "Reversal/refund of a large amount suggests funds may have passed through briefly."
        }
        
    return {
        "rule_id": "RAPID_MOVEMENT",
        "rule_name": "Rapid Movement of Funds",
        "triggered": bool(triggered),
        "confidence": confidence,
        "evidence": evidence
    }

def check_round_number(normalized: dict) -> dict:
    amount = normalized.get("transaction_amount")
    
    triggered = amount is not None and float(amount) > 0 and float(amount) % 100000 == 0
    confidence = "MEDIUM" if amount and float(amount) >= 500000 else "LOW"
    
    evidence = {}
    if triggered:
        evidence = {
            "field": "transaction_amount",
            "value": str(amount),
            "explanation": f"Exact round number of ₹{float(amount):,.0f} with no fractional component."
        }
        
    return {
        "rule_id": "ROUND_NUMBER",
        "rule_name": "Large Round Number",
        "triggered": bool(triggered),
        "confidence": confidence,
        "evidence": evidence
    }

def check_dormant_activation(normalized: dict) -> dict:
    reason = normalized.get("alert_reason")
    
    triggered = reason is not None and "dormant" in str(reason).lower()
    confidence = "HIGH"
    
    evidence = {}
    if triggered:
        evidence = {
            "field": "alert_reason",
            "explanation": "TMS flagged account as dormant prior to this activity."
        }
        
    return {
        "rule_id": "DORMANT_ACTIVATION",
        "rule_name": "Dormant Account Activation",
        "triggered": bool(triggered),
        "confidence": confidence,
        "evidence": evidence
    }

def check_high_risk_type(normalized: dict) -> dict:
    txn_type = normalized.get("transaction_type")
    HIGH_RISK_TYPES = ["CRYPTO_PURCHASE", "INTERNATIONAL_WIRE", "FOREX_TRANSFER", "HAWALA"]
    
    triggered = txn_type is not None and str(txn_type).upper() in HIGH_RISK_TYPES
    confidence = "HIGH"
    
    evidence = {}
    if triggered:
        evidence = {
            "field": "transaction_type",
            "value": str(txn_type),
            "explanation": f"Transaction type '{txn_type}' is classified as high-risk under AML guidelines."
        }
        
    return {
        "rule_id": "HIGH_RISK_TYPE",
        "rule_name": "High Risk Transaction Type",
        "triggered": bool(triggered),
        "confidence": confidence,
        "evidence": evidence
    }

def check_velocity(normalized: dict) -> dict:
    reason = normalized.get("alert_reason")
    risk_score = normalized.get("risk_score")

    # Fires ONLY when the bank's TMS actually reported velocity (keyword in alert_reason).
    # A high composite risk_score alone must NOT trigger this rule: that used to fabricate
    # "multiple transactions within a short window" as evidence in the SAR when no such
    # pattern was observed (high score is already covered by RISK_SCORE_THRESHOLD, and any
    # score >= 90 crosses the SAR threshold regardless, so this changes no SAR decision).
    triggered = bool(reason and "velocity" in str(reason).lower())
    confidence = "HIGH" if risk_score and int(risk_score) >= 90 else "MEDIUM"

    evidence = {}
    if triggered:
        evidence = {
            "field": "alert_reason",
            "explanation": "The bank's TMS reported a high-velocity pattern — multiple transactions within a short window."
        }
        
    return {
        "rule_id": "VELOCITY",
        "rule_name": "High Velocity",
        "triggered": bool(triggered),
        "confidence": confidence,
        "evidence": evidence
    }

def check_counterparty_risk(normalized: dict) -> dict:
    inst = normalized.get("counterparty_institution")
    HIGH_RISK_INSTITUTIONS = ["Unknown Bank", "Shell Bank", "Offshore Co.", "Anonymous"]
    
    triggered = inst and any(hri.lower() in str(inst).lower() for hri in HIGH_RISK_INSTITUTIONS)
    confidence = "MEDIUM"
    
    evidence = {}
    if triggered:
        evidence = {
            "field": "counterparty_institution",
            "explanation": "Counterparty institution matches high-risk pattern."
        }
        
    return {
        "rule_id": "COUNTERPARTY_RISK",
        "rule_name": "High Risk Counterparty",
        "triggered": bool(triggered),
        "confidence": confidence,
        "evidence": evidence
    }

def check_risk_score_threshold(normalized: dict) -> dict:
    risk_score = normalized.get("risk_score")
    from app.config import settings
    THRESHOLD = settings.SAR_RISK_THRESHOLD  # single source of truth (config)

    triggered = risk_score is not None and int(risk_score) >= THRESHOLD
    confidence = "HIGH" if risk_score and int(risk_score) >= 85 else "MEDIUM"
    
    evidence = {}
    if triggered:
        evidence = {
            "field": "risk_score",
            "value": str(risk_score),
            "explanation": f"Risk score of {risk_score} exceeds the threshold of {THRESHOLD}."
        }
        
    return {
        "rule_id": "RISK_SCORE_THRESHOLD",
        "rule_name": "Risk Score Threshold Exceeded",
        "triggered": bool(triggered),
        "confidence": confidence,
        "evidence": evidence
    }

def analyze(normalized: dict) -> List[Dict[str, Any]]:
    # Coerce attacker-controllable numeric fields once, so the individual
    # checks' float()/int() casts can never raise on crafted payloads
    normalized = dict(normalized)
    normalized["transaction_amount"] = _safe_float(normalized.get("transaction_amount"))
    normalized["risk_score"] = _safe_int(normalized.get("risk_score"))
    return [
        check_structuring(normalized),
        check_rapid_movement(normalized),
        check_round_number(normalized),
        check_dormant_activation(normalized),
        check_high_risk_type(normalized),
        check_velocity(normalized),
        check_counterparty_risk(normalized),
        check_risk_score_threshold(normalized)
    ]
