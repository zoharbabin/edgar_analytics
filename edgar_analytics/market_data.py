"""Optional market data integration via yfinance.

Requires the ``valuation`` extra::

    pip install edgar-analytics[valuation]

When yfinance is unavailable, all functions return NaN gracefully.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from .logging_utils import get_logger

logger = get_logger(__name__)

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    yf = None  # type: ignore[assignment]
    HAS_YFINANCE = False


def get_market_cap(ticker: str) -> float:
    """Fetch current market capitalization for a ticker.

    Returns NaN if yfinance is not installed or the lookup fails."""
    if not HAS_YFINANCE:
        logger.debug("yfinance not installed — market_cap unavailable for %s", ticker)
        return float("nan")

    try:
        info = yf.Ticker(ticker).info
        cap = info.get("marketCap")
        if cap is not None:
            return float(cap)
    except Exception as exc:
        logger.warning("Failed to fetch market cap for %s: %s", ticker, exc)

    return float("nan")


def get_share_price(ticker: str) -> float:
    """Fetch the current share price for a ticker.

    Returns NaN if yfinance is not installed or the lookup fails."""
    if not HAS_YFINANCE:
        return float("nan")

    try:
        info = yf.Ticker(ticker).info
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if price is not None:
            return float(price)
    except Exception as exc:
        logger.warning("Failed to fetch price for %s: %s", ticker, exc)

    return float("nan")


_NAN = float("nan")


@dataclass
class ValuationRatios:
    """Market-derived valuation multiples."""

    pe_ratio: float = _NAN
    pb_ratio: float = _NAN
    ev_ebitda: float = _NAN
    earnings_yield: float = _NAN


def compute_valuation_ratios(
    market_cap: float, share_price: float, metrics: dict,
) -> ValuationRatios:
    """Compute P/E, P/B, EV/EBITDA, and earnings yield.

    All inputs come from the caller — no network calls are made here.
    Returns NaN for anything that cannot be computed.

    P/E uses diluted EPS (``share_price / eps_diluted``) when available,
    falling back to ``market_cap / net_income`` otherwise.
    """
    net_income = metrics.get("Net Income", 0.0)
    total_equity = metrics.get("_total_equity", 0.0)
    ebitda = metrics.get("EBITDA (standard)", _NAN)
    short_debt = metrics.get("_short_term_debt", 0.0)
    long_debt = metrics.get("_long_term_debt", 0.0)
    cash = metrics.get("_cash_equivalents", 0.0)
    st_investments = metrics.get("_short_term_investments", 0.0)
    preferred = metrics.get("_preferred_stock", 0.0)
    minority = metrics.get("_minority_interest", 0.0)

    scores = metrics.get("_scores", {})
    per_share = scores.get("per_share", None)
    eps_diluted = getattr(per_share, "eps_diluted", _NAN)

    pe = _NAN
    if not math.isnan(share_price) and not math.isnan(eps_diluted) and eps_diluted > 0:
        pe = share_price / eps_diluted
    elif not math.isnan(market_cap) and net_income > 0:
        pe = market_cap / net_income

    pb = (market_cap / total_equity) if (
        not math.isnan(market_cap) and total_equity > 0
    ) else _NAN

    # EV = Market Cap + Total Debt + Preferred Stock + Minority Interest - Cash & Equivalents - ST Investments
    ev = _NAN
    if not math.isnan(market_cap):
        ev = market_cap + short_debt + long_debt + preferred + minority - cash - st_investments
    ev_ebitda = (ev / ebitda) if (
        not math.isnan(ev) and not math.isnan(ebitda) and ebitda > 0
    ) else _NAN

    earnings_yield = (1.0 / pe) if (
        not math.isnan(pe) and pe != 0
    ) else _NAN

    return ValuationRatios(
        pe_ratio=pe, pb_ratio=pb, ev_ebitda=ev_ebitda,
        earnings_yield=earnings_yield,
    )
