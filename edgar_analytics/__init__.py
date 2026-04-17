# edgar_analytics/__init__.py

"""
edgar_analytics
===============

A library for analyzing SEC EDGAR filings, computing financial metrics,
forecasting revenues, and generating insightful summaries for investors
and analysts.

Quick start (programmatic)::

    import edgar_analytics as ea

    result = ea.analyze("AAPL", peers=["MSFT", "GOOGL"])
    print(result.main.annual_snapshot.metrics.revenue)
    print(result["MSFT"].annual_snapshot.metrics.net_margin_pct)

Modules
-------
- models: Typed dataclass results (AnalysisResult, TickerAnalysis, SnapshotMetrics, …).
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

from .models import (
    AnalysisResult,
    TickerAnalysis,
    FilingSnapshot,
    SnapshotMetrics,
    ScoresResult,
    FilingInfo,
    MultiYearData,
    ForecastResult,
)
from .synonyms import SYNONYMS
from .metrics import (
    compute_ratios_and_metrics,
    get_single_filing_snapshot,
    get_filing_snapshot_with_fallback,
    get_prior_annual_metrics,
    ANNUAL_FORM_TYPES,
    QUARTERLY_FORM_TYPES,
)
from .forecasting import forecast_revenue, ForecastStrategy, ArimaForecastStrategy
from .multi_period_analysis import (
    retrieve_multi_year_data,
    analyze_quarterly_balance_sheets,
    check_additional_alerts_quarterly,
)
from .synonyms_utils import (
    find_synonym_value,
    find_best_synonym_row,
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
from .market_data import get_market_cap, get_share_price, HAS_YFINANCE
from .cache import CacheLayer, HAS_DISKCACHE
from .company_facts import CompanyFactsClient
from .scores import (
    PerShareMetrics,
    WorkingCapitalCycle,
    CapitalEfficiency,
    DuPontDecomposition,
    PiotroskiScore,
    AltmanZScore,
    BeneishMScore,
    compute_ttm,
    compute_all_scores,
    run_dqc_checks,
)


def analyze(
    ticker: str,
    peers=None,
    n_years: int = 3,
    n_quarters: int = 10,
    disable_forecast: bool = False,
    identity=None,
) -> AnalysisResult:
    """Run a full EDGAR analysis and return structured results.

    This is the recommended entry point for programmatic usage::

        import edgar_analytics as ea
        result = ea.analyze("AAPL", peers=["MSFT"])
        print(result.main.annual_snapshot.metrics.revenue)

    :param ticker: Main company ticker symbol (e.g. ``"AAPL"``).
    :param peers: Optional list of peer ticker symbols.
    :param n_years: Number of annual filings to retrieve (default 3).
    :param n_quarters: Number of quarterly filings to retrieve (default 10).
    :param disable_forecast: Skip ARIMA revenue forecasting.
    :param identity: SEC EDGAR identity string (``"Name <email>"``).
    :returns: An :class:`AnalysisResult` with typed fields for every ticker.
    """
    orchestrator = TickerOrchestrator()
    return orchestrator.analyze(
        ticker=ticker,
        peers=peers,
        n_years=n_years,
        n_quarters=n_quarters,
        disable_forecast=disable_forecast,
        identity=identity,
    )


__all__ = [
    # Public API
    "analyze",
    "AnalysisResult",
    "TickerAnalysis",
    "FilingSnapshot",
    "SnapshotMetrics",
    "ScoresResult",
    "FilingInfo",
    "MultiYearData",
    "ForecastResult",
    # Orchestrator & Reporting
    "TickerOrchestrator",
    "ReportingEngine",
    # Metrics
    "SYNONYMS",
    "compute_ratios_and_metrics",
    "get_single_filing_snapshot",
    "get_filing_snapshot_with_fallback",
    "get_prior_annual_metrics",
    "ANNUAL_FORM_TYPES",
    "QUARTERLY_FORM_TYPES",
    # Forecasting
    "forecast_revenue",
    "ForecastStrategy",
    "ArimaForecastStrategy",
    # Multi-period
    "retrieve_multi_year_data",
    "analyze_quarterly_balance_sheets",
    "check_additional_alerts_quarterly",
    # Utilities
    "find_synonym_value",
    "find_best_synonym_row",
    "flip_sign_if_negative_expense",
    "compute_capex_single_period",
    "compute_capex_for_column",
    "parse_period_label",
    "custom_float_format",
    "ensure_dataframe",
    "make_numeric_df",
    # Scoring models
    "PerShareMetrics",
    "WorkingCapitalCycle",
    "CapitalEfficiency",
    "DuPontDecomposition",
    "PiotroskiScore",
    "AltmanZScore",
    "BeneishMScore",
    "compute_ttm",
    "compute_all_scores",
    "run_dqc_checks",
    # Market data
    "get_market_cap",
    "get_share_price",
    "HAS_YFINANCE",
    # Caching
    "CacheLayer",
    "HAS_DISKCACHE",
    # CompanyFacts validation
    "CompanyFactsClient",
]