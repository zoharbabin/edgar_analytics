# tests/test_cli.py

import pytest
from click.testing import CliRunner
from edgar_analytics.cli import main

@pytest.fixture
def runner():
    return CliRunner()

def test_cli_no_peers(runner, caplog):
    """
    Test the CLI with a single ticker and no peers.
    """
    result = runner.invoke(main, ["AAPL"])
    assert result.exit_code == 0  
    assert "Analyzing company: AAPL" in caplog.text

def test_cli_with_peers(runner, caplog):
    """
    Test the CLI with multiple peers.
    """
    result = runner.invoke(main, ["AAPL", "MSFT", "GOOGL"])
    assert result.exit_code == 0
    assert "Comparing AAPL with peers: ['MSFT', 'GOOGL']" in caplog.text

def test_cli_with_csv(runner, tmp_path, caplog):
    """
    Test the CLI while passing a csv output path.
    """
    csv_file = tmp_path / "out.csv"
    result = runner.invoke(main, ["AAPL", "MSFT", "--csv", str(csv_file)])
    assert result.exit_code == 0
    assert csv_file.exists()
    assert "Snapshot summary saved to" in caplog.text

def test_cli_invalid_ticker(runner, caplog):
    """
    Test the CLI with an invalid ticker to ensure error handling.
    """
    result = runner.invoke(main, ["@BADTICKER"])
    assert result.exit_code == 0  # Depending on how you handle errors
    assert "Invalid main ticker: @BADTICKER" in caplog.text
