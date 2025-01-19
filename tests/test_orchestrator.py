"""
tests/test_orchestrator.py

Tests for orchestrator.py (TickerOrchestrator). 
We mock external Edgar calls, forecast calls, etc., to avoid real network operations.
ReportingEngine tests have been moved to test_reporting.py.
"""

import pytest
from unittest.mock import patch
from pathlib import Path

from edgar_analytics.orchestrator import TickerOrchestrator
from edgar_analytics.reporting import ReportingEngine


def test_analyze_company_basic(caplog):
    """
    Verify that orchestrator logs "Analyzing company: AAPL"
    and logs "Comparing AAPL with peers: []" even if no peers.
    """
    with patch("edgar_analytics.orchestrator.TickerOrchestrator._analyze_ticker_for_metrics") as mock_analyze, \
         patch("edgar_analytics.reporting.ReportingEngine.summarize_metrics_table") as mock_summary:

        mock_analyze.return_value = {
            "annual_snapshot": {"metrics": {"Revenue": 123, "Alerts": []}},
            "extra_alerts": []
        }

        orchestrator = TickerOrchestrator()
        orchestrator.analyze_company("AAPL", peers=[], csv_path=None)

    # Check logs
    assert "Analyzing company: AAPL" in caplog.text, (
        "Expected 'Analyzing company: AAPL' in logs."
    )
    assert "Comparing AAPL with peers: []" in caplog.text, (
        "Expected 'Comparing AAPL with peers: []' in logs."
    )


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


def test_analyze_company_invalid_peer(caplog):
    """
    Invalid peer scenario: should log a warning and skip that peer.
    """
    orchestrator = TickerOrchestrator()
    orchestrator.analyze_company("AAPL", peers=["@@@", "MSFT"])

    # Check logs
    assert "Skipping invalid peer ticker: @@@" in caplog.text


def test_analyze_company_exception_in_creation(caplog):
    """
    If creating the Company object raises an Exception, it should log an error
    and skip further processing.
    """
    with patch("edgar_analytics.orchestrator.Company", side_effect=Exception("Creation error")):
        orchestrator = TickerOrchestrator()
        orchestrator.analyze_company("AAPL", peers=[])

    assert "Failed to create Company object for AAPL: Creation error" in caplog.text
