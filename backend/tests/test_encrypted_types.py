"""At-rest encryption decorators — round trip + legacy plaintext tolerance."""
from app.models.encrypted_types import EncryptedJSONB, EncryptedText


class TestEncryptedJSONB:
    def setup_method(self):
        self.t = EncryptedJSONB()

    def test_round_trip(self):
        val = {"customer_name": "Rohan Mehta", "account": "5012"}
        stored = self.t.process_bind_param(val, None)
        assert "__enc__" in stored
        assert "Rohan" not in str(stored)  # ciphertext hides PII
        assert self.t.process_result_value(stored, None) == val

    def test_legacy_plaintext_still_reads(self):
        legacy = {"customer_name": "Old Row"}
        assert self.t.process_result_value(legacy, None) == legacy

    def test_none_passthrough(self):
        assert self.t.process_bind_param(None, None) is None
        assert self.t.process_result_value(None, None) is None


class TestEncryptedText:
    def setup_method(self):
        self.t = EncryptedText()

    def test_round_trip(self):
        val = "Customer Rohan Mehta sent 985000 to Offshore Co."
        stored = self.t.process_bind_param(val, None)
        assert stored.startswith("enc::v1::")
        assert "Rohan" not in stored
        assert self.t.process_result_value(stored, None) == val

    def test_legacy_plaintext_still_reads(self):
        assert self.t.process_result_value("old narrative, no prefix", None) == "old narrative, no prefix"

    def test_none_passthrough(self):
        assert self.t.process_bind_param(None, None) is None
        assert self.t.process_result_value(None, None) is None
