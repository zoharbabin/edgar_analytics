"""tests/test_scores.py — unit tests for scoring models."""

import math
import pytest
import pandas as pd

from edgar_analytics.scores import (
    PerShareMetrics,
    WorkingCapitalCycle,
    CapitalEfficiency,
    DuPontDecomposition,
    PiotroskiScore,
    AltmanZScore,
    BeneishMScore,
    compute_ttm,
    compute_all_scores,
    run_dqc_checks,
)


class TestPerShareMetrics:
    def test_basic_computation(self):
        income_df = pd.DataFrame(
            {"Value": [2.50, 2.40, 100]},
            index=["Basic EPS", "Diluted EPS", "Net income"],
        )
        balance_df = pd.DataFrame(
            {"Value": [5000, 1_000_000]},
            index=["Total shareholders' equity", "Shares outstanding"],
        )
        ps = PerShareMetrics.compute(income_df, balance_df, 100, 5000, 80)
        assert ps.eps_basic == pytest.approx(2.50)
        assert ps.eps_diluted == pytest.approx(2.40)
        assert ps.book_value_per_share == pytest.approx(0.005)
        assert ps.fcf_per_share == pytest.approx(0.00008)

    def test_fallback_eps_from_net_income(self):
        income_df = pd.DataFrame({"Value": [100]}, index=["Net income"])
        balance_df = pd.DataFrame({"Value": [50]}, index=["Shares outstanding"])
        ps = PerShareMetrics.compute(income_df, balance_df, 100, 1000, 80)
        assert ps.eps_basic == pytest.approx(2.0)
        assert math.isnan(ps.eps_diluted), "Diluted EPS should be NaN when not reported (no diluted share count)"

    def test_zero_shares(self):
        income_df = pd.DataFrame({"Value": [100]}, index=["Net income"])
        balance_df = pd.DataFrame({"Value": [0]}, index=["No shares"])
        ps = PerShareMetrics.compute(income_df, balance_df, 100, 1000, 80)
        assert math.isnan(ps.book_value_per_share)
        assert math.isnan(ps.fcf_per_share)


class TestWorkingCapitalCycle:
    def test_basic(self):
        wc = WorkingCapitalCycle.compute(
            revenue=365_000, cost_of_revenue=200_000,
            accounts_receivable=50_000, inventory=30_000,
            accounts_payable=20_000,
        )
        assert wc.dso == pytest.approx(50.0, abs=0.1)
        assert wc.dio == pytest.approx(54.75, abs=0.1)
        assert wc.dpo == pytest.approx(36.5, abs=0.1)
        assert wc.cash_conversion_cycle == pytest.approx(50.0 + 54.75 - 36.5, abs=0.2)

    def test_zero_revenue(self):
        wc = WorkingCapitalCycle.compute(0, 0, 100, 50, 20)
        assert math.isnan(wc.dso)
        assert math.isnan(wc.cash_conversion_cycle)


class TestCapitalEfficiency:
    def test_basic(self):
        # income_before_taxes=400 (e.g. EBIT 500 - interest 100)
        ce = CapitalEfficiency.compute(
            operating_income=500, income_tax_expense=100,
            income_before_taxes=400,
            revenue=2000, total_assets=5000, total_equity=3000,
            short_term_debt=200, long_term_debt=800, cash_equiv=500,
        )
        # effective_tax_rate = 100/400 = 0.25
        assert ce.nopat == pytest.approx(375.0)  # 500 * (1 - 0.25)
        assert ce.invested_capital == pytest.approx(3500.0)  # 3000+200+800-500
        assert ce.roic_pct == pytest.approx(375 / 3500 * 100, abs=0.1)
        assert ce.asset_turnover == pytest.approx(0.4)

    def test_zero_invested_capital(self):
        ce = CapitalEfficiency.compute(500, 100, 400, 2000, 5000, 0, 0, 0, 0)
        assert math.isnan(ce.roic_pct)

    def test_negative_invested_capital(self):
        """Cash-rich company where cash > equity + debt: IC is negative, ROIC is NaN."""
        ce = CapitalEfficiency.compute(
            operating_income=500, income_tax_expense=100,
            income_before_taxes=400,
            revenue=2000, total_assets=5000, total_equity=1000,
            short_term_debt=0, long_term_debt=0, cash_equiv=2000,
        )
        assert ce.invested_capital == pytest.approx(-1000.0)
        assert math.isnan(ce.roic_pct)

    def test_tax_benefit(self):
        """Negative tax (benefit) should result in 0% effective rate (clamped)."""
        ce = CapitalEfficiency.compute(
            operating_income=100, income_tax_expense=-20,
            income_before_taxes=120,
            revenue=500, total_assets=1000, total_equity=600,
            short_term_debt=0, long_term_debt=200, cash_equiv=100,
        )
        # effective_tax = -20/120 = -0.167, clamped to 0.0
        assert ce.nopat == pytest.approx(100.0)  # 100 * (1 - 0)
        assert ce.invested_capital == pytest.approx(700.0)


class TestDuPontDecomposition:
    def test_3_component(self):
        dp = DuPontDecomposition.compute(
            net_income=100, revenue=1000, total_assets=5000,
            total_equity=2000, ebit=200, income_before_taxes=150,
        )
        npm = 100 / 1000
        at = 1000 / 5000
        em = 5000 / 2000
        assert dp.roe_3 == pytest.approx(npm * at * em * 100, abs=0.01)

    def test_5_component(self):
        dp = DuPontDecomposition.compute(
            net_income=100, revenue=1000, total_assets=5000,
            total_equity=2000, ebit=200, income_before_taxes=150,
        )
        assert dp.tax_burden == pytest.approx(100 / 150, abs=0.01)
        assert dp.interest_burden == pytest.approx(150 / 200, abs=0.01)
        assert dp.operating_margin == pytest.approx(200 / 1000, abs=0.01)
        assert not math.isnan(dp.roe_5)

    def test_zero_equity(self):
        dp = DuPontDecomposition.compute(100, 1000, 5000, 0, 200, 150)
        assert math.isnan(dp.equity_multiplier)
        assert math.isnan(dp.roe_3)

    def test_negative_equity(self):
        """Negative equity produces NaN ROE (sign inversions lose meaning) with a warning flag."""
        dp = DuPontDecomposition.compute(
            net_income=-50, revenue=1000, total_assets=5000,
            total_equity=-2000, ebit=200, income_before_taxes=150,
        )
        assert dp.equity_multiplier == pytest.approx(5000 / -2000)
        assert math.isnan(dp.roe_3), "DuPont ROE should be NaN when equity is negative"
        assert math.isnan(dp.roe_5), "DuPont ROE-5 should be NaN when equity is negative"
        assert dp.negative_equity_warning is True


class TestPiotroskiScore:
    def test_perfect_score(self):
        ps = PiotroskiScore.compute(
            net_income=100, total_assets=5000, total_assets_prev=4500,
            operating_cf=200, roa=5.0, roa_prev=3.0,
            long_term_debt=500, long_term_debt_prev=700,
            current_ratio=2.0, current_ratio_prev=1.5,
            shares_outstanding=1000, shares_outstanding_prev=1000,
            gross_margin=40.0, gross_margin_prev=35.0,
            asset_turnover=0.5, asset_turnover_prev=0.4,
        )
        assert ps.score == 9

    def test_worst_score(self):
        ps = PiotroskiScore.compute(
            net_income=-50, total_assets=5000, total_assets_prev=5000,
            operating_cf=-100, roa=-2.0, roa_prev=1.0,
            long_term_debt=900, long_term_debt_prev=700,
            current_ratio=0.8, current_ratio_prev=1.2,
            shares_outstanding=1200, shares_outstanding_prev=1000,
            gross_margin=30.0, gross_margin_prev=35.0,
            asset_turnover=0.3, asset_turnover_prev=0.4,
        )
        assert ps.score == 0

    def test_partial_score(self):
        ps = PiotroskiScore.compute(
            net_income=100, total_assets=5000, total_assets_prev=5000,
            operating_cf=200, roa=3.0, roa_prev=3.0,
            long_term_debt=700, long_term_debt_prev=700,
            current_ratio=1.5, current_ratio_prev=1.5,
            shares_outstanding=1000, shares_outstanding_prev=1000,
            gross_margin=35.0, gross_margin_prev=35.0,
            asset_turnover=0.4, asset_turnover_prev=0.4,
        )
        assert 0 < ps.score < 9


class TestAltmanZScore:
    def test_safe_zone(self):
        az = AltmanZScore.compute(
            working_capital=2000, retained_earnings=3000,
            ebit=1500, market_cap=10000,
            total_liabilities=2000, revenue=8000, total_assets=5000,
        )
        assert az.z_score > 2.99
        assert az.zone == "Safe"

    def test_distress_zone(self):
        az = AltmanZScore.compute(
            working_capital=-500, retained_earnings=-1000,
            ebit=-200, market_cap=500,
            total_liabilities=8000, revenue=1000, total_assets=5000,
        )
        assert az.z_score < 1.81
        assert az.zone == "Distress"

    def test_zero_assets(self):
        az = AltmanZScore.compute(0, 0, 0, 0, 0, 0, 0)
        assert math.isnan(az.z_score)

    def test_no_market_cap(self):
        az = AltmanZScore.compute(1000, 2000, 500, float("nan"), 3000, 5000, 5000)
        assert math.isnan(az.z_score)


class TestBeneishMScore:
    def test_basic(self):
        bm = BeneishMScore.compute(
            revenue=1000, revenue_prev=900,
            receivables=100, receivables_prev=85,
            gross_margin_pct=40, gross_margin_pct_prev=42,
            total_assets=5000, total_assets_prev=4500,
            current_assets=1500, current_assets_prev=1300,
            current_liabilities=800, current_liabilities_prev=700,
            long_term_debt=1200, long_term_debt_prev=1100,
            depreciation_rate=0.10, depreciation_rate_prev=0.10,
            sga_pct=0.15, sga_pct_prev=0.15,
            operating_cf=200, net_income=150,
            ppe=2000, ppe_prev=1800,
        )
        assert not math.isnan(bm.m_score)
        assert len(bm.indices) == 8
        assert "DSRI" in bm.indices
        lvgi_expected = ((800 + 1200) / 5000) / ((700 + 1100) / 4500)
        assert bm.indices["LVGI"] == pytest.approx(lvgi_expected, abs=0.01)
        aqi_expected = (1 - (1500 + 2000) / 5000) / (1 - (1300 + 1800) / 4500)
        assert bm.indices["AQI"] == pytest.approx(aqi_expected, abs=0.01)

    def test_zero_prev_revenue(self):
        bm = BeneishMScore.compute(
            revenue=100, revenue_prev=0,
            receivables=10, receivables_prev=10,
            gross_margin_pct=40, gross_margin_pct_prev=40,
            total_assets=500, total_assets_prev=0,
            current_assets=200, current_assets_prev=150,
            current_liabilities=50, current_liabilities_prev=40,
            long_term_debt=100, long_term_debt_prev=80,
            depreciation_rate=0.1, depreciation_rate_prev=0.1,
            sga_pct=0.15, sga_pct_prev=0.15,
            operating_cf=50, net_income=30,
            ppe=100, ppe_prev=100,
        )
        assert math.isnan(bm.m_score)


class TestComputeTTM:
    def test_basic(self):
        data = {
            "Revenue": {
                "Q1-2023": 100, "Q2-2023": 110,
                "Q3-2023": 120, "Q4-2023": 130,
                "Q1-2024": 140,
            },
        }
        ttm = compute_ttm(data)
        assert ttm["Revenue"] == pytest.approx(500)  # 110+120+130+140

    def test_ratio_metric_uses_latest(self):
        data = {
            "Gross Margin %": {"Q1-2024": 25.0, "Q2-2024": 26.0, "Q3-2024": 27.0, "Q4-2024": 28.0},
        }
        ttm = compute_ttm(data)
        assert ttm["Gross Margin %"] == pytest.approx(28.0)

    def test_operating_margin_not_summed(self):
        data = {
            "Operating Margin %": {"Q1-2024": 10.0, "Q2-2024": 11.0, "Q3-2024": 12.0, "Q4-2024": 13.0},
        }
        ttm = compute_ttm(data)
        assert ttm["Operating Margin %"] == pytest.approx(13.0)

    def test_insufficient_data(self):
        data = {"Revenue": {"Q1-2023": 100, "Q2-2023": 110}}
        ttm = compute_ttm(data)
        assert "Revenue" not in ttm


class TestComputeAllScores:
    def test_returns_all_keys(self):
        metrics = {
            "Revenue": 1000, "Net Income": 100, "CostOfRev": 400,
            "Free Cash Flow": 80, "Cash from Operations": 150,
            "Operating Income": 200, "Income Tax Expense": 40,
            "EBIT (standard)": 200, "Interest Expense": 20,
        }
        bal_df = pd.DataFrame(
            {"Value": [5000, 2000, 3000, 500, 100, 200, 50, 800, 1000, 1500]},
            index=[
                "Total assets", "Total liabilities",
                "Total shareholders' equity", "Cash and cash equivalents",
                "Short-term debt", "Long-term debt",
                "Accounts receivable", "Inventories",
                "Accounts payable", "Retained Earnings",
            ],
        )
        inc_df = pd.DataFrame(
            {"Value": [1000, 100, 200]},
            index=["Net sales", "Net income", "Pretax income"],
        )
        cf_df = pd.DataFrame({"Value": [150]}, index=["Cash generated by operating activities"])

        scores = compute_all_scores(metrics, bal_df, inc_df, cf_df)
        assert "per_share" in scores
        assert "working_capital" in scores
        assert "capital_efficiency" in scores
        assert "dupont" in scores
        assert "altman" in scores


class TestComputeAllScoresWithPrior:
    def _make_metrics(self, revenue=1000, net_income=100, **overrides):
        """Helper to build a metrics dict with all internal keys."""
        m = {
            "Revenue": revenue, "Net Income": net_income, "CostOfRev": 400,
            "Free Cash Flow": 80, "Cash from Operations": 150,
            "Operating Income": 200, "Income Tax Expense": 40,
            "EBIT (standard)": 200, "Interest Expense": 20,
            "Gross Margin %": 60.0, "Current Ratio": 2.0, "ROA %": 5.0,
            "_total_assets": 5000, "_total_liabilities": 2000,
            "_total_equity": 3000, "_current_assets": 2000,
            "_current_liabilities": 1000, "_short_term_debt": 100,
            "_long_term_debt": 200, "_cash_equivalents": 500,
            "_accounts_receivable": 50, "_inventory": 800,
            "_accounts_payable": 300, "_retained_earnings": 1500,
            "_ppe_net": 2000, "_shares_outstanding": 1000,
            "_dep_amort": 100, "_sga": 150,
            "_short_term_investments": 0,
            "_income_before_taxes": 140,
        }
        m.update(overrides)
        return m

    def test_with_prior_metrics_adds_piotroski(self):
        curr = self._make_metrics()
        prev = self._make_metrics(revenue=900, net_income=80)
        scores = compute_all_scores(
            curr, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(),
            prior_metrics=prev,
        )
        assert "piotroski" in scores
        assert scores["piotroski"].score >= 0

    def test_altman_always_computed(self):
        """Altman Z-Score is a single-period model — computed even without prior data."""
        curr = self._make_metrics()
        scores = compute_all_scores(
            curr, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(),
            market_cap=10000,
        )
        assert "altman" in scores
        assert not math.isnan(scores["altman"].z_score)

    def test_with_prior_metrics_adds_beneish(self):
        curr = self._make_metrics()
        prev = self._make_metrics(revenue=900)
        scores = compute_all_scores(
            curr, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(),
            prior_metrics=prev,
        )
        assert "beneish" in scores
        assert not math.isnan(scores["beneish"].m_score)

    def test_without_prior_metrics_no_yoy_scores(self):
        curr = self._make_metrics()
        scores = compute_all_scores(
            curr, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(),
        )
        assert "piotroski" not in scores
        assert "altman" in scores  # Altman is always computed
        assert "beneish" not in scores


class TestDQCChecks:
    def test_negative_revenue_flagged(self):
        df = pd.DataFrame({"Value": [-1000]}, index=["Revenue"])
        warnings = run_dqc_checks(df)
        assert any("Revenue" in w and "negative" in w for w in warnings)

    def test_positive_values_clean(self):
        df = pd.DataFrame({"Value": [1000, 500]}, index=["Revenue", "Total assets"])
        warnings = run_dqc_checks(df)
        assert len(warnings) == 0

    def test_empty_df(self):
        assert run_dqc_checks(pd.DataFrame()) == []

    def test_negative_total_assets(self):
        df = pd.DataFrame({"Value": [-5000]}, index=["Total assets"])
        warnings = run_dqc_checks(df)
        assert any("Total assets" in w for w in warnings)

    def test_negative_equity_not_flagged(self):
        """Negative equity is legitimate (buyback-heavy companies like MCD, SBUX)."""
        df = pd.DataFrame({"Value": [-3000]}, index=["Total shareholders' equity"])
        warnings = run_dqc_checks(df)
        assert len(warnings) == 0


class TestFinancialCompanySuppression:
    """is_financial=True suppresses inapplicable scores."""

    def _make_metrics(self):
        return {
            "Revenue": 50_000, "Net Income": 5_000, "CostOfRev": 0,
            "Free Cash Flow": 3_000, "Cash from Operations": 7_000,
            "Operating Income": 8_000, "Income Tax Expense": 2_000,
            "EBIT (standard)": 8_000, "Gross Margin %": 100.0,
            "_total_assets": 500_000, "_total_liabilities": 450_000,
            "_total_equity": 50_000, "_current_assets": 200_000,
            "_current_liabilities": 180_000, "_short_term_debt": 10_000,
            "_long_term_debt": 100_000, "_cash_equivalents": 50_000,
            "_accounts_receivable": 20_000, "_inventory": 0,
            "_accounts_payable": 15_000, "_retained_earnings": 30_000,
            "_ppe_net": 5_000, "_shares_outstanding": 1_000,
            "_dep_amort": 500, "_sga": 3_000,
            "_short_term_investments": 0, "_income_before_taxes": 7_000,
        }

    def test_working_capital_suppressed(self):
        scores = compute_all_scores(
            self._make_metrics(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(),
            is_financial=True,
        )
        assert math.isnan(scores["working_capital"].dso)
        assert math.isnan(scores["working_capital"].cash_conversion_cycle)

    def test_altman_suppressed(self):
        scores = compute_all_scores(
            self._make_metrics(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(),
            market_cap=1_000_000, is_financial=True,
        )
        assert math.isnan(scores["altman"].z_score)

    def test_dupont_still_computed(self):
        scores = compute_all_scores(
            self._make_metrics(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(),
            is_financial=True,
        )
        assert not math.isnan(scores["dupont"].roe_3)

    def test_non_financial_computes_normally(self):
        scores = compute_all_scores(
            self._make_metrics(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(),
            market_cap=1_000_000, is_financial=False,
        )
        assert not math.isnan(scores["altman"].z_score)
        assert not math.isnan(scores["working_capital"].dso)
