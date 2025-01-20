"""
orchestrator.py

Coordinates the entire EDGAR-based analysis: validating tickers,
fetching data, computing metrics, multi-year analysis, forecasting,
and final reporting.
"""

import re
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


class TickerDetector:
    """
    Manages detection/validation of valid public company ticker symbols (regex-based).
    Allows BFS search for known patterns e.g. 'AAPL', 'BRK.B', 'NGG.L'.
    """

    _TICKER_REGEX = re.compile(r"\b[A-Z]{1,5}(?:[.\-][A-Z0-9]{1,4})?\b")
    _TICKER_FULLMATCH_REGEX = re.compile(r"^[A-Z]{1,5}(?:[.\-][A-Z0-9]{1,4})?$")

    @classmethod
    def search(cls, text: str):
        """
        Find a ticker-like substring in TEXT using _TICKER_REGEX. Return a re.Match or None.
        """
        if not isinstance(text, str):
            raise ValueError("Input must be a string for TickerDetector.search().")
        return cls._TICKER_REGEX.search(text)

    @classmethod
    def validate_ticker_symbol(cls, ticker: str) -> bool:
        """
        Validate entire string is a valid ticker. 1-5 letters + optional . or - suffix.
        """
        if not isinstance(ticker, str):
            raise ValueError("Ticker must be a string.")
        return bool(cls._TICKER_FULLMATCH_REGEX.fullmatch(ticker))


class TickerOrchestrator:
    """
    High-level orchestrator for EDGAR analysis:
      - Validate main ticker + peers
      - Gather annual & quarterly snapshots
      - Retrieve multi-year data, run forecasts
      - Summarize results with ReportingEngine
    """

    def __init__(self) -> None:
        self.logger: logging.Logger = get_logger(self.__class__.__name__)
        self.reporting_engine = ReportingEngine()

    def analyze_company(
        self,
        ticker: str,
        peers: List[str],
        csv_path: Optional[str] = None
    ) -> None:
        """
        Main entry to analyze TICKER plus optional peer tickers. 
        Summarize results in logs & optional CSV.
        """
        if not TickerDetector.validate_ticker_symbol(ticker):
            self.logger.error("Invalid main ticker: %s", ticker)
            return

        set_identity("Your Name <your.email@example.com>")
        self.logger.info("Analyzing company: %s", ticker)

        metrics_map: Dict[str, Dict[str, Any]] = {}
        main_data = self._analyze_ticker_for_metrics(ticker)
        metrics_map[ticker] = main_data

        self.logger.info("Comparing %s with peers: %s", ticker, peers)
        for peer in peers:
            if TickerDetector.validate_ticker_symbol(peer):
                peer_data = self._analyze_ticker_for_metrics(peer)
                metrics_map[peer] = peer_data
            else:
                self.logger.warning("Skipping invalid peer ticker: %s", peer)

        self.reporting_engine.summarize_metrics_table(metrics_map=metrics_map, main_ticker=ticker, csv_path=csv_path)
        self.logger.info("Analysis complete. Check logs or CSV if provided.")

    def _analyze_ticker_for_metrics(self, ticker: str) -> Dict[str, Any]:
        """
        For a single ticker: gather latest 10-K, 10-Q, multi-year data, forecast, 
        plus quarterly-based alerts. Return a dictionary of all results.
        """
        self.logger.info("Analyzing ticker: %s", ticker)
        try:
            comp = Company(ticker)
        except Exception as exc:
            self.logger.exception("Failed to create Company object for %s: %s", ticker, exc)
            return {}

        annual_snap = get_single_filing_snapshot(comp, "10-K")
        quarterly_snap = get_single_filing_snapshot(comp, "10-Q")

        multi_data = retrieve_multi_year_data(ticker, n_years=3, n_quarters=10)
        rev_annual = multi_data.get("annual_data", {}).get("Revenue", {})
        rev_quarterly = multi_data.get("quarterly_data", {}).get("Revenue", {})

        annual_fc = forecast_revenue_arima(rev_annual, is_quarterly=False)
        quarterly_fc = forecast_revenue_arima(rev_quarterly, is_quarterly=True)

        quarterly_info = analyze_quarterly_balance_sheets(comp, n_quarters=10)
        extra_alerts = check_additional_alerts_quarterly(quarterly_info)

        return {
            "annual_snapshot": annual_snap,
            "quarterly_snapshot": quarterly_snap,
            "multiyear": multi_data,
            "forecast": {
                "annual_rev_forecast": annual_fc,
                "quarterly_rev_forecast": quarterly_fc,
            },
            "extra_alerts": extra_alerts,
        }
