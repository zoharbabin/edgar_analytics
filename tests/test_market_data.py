"""tests/test_market_data.py — tests for market data module."""

import math
from unittest.mock import patch, MagicMock

from edgar_analytics.market_data import get_market_cap, get_share_price


class TestGetMarketCap:
    def test_returns_nan_without_yfinance(self):
        with patch("edgar_analytics.market_data.HAS_YFINANCE", False):
            result = get_market_cap("AAPL")
            assert math.isnan(result)

    def test_returns_value_with_yfinance(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {"marketCap": 3_000_000_000_000}
        with patch("edgar_analytics.market_data.HAS_YFINANCE", True), \
             patch("edgar_analytics.market_data.yf") as mock_yf:
            mock_yf.Ticker.return_value = mock_ticker
            result = get_market_cap("AAPL")
            assert result == 3_000_000_000_000

    def test_returns_nan_on_api_error(self):
        with patch("edgar_analytics.market_data.HAS_YFINANCE", True), \
             patch("edgar_analytics.market_data.yf") as mock_yf:
            mock_yf.Ticker.side_effect = RuntimeError("API down")
            result = get_market_cap("AAPL")
            assert math.isnan(result)

    def test_returns_nan_when_marketcap_missing(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {}
        with patch("edgar_analytics.market_data.HAS_YFINANCE", True), \
             patch("edgar_analytics.market_data.yf") as mock_yf:
            mock_yf.Ticker.return_value = mock_ticker
            result = get_market_cap("AAPL")
            assert math.isnan(result)


class TestGetSharePrice:
    def test_returns_nan_without_yfinance(self):
        with patch("edgar_analytics.market_data.HAS_YFINANCE", False):
            result = get_share_price("AAPL")
            assert math.isnan(result)

    def test_returns_current_price(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {"currentPrice": 175.50}
        with patch("edgar_analytics.market_data.HAS_YFINANCE", True), \
             patch("edgar_analytics.market_data.yf") as mock_yf:
            mock_yf.Ticker.return_value = mock_ticker
            result = get_share_price("AAPL")
            assert result == 175.50

    def test_falls_back_to_regular_market_price(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {"regularMarketPrice": 174.00}
        with patch("edgar_analytics.market_data.HAS_YFINANCE", True), \
             patch("edgar_analytics.market_data.yf") as mock_yf:
            mock_yf.Ticker.return_value = mock_ticker
            result = get_share_price("AAPL")
            assert result == 174.00
