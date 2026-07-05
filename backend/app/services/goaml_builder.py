"""
Build a goAML STR filing from an approved SAR.

This is the regulator-facing structure (FIU-India goAML). It is assembled from the
alert's normalized payload (REAL values — the bank-facing filing uses real names,
not masked tokens), the approved narrative, the triggered rules, and the approving
officer.

`build_goaml_str` returns the report as a dict (easy to inspect/transport);
`build_goaml_xml` serializes that dict to goAML-aligned XML — well-formed and
structured after the FIU-IND goAML STR <report> element. NOTE (be honest in any
pitch): the XML follows the goAML report structure but is NOT yet validated against
the official goAML XSD, so it is a submission-ready *draft*, not a certified filing.
"""
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Any, Dict, List, Optional

# AML rule -> goAML-style suspicion indicator code (for report_indicators).
# Keyed by BOTH the rule_id (what alerts.py passes — ComplianceMatch.rule_id) AND the
# human rule_name, so the lookup is correct regardless of which the caller supplies.
# (Previously this was keyed by rule_name only but received rule_ids, so every lookup
# missed and report_indicators leaked raw rule ids instead of goAML codes.)
INDICATOR_MAP = {
    # rule_id (from compliance_analyzer.py) -> goAML indicator code
    "STRUCTURING": "STRUCTURING_BELOW_THRESHOLD",
    "RAPID_MOVEMENT": "RAPID_PASS_THROUGH",
    "ROUND_NUMBER": "ROUND_AMOUNT",
    "DORMANT_ACTIVATION": "DORMANT_REACTIVATION",
    "HIGH_RISK_TYPE": "HIGH_RISK_INSTRUMENT",
    "VELOCITY": "HIGH_VELOCITY",
    "COUNTERPARTY_RISK": "HIGH_RISK_COUNTERPARTY",
    "RISK_SCORE_THRESHOLD": "HIGH_COMPOSITE_RISK_SCORE",
    # rule_name aliases (defensive — same codes)
    "Structuring / Smurfing": "STRUCTURING_BELOW_THRESHOLD",
    "Rapid Movement of Funds": "RAPID_PASS_THROUGH",
    "Large Round Number": "ROUND_AMOUNT",
    "Dormant Account Activation": "DORMANT_REACTIVATION",
    "High Risk Transaction Type": "HIGH_RISK_INSTRUMENT",
    "High Velocity": "HIGH_VELOCITY",
    "High Risk Counterparty": "HIGH_RISK_COUNTERPARTY",
    "Risk Score Threshold Exceeded": "HIGH_COMPOSITE_RISK_SCORE",
}
# transaction_type -> goAML transmode_code (representative)
TRANSMODE = {"INTERNATIONAL_WIRE": "TT", "FOREX_TRANSFER": "FX", "CRYPTO_PURCHASE": "VA",
             "HAWALA": "IVTS", "REVERSAL": "RV", "REFUND": "RF"}


def build_goaml_str(alert, draft, rule_names: List[str], tenant,
                    officer_name: str, submission_date: str) -> Dict[str, Any]:
    """alert: Alert row · draft: SARDraft row · rule_names: triggered rule names ·
    tenant: Tenant row · officer_name: approver · submission_date: ISO string."""
    norm: Dict[str, Any] = alert.normalized_payload or {}
    txn_type = norm.get("transaction_type") or alert.transaction_type or ""
    structured = (draft.draft_structured if isinstance(draft.draft_structured, dict) else {}) or {}
    narrative = draft.approved_text or draft.rehydrated_text or draft.draft_text or ""

    return {
        "report": {
            "rentity_id": getattr(tenant, "tenant_id_public", None) or str(tenant.id),
            "rentity_name": getattr(tenant, "name", None) or getattr(tenant, "legal_name", None),
            "submission_code": "E",                 # E = electronic
            "report_code": "STR",
            "entity_reference": str(draft.id),
            "submission_date": submission_date,
            "currency_code_local": norm.get("transaction_currency") or alert.transaction_currency or "INR",
            "reporting_person": {"name": officer_name},
            "report_indicators": [INDICATOR_MAP.get(r, r) for r in rule_names],
            "reason": narrative,                     # ground of suspicion (rehydrated, real PII)
            "action": structured.get("recommended_action", ""),
            "transaction": {
                "transactionnumber": norm.get("transaction_id") or alert.transaction_id,
                "date_transaction": norm.get("transaction_timestamp")
                                    or (alert.transaction_timestamp.isoformat() if alert.transaction_timestamp else None),
                "value_local": float(alert.transaction_amount) if alert.transaction_amount is not None
                               else norm.get("transaction_amount"),
                "transmode_code": TRANSMODE.get(str(txn_type).upper(), "OT"),
                "transaction_description": f"{txn_type} {norm.get('transaction_direction', '')}".strip(),
                # bi-party: from = our client (payer), to = external receiver
                "t_from_my_client": {
                    "from_funds_code": "K",          # K = account
                    "from_account": {
                        "institution_name": getattr(tenant, "name", None) or "Reporting Entity",
                        "account": norm.get("account_id"),
                    },
                    "from_person": {"name": norm.get("customer_name"),
                                    "client_ref": norm.get("customer_id")},
                },
                "t_to": {
                    "to_funds_code": "K",
                    "to_account": {
                        "institution_name": norm.get("counterparty_institution"),
                        "account": norm.get("counterparty_account"),
                    },
                    "to_person": {"name": norm.get("counterparty_name")},
                },
            },
        }
    }


def _append_xml(parent: ET.Element, key: str, value: Any) -> None:
    """Recursively serialize a report value into goAML XML under `parent`."""
    # report_indicators is a list of code strings -> <report_indicators><indicator>..</indicator>
    if key == "report_indicators" and isinstance(value, list):
        holder = ET.SubElement(parent, "report_indicators")
        for code in value:
            ET.SubElement(holder, "indicator").text = str(code)
        return
    if isinstance(value, dict):
        node = ET.SubElement(parent, key)
        for k, v in value.items():
            _append_xml(node, k, v)
    elif isinstance(value, list):
        for item in value:  # repeat the element for each list member
            _append_xml(parent, key, item)
    else:
        ET.SubElement(parent, key).text = "" if value is None else str(value)


def build_goaml_xml(report: Dict[str, Any]) -> str:
    """Serialize a `build_goaml_str` report dict to goAML-aligned XML (pretty-printed).
    Well-formed and structured after the FIU-IND goAML STR <report>; XSD certification
    is still pending, so treat it as a submission-ready draft."""
    inner = report.get("report", report) if isinstance(report, dict) else {}
    root = ET.Element("report")
    for k, v in inner.items():
        _append_xml(root, k, v)
    raw = ET.tostring(root, encoding="unicode")
    return minidom.parseString(raw).toprettyxml(indent="  ")
