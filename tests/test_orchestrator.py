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

    # Check logs: we should see 'Analyzing company: AAPL' and 'Comparing AAPL with peers: []'
    logs = caplog.text
    assert "Analyzing company: AAPL" in logs, "Expected 'Analyzing company: AAPL' in logs."
    assert "Comparing AAPL with peers: []" in logs, "Expected 'Comparing AAPL with peers: []' in logs."


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
         caplog.at_level(logging.WARNING, logger="edgar_analytics.orchestrator"):
        mock_company.return_value = MagicMock()

        orchestrator = TickerOrchestrator()
        orchestrator.analyze_company("AAPL", peers=["@@@", "MSFT"])

    logs = caplog.text
    assert "Skipping invalid peer ticker: @@@" in logs, "Should log a warning about invalid peer."


def test_analyze_company_exception_in_creation(caplog):
    """
    If creating the Company object raises an Exception, it should log an error
    and skip further processing.
    """
    with patch("edgar_analytics.orchestrator.Company", side_effect=Exception("Creation error")):
        orchestrator = TickerOrchestrator()
        orchestrator.analyze_company("AAPL", peers=[])

    assert "Failed to create Company object for AAPL: Creation error" in caplog.text


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