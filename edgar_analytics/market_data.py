"""Optional market data integration via yfinance.

Requires the ``valuation`` extra::

    pip install edgar-analytics[valuation]

When yfinance is unavailable, all functions return NaN gracefully.
"""

from __future__ import annotations

import pandas as pd

from .logging_utils import get_logger

logger = get_logger(__name__)

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
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
