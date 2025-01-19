"""
orchestrator.py

This module orchestrates the entire EDGAR ticker analysis process. It validates
tickers, retrieves data, and calls into other modules (e.g., metrics, forecasting,
multi_period_analysis) to obtain results. It then delegates presentation/reporting
responsibilities to reporting.py.
"""

import logging
from typing import Dict, Any, List, Optional

from edgar import Company, set_identity

from .data_utils import get_logger
from .metrics import get_single_filing_snapshot
from .forecasting import forecast_revenue_arima
from .multi_period_analysis import (
    retrieve_multi_year_data,
    analyze_quarterly_balance_sheets,
    check_additional_alerts_quarterly,
)
from .reporting import ReportingEngine


def validate_ticker_symbol(ticker: str) -> bool:
    """
    Validate ticker symbols to prevent misuse or injection-like strings.

    Parameters
    ----------
    ticker : str
        A company's ticker symbol.

    Returns
    -------
    bool
        True if the ticker is deemed valid, False otherwise.
    """
    return 1 <= len(ticker) <= 10 and ticker.isalnum()


class TickerOrchestrator:
    """
    A high-level orchestrator for EDGAR-based financial metrics.

    Responsibilities:
    - Validate tickers.
    - Gather data from various modules (annual, quarterly snapshots, multi-year).
    - Integrate forecasting results.
    - Collect any alerts.
    - Delegate final reporting to ReportingEngine.
    """

    def __init__(self) -> None:
        """Initialize the orchestrator with a dedicated logger and reporting engine."""
        self.logger: logging.Logger = get_logger(self.__class__.__name__)
        self.reporting_engine = ReportingEngine()

    def analyze_company(
        self,
        ticker: str,
        peers: List[str],
        csv_path: Optional[str] = None
    ) -> None:
        """
        Entry point to orchestrate analysis for one main ticker plus a list of peers.

        Parameters
        ----------
        ticker : str
            The primary ticker symbol.
        peers : List[str]
            A list of peer ticker symbols for comparison.
        csv_path : Optional[str]
            File path to save the CSV summary. If None, no CSV is created.

        Returns
        -------
        None
        """
        if not validate_ticker_symbol(ticker):
            self.logger.error("Invalid main ticker: %s", ticker)
            return

        # Setting identity for external EDGAR library
        set_identity("Your Name <your.email@example.com>")
        self.logger.info("Analyzing company: %s", ticker)

        metrics_map: Dict[str, Dict[str, Any]] = {}
        main_data = self._analyze_ticker_for_metrics(ticker)
        metrics_map[ticker] = main_data

        self.logger.info("Comparing %s with peers: %s", ticker, peers)
        for peer in peers:
            if validate_ticker_symbol(peer):
                peer_data = self._analyze_ticker_for_metrics(peer)
                metrics_map[peer] = peer_data
            else:
                self.logger.warning("Skipping invalid peer ticker: %s", peer)

        self.reporting_engine.summarize_metrics_table(
            metrics_map=metrics_map,
            main_ticker=ticker,
            csv_path=csv_path
        )
        self.logger.info(
            "Analysis complete. Refer to logs or the CSV output if provided."
        )

    def _analyze_ticker_for_metrics(self, ticker: str) -> Dict[str, Any]:
        """
        Retrieve analysis data for a single ticker. This includes:
          1) Latest 10-K + 10-Q snapshots
          2) Multi-year data retrieval
          3) Forecasting (annual & quarterly)
          4) Additional quarterly-based alerts

        Parameters
        ----------
        ticker : str
            The company's ticker symbol.

        Returns
        -------
        Dict[str, Any]
            A dictionary containing annual_snapshot, quarterly_snapshot,
            multiyear data, forecasts, and extra_alerts.
        """
        self.logger.info("Analyzing ticker: %s", ticker)

        try:
            comp = Company(ticker)
        except Exception as exc:
            self.logger.exception(
                "Failed to create Company object for %s: %s",
                ticker, exc
            )
            return {}

        # Latest snapshots
        annual_snap = get_single_filing_snapshot(comp, "10-K")
        quarterly_snap = get_single_filing_snapshot(comp, "10-Q")

        # Multi-year data & revenue forecasts
        multi_data = retrieve_multi_year_data(ticker, n_years=3, n_quarters=10)
        rev_annual = multi_data.get("annual_data", {}).get("Revenue", {})
        rev_quarterly = multi_data.get("quarterly_data", {}).get("Revenue", {})

        annual_forecast = forecast_revenue_arima(
            rev_annual, is_quarterly=False
        )
        quarterly_forecast = forecast_revenue_arima(
            rev_quarterly, is_quarterly=True
        )

        # Additional quarterly-based alerts
        quarterly_info = analyze_quarterly_balance_sheets(comp, n_quarters=10)
        extra_alerts = check_additional_alerts_quarterly(quarterly_info)

        return {
            "annual_snapshot": annual_snap,
            "quarterly_snapshot": quarterly_snap,
            "multiyear": multi_data,
            "forecast": {
                "annual_rev_forecast": annual_forecast,
                "quarterly_rev_forecast": quarterly_forecast,
            },
            "extra_alerts": extra_alerts,
        }

