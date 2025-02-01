# edgar_analytics/__init__.py

"""
edgar_analytics
===============

A library for analyzing SEC EDGAR filings, computing financial metrics,
forecasting revenues, and generating insightful summaries for investors
and analysts.

Modules
-------
- config: Configuration constants and settings.
- synonyms: Master synonyms dictionary for financial concepts.
- logging_utils: Logging configuration utilities.
- data_utils: DataFrame and parsing helper functions.
- synonyms_utils: Utilities for handling synonyms in financial data.
- metrics: Functions for computing financial ratios and metrics.
- forecasting: Revenue forecasting using a strategy-based approach (ARIMA by default).
- multi_period_analysis: Multi-year and quarterly trend analysis.
- orchestrator: High-level class orchestrating the entire analysis flow.
- reporting: Presentation, logging, and CSV export of analysis results.
- cli: Command-line interface for the library.
"""

from .synonyms import SYNONYMS
from .metrics import compute_ratios_and_metrics, get_single_filing_snapshot
from .forecasting import forecast_revenue, ForecastStrategy, ArimaForecastStrategy
from .multi_period_analysis import (
    retrieve_multi_year_data,
    analyze_quarterly_balance_sheets,
    check_additional_alerts_quarterly,
)
from .synonyms_utils import (
    find_synonym_value,
    flip_sign_if_negative_expense,
    compute_capex_single_period,
    compute_capex_for_column,
)
from .data_utils import (
    parse_period_label,
    custom_float_format,
    ensure_dataframe,
    make_numeric_df
)
from .orchestrator import TickerOrchestrator
from .reporting import ReportingEngine

__all__ = [
    "SYNONYMS",
    "compute_ratios_and_metrics",
    "get_single_filing_snapshot",
    "forecast_revenue",
    "ForecastStrategy",
    "ArimaForecastStrategy",
    "retrieve_multi_year_data",
    "analyze_quarterly_balance_sheets",
    "check_additional_alerts_quarterly",
    "find_synonym_value",
    "flip_sign_if_negative_expense",
    "compute_capex_single_period",
    "compute_capex_for_column",
    "parse_period_label",
    "custom_float_format",
    "ensure_dataframe",
    "make_numeric_df",
    "TickerOrchestrator",
    "ReportingEngine",
]