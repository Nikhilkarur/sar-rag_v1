from typing import Any, Dict, List

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
    
    triggered = (reason and "velocity" in str(reason).lower()) or (risk_score and int(risk_score) >= 90)
    confidence = "HIGH" if risk_score and int(risk_score) >= 90 else "MEDIUM"
    
    evidence = {}
    if triggered:
        evidence = {
            "explanation": "High-velocity pattern detected — multiple transactions within a short window."
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
    THRESHOLD = 75
    
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
