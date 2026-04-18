# tests/test_cli.py

import logging
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from edgar_analytics.cli import main
from edgar_analytics.logging_utils import configure_logging
from edgar_analytics.orchestrator import TickerFetchError

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def mock_company():
    """Returns a mocked Company object with no real network calls."""
    mock_comp = MagicMock()
    # e.g. no real filings fetched
    mock_comp.get_filings.return_value.head.return_value = []
    return mock_comp

@pytest.fixture
def mock_multifin():
    """
    Returns a mock for 'edgar.MultiFinancials' so it doesn't do
    real XBRL parsing or network calls.
    """
    mock_mf = MagicMock()
    # Provide trivial or None returns
    mock_mf.income_statement = None
    mock_mf.balance_sheet = None
    mock_mf.cash_flow_statement = None
    return mock_mf

@pytest.fixture(autouse=True)
def _setup_logging():
    """Configure logging before each test."""
    configure_logging("INFO", suppress_logs=False)

@patch("edgar_analytics.orchestrator.set_identity")
@patch("edgar_analytics.multi_period_analysis.Company")
@patch("edgar_analytics.multi_period_analysis.MultiFinancials")
@patch("edgar_analytics.orchestrator.Company")
@pytest.mark.slow
def test_cli_no_peers(
    mock_OrcCompany,
    mock_MultiFinancials,
    mock_MPACompany,
    mock_set_identity,
    mock_company,
    mock_multifin,
    runner,
    caplog
):
    mock_OrcCompany.return_value = mock_company
    mock_MPACompany.return_value = mock_company
    mock_MultiFinancials.return_value = mock_multifin

    with caplog.at_level(logging.INFO, logger="edgar_analytics.orchestrator"):
        result = runner.invoke(main, ["AAPL"])
        assert result.exit_code == 0
        assert "Analyzing company: AAPL" in caplog.text


@patch("edgar_analytics.orchestrator.set_identity")
@patch("edgar_analytics.multi_period_analysis.Company")
@patch("edgar_analytics.multi_period_analysis.MultiFinancials")
@patch("edgar_analytics.orchestrator.Company")
def test_cli_with_peers(
    mock_OrcCompany,
    mock_MultiFinancials,
    mock_MPACompany,
    mock_set_identity,
    mock_company,
    mock_multifin,
    runner,
    caplog
):
    mock_OrcCompany.return_value = mock_company
    mock_MPACompany.return_value = mock_company
    mock_MultiFinancials.return_value = mock_multifin

    result = runner.invoke(main, ["AAPL", "MSFT", "GOOGL"])
    assert result.exit_code == 0
    assert "Analyzing company: AAPL" in caplog.text


@patch("edgar_analytics.orchestrator.set_identity")
@patch("edgar_analytics.multi_period_analysis.Company")
@patch("edgar_analytics.multi_period_analysis.MultiFinancials")
@patch("edgar_analytics.orchestrator.Company")
def test_cli_with_csv(
    mock_OrcCompany,
    mock_MultiFinancials,
    mock_MPACompany,
    mock_set_identity,
    mock_company,
    mock_multifin,
    runner,
    tmp_path,
    caplog
):
    mock_OrcCompany.return_value = mock_company
    mock_MPACompany.return_value = mock_company
    mock_MultiFinancials.return_value = mock_multifin

    csv_file = tmp_path / "out.csv"
    with caplog.at_level(logging.INFO, logger="edgar_analytics.reporting"):
        result = runner.invoke(main, ["AAPL", "MSFT", "--csv", str(csv_file)])
        assert result.exit_code == 0
        assert csv_file.exists(), "CSV file was not created"
        assert "Snapshot summary saved to" in caplog.text


@patch("edgar_analytics.orchestrator.set_identity")
@patch("edgar_analytics.multi_period_analysis.Company")
@patch("edgar_analytics.multi_period_analysis.MultiFinancials")
@patch("edgar_analytics.orchestrator.Company")
def test_cli_invalid_ticker(
    mock_OrcCompany,
    mock_MultiFinancials,
    mock_MPACompany,
    mock_set_identity,
    mock_company,
    mock_multifin,
    runner,
    caplog
):
    mock_OrcCompany.return_value = mock_company
    mock_MPACompany.return_value = mock_company
    mock_MultiFinancials.return_value = mock_multifin

    with caplog.at_level(logging.ERROR, logger="edgar_analytics.cli"):
        result = runner.invoke(main, ["@BADTICKER"])
    assert result.exit_code == 1
    assert "Invalid ticker symbol" in caplog.text


@patch("edgar_analytics.orchestrator.set_identity")
@patch("edgar_analytics.orchestrator.Company")
def test_cli_catches_ticker_fetch_error(
    mock_OrcCompany,
    mock_set_identity,
    runner,
    caplog,
):
    mock_OrcCompany.side_effect = TickerFetchError("Could not resolve FAKE")
    with caplog.at_level(logging.ERROR, logger="edgar_analytics.cli"):
        result = runner.invoke(main, ["FAKE"])
    assert result.exit_code == 1
    assert "Could not resolve FAKE" in caplog.text
