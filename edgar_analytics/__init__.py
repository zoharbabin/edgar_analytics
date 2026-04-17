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
"""

__version__ = "0.9.0"

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
from .orchestrator import TickerOrchestrator, EdgarAnalyticsError, TickerFetchError
from .scores import (
    PerShareMetrics,
    WorkingCapitalCycle,
    CapitalEfficiency,
    DuPontDecomposition,
    PiotroskiScore,
    AltmanZScore,
    BeneishMScore,
)
from .forecasting import ForecastStrategy, ArimaForecastStrategy
from .market_data import ValuationRatios


def analyze(
    ticker: str,
    peers=None,
    n_years: int = 3,
    n_quarters: int = 10,
    disable_forecast: bool = False,
    identity=None,
    alerts_config=None,
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
    :param alerts_config: Optional dict of alert threshold overrides
        (e.g. ``{"HIGH_LEVERAGE": 5.0}``).
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
        alerts_config=alerts_config,
    )


__all__ = [
    # Version
    "__version__",
    # Public entry point
    "analyze",
    # Result types
    "AnalysisResult",
    "TickerAnalysis",
    "FilingSnapshot",
    "SnapshotMetrics",
    "ScoresResult",
    "FilingInfo",
    "MultiYearData",
    "ForecastResult",
    # Orchestrator
    "TickerOrchestrator",
    # Exceptions
    "EdgarAnalyticsError",
    "TickerFetchError",
    # Scoring model dataclasses
    "PerShareMetrics",
    "WorkingCapitalCycle",
    "CapitalEfficiency",
    "DuPontDecomposition",
    "PiotroskiScore",
    "AltmanZScore",
    "BeneishMScore",
    # Forecasting (strategy extensibility)
    "ForecastStrategy",
    "ArimaForecastStrategy",
    # Valuation
    "ValuationRatios",
]