"""PII masking + rehydration — the privacy-critical round trip."""
from app.services.pii_masker import generate_token, mask_payload, rehydrate_text


class TestGenerateToken:
    def test_name_prefix(self):
        assert generate_token("Rohan Mehta", "customer_name").startswith("USR_")

    def test_account_prefix(self):
        assert generate_token("ACC-900900", "account_id").startswith("ACC_")

    def test_deterministic(self):
        # same entity → same token, so it links across transactions
        assert generate_token("Rohan Mehta", "customer_name") == generate_token("Rohan Mehta", "customer_name")

    def test_different_values_differ(self):
        assert generate_token("A", "customer_name") != generate_token("B", "customer_name")


class TestMaskPayload:
    def test_masks_only_pii_fields(self):
        normalized = {"customer_name": "Rohan Mehta", "transaction_amount": 985000}
        masked, token_map = mask_payload(normalized, ["customer_name"])
        assert masked["customer_name"].startswith("USR_")
        assert masked["transaction_amount"] == 985000  # non-PII untouched
        assert masked["customer_name"] in token_map
        assert token_map[masked["customer_name"]] == "Rohan Mehta"

    def test_missing_field_skipped(self):
        masked, token_map = mask_payload({"transaction_amount": 100}, ["customer_name"])
        assert token_map == {}

    def test_does_not_mutate_original(self):
        normalized = {"customer_name": "Rohan Mehta"}
        mask_payload(normalized, ["customer_name"])
        assert normalized["customer_name"] == "Rohan Mehta"


class TestRoundTrip:
    def test_mask_then_rehydrate_restores_original(self):
        normalized = {"customer_name": "Rohan Mehta", "account_id": "ACC-900900"}
        masked, token_map = mask_payload(normalized, ["customer_name", "account_id"])
        narrative = f"The customer {masked['customer_name']} used {masked['account_id']}."
        restored = rehydrate_text(narrative, token_map)
        assert "Rohan Mehta" in restored and "ACC-900900" in restored
        assert "USR_" not in restored and "ACC_" not in restored

    def test_rehydrate_empty_is_safe(self):
        assert rehydrate_text("", {}) == ""
