"""goAML STR assembly — the regulator-facing structure with real values."""
import xml.etree.ElementTree as ET
from types import SimpleNamespace
from app.services.goaml_builder import build_goaml_str, build_goaml_xml, INDICATOR_MAP


def _fixtures():
    alert = SimpleNamespace(
        normalized_payload={
            "transaction_id": "TXN-1", "transaction_type": "INTERNATIONAL_WIRE",
            "transaction_amount": 985000, "transaction_currency": "INR",
            "customer_name": "Rohan Mehta", "customer_id": "CUST-9007",
            "account_id": "ACC-900900", "counterparty_name": "Global Holdings",
            "counterparty_account": "OFF-112233", "counterparty_institution": "Offshore Co.",
        },
        transaction_type="INTERNATIONAL_WIRE", transaction_amount=985000,
        transaction_currency="INR", transaction_id="TXN-1", transaction_timestamp=None,
    )
    draft = SimpleNamespace(
        draft_structured={"recommended_action": "File the STR per Section 5.1."},
        approved_text="Suspicious international wire...", rehydrated_text=None, draft_text=None,
        id="draft-1",
    )
    tenant = SimpleNamespace(tenant_id_public="TEN-0005", name="Meridian Bank Limited", id="uuid-1")
    return alert, draft, tenant


class TestBuildGoaml:
    def test_maps_rule_ids_to_goaml_codes(self):
        alert, draft, tenant = _fixtures()
        rep = build_goaml_str(alert, draft, ["STRUCTURING", "HIGH_RISK_TYPE"], tenant, "Officer", "2026-07-05")["report"]
        assert rep["report_indicators"] == ["STRUCTURING_BELOW_THRESHOLD", "HIGH_RISK_INSTRUMENT"]

    def test_uses_real_values(self):
        alert, draft, tenant = _fixtures()
        rep = build_goaml_str(alert, draft, [], tenant, "Officer", "2026-07-05")["report"]
        assert rep["rentity_name"] == "Meridian Bank Limited"
        assert rep["report_code"] == "STR"
        txn = rep["transaction"]
        assert txn["t_from_my_client"]["from_person"]["name"] == "Rohan Mehta"
        assert txn["t_to"]["to_account"]["account"] == "OFF-112233"
        assert txn["value_local"] == 985000

    def test_unknown_rule_falls_back_to_its_own_id(self):
        alert, draft, tenant = _fixtures()
        rep = build_goaml_str(alert, draft, ["MADE_UP_RULE"], tenant, "Officer", "2026-07-05")["report"]
        assert rep["report_indicators"] == ["MADE_UP_RULE"]

    def test_indicator_map_covers_every_rule_id(self):
        # Every rule_id the analyzer can emit must have a goAML code
        rule_ids = {"STRUCTURING", "RAPID_MOVEMENT", "ROUND_NUMBER", "DORMANT_ACTIVATION",
                    "HIGH_RISK_TYPE", "VELOCITY", "COUNTERPARTY_RISK", "RISK_SCORE_THRESHOLD"}
        assert rule_ids.issubset(INDICATOR_MAP.keys())


class TestBuildGoamlXml:
    def _report(self):
        alert, draft, tenant = _fixtures()
        return build_goaml_str(alert, draft, ["STRUCTURING", "HIGH_RISK_TYPE"], tenant, "Officer", "2026-07-05")

    def test_is_well_formed_xml(self):
        xml = build_goaml_xml(self._report())
        root = ET.fromstring(xml)  # raises if malformed
        assert root.tag == "report"

    def test_indicators_serialized_as_elements(self):
        root = ET.fromstring(build_goaml_xml(self._report()))
        codes = [i.text for i in root.find("report_indicators").findall("indicator")]
        assert codes == ["STRUCTURING_BELOW_THRESHOLD", "HIGH_RISK_INSTRUMENT"]

    def test_real_values_present_in_xml(self):
        xml = build_goaml_xml(self._report())
        assert "Rohan Mehta" in xml and "Meridian Bank Limited" in xml and "STR" in xml

    def test_nested_transaction_structure(self):
        root = ET.fromstring(build_goaml_xml(self._report()))
        name = root.find("transaction/t_from_my_client/from_person/name")
        assert name is not None and name.text == "Rohan Mehta"
