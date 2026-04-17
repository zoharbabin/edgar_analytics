"""
tests/conftest.py

Shared fixtures for the edgar_analytics test suite.
Pytest will automatically discover these fixtures for any test
in this directory or subdirectories.
"""

import logging
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that hit real EDGAR API",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-integration"):
        return
    skip_integration = pytest.mark.skip(reason="needs --run-integration to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


@pytest.fixture(autouse=True)
def _reset_logging_handlers():
    """Ensure logging handlers are cleaned up between tests to prevent
    handler accumulation and file descriptor leaks."""
    yield
    edgar_logger = logging.getLogger("edgar_analytics")
    for handler in edgar_logger.handlers[:]:
        handler.flush()
        handler.close()
    edgar_logger.handlers.clear()


@pytest.fixture
def dummy_metrics_map():
    """
    Example fixture returning a dictionary structure that the summarizing logic expects.
    Each ticker's 'annual_snapshot'/'quarterly_snapshot' can mimic what the orchestrator
    might produce, plus 'extra_alerts'.
    """
    return {
        "AAPL": {
            "annual_snapshot": {
                "metrics": {
                    "Revenue": 394328000000.0,
                    "Net Income": 99803000000.0,
                    "Debt-to-Equity": 4.67,
                    "Alerts": ["Debt-to-Equity above 3.0 => High leverage!"],
                },
                "filing_info": {
                    "form_type": "10-K",
                    "filed_date": "2024-11-01",
                },
            },
            "quarterly_snapshot": {},
            "extra_alerts": [
                "Receivables spiked +30% from previous quarter"
            ],
        },
        "MSFT": {
            "annual_snapshot": {
                "metrics": {
                    "Revenue": 198270000000.0,
                },
                "filing_info": {
                    "form_type": "10-K",
                    "filed_date": "2024-07-30",
                },
            },
            "quarterly_snapshot": {},
            "extra_alerts": [],
        },
    }


@pytest.fixture
def empty_metrics_map():
    """Returns an empty dict, simulating zero data available in metrics_map."""
    return {}
