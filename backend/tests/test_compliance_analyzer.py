"""The 8 deterministic typology rules — including the regressions we fixed."""
from app.services.compliance_analyzer import (
    analyze, check_structuring, check_velocity, check_high_risk_type,
    check_round_number, check_counterparty_risk, check_risk_score_threshold,
)


def _fired(result):
    return result["triggered"]


class TestStructuring:
    def test_just_below_threshold_high(self):
        r = check_structuring({"transaction_amount": 985000})
        assert _fired(r) and r["confidence"] == "HIGH"

    def test_lower_band_medium(self):
        r = check_structuring({"transaction_amount": 820000})
        assert _fired(r) and r["confidence"] == "MEDIUM"

    def test_at_reporting_threshold_not_structuring(self):
        # 10,00,000 is the threshold itself, not "just below" it
        assert not _fired(check_structuring({"transaction_amount": 1000000}))

    def test_small_amount_clean(self):
        assert not _fired(check_structuring({"transaction_amount": 4500}))


class TestVelocityKeywordOnly:
    """Regression: velocity must fire ONLY on the bank's reason keyword, never on a
    high score alone (which used to fabricate a 'multiple transactions' claim)."""

    def test_keyword_fires(self):
        r = check_velocity({"alert_reason": "High velocity - 8 txns in 1hr", "risk_score": 60})
        assert _fired(r)

    def test_high_score_alone_does_not_fire(self):
        assert not _fired(check_velocity({"alert_reason": "large wire", "risk_score": 98}))

    def test_no_reason_no_fire(self):
        assert not _fired(check_velocity({"alert_reason": None, "risk_score": 95}))


class TestHighRiskType:
    def test_international_wire(self):
        assert _fired(check_high_risk_type({"transaction_type": "INTERNATIONAL_WIRE"}))

    def test_crypto(self):
        assert _fired(check_high_risk_type({"transaction_type": "CRYPTO_PURCHASE"}))

    def test_plain_transfer_clean(self):
        assert not _fired(check_high_risk_type({"transaction_type": "TRANSFER"}))


class TestRoundNumber:
    def test_exact_multiple_fires(self):
        assert _fired(check_round_number({"transaction_amount": 500000}))

    def test_non_multiple_clean(self):
        assert not _fired(check_round_number({"transaction_amount": 250001}))

    def test_zero_not_flagged(self):
        assert not _fired(check_round_number({"transaction_amount": 0}))


class TestCounterpartyRisk:
    def test_offshore_matches(self):
        assert _fired(check_counterparty_risk({"counterparty_institution": "Offshore Co."}))

    def test_known_bank_clean(self):
        assert not _fired(check_counterparty_risk({"counterparty_institution": "HDFC Bank"}))


class TestAnalyzeRobustness:
    def test_returns_all_eight_rules(self):
        assert len(analyze({})) == 8

    def test_garbage_payload_does_not_raise(self):
        # crafted non-numeric fields must never 500 the pipeline
        results = analyze({"transaction_amount": "N/A", "risk_score": "bogus", "alert_reason": None})
        assert len(results) == 8
        assert all("rule_id" in r for r in results)

    def test_clean_transaction_fires_nothing(self):
        results = analyze({"transaction_amount": 4500, "transaction_type": "TRANSFER",
                           "risk_score": 10, "alert_reason": "routine"})
        assert not any(r["triggered"] for r in results)
