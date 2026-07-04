"""Composite risk scoring — the additive model + threshold gate."""
from app.services.risk_scoring import clamp_score, compute_composite_risk, warrants_sar
from app.config import settings


def _rule(rule_id, confidence, triggered=True):
    return {"rule_id": rule_id, "confidence": confidence, "triggered": triggered}


class TestClampScore:
    def test_normal(self):
        assert clamp_score(60) == 60

    def test_string_number(self):
        assert clamp_score("82") == 82

    def test_negative_floors_to_zero(self):
        assert clamp_score(-40) == 0

    def test_over_100_caps(self):
        assert clamp_score(9999) == 100

    def test_garbage_is_zero(self):
        assert clamp_score("N/A") == 0
        assert clamp_score(None) == 0


class TestCompositeRisk:
    def test_bank_score_plus_high_rule(self):
        # dormant Rs25k case: bank 60 + DORMANT_ACTIVATION(HIGH,+20) = 80
        assert compute_composite_risk(60, [_rule("DORMANT_ACTIVATION", "HIGH")]) == 80

    def test_medium_rule_adds_10(self):
        assert compute_composite_risk(50, [_rule("ROUND_NUMBER", "MEDIUM")]) == 60

    def test_multiple_rules_stack(self):
        rules = [_rule("STRUCTURING", "HIGH"), _rule("COUNTERPARTY_RISK", "MEDIUM")]
        assert compute_composite_risk(60, rules) == 90

    def test_caps_at_100(self):
        rules = [_rule("STRUCTURING", "HIGH"), _rule("HIGH_RISK_TYPE", "HIGH")]
        assert compute_composite_risk(100, rules) == 100

    def test_risk_score_threshold_rule_scores_zero(self):
        # RISK_SCORE_THRESHOLD only re-encodes the bank's own number → must NOT double it.
        assert compute_composite_risk(80, [_rule("RISK_SCORE_THRESHOLD", "HIGH")]) == 80

    def test_untriggered_rules_ignored(self):
        assert compute_composite_risk(30, [_rule("STRUCTURING", "HIGH", triggered=False)]) == 30

    def test_garbage_bank_score_does_not_crash(self):
        assert compute_composite_risk("bogus", [_rule("STRUCTURING", "HIGH")]) == 20


class TestWarrantsSar:
    def test_at_threshold_files(self):
        assert warrants_sar(settings.SAR_RISK_THRESHOLD) is True

    def test_below_threshold_clears(self):
        assert warrants_sar(settings.SAR_RISK_THRESHOLD - 1) is False
