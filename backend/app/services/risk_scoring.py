"""
Composite risk scoring — the single source of truth for how an alert's risk score
is computed and whether it warrants a SAR.

Both the live ingest path (routers/ingest.py) and the portal simulator
(routers/alerts.py) call these, so the two can never drift apart (they used to
carry copy-pasted scoring loops that had to be kept in sync by hand).

Model (additive): the bank's own risk_score is the BASE, and Aegis's deterministic
typology rules ADD on top (HIGH +20, MEDIUM +10). RISK_SCORE_THRESHOLD is excluded —
it merely re-encodes the bank's own numeric score as a rule, so counting it would
double the bank's number; it still fires as an indicator but contributes 0 points.
"""
from typing import List, Dict, Any

from app.config import settings

_HIGH_POINTS = 20
_MEDIUM_POINTS = 10


def clamp_score(value) -> int:
    """Coerce a (possibly attacker-controlled) risk_score to an int in 0..100.
    Garbage / negative / huge values collapse to a safe bounded number."""
    try:
        n = int(float(value or 0))
    except (TypeError, ValueError):
        n = 0
    return max(0, min(100, n))


def compute_composite_risk(bank_score, analysis_results: List[Dict[str, Any]]) -> int:
    """base bank score + points for each triggered Aegis rule (except RISK_SCORE_THRESHOLD).
    Clamped to 0..100."""
    score = clamp_score(bank_score)
    for r in analysis_results:
        if r.get("triggered") and r.get("rule_id") != "RISK_SCORE_THRESHOLD":
            conf = r.get("confidence")
            if conf == "HIGH":
                score += _HIGH_POINTS
            elif conf == "MEDIUM":
                score += _MEDIUM_POINTS
    return min(100, score)


def warrants_sar(composite_score: int) -> bool:
    """True when the composite score meets the configured SAR threshold."""
    return composite_score >= settings.SAR_RISK_THRESHOLD
