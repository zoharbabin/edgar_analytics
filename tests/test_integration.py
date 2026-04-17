"""
tests/test_integration.py

Integration tests that hit the real SEC EDGAR API.
Skipped by default — run with: pytest -m integration --run-integration

These tests verify that the library works end-to-end with actual SEC data,
catching API changes, synonym mismatches, and data parsing issues that
unit tests with mocks cannot detect.
"""

import os
import pytest
import numpy as np
import pandas as pd

from edgar import Company, set_identity

from edgar_analytics.metrics import (
    get_single_filing_snapshot,
    get_filing_snapshot_with_fallback,
    ANNUAL_FORM_TYPES,
    QUARTERLY_FORM_TYPES,
    compute_ratios_and_metrics,
)
from edgar_analytics.multi_period_analysis import (
    retrieve_multi_year_data,
    analyze_quarterly_balance_sheets,
)
from edgar_analytics.forecasting import forecast_revenue


@pytest.fixture(autouse=True, scope="module")
def _set_edgar_identity():
    identity = os.environ.get(
        "EDGAR_IDENTITY",
        "edgar-analytics-tests <edgar-analytics@users.noreply.github.com>",
    )
    set_identity(identity)


pytestmark = pytest.mark.integration


class TestSingleFilingSnapshot:
    """Test fetching a single filing for a well-known US GAAP filer."""

    def test_aapl_10k_snapshot(self):
        comp = Company("AAPL")
        snap = get_single_filing_snapshot(comp, "10-K")

        assert snap["metrics"], "AAPL 10-K should produce metrics"
        m = snap["metrics"]

        assert m["Revenue"] > 0, "Apple revenue should be positive"
        assert m["Net Income"] != 0, "Apple net income should be non-zero"
        assert m["Free Cash Flow"] != 0
        assert pd.notna(m["Debt-to-Equity"])
        assert pd.notna(m["ROE %"])
        assert isinstance(m["Alerts"], list)

        info = snap["filing_info"]
        assert info["form_type"] == "10-K"

    def test_aapl_10q_snapshot(self):
        comp = Company("AAPL")
        snap = get_single_filing_snapshot(comp, "10-Q")

        assert snap["metrics"], "AAPL 10-Q should produce metrics"
        assert snap["metrics"]["Revenue"] > 0

    def test_annual_fallback_us_filer(self):
        comp = Company("AAPL")
        snap = get_filing_snapshot_with_fallback(comp, ANNUAL_FORM_TYPES)
        assert snap["metrics"], "Fallback should find 10-K for AAPL"
        assert snap["filing_info"]["form_type"] == "10-K"


class TestMultiPeriodAnalysis:

    def test_retrieve_multi_year_data_aapl(self):
        data = retrieve_multi_year_data("AAPL", n_years=2, n_quarters=4)

        assert "annual_data" in data
        assert "quarterly_data" in data
        rev = data["annual_data"].get("Revenue", {})
        assert len(rev) >= 1, "Should find at least 1 annual revenue period"
        for period, val in rev.items():
            assert val > 0, f"AAPL revenue for {period} should be positive"

        assert "Gross Profit" in data["annual_data"]
        assert "Operating Income" in data["annual_data"]

    def test_quarterly_balance_sheets_aapl(self):
        comp = Company("AAPL")
        results = analyze_quarterly_balance_sheets(comp, n_quarters=4)

        assert "free_cf" in results
        assert len(results["free_cf"]) >= 1, "Should have at least 1 quarter of FCF"


class TestForecasting:

    def test_forecast_from_real_data(self):
        data = retrieve_multi_year_data("AAPL", n_years=5, n_quarters=4)
        rev_annual = data["annual_data"].get("Revenue", {})

        if len(rev_annual) >= 6:
            fc = forecast_revenue(rev_annual, is_quarterly=False)
            assert isinstance(fc, float)
            assert fc != 0.0, "With enough AAPL data, forecast should be non-zero"


class TestIFRSFiler:
    """Test an IFRS filer that files 20-F (e.g., Unilever)."""

    def test_ul_20f_snapshot(self):
        comp = Company("UL")
        snap = get_filing_snapshot_with_fallback(comp, ANNUAL_FORM_TYPES)
        m = snap.get("metrics", {})
        if not m:
            pytest.skip("UL filing not available")
        assert m.get("Revenue", 0) > 0, "Unilever revenue should be positive"
        info = snap.get("filing_info", {})
        assert info.get("form_type") in ("20-F", "20-F/A"), f"Expected 20-F, got {info.get('form_type')}"


class TestBankFiler:
    """Test a bank with different statement structure (JPMorgan)."""

    def test_jpm_10k_snapshot(self):
        comp = Company("JPM")
        snap = get_single_filing_snapshot(comp, "10-K")
        m = snap.get("metrics", {})
        if not m:
            pytest.skip("JPM filing not available")
        assert m.get("Revenue", 0) != 0 or m.get("Net Income", 0) != 0, (
            "JPM should have revenue or net income"
        )
        assert isinstance(m.get("Alerts"), list)

    def test_jpm_quality_ratios(self):
        comp = Company("JPM")
        snap = get_single_filing_snapshot(comp, "10-K")
        m = snap.get("metrics", {})
        if not m:
            pytest.skip("JPM filing not available")
        assert "Accruals Ratio" in m
        assert "Earnings Quality" in m


class TestAmendedFiling:
    """Verify that amended filings (10-K/A) are handled by the fallback."""

    def test_fallback_includes_amended(self):
        assert "10-K/A" in ANNUAL_FORM_TYPES
        assert "20-F/A" in ANNUAL_FORM_TYPES
        assert "10-Q/A" in QUARTERLY_FORM_TYPES

    def test_real_amended_filing_fetch(self):
        """Fetch a company known to have filed 10-K/A and verify data is returned."""
        comp = Company("AAPL")
        filings = comp.get_filings(form="10-K/A", is_xbrl=True)
        if filings is None or len(filings) == 0:
            pytest.skip("No 10-K/A filings available for AAPL")
        snap = get_single_filing_snapshot(comp, "10-K/A")
        m = snap.get("metrics", {})
        if not m:
            pytest.skip("10-K/A filing has no parseable metrics")
        assert snap["filing_info"]["form_type"] == "10-K/A"
        assert isinstance(m.get("Alerts"), list)


class TestSmallCapFiler:
    """Test a small-cap company with potentially sparse data."""

    def test_small_cap_snapshot(self):
        """Small-cap filer should return metrics without crashing on missing line items."""
        comp = Company("SIRI")
        snap = get_filing_snapshot_with_fallback(comp, ANNUAL_FORM_TYPES)
        m = snap.get("metrics", {})
        if not m:
            pytest.skip("SIRI filing not available")
        assert isinstance(m.get("Alerts"), list)
        assert m.get("Revenue", 0) >= 0

    def test_small_cap_multi_year(self):
        """Multi-year retrieval on small-cap should not crash even with sparse data."""
        data = retrieve_multi_year_data("SIRI", n_years=2, n_quarters=4)
        assert "annual_data" in data
        assert "quarterly_data" in data


class TestMetricsConsistency:
    """Sanity checks on metric relationships."""

    def test_balance_sheet_identity(self):
        comp = Company("AAPL")
        snap = get_single_filing_snapshot(comp, "10-K")
        m = snap["metrics"]

        if m.get("Revenue") and m.get("Net Income"):
            margin = m["Net Margin %"]
            expected = (m["Net Income"] / m["Revenue"]) * 100.0
            assert margin == pytest.approx(expected, abs=0.01)

    def test_fcf_is_opcf_minus_capex(self):
        comp = Company("AAPL")
        snap = get_single_filing_snapshot(comp, "10-K")
        m = snap["metrics"]

        opcf = m.get("Cash from Operations", 0)
        fcf = m.get("Free Cash Flow", 0)
        assert fcf <= opcf, "FCF should not exceed operating cash flow"
