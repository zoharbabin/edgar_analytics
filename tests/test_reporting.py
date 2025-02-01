"""
tests/test_reporting.py

Tests for the edgar_analytics.reporting module (ReportingEngine).
This file covers CSV export, alert/warning logs, negative CAGR scenarios, etc.
"""

import pytest
from unittest.mock import patch
from pathlib import Path

from edgar_analytics.reporting import ReportingEngine
import pandas as pd


def test_summarize_metrics_table_no_csv(dummy_metrics_map):
    """
    If csv_path is None, we expect:
     - no CSV writing attempts
     - no log about CSV saving
    """
    reporting_engine = ReportingEngine()
    with patch("pandas.DataFrame.to_csv") as mock_to_csv, \
         patch.object(reporting_engine.logger, "info") as mock_info:

        reporting_engine.summarize_metrics_table(
            metrics_map=dummy_metrics_map,
            main_ticker="AAPL",
            csv_path=None
        )
        mock_to_csv.assert_not_called()

        # Check the logger's info messages
        infos = [call.args[0] for call in mock_info.call_args_list]
        assert not any("saved to" in msg for msg in infos), (
            "Should NOT log about CSV saving if csv_path is None."
        )


def test_summarize_metrics_table_with_csv(tmp_path, dummy_metrics_map):
    """
    If csv_path is provided, ensure:
     - directories are created (via Path.mkdir)
     - to_csv is called
     - logger mentions saving
    """
    
    reporting_engine = ReportingEngine()
    outdir = tmp_path / "outputs"
    outdir.mkdir(exist_ok=True)
    csv_path = outdir / "summary.csv"
    
    with patch.object(Path, "mkdir") as mock_mkdir, \
         patch("pandas.DataFrame.to_csv") as mock_to_csv, \
         patch.object(reporting_engine.logger, "info") as mock_info:

        reporting_engine.summarize_metrics_table(
            metrics_map=dummy_metrics_map,
            main_ticker="AAPL",
            csv_path=str(csv_path)
        )

        mock_mkdir.assert_called_with(parents=True, exist_ok=True)
        mock_to_csv.assert_called_once_with(csv_path.resolve(), index=True)

        info_msgs = [call.args[0] for call in mock_info.call_args_list]
        # or for call in mock_info.call_args_list: call.args => the format string & call.args[1:] => params
        assert any("Snapshot summary saved to" in msg for msg in info_msgs), "Should log about CSV saving."


def test_summarize_metrics_table_empty_data(empty_metrics_map):
    """
    If we pass an empty map, we expect:
     - no to_csv calls
     - a log about no or empty data
    """
    reporting_engine = ReportingEngine()
    with patch("pandas.DataFrame.to_csv") as mock_to_csv, \
         patch.object(reporting_engine.logger, "info") as mock_info:

        reporting_engine.summarize_metrics_table(
            metrics_map=empty_metrics_map,
            main_ticker="FAKE"
        )
        mock_to_csv.assert_not_called()

        info_msgs = [call.args[0] for call in mock_info.call_args_list]
        assert any("No snapshot data" in msg or "empty" in msg for msg in info_msgs), (
            "Should log about empty data if metrics_map is empty."
        )


def test_summarize_metrics_table_alerts_triggers(dummy_metrics_map):
    """
    If certain data triggers alerts or has extra_alerts, it should log as warnings.
    For instance, AAPL has a high Debt-to-Equity, and an extra_alert for receivables.
    """
    reporting_engine = ReportingEngine()
    with patch.object(reporting_engine.logger, "warning") as mock_warn:
        reporting_engine.summarize_metrics_table(
            metrics_map=dummy_metrics_map,
            main_ticker="AAPL",
            csv_path=None
        )
        calls = mock_warn.call_args_list

        found_alert_call = False

        for call_args in calls:
            if not call_args.args:
                continue
            format_str = call_args.args[0]
            log_params = call_args.args[1:]
            expanded_message = format_str % log_params
            if "Alerts for AAPL:" in expanded_message:
                found_alert_call = True

        assert found_alert_call, (
            "Expected an alerts call mentioning 'Alerts for AAPL'."
        )


def test_log_multi_year_negative_cagr(caplog):
    """
    Provide multi-year data that yields a negative CAGR, ensuring the
    'Overall revenue has contracted' branch is hit.
    """
    reporting_engine = ReportingEngine()
    # earliest year= 2020 => 1000, latest year= 2023 => 500 => negative CAGR
    metrics_map = {
        "FAKE": {
            "multiyear": {
                "annual_data": {"Revenue": {"2020": 1000, "2023": 500}},
                "yoy_revenue_growth": {},
                "cagr_revenue": -20.0,
            },
            "forecast": {
                "annual_rev_forecast": 0.0,
                "quarterly_rev_forecast": 0.0,
            }
        }
    }

    with caplog.at_level("INFO", logger="edgar_analytics.reporting"):
        # changed from _log_multi_year_and_forecast => _show_multi_year_and_forecast
        reporting_engine._show_multi_year_and_forecast(metrics_map)

    assert "Overall revenue has contracted" in caplog.text, (
        "Expected negative CAGR log message."
    )
