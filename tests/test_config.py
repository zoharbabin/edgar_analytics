"""tests/test_config.py — tests for configuration module."""

from edgar_analytics.config import ALERTS_CONFIG, get_alerts_config


class TestAlertsConfig:
    def test_defaults_exist(self):
        required_keys = {
            "NEGATIVE_MARGIN", "HIGH_LEVERAGE", "LOW_ROE", "LOW_ROA",
            "NET_DEBT_EBITDA_THRESHOLD", "INTEREST_COVERAGE_THRESHOLD",
            "SUSTAINED_NEG_FCF_QUARTERS", "INVENTORY_SPIKE_THRESHOLD",
            "RECEIVABLE_SPIKE_THRESHOLD",
        }
        assert required_keys.issubset(ALERTS_CONFIG.keys())

    def test_defaults_are_numeric(self):
        for key, val in ALERTS_CONFIG.items():
            assert isinstance(val, (int, float)), f"{key} is not numeric: {val!r}"

    def test_get_alerts_config_without_overrides(self):
        result = get_alerts_config(None)
        assert result is ALERTS_CONFIG

    def test_get_alerts_config_with_overrides(self):
        result = get_alerts_config({"HIGH_LEVERAGE": 10.0})
        assert result["HIGH_LEVERAGE"] == 10.0
        assert result["LOW_ROE"] == ALERTS_CONFIG["LOW_ROE"]

    def test_overrides_do_not_mutate_defaults(self):
        original = ALERTS_CONFIG["HIGH_LEVERAGE"]
        get_alerts_config({"HIGH_LEVERAGE": 999})
        assert ALERTS_CONFIG["HIGH_LEVERAGE"] == original
