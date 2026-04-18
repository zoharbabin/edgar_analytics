"""
orchestrator.py

Coordinates the entire EDGAR-based analysis: validating tickers,
fetching data, computing metrics, multi-year analysis, forecasting,
and final reporting.
"""

import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional

import pandas as pd
from edgar import Company, set_identity

from .logging_utils import get_logger
from .models import AnalysisResult, TickerAnalysis


class EdgarAnalyticsError(Exception):
    """Base exception for edgar_analytics operational errors."""


class TickerFetchError(EdgarAnalyticsError):
    """Raised when a ticker cannot be resolved or its filings cannot be fetched."""
from .reporting import ReportingEngine
from .metrics import (
    get_single_filing_snapshot,
    get_filing_snapshot_with_fallback,
    get_prior_annual_metrics,
    ANNUAL_FORM_TYPES,
    QUARTERLY_FORM_TYPES,
)
from .scores import compute_all_scores, compute_ttm
from .forecasting import forecast_revenue
from .multi_period_analysis import (
    retrieve_multi_year_data,
    analyze_quarterly_balance_sheets,
    check_additional_alerts_quarterly,
)
from .market_data import get_market_cap, get_share_price, compute_valuation_ratios
from .cache import CacheLayer
from .company_facts import CompanyFactsClient

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

    _SEC_LOCK = threading.Lock()
    _SEC_LAST_REQUEST = 0.0
    _SEC_MIN_INTERVAL = 0.1

    _IDENTITY_LOCK = threading.Lock()

    def __init__(self, cache_dir: Optional[str] = None, enable_cache: bool = True) -> None:
        self.logger = logger
        self.reporting_engine = ReportingEngine()
        self._cache = CacheLayer(directory=cache_dir or ".edgar_cache", enabled=enable_cache)
        self._facts_client = CompanyFactsClient()
        self._alerts_config: Optional[Dict[str, Any]] = None

    def close(self) -> None:
        self._cache.close()

    def __enter__(self) -> "TickerOrchestrator":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def analyze(
        self,
        ticker: str,
        peers: Optional[List[str]] = None,
        n_years: int = 3,
        n_quarters: int = 10,
        disable_forecast: bool = False,
        identity: Optional[str] = None,
        alerts_config: Optional[Dict[str, Any]] = None,
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
        :param alerts_config: Optional dict of alert threshold overrides
            (e.g. ``{"HIGH_LEVERAGE": 5.0}``).  Keys not provided keep defaults.
        :returns: An :class:`AnalysisResult` with typed fields for every ticker.
        :raises ValueError: If the main ticker symbol is syntactically invalid.
        :raises TickerFetchError: If the main ticker cannot be resolved or fetched.
        """
        if not TickerDetector.validate_ticker_symbol(ticker):
            raise ValueError(f"Invalid ticker symbol: {ticker!r}")

        self._set_identity(identity)
        self._alerts_config = alerts_config
        self.logger.info("Analyzing company: %s", ticker)

        result = AnalysisResult(main_ticker=ticker)

        main_data = self._analyze_ticker_for_metrics(
            ticker, n_years=n_years, n_quarters=n_quarters,
            disable_forecast=disable_forecast,
        )
        result.tickers[ticker] = TickerAnalysis.from_dict(ticker, main_data)

        valid_peers = [p for p in (peers or []) if TickerDetector.validate_ticker_symbol(p)]
        for p in (peers or []):
            if not TickerDetector.validate_ticker_symbol(p):
                self.logger.warning("Skipping invalid peer ticker: %s", p)

        if valid_peers:
            with ThreadPoolExecutor(max_workers=min(len(valid_peers), 5)) as pool:
                futures = {
                    pool.submit(
                        self._analyze_ticker_with_semaphore,
                        peer, n_years, n_quarters, disable_forecast,
                    ): peer
                    for peer in valid_peers
                }
                for future in as_completed(futures):
                    peer = futures[future]
                    try:
                        peer_data = future.result()
                        result.tickers[peer] = TickerAnalysis.from_dict(peer, peer_data)
                    except (TickerFetchError, OSError, ValueError, KeyError) as exc:
                        self.logger.error("Peer %s failed: %s", peer, exc, exc_info=True)

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

    def _analyze_ticker_with_semaphore(
        self, ticker: str, n_years: int, n_quarters: int, disable_forecast: bool,
    ) -> Dict[str, Any]:
        import time
        with self._SEC_LOCK:
            now = time.monotonic()
            wait = self._SEC_MIN_INTERVAL - (now - self._SEC_LAST_REQUEST)
            if wait > 0:
                time.sleep(wait)
            TickerOrchestrator._SEC_LAST_REQUEST = time.monotonic()
        return self._analyze_ticker_for_metrics(
            ticker, n_years=n_years, n_quarters=n_quarters,
            disable_forecast=disable_forecast,
        )

    def _set_identity(self, identity: Optional[str]) -> None:
        with self._IDENTITY_LOCK:
            if identity:
                set_identity(identity)
            else:
                self.logger.warning(
                    "No --identity provided. SEC EDGAR requires a valid identity "
                    "(e.g. 'Name <email>'). Set via --identity or EDGAR_IDENTITY env var."
                )
                from edgar_analytics import __version__
                default = f"edgar-analytics/{__version__} <edgar-analytics@users.noreply.github.com>"
                env_identity = os.environ.get("EDGAR_IDENTITY", default)
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
        except (ValueError, KeyError, OSError) as exc:
            raise TickerFetchError(f"Cannot resolve ticker {ticker!r}: {exc}") from exc

        sic = getattr(comp, "sic", None)
        is_financial = isinstance(sic, int) and 6000 <= sic <= 6999

        annual_snap = self._cached_snapshot(
            comp, ticker, ANNUAL_FORM_TYPES, is_current=False,
            alerts_config=self._alerts_config, is_financial=is_financial,
        )
        quarterly_snap = self._cached_snapshot(
            comp, ticker, QUARTERLY_FORM_TYPES, is_current=True,
            alerts_config=self._alerts_config, is_financial=is_financial,
        )

        self._cross_validate(ticker, annual_snap)

        multi_data = retrieve_multi_year_data(ticker, n_years=n_years, n_quarters=n_quarters)
        rev_annual = multi_data.get("annual_data", {}).get("Revenue", {})
        rev_quarterly = multi_data.get("quarterly_data", {}).get("Revenue", {})

        annual_fc, quarterly_fc = 0.0, 0.0
        if not disable_forecast:
            annual_fc = forecast_revenue(rev_annual, is_quarterly=False)
            quarterly_fc = forecast_revenue(rev_quarterly, is_quarterly=True)

        ttm_data = compute_ttm(multi_data.get("quarterly_data", {}))
        multi_data["ttm"] = ttm_data

        quarterly_info = analyze_quarterly_balance_sheets(comp, n_quarters=n_quarters)
        extra_alerts = check_additional_alerts_quarterly(quarterly_info, alerts_config=self._alerts_config)

        market_cap = get_market_cap(ticker)
        share_price = get_share_price(ticker)

        if annual_snap.get("metrics"):
            valuation = compute_valuation_ratios(market_cap, share_price, annual_snap["metrics"])
            annual_snap["metrics"]["_valuation"] = valuation

        self._enhance_scores_with_prior_year(
            comp, annual_snap, market_cap, is_financial=is_financial,
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

    def _cached_snapshot(
        self, comp: Company, ticker: str, form_types: tuple, is_current: bool,
        alerts_config: Optional[Dict[str, Any]] = None,
        is_financial: bool = False,
    ) -> dict:
        """Fetch a filing snapshot, using cache when available."""
        cache_ns = "snapshot"
        form_label = "quarterly" if is_current else "annual"
        cached = self._cache.get(cache_ns, ticker, form_label)
        if cached is not None:
            self.logger.debug("Cache hit for %s %s snapshot", ticker, form_label)
            return cached

        snap = get_filing_snapshot_with_fallback(
            comp, form_types, alerts_config=alerts_config, is_financial=is_financial,
        )

        if snap.get("metrics"):
            accession = snap.get("filing_info", {}).get("accession_no", "")
            if is_current:
                self._cache.set_current(snap, cache_ns, ticker, form_label)
            else:
                self._cache.set_immutable(snap, cache_ns, ticker, form_label)
            self.logger.debug("Cached %s %s snapshot (accession=%s)", ticker, form_label, accession)

        return snap

    def _cross_validate(self, ticker: str, annual_snap: dict) -> None:
        """Run CompanyFacts cross-validation on annual metrics."""
        metrics = annual_snap.get("metrics")
        if not metrics:
            return
        try:
            facts = self._facts_client.fetch(ticker)
            self._facts_client.validate_metrics(facts, metrics, ticker=ticker)
        except (OSError, ValueError, KeyError) as exc:
            self.logger.debug("CompanyFacts validation skipped for %s: %s", ticker, exc)

    def _enhance_scores_with_prior_year(
        self,
        comp: Company,
        annual_snap: dict,
        market_cap: float,
        is_financial: bool = False,
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
            is_financial=is_financial,
        )
        if "altman" in enhanced:
            existing_scores["altman"] = enhanced["altman"]

        # Piotroski and Beneish require prior-period data.
        prior_metrics = get_prior_annual_metrics(
            comp, alerts_config=self._alerts_config, is_financial=is_financial,
        )
        if prior_metrics:
            enhanced_yoy = compute_all_scores(
                metrics=current_metrics,
                balance_df=pd.DataFrame(),
                income_df=pd.DataFrame(),
                cash_df=pd.DataFrame(),
                market_cap=market_cap,
                prior_metrics=prior_metrics,
                is_financial=is_financial,
            )
            for k in ("piotroski", "beneish"):
                if k in enhanced_yoy:
                    existing_scores[k] = enhanced_yoy[k]

            # Sloan Accrual = (ΔWorkingCapital - ΔCash - D&A) / Avg Total Assets
            ca, cl = current_metrics.get("_current_assets", 0), current_metrics.get("_current_liabilities", 0)
            p_ca, p_cl = prior_metrics.get("_current_assets", 0), prior_metrics.get("_current_liabilities", 0)
            delta_wc = (ca - cl) - (p_ca - p_cl)
            delta_cash = current_metrics.get("_cash_equivalents", 0) - prior_metrics.get("_cash_equivalents", 0)
            dep = current_metrics.get("_dep_amort", 0)
            avg_ta = (current_metrics.get("_total_assets", 0) + prior_metrics.get("_total_assets", 0)) / 2
            current_metrics["Sloan Accrual"] = (
                (delta_wc - delta_cash - dep) / avg_ta if avg_ta > 0 else float("nan")
            )
        else:
            self.logger.debug("No prior-year annual filing — skipping YoY scores.")

        current_metrics["_scores"] = existing_scores
