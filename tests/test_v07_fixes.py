"""tests/test_v07_fixes.py — regression tests for all v0.7.0 audit fixes."""

import math
import pytest
import pandas as pd

from edgar_analytics.scores import (
    AltmanZScore,
    BeneishMScore,
    DuPontDecomposition,
    PerShareMetrics,
    compute_ttm,
)
from edgar_analytics.config import ALERTS_CONFIG, get_alerts_config


class TestTTMFlowVsStock:
    """C1: compute_ttm must sum flow metrics and use latest for stock metrics."""

    def test_flow_metric_summed(self):
        data = {
            "Revenue": {"Q1-2024": 100, "Q2-2024": 110, "Q3-2024": 120, "Q4-2024": 130},
        }
        ttm = compute_ttm(data)
        assert ttm["Revenue"] == pytest.approx(460)

    def test_stock_metric_uses_latest(self):
        data = {
            "Total Assets": {"Q1-2024": 5000, "Q2-2024": 5200, "Q3-2024": 5400, "Q4-2024": 5600},
        }
        ttm = compute_ttm(data)
        assert ttm["Total Assets"] == pytest.approx(5600)

    def test_stock_metric_with_one_quarter(self):
        data = {"Total Equity": {"Q4-2024": 3000}}
        ttm = compute_ttm(data)
        assert ttm["Total Equity"] == 3000

    def test_flow_metric_needs_4_quarters(self):
        data = {"Revenue": {"Q1-2024": 100, "Q2-2024": 110}}
        ttm = compute_ttm(data)
        assert "Revenue" not in ttm

    def test_mixed_flow_and_stock(self):
        data = {
            "Revenue": {"Q1-2024": 100, "Q2-2024": 110, "Q3-2024": 120, "Q4-2024": 130},
            "Total Assets": {"Q1-2024": 5000, "Q2-2024": 5200, "Q3-2024": 5400, "Q4-2024": 5600},
            "Current Liabilities": {"Q1-2024": 800, "Q4-2024": 1000},
        }
        ttm = compute_ttm(data)
        assert ttm["Revenue"] == pytest.approx(460)
        assert ttm["Total Assets"] == pytest.approx(5600)
        assert ttm["Current Liabilities"] == pytest.approx(1000)


class TestAltmanZDoublePrime:
    """S-FA1: Z'' model for non-manufacturing companies."""

    def test_manufacturing_model_selected(self):
        az = AltmanZScore.compute(
            working_capital=2000, retained_earnings=3000, ebit=1500,
            market_cap=10000, total_liabilities=2000, revenue=8000,
            total_assets=5000, book_value_equity=3000,
            is_manufacturing=True,
        )
        assert "manufacturing" in az.model.lower()
        assert az.z_score > 0

    def test_non_manufacturing_model_selected(self):
        az = AltmanZScore.compute(
            working_capital=2000, retained_earnings=3000, ebit=1500,
            market_cap=10000, total_liabilities=2000, revenue=8000,
            total_assets=5000, book_value_equity=3000,
            is_manufacturing=False,
        )
        assert "non-manufacturing" in az.model.lower()
        assert az.z_score > 0

    def test_auto_detect_service_company(self):
        """Low asset turnover (rev/assets < 0.5) should trigger Z'' model."""
        az = AltmanZScore.compute(
            working_capital=500, retained_earnings=1000, ebit=300,
            market_cap=5000, total_liabilities=2000, revenue=400,
            total_assets=5000, book_value_equity=3000,
        )
        assert "non-manufacturing" in az.model.lower()

    def test_model_field_populated(self):
        az = AltmanZScore.compute(
            working_capital=2000, retained_earnings=3000, ebit=1500,
            market_cap=10000, total_liabilities=2000, revenue=8000,
            total_assets=5000, book_value_equity=3000,
        )
        assert az.model != ""

    def test_z_double_prime_thresholds(self):
        """Z'' uses different thresholds: Safe > 2.60, Distress < 1.10."""
        az = AltmanZScore.compute(
            working_capital=2000, retained_earnings=3000, ebit=1500,
            market_cap=10000, total_liabilities=2000, revenue=400,
            total_assets=5000, book_value_equity=3000,
            is_manufacturing=False,
        )
        if az.z_score > 2.60:
            assert az.zone == "Safe"
        elif az.z_score > 1.10:
            assert az.zone == "Grey"
        else:
            assert az.zone == "Distress"


class TestBeneishGMIFix:
    """S-FA6: GMI should not default to 1.0 when current GM is zero."""

    def test_gmi_high_when_current_gm_zero(self):
        bm = BeneishMScore.compute(
            revenue=1000, revenue_prev=900,
            receivables=100, receivables_prev=85,
            gross_margin_pct=0.0, gross_margin_pct_prev=42.0,
            total_assets=5000, total_assets_prev=4500,
            current_assets=1500, current_assets_prev=1300,
            current_liabilities=800, current_liabilities_prev=700,
            long_term_debt=1200, long_term_debt_prev=1100,
            depreciation_rate=0.10, depreciation_rate_prev=0.10,
            sga_pct=0.15, sga_pct_prev=0.15,
            operating_cf=200, net_income=150,
            ppe=2000, ppe_prev=1800,
        )
        assert bm.indices["GMI"] > 100, "GMI should be very high when current GM drops to zero"

    def test_gmi_neutral_when_both_zero(self):
        bm = BeneishMScore.compute(
            revenue=1000, revenue_prev=900,
            receivables=100, receivables_prev=85,
            gross_margin_pct=0.0, gross_margin_pct_prev=0.0,
            total_assets=5000, total_assets_prev=4500,
            current_assets=1500, current_assets_prev=1300,
            current_liabilities=800, current_liabilities_prev=700,
            long_term_debt=1200, long_term_debt_prev=1100,
            depreciation_rate=0.10, depreciation_rate_prev=0.10,
            sga_pct=0.15, sga_pct_prev=0.15,
            operating_cf=200, net_income=150,
            ppe=2000, ppe_prev=1800,
        )
        assert bm.indices["GMI"] == pytest.approx(1.0)


class TestDuPontNegativeEquity:
    """S-FA2: DuPont ROE should be NaN when equity is negative."""

    def test_positive_equity_computes_normally(self):
        dp = DuPontDecomposition.compute(100, 1000, 5000, 2000, 200, 150)
        assert not math.isnan(dp.roe_3)
        assert dp.negative_equity_warning is False

    def test_negative_equity_returns_nan_roe(self):
        dp = DuPontDecomposition.compute(100, 1000, 5000, -500, 200, 150)
        assert math.isnan(dp.roe_3)
        assert math.isnan(dp.roe_5)
        assert dp.negative_equity_warning is True

    def test_components_still_computed(self):
        dp = DuPontDecomposition.compute(100, 1000, 5000, -500, 200, 150)
        assert not math.isnan(dp.net_profit_margin)
        assert not math.isnan(dp.asset_turnover)
        assert not math.isnan(dp.equity_multiplier)


class TestEPSFallback:
    """S-FA4: Diluted EPS should be NaN when not reported."""

    def test_diluted_nan_when_not_reported(self):
        income_df = pd.DataFrame({"Value": [100]}, index=["Net income"])
        balance_df = pd.DataFrame({"Value": [50]}, index=["Shares outstanding"])
        ps = PerShareMetrics.compute(income_df, balance_df, 100, 1000, 80)
        assert ps.eps_basic == pytest.approx(2.0)
        assert math.isnan(ps.eps_diluted)

    def test_both_reported(self):
        income_df = pd.DataFrame(
            {"Value": [3.50, 3.40]},
            index=["Basic EPS", "Diluted EPS"],
        )
        balance_df = pd.DataFrame({"Value": [1000]}, index=["Shares outstanding"])
        ps = PerShareMetrics.compute(income_df, balance_df, 100, 5000, 80)
        assert ps.eps_basic == pytest.approx(3.50)
        assert ps.eps_diluted == pytest.approx(3.40)


class TestAlertsConfigOverrides:
    """S-ENG5: Alert thresholds should be configurable."""

    def test_default_config_unchanged(self):
        cfg = get_alerts_config(None)
        assert cfg["HIGH_LEVERAGE"] == 3.0

    def test_override_merges(self):
        cfg = get_alerts_config({"HIGH_LEVERAGE": 10.0, "LOW_ROE": 1.0})
        assert cfg["HIGH_LEVERAGE"] == 10.0
        assert cfg["LOW_ROE"] == 1.0
        assert cfg["NEGATIVE_MARGIN"] == 0.0

    def test_original_not_mutated(self):
        get_alerts_config({"HIGH_LEVERAGE": 999})
        assert ALERTS_CONFIG["HIGH_LEVERAGE"] == 3.0


class TestVersionAttribute:
    def test_version_exists(self):
        import edgar_analytics
        assert hasattr(edgar_analytics, "__version__")
        assert isinstance(edgar_analytics.__version__, str)
        assert edgar_analytics.__version__ == "0.8.1"


class TestReducedPublicSurface:
    def test_all_contains_essential_names(self):
        import edgar_analytics
        assert "analyze" in edgar_analytics.__all__
        assert "AnalysisResult" in edgar_analytics.__all__
        assert "TickerOrchestrator" in edgar_analytics.__all__
        assert "EdgarAnalyticsError" in edgar_analytics.__all__
        assert "TickerFetchError" in edgar_analytics.__all__

    def test_internal_utilities_not_in_all(self):
        import edgar_analytics
        assert "find_synonym_value" not in edgar_analytics.__all__
        assert "make_numeric_df" not in edgar_analytics.__all__
        assert "SYNONYMS" not in edgar_analytics.__all__
        assert "compute_all_scores" not in edgar_analytics.__all__

    def test_internal_modules_still_importable(self):
        from edgar_analytics.synonyms import SYNONYMS
        from edgar_analytics.synonyms_utils import find_synonym_value
        from edgar_analytics.data_utils import parse_period_label
        assert SYNONYMS is not None
        assert find_synonym_value is not None
        assert parse_period_label is not None
