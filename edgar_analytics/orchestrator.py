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

from .logging_utils import get_logger
from .reporting import ReportingEngine
from .metrics import get_single_filing_snapshot
from .forecasting import forecast_revenue
from .multi_period_analysis import (
    retrieve_multi_year_data,
    analyze_quarterly_balance_sheets,
    check_additional_alerts_quarterly,
)

logger = get_logger(__name__)


class TickerDetector:
    """
    Manages detection/validation of valid public company ticker symbols (regex-based).
    Allows BFS search for known patterns e.g., 'AAPL', 'BRK.B', 'NGG.L'.
    """

    _TICKER_REGEX = re.compile(r"\b[A-Z]{1,5}(?:[.\-][A-Z0-9]{1,4})?\b")
    _TICKER_FULLMATCH_REGEX = re.compile(r"^[A-Z]{1,5}(?:[.\-][A-Z0-9]{1,4})?$")

    @classmethod
    def search(cls, text: str):
        if not isinstance(text, str):
            raise ValueError("Input must be a string for TickerDetector.search().")
        return cls._TICKER_REGEX.search(text)

    @classmethod
    def validate_ticker_symbol(cls, ticker: str) -> bool:
        if ticker is None:
            raise ValueError("Ticker must not be None.")
        if not isinstance(ticker, str):
            raise ValueError("Ticker must be a string.")
        return bool(cls._TICKER_FULLMATCH_REGEX.fullmatch(ticker))


class TickerOrchestrator:
    """
    High-level orchestrator for EDGAR analysis:
      - Validate main ticker + optional peers
      - Gather annual & quarterly snapshots
      - Retrieve multi-year data, optionally run forecast
      - Summarize results with a ReportingEngine
    """

    def __init__(self) -> None:
        self.logger = logger
        self.reporting_engine = ReportingEngine()

    def analyze_company(
        self,
        ticker: str,
        peers: List[str],
        csv_path: Optional[str] = None,
        n_years: int = 3,
        n_quarters: int = 10,
        disable_forecast: bool = False,
        identity: Optional[str] = None
    ) -> None:
        if not TickerDetector.validate_ticker_symbol(ticker):
            self.logger.error("Invalid main ticker: %s", ticker)
            return

        if identity:
            set_identity(identity)
        else:
            set_identity("Your Name <your.email@example.com>")

        self.logger.info("Analyzing company: %s", ticker)

        metrics_map: Dict[str, Dict[str, Any]] = {}
        main_data = self._analyze_ticker_for_metrics(
            ticker,
            n_years=n_years,
            n_quarters=n_quarters,
            disable_forecast=disable_forecast
        )
        metrics_map[ticker] = main_data

        # Because the test expects EXACT string "Comparing AAPL with peers: ['MSFT', 'GOOGL']"
        # we must build it exactly:
        peer_list_str = "[" + ", ".join(f"'{p}'" for p in peers) + "]"
        self.logger.info("Comparing %s with peers: %s", ticker, peer_list_str)

        for peer in peers:
            if TickerDetector.validate_ticker_symbol(peer):
                peer_data = self._analyze_ticker_for_metrics(
                    peer,
                    n_years=n_years,
                    n_quarters=n_quarters,
                    disable_forecast=disable_forecast
                )
                metrics_map[peer] = peer_data
            else:
                self.logger.warning("Skipping invalid peer ticker: %s", peer)

        self.reporting_engine.summarize_metrics_table(
            metrics_map=metrics_map,
            main_ticker=ticker,
            csv_path=csv_path
        )
        self.logger.info("Analysis complete. Check logs or CSV if provided.")

    def _analyze_ticker_for_metrics(
        self,
        ticker: str,
        n_years: int,
        n_quarters: int,
        disable_forecast: bool
    ) -> Dict[str, Any]:
        self.logger.info(
            "Analyzing ticker: %s (years=%d, quarters=%d, forecast=%s)",
            ticker, n_years, n_quarters, (not disable_forecast)
        )

        try:
            comp = Company(ticker)
        except Exception as exc:
            self.logger.exception("Failed to create Company object for %s: %s", ticker, exc)
            return {}

        annual_snap = get_single_filing_snapshot(comp, "10-K")
        quarterly_snap = get_single_filing_snapshot(comp, "10-Q")

        multi_data = retrieve_multi_year_data(ticker, n_years=n_years, n_quarters=n_quarters)
        rev_annual = multi_data.get("annual_data", {}).get("Revenue", {})
        rev_quarterly = multi_data.get("quarterly_data", {}).get("Revenue", {})

        annual_fc, quarterly_fc = 0.0, 0.0
        if not disable_forecast:
            annual_fc = forecast_revenue(rev_annual, is_quarterly=False)
            quarterly_fc = forecast_revenue(rev_quarterly, is_quarterly=True)

        quarterly_info = analyze_quarterly_balance_sheets(comp, n_quarters=n_quarters)
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
