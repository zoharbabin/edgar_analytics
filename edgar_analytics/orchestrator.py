"""
orchestrator.py

Coordinates the entire EDGAR-based analysis: validating tickers,
fetching data, computing metrics, multi-year analysis, forecasting,
and final reporting.
"""

import os
import re
from typing import Dict, Any, List, Optional

import pandas as pd
from edgar import Company, set_identity

from .logging_utils import get_logger
from .models import AnalysisResult, TickerAnalysis
from .reporting import ReportingEngine
from .metrics import (
    get_single_filing_snapshot,
    get_filing_snapshot_with_fallback,
    get_prior_annual_metrics,
    ANNUAL_FORM_TYPES,
    QUARTERLY_FORM_TYPES,
)
from .scores import compute_all_scores
from .forecasting import forecast_revenue
from .multi_period_analysis import (
    retrieve_multi_year_data,
    analyze_quarterly_balance_sheets,
    check_additional_alerts_quarterly,
)
from .market_data import get_market_cap

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

    def analyze(
        self,
        ticker: str,
        peers: Optional[List[str]] = None,
        n_years: int = 3,
        n_quarters: int = 10,
        disable_forecast: bool = False,
        identity: Optional[str] = None,
    ) -> AnalysisResult:
        """Run a full EDGAR analysis and return structured results.

        This is the primary programmatic API. It fetches filings, computes
        metrics, and returns an :class:`AnalysisResult` dataclass. No console
        output is produced; call :meth:`analyze_company` for CLI-style output.

        :param ticker: Main company ticker symbol (e.g. ``"AAPL"``).
        :param peers: Optional list of peer ticker symbols.
        :param n_years: Number of annual filings to retrieve.
        :param n_quarters: Number of quarterly filings to retrieve.
        :param disable_forecast: Skip ARIMA revenue forecasting.
        :param identity: SEC EDGAR identity string (``"Name <email>"``).
        :returns: An :class:`AnalysisResult` with typed fields for every ticker.
        :raises ValueError: If the main ticker is invalid.
        """
        if not TickerDetector.validate_ticker_symbol(ticker):
            raise ValueError(f"Invalid ticker symbol: {ticker!r}")

        self._set_identity(identity)
        self.logger.info("Analyzing company: %s", ticker)

        result = AnalysisResult(main_ticker=ticker)

        main_data = self._analyze_ticker_for_metrics(
            ticker, n_years=n_years, n_quarters=n_quarters,
            disable_forecast=disable_forecast,
        )
        result.tickers[ticker] = TickerAnalysis.from_dict(ticker, main_data)

        for peer in (peers or []):
            if TickerDetector.validate_ticker_symbol(peer):
                peer_data = self._analyze_ticker_for_metrics(
                    peer, n_years=n_years, n_quarters=n_quarters,
                    disable_forecast=disable_forecast,
                )
                result.tickers[peer] = TickerAnalysis.from_dict(peer, peer_data)
            else:
                self.logger.warning("Skipping invalid peer ticker: %s", peer)

        self.logger.info("Analysis complete.")
        return result

    def analyze_company(
        self,
        ticker: str,
        peers: List[str],
        csv_path: Optional[str] = None,
        n_years: int = 3,
        n_quarters: int = 10,
        disable_forecast: bool = False,
        identity: Optional[str] = None
    ) -> AnalysisResult:
        """Run analysis with console output and optional CSV export.

        Wraps :meth:`analyze` and passes results through the reporting engine
        for console display. Returns the same :class:`AnalysisResult`.
        """
        result = self.analyze(
            ticker=ticker,
            peers=peers,
            n_years=n_years,
            n_quarters=n_quarters,
            disable_forecast=disable_forecast,
            identity=identity,
        )

        metrics_map: Dict[str, Dict[str, Any]] = {
            t: ta.to_dict() for t, ta in result.tickers.items()
        }
        self.reporting_engine.summarize_metrics_table(
            metrics_map=metrics_map,
            main_ticker=ticker,
            csv_path=csv_path,
        )
        self.logger.info("Analysis complete. Check logs or CSV if provided.")
        return result

    def _set_identity(self, identity: Optional[str]) -> None:
        if identity:
            set_identity(identity)
        else:
            self.logger.warning(
                "No --identity provided. SEC EDGAR requires a valid identity "
                "(e.g. 'Name <email>'). Set via --identity or EDGAR_IDENTITY env var."
            )
            env_identity = os.environ.get("EDGAR_IDENTITY", "edgar-analytics <edgar-analytics@users.noreply.github.com>")
            set_identity(env_identity)

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

        annual_snap = get_filing_snapshot_with_fallback(comp, ANNUAL_FORM_TYPES)
        quarterly_snap = get_filing_snapshot_with_fallback(comp, QUARTERLY_FORM_TYPES)

        multi_data = retrieve_multi_year_data(ticker, n_years=n_years, n_quarters=n_quarters)
        rev_annual = multi_data.get("annual_data", {}).get("Revenue", {})
        rev_quarterly = multi_data.get("quarterly_data", {}).get("Revenue", {})

        annual_fc, quarterly_fc = 0.0, 0.0
        if not disable_forecast:
            annual_fc = forecast_revenue(rev_annual, is_quarterly=False)
            quarterly_fc = forecast_revenue(rev_quarterly, is_quarterly=True)

        quarterly_info = analyze_quarterly_balance_sheets(comp, n_quarters=n_quarters)
        extra_alerts = check_additional_alerts_quarterly(quarterly_info)

        market_cap = get_market_cap(ticker)

        self._enhance_scores_with_prior_year(
            comp, annual_snap, market_cap,
        )

        return {
            "annual_snapshot": annual_snap,
            "quarterly_snapshot": quarterly_snap,
            "multiyear": multi_data,
            "forecast": {
                "annual_rev_forecast": annual_fc,
                "quarterly_rev_forecast": quarterly_fc,
            },
            "extra_alerts": extra_alerts,
            "market_cap": market_cap,
        }

    def _enhance_scores_with_prior_year(
        self,
        comp: Company,
        annual_snap: dict,
        market_cap: float,
    ) -> None:
        """Enhance existing scores with Altman (needs market_cap), Piotroski, and Beneish."""
        current_metrics = annual_snap.get("metrics")
        if not current_metrics:
            return

        existing_scores = current_metrics.get("_scores", {})

        # Altman Z-Score only needs current-period data + market_cap.
        # The base compute_all_scores call in metrics.py lacks market_cap,
        # so we always recompute Altman here where market_cap is available.
        enhanced = compute_all_scores(
            metrics=current_metrics,
            balance_df=pd.DataFrame(),
            income_df=pd.DataFrame(),
            cash_df=pd.DataFrame(),
            market_cap=market_cap,
        )
        if "altman" in enhanced:
            existing_scores["altman"] = enhanced["altman"]

        # Piotroski and Beneish require prior-period data.
        prior_metrics = get_prior_annual_metrics(comp)
        if prior_metrics:
            enhanced_yoy = compute_all_scores(
                metrics=current_metrics,
                balance_df=pd.DataFrame(),
                income_df=pd.DataFrame(),
                cash_df=pd.DataFrame(),
                market_cap=market_cap,
                prior_metrics=prior_metrics,
            )
            for k in ("piotroski", "beneish"):
                if k in enhanced_yoy:
                    existing_scores[k] = enhanced_yoy[k]
        else:
            self.logger.debug("No prior-year annual filing — skipping YoY scores.")

        current_metrics["_scores"] = existing_scores
