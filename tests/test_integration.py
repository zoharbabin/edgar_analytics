"""
tests/test_integration.py

Integration tests that hit the real SEC EDGAR API.
Skipped by default — run with: pytest -m integration --run-integration

These tests verify that the library works end-to-end with actual SEC data,
catching API changes, synonym mismatches, and data parsing issues that
unit tests with mocks cannot detect.
"""

import os
import time
import pytest
import pandas as pd

from edgar import Company, set_identity

from edgar_analytics.metrics import (
    get_single_filing_snapshot,
    get_filing_snapshot_with_fallback,
    ANNUAL_FORM_TYPES,
    QUARTERLY_FORM_TYPES,
)
from edgar_analytics.multi_period_analysis import (
    retrieve_multi_year_data,
    analyze_quarterly_balance_sheets,
)
from edgar_analytics.forecasting import forecast_revenue

SEC_REQUEST_DELAY = float(os.environ.get("SEC_REQUEST_DELAY", "1.2"))
SEC_MAX_RETRIES = int(os.environ.get("SEC_MAX_RETRIES", "4"))


def _with_sec_retry(fn, *args, **kwargs):
    """Retry a callable that hits the SEC API, with exponential backoff on 403/429/503."""
    last_exc = None
    for attempt in range(SEC_MAX_RETRIES):
        try:
            time.sleep(SEC_REQUEST_DELAY)
            return fn(*args, **kwargs)
        except Exception as exc:
            exc_str = str(exc)
            if any(code in exc_str for code in ("403", "429", "503")):
                last_exc = exc
                wait = 2 ** attempt * 2
                print(f"SEC {exc_str[:60]}... retry {attempt + 1}/{SEC_MAX_RETRIES} in {wait}s")
                time.sleep(wait)
                continue
            raise
    pytest.skip(f"SEC API unavailable after {SEC_MAX_RETRIES} retries: {last_exc}")


def sec_company(ticker: str) -> Company:
    """Create and warm an edgar.Company, retrying on SEC rate-limit/block."""
    def _create():
        comp = Company(ticker)
        # Force lazy data load so 403 surfaces here, not mid-assertion
        _ = comp.name
        return comp
    return _with_sec_retry(_create)


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
        comp = sec_company("AAPL")
        snap = _with_sec_retry(get_single_filing_snapshot, comp, "10-K")

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
        comp = sec_company("AAPL")
        snap = _with_sec_retry(get_single_filing_snapshot, comp, "10-Q")

        assert snap["metrics"], "AAPL 10-Q should produce metrics"
        assert snap["metrics"]["Revenue"] > 0

    def test_annual_fallback_us_filer(self):
        comp = sec_company("AAPL")
        snap = _with_sec_retry(get_filing_snapshot_with_fallback, comp, ANNUAL_FORM_TYPES)
        assert snap["metrics"], "Fallback should find 10-K for AAPL"
        assert snap["filing_info"]["form_type"] == "10-K"


class TestMultiPeriodAnalysis:

    def test_retrieve_multi_year_data_aapl(self):
        data = _with_sec_retry(retrieve_multi_year_data, "AAPL", n_years=2, n_quarters=4)

        assert "annual_data" in data
        assert "quarterly_data" in data
        rev = data["annual_data"].get("Revenue", {})
        assert len(rev) >= 1, "Should find at least 1 annual revenue period"
        for period, val in rev.items():
            assert val > 0, f"AAPL revenue for {period} should be positive"

        assert "Gross Profit" in data["annual_data"]
        assert "Operating Income" in data["annual_data"]

    def test_quarterly_balance_sheets_aapl(self):
        comp = sec_company("AAPL")
        results = _with_sec_retry(analyze_quarterly_balance_sheets, comp, n_quarters=4)

        assert "free_cf" in results
        assert len(results["free_cf"]) >= 1, "Should have at least 1 quarter of FCF"


class TestForecasting:

    def test_forecast_from_real_data(self):
        data = _with_sec_retry(retrieve_multi_year_data, "AAPL", n_years=5, n_quarters=4)
        rev_annual = data["annual_data"].get("Revenue", {})

        if len(rev_annual) >= 6:
            fc = forecast_revenue(rev_annual, is_quarterly=False)
            assert isinstance(fc, float)
            assert fc != 0.0, "With enough AAPL data, forecast should be non-zero"


class TestIFRSFiler:
    """Test an IFRS filer that files 20-F (e.g., Unilever)."""

    def test_ul_20f_snapshot(self):
        comp = sec_company("UL")
        snap = _with_sec_retry(get_filing_snapshot_with_fallback, comp, ANNUAL_FORM_TYPES)
        m = snap.get("metrics", {})
        if not m:
            pytest.skip("UL filing not available")
        assert m.get("Revenue", 0) > 0, "Unilever revenue should be positive"
        info = snap.get("filing_info", {})
        assert info.get("form_type") in ("20-F", "20-F/A"), f"Expected 20-F, got {info.get('form_type')}"


class TestBankFiler:
    """Test a bank with different statement structure (JPMorgan)."""

    def test_jpm_10k_snapshot(self):
        comp = sec_company("JPM")
        snap = _with_sec_retry(get_single_filing_snapshot, comp, "10-K")
        m = snap.get("metrics", {})
        if not m:
            pytest.skip("JPM filing not available")
        assert m.get("Revenue", 0) != 0 or m.get("Net Income", 0) != 0, (
            "JPM should have revenue or net income"
        )
        assert isinstance(m.get("Alerts"), list)

    def test_jpm_quality_ratios(self):
        comp = sec_company("JPM")
        snap = _with_sec_retry(get_single_filing_snapshot, comp, "10-K")
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
        comp = sec_company("AAPL")
        filings = _with_sec_retry(comp.get_filings, form="10-K/A", is_xbrl=True)
        if filings is None or len(filings) == 0:
            pytest.skip("No 10-K/A filings available for AAPL")
        snap = _with_sec_retry(get_single_filing_snapshot, comp, "10-K/A")
        m = snap.get("metrics", {})
        if not m:
            pytest.skip("10-K/A filing has no parseable metrics")
        assert snap["filing_info"]["form_type"] == "10-K/A"
        assert isinstance(m.get("Alerts"), list)


class TestSmallCapFiler:
    """Test a small-cap company with potentially sparse data."""

    def test_small_cap_snapshot(self):
        """Small-cap filer should return metrics without crashing on missing line items."""
        comp = sec_company("SIRI")
        snap = _with_sec_retry(get_filing_snapshot_with_fallback, comp, ANNUAL_FORM_TYPES)
        m = snap.get("metrics", {})
        if not m:
            pytest.skip("SIRI filing not available")
        assert isinstance(m.get("Alerts"), list)
        assert m.get("Revenue", 0) >= 0

    def test_small_cap_multi_year(self):
        """Multi-year retrieval on small-cap should not crash even with sparse data."""
        data = _with_sec_retry(retrieve_multi_year_data, "SIRI", n_years=2, n_quarters=4)
        assert "annual_data" in data
        assert "quarterly_data" in data


class TestMetricsConsistency:
    """Sanity checks on metric relationships."""

    def test_balance_sheet_identity(self):
        comp = sec_company("AAPL")
        snap = _with_sec_retry(get_single_filing_snapshot, comp, "10-K")
        m = snap["metrics"]

        if m.get("Revenue") and m.get("Net Income"):
            margin = m["Net Margin %"]
            expected = (m["Net Income"] / m["Revenue"]) * 100.0
            assert margin == pytest.approx(expected, abs=0.01)

    def test_fcf_is_opcf_minus_capex(self):
        comp = sec_company("AAPL")
        snap = _with_sec_retry(get_single_filing_snapshot, comp, "10-K")
        m = snap["metrics"]

        opcf = m.get("Cash from Operations", 0)
        fcf = m.get("Free Cash Flow", 0)
        assert fcf <= opcf, "FCF should not exceed operating cash flow"


class TestSynonymCoverage:
    """Verify synonym lists contain matches for real XBRL concepts."""

    def test_aapl_xbrl_concepts_covered(self):
        from edgar_analytics.synonyms import SYNONYMS
        from edgar_analytics.company_facts import CompanyFactsClient

        client = CompanyFactsClient()
        facts = _with_sec_retry(client.fetch, "AAPL")
        if facts is None:
            pytest.skip("CompanyFacts API unavailable")

        gaap = facts.get("facts", {}).get("us-gaap", {})
        if not gaap:
            pytest.skip("No us-gaap facts returned")
        gaap_concepts = set(gaap.keys())

        def strip_prefix(tag):
            for pfx in ("us-gaap:", "us-gaap_"):
                if tag.startswith(pfx):
                    return tag[len(pfx):]
            return tag

        for key in ("revenue", "net_income", "total_assets", "cash_equivalents"):
            tags = {strip_prefix(t) for t in SYNONYMS[key]}
            assert tags & gaap_concepts, (
                f"No synonym for '{key}' matches AAPL XBRL concepts. "
                f"Checked: {sorted(tags)[:5]}..."
            )
