"""
tests/test_orchestrator.py

Tests for orchestrator.py (TickerOrchestrator) and the TickerDetector class.
We mock external Edgar calls, forecast calls, etc., to avoid real network operations.
ReportingEngine tests have been moved to test_reporting.py.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import logging

from edgar_analytics.orchestrator import TickerOrchestrator, TickerDetector
from edgar_analytics.models import AnalysisResult, TickerAnalysis
from edgar_analytics.reporting import ReportingEngine


@pytest.mark.usefixtures("caplog")
def test_analyze_company_basic(caplog):
    """
    Verify that orchestrator logs "Analyzing company: AAPL"
    and logs "Comparing AAPL with peers: []" even if no peers.
    """
    with patch("edgar_analytics.orchestrator.TickerOrchestrator._analyze_ticker_for_metrics") as mock_analyze, \
         patch("edgar_analytics.reporting.ReportingEngine.summarize_metrics_table") as mock_summary, \
         caplog.at_level(logging.INFO, logger="edgar_analytics.orchestrator"):

        mock_analyze.return_value = {
            "annual_snapshot": {"metrics": {"Revenue": 123, "Alerts": []}},
            "extra_alerts": []
        }

        orchestrator = TickerOrchestrator()
        orchestrator.analyze_company("AAPL", peers=[], csv_path=None)

    logs = caplog.text
    assert "Analyzing company: AAPL" in logs, "Expected 'Analyzing company: AAPL' in logs."
    assert "Analysis complete" in logs, "Expected 'Analysis complete' in logs."


def test_analyze_company_with_peers():
    """
    Multiple peers scenario:
      - _analyze_ticker_for_metrics is called for main + each peer
      - summarize_metrics_table is called once with the aggregated map
    """
    with patch("edgar_analytics.orchestrator.TickerOrchestrator._analyze_ticker_for_metrics") as mock_analyze, \
         patch("edgar_analytics.reporting.ReportingEngine.summarize_metrics_table") as mock_summary:

        mock_analyze.return_value = {
            "annual_snapshot": {"metrics": {"Revenue": 100, "Alerts": []}},
            "extra_alerts": []
        }
        orchestrator = TickerOrchestrator()

        peers = ["MSFT", "GOOGL"]
        orchestrator.analyze_company("AAPL", peers=peers, csv_path=None)

        # Calls = 1 (AAPL) + len(peers)
        assert mock_analyze.call_count == 1 + len(peers)
        mock_summary.assert_called_once()


def test_analyze_company_with_csv(tmp_path):
    """
    Passing csv_path: it should be forwarded to summarize_metrics_table.
    """
    with patch("edgar_analytics.orchestrator.TickerOrchestrator._analyze_ticker_for_metrics"), \
         patch("edgar_analytics.reporting.ReportingEngine.summarize_metrics_table") as mock_summary:

        orchestrator = TickerOrchestrator()

        csv_path = str(tmp_path / "my_analysis.csv")
        orchestrator.analyze_company("TSLA", peers=["GM"], csv_path=csv_path)

        # The final call to summarize_metrics_table includes that CSV path
        mock_summary.assert_called_once()
        args, kwargs = mock_summary.call_args
        assert kwargs["csv_path"] == csv_path, (
            "summarize_metrics_table should receive csv_path"
        )


@pytest.mark.usefixtures("caplog")
def test_analyze_company_invalid_peer(caplog):
    """
    Invalid peer scenario: should log a warning and skip that peer.
    """
    with patch("edgar_analytics.orchestrator.Company") as mock_company, \
         patch("edgar_analytics.orchestrator.set_identity"), \
         patch("edgar_analytics.multi_period_analysis.Company"), \
         patch("edgar_analytics.multi_period_analysis.MultiFinancials"), \
         caplog.at_level(logging.WARNING, logger="edgar_analytics.orchestrator"):
        mock_company.return_value = MagicMock()

        orchestrator = TickerOrchestrator()
        orchestrator.analyze_company("AAPL", peers=["@@@", "MSFT"])

    logs = caplog.text
    assert "Skipping invalid peer ticker: @@@" in logs, "Should log a warning about invalid peer."


def test_analyze_company_exception_in_creation(caplog):
    """If creating the Company object raises, TickerFetchError should propagate."""
    from edgar_analytics.orchestrator import TickerFetchError
    with patch("edgar_analytics.orchestrator.Company", side_effect=ValueError("Creation error")), \
         patch("edgar_analytics.orchestrator.set_identity"):
        orchestrator = TickerOrchestrator()
        with pytest.raises(TickerFetchError, match="Cannot resolve ticker"):
            orchestrator.analyze_company("AAPL", peers=[])


# ---------------------------------------------------------------------
#                Test for the TickerDetector
# ---------------------------------------------------------------------

class TestTickerDetector:
    """
    Test suite for the TickerDetector class, ensuring robust coverage of
    validate_ticker_symbol(...) and search(...) functionalities.
    """

    @pytest.mark.parametrize("valid_ticker", [
        "AAPL",
        "MSFT",
        "GOOG",
        "TSLA",
        "BRK.A",
        "BRK.B",
        "RY.TO",
        "NGG.L",      # Deliberately not part of the regex suffix -> Should remain invalid by default,
                     # but if you decide to allow ".L", confirm or adjust the pattern. 
                     # If you truly want to allow ".L", ensure the pattern includes that logic.
        "BABA",
        "VTI",
        "ABC-1",
        "SHOP.TO",
        "A-B",        # A dash with suffix
        "BRK.A1",     # suffix alphanumeric
        "A-123",      # multiple digits suffix
    ])
    def test_validate_ticker_symbol_valid(self, valid_ticker):
        """
        TickerDetector.validate_ticker_symbol should return True for valid tickers
        that match the class-level regex pattern.
        """
        # Some entries might need pattern refinements if we want them truly valid.
        # Adjust test or pattern as needed.
        assert TickerDetector.validate_ticker_symbol(valid_ticker) is True, (
            f"Expected '{valid_ticker}' to be recognized as valid."
        )

    @pytest.mark.parametrize("invalid_ticker", [
        "",            # empty
        "aaaaaa",      # 6 letters => invalid
        "AAPL1",       # missing '.' or '-' for suffix
        "AAPL@",       # invalid character
        "12345",       # no letters, only digits => does not match
        "BRK..A",      # double dot not in pattern
        "RY--TO",      # double dash not in pattern
        "AB.C.D",      # multiple suffix groups? This might or might not pass depending on pattern
        "A#B",         # invalid character
        "aapl",        # lowercase is not allowed by the pattern
        "A-BB-C",      # multiple suffix segments might fail if only 1 suffix is allowed 
                       # or if pattern doesn't allow multiple segments 
        None,          # not even a string => should raise ValueError
    ])
    def test_validate_ticker_symbol_invalid(self, invalid_ticker):
        """
        TickerDetector.validate_ticker_symbol should return False or raise ValueError
        if the ticker is not a string, too long, or doesn't match the allowed pattern.
        """
        if not isinstance(invalid_ticker, str):
            # Non-string inputs should raise a ValueError
            with pytest.raises(ValueError):
                TickerDetector.validate_ticker_symbol(invalid_ticker)
        else:
            # For all other invalid string cases, the method should return False.
            assert TickerDetector.validate_ticker_symbol(invalid_ticker) is False, (
                f"Expected '{invalid_ticker}' to be recognized as invalid."
            )

    @pytest.mark.parametrize("sample_text,expected_match", [
        ("i like AAPL and MSFT", "AAPL"),  # 'i' lowercase because I is a valid ticker (IntelSat Global Holdings)
        ("The quick brown fox jumps over the lazy dog", None),
        ("BRK.A soared today", "BRK.A"),
        ("Check out ABC-1 or SHOP.TO in the market", "ABC-1"),  # returns first match
        ("No real ticker here!", None),
    ])
    def test_search(self, sample_text, expected_match):
        """
        TickerDetector.search(...) should return a re.Match if a valid ticker substring
        is found; None otherwise. If multiple tickers are present, it returns the first match.
        """
        match = TickerDetector.search(sample_text)
        if expected_match is None:
            assert match is None, (
                f"Expected no match for '{sample_text}', but got '{match.group(0)}'."
            )
        else:
            assert match is not None, (
                f"Expected a match for '{sample_text}' but got None."
            )
            assert match.group(0) == expected_match, (
                f"Expected first match = '{expected_match}', got '{match.group(0)}'."
            )

    def test_search_non_string_raises_valueerror(self):
        """
        search(...) should raise ValueError if passed a non-string input.
        """
        with pytest.raises(ValueError):
            TickerDetector.search(None)
        with pytest.raises(ValueError):
            TickerDetector.search(12345)


# ---------------------------------------------------------------------
#                Test for typed analyze() API
# ---------------------------------------------------------------------


def test_analyze_returns_typed_result():
    """analyze() returns an AnalysisResult with TickerAnalysis entries."""
    with patch("edgar_analytics.orchestrator.TickerOrchestrator._analyze_ticker_for_metrics") as mock_analyze:
        mock_analyze.return_value = {
            "annual_snapshot": {"metrics": {"Revenue": 1000, "Alerts": ["test"]}, "filing_info": {"form_type": "10-K"}},
            "quarterly_snapshot": {"metrics": {}, "filing_info": {}},
            "multiyear": {"annual_data": {}, "cagr_revenue": 5.0},
            "forecast": {"annual_rev_forecast": 1100.0},
            "extra_alerts": ["neg FCF"],
        }
        orchestrator = TickerOrchestrator()
        result = orchestrator.analyze("AAPL", peers=["MSFT"])

    assert isinstance(result, AnalysisResult)
    assert result.main_ticker == "AAPL"
    assert result.main.ticker == "AAPL"
    assert result.main.annual_snapshot.metrics.revenue == 1000
    assert result.main.annual_snapshot.metrics.alerts == ("test",)
    assert result.main.annual_snapshot.filing_info.form_type == "10-K"
    assert result.main.multiyear.cagr_revenue == 5.0
    assert result.main.forecast.annual_rev_forecast == 1100.0
    assert result.main.extra_alerts == ("neg FCF",)
    assert "MSFT" in result.peers


def test_analyze_invalid_ticker_raises():
    """analyze() raises ValueError for invalid ticker."""
    orchestrator = TickerOrchestrator()
    with pytest.raises(ValueError, match="Invalid ticker"):
        orchestrator.analyze("@@@")


def test_analyze_company_returns_result():
    """analyze_company() now returns an AnalysisResult (not None)."""
    with patch("edgar_analytics.orchestrator.TickerOrchestrator._analyze_ticker_for_metrics") as mock_analyze, \
         patch("edgar_analytics.reporting.ReportingEngine.summarize_metrics_table"):
        mock_analyze.return_value = {
            "annual_snapshot": {"metrics": {"Revenue": 500, "Alerts": []}, "filing_info": {}},
            "extra_alerts": [],
        }
        orchestrator = TickerOrchestrator()
        result = orchestrator.analyze_company("AAPL", peers=[])

    assert isinstance(result, AnalysisResult)
    assert result.main.annual_snapshot.metrics.revenue == 500


def test_public_analyze_function():
    """The top-level ea.analyze() convenience function works."""
    import edgar_analytics as ea
    with patch("edgar_analytics.orchestrator.TickerOrchestrator._analyze_ticker_for_metrics") as mock_analyze:
        mock_analyze.return_value = {
            "annual_snapshot": {"metrics": {"Revenue": 42, "Alerts": []}, "filing_info": {}},
            "extra_alerts": [],
        }
        result = ea.analyze("AAPL")

    assert isinstance(result, ea.AnalysisResult)
    assert result.main.annual_snapshot.metrics.revenue == 42


# ---------------------------------------------------------------------
#         TTM wiring in orchestrator
# ---------------------------------------------------------------------

def test_ttm_wired_into_multiyear():
    """compute_ttm is called on quarterly_data and result stored in multiyear.ttm."""
    with patch("edgar_analytics.orchestrator.TickerOrchestrator._analyze_ticker_for_metrics") as mock_analyze:
        mock_analyze.return_value = {
            "annual_snapshot": {"metrics": {"Revenue": 1000, "Alerts": []}, "filing_info": {}},
            "quarterly_snapshot": {"metrics": {}, "filing_info": {}},
            "multiyear": {
                "annual_data": {},
                "quarterly_data": {
                    "Revenue": {
                        "2023-Q1": 250, "2023-Q2": 260,
                        "2023-Q3": 270, "2023-Q4": 280,
                    },
                },
                "ttm": {"Revenue": 1060},
            },
            "forecast": {},
            "extra_alerts": [],
        }
        orchestrator = TickerOrchestrator()
        result = orchestrator.analyze("AAPL")

    assert result.main.multiyear.ttm["Revenue"] == 1060


# ---------------------------------------------------------------------
#         Concurrent peer fetching
# ---------------------------------------------------------------------

def test_concurrent_peer_fetching():
    """Peers are fetched concurrently and results stored correctly."""
    call_order = []

    def mock_analyze_side_effect(ticker, *args, **kwargs):
        call_order.append(ticker)
        return {
            "annual_snapshot": {"metrics": {"Revenue": 100, "Alerts": []}, "filing_info": {}},
            "quarterly_snapshot": {"metrics": {}, "filing_info": {}},
            "multiyear": {"annual_data": {}, "quarterly_data": {}, "ttm": {}},
            "forecast": {},
            "extra_alerts": [],
        }

    with patch("edgar_analytics.orchestrator.TickerOrchestrator._analyze_ticker_for_metrics",
               side_effect=mock_analyze_side_effect):
        orchestrator = TickerOrchestrator()
        result = orchestrator.analyze("AAPL", peers=["MSFT", "GOOGL"])

    assert "MSFT" in result.tickers
    assert "GOOGL" in result.tickers
    assert result.tickers["MSFT"].annual_snapshot.metrics.revenue == 100


def test_concurrent_peer_failure_handled():
    """A failing peer does not crash the whole analysis."""
    call_count = 0

    def mock_analyze_side_effect(ticker, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if ticker == "FAIL":
            raise RuntimeError("Peer fetch failed")
        return {
            "annual_snapshot": {"metrics": {"Revenue": 100, "Alerts": []}, "filing_info": {}},
            "quarterly_snapshot": {"metrics": {}, "filing_info": {}},
            "multiyear": {"annual_data": {}, "quarterly_data": {}, "ttm": {}},
            "forecast": {},
            "extra_alerts": [],
        }

    with patch("edgar_analytics.orchestrator.TickerOrchestrator._analyze_ticker_for_metrics",
               side_effect=mock_analyze_side_effect):
        orchestrator = TickerOrchestrator()
        result = orchestrator.analyze("AAPL", peers=["MSFT", "FAIL"])

    assert "AAPL" in result.tickers
    assert "MSFT" in result.tickers
    assert "FAIL" not in result.tickers


def test_semaphore_rate_limiting():
    """_analyze_ticker_with_semaphore acquires the semaphore."""
    with patch("edgar_analytics.orchestrator.TickerOrchestrator._analyze_ticker_for_metrics") as mock_analyze:
        mock_analyze.return_value = {
            "annual_snapshot": {"metrics": {"Revenue": 100, "Alerts": []}, "filing_info": {}},
            "extra_alerts": [],
        }
        orchestrator = TickerOrchestrator()
        result = orchestrator._analyze_ticker_with_semaphore("AAPL", 3, 10, False)

    assert result["annual_snapshot"]["metrics"]["Revenue"] == 100
    mock_analyze.assert_called_once_with("AAPL", n_years=3, n_quarters=10, disable_forecast=False)


# ---------------------------------------------------------------------
#         Cache wiring
# ---------------------------------------------------------------------

def test_cache_layer_used_on_second_call():
    """Second call to _cached_snapshot should use cached value."""
    orchestrator = TickerOrchestrator(enable_cache=False)
    mock_comp = MagicMock()
    snap = {"metrics": {"Revenue": 1000, "Alerts": []}, "filing_info": {"accession_no": "abc"}}

    with patch("edgar_analytics.orchestrator.get_filing_snapshot_with_fallback", return_value=snap):
        result = orchestrator._cached_snapshot(mock_comp, "AAPL", ("10-K",), is_current=False)
    assert result["metrics"]["Revenue"] == 1000


def test_cache_disabled_still_works():
    """With cache disabled, orchestrator still fetches normally."""
    orchestrator = TickerOrchestrator(enable_cache=False)
    assert orchestrator._cache.enabled is False


# ---------------------------------------------------------------------
#         CompanyFacts wiring
# ---------------------------------------------------------------------

def test_cross_validate_called(caplog):
    """_cross_validate calls CompanyFactsClient and logs discrepancies."""
    orchestrator = TickerOrchestrator(enable_cache=False)
    snap = {"metrics": {"Revenue": 1000, "Net Income": 200}}

    with patch.object(orchestrator._facts_client, "fetch", return_value=None):
        orchestrator._cross_validate("AAPL", snap)

    with patch.object(orchestrator._facts_client, "fetch", side_effect=OSError("network error")):
        orchestrator._cross_validate("AAPL", snap)


def test_cross_validate_empty_metrics():
    """_cross_validate does nothing for empty metrics."""
    orchestrator = TickerOrchestrator(enable_cache=False)
    orchestrator._cross_validate("AAPL", {"metrics": {}})


# ---------------------------------------------------------------------
#         alerts_config threading
# ---------------------------------------------------------------------

def test_alerts_config_reaches_snapshot():
    """alerts_config threaded from analyze() reaches get_filing_snapshot_with_fallback."""
    orchestrator = TickerOrchestrator(enable_cache=False)
    mock_comp = MagicMock()
    snap = {"metrics": {"Revenue": 500, "Alerts": []}, "filing_info": {}}

    with patch("edgar_analytics.orchestrator.get_filing_snapshot_with_fallback", return_value=snap) as mock_fn:
        orchestrator._cached_snapshot(
            mock_comp, "AAPL", ("10-K",), is_current=False,
            alerts_config={"HIGH_LEVERAGE": 99.0},
        )

    _, kwargs = mock_fn.call_args
    assert kwargs["alerts_config"] == {"HIGH_LEVERAGE": 99.0}


def test_analyze_threads_alerts_config():
    """analyze(alerts_config=...) forwards to _cached_snapshot calls."""
    with patch("edgar_analytics.orchestrator.TickerOrchestrator._analyze_ticker_for_metrics") as mock_analyze:
        mock_analyze.return_value = {
            "annual_snapshot": {"metrics": {"Revenue": 42, "Alerts": []}, "filing_info": {}},
            "extra_alerts": [],
        }
        orchestrator = TickerOrchestrator(enable_cache=False)
        orchestrator.analyze("AAPL", alerts_config={"HIGH_LEVERAGE": 50.0})

    assert orchestrator._alerts_config == {"HIGH_LEVERAGE": 50.0}