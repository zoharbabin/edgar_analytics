"""tests/test_market_data.py — tests for market data module."""

import math
import pytest
from unittest.mock import patch, MagicMock

from edgar_analytics.market_data import get_market_cap, get_share_price, compute_valuation_ratios
from edgar_analytics.scores import PerShareMetrics


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


class TestValuationRatios:
    def _metrics(self, eps_diluted=float("nan"), **overrides):
        m = {
            "Net Income": 100_000,
            "EBITDA (standard)": 150_000,
            "_total_equity": 500_000,
            "_short_term_debt": 50_000,
            "_long_term_debt": 200_000,
            "_cash_equivalents": 100_000,
            "_short_term_investments": 0,
            "_preferred_stock": 0,
            "_minority_interest": 0,
            "_scores": {
                "per_share": PerShareMetrics(eps_diluted=eps_diluted),
            },
        }
        m.update(overrides)
        return m

    def test_pe_uses_diluted_eps(self):
        v = compute_valuation_ratios(1_000_000, 175.0, self._metrics(eps_diluted=17.5))
        assert v.pe_ratio == pytest.approx(10.0)

    def test_pe_falls_back_to_market_cap_over_ni(self):
        v = compute_valuation_ratios(1_000_000, 175.0, self._metrics())
        assert v.pe_ratio == pytest.approx(10.0)

    def test_pb_ratio(self):
        v = compute_valuation_ratios(1_000_000, 175.0, self._metrics())
        assert v.pb_ratio == pytest.approx(2.0)

    def test_ev_ebitda(self):
        v = compute_valuation_ratios(1_000_000, 175.0, self._metrics())
        ev = 1_000_000 + 50_000 + 200_000 - 100_000
        assert v.ev_ebitda == pytest.approx(ev / 150_000)

    def test_earnings_yield_from_diluted_pe(self):
        v = compute_valuation_ratios(1_000_000, 175.0, self._metrics(eps_diluted=17.5))
        assert v.earnings_yield == pytest.approx(0.1)

    def test_nan_when_no_market_cap(self):
        v = compute_valuation_ratios(float("nan"), float("nan"), self._metrics())
        assert math.isnan(v.pe_ratio)
        assert math.isnan(v.pb_ratio)
        assert math.isnan(v.ev_ebitda)

    def test_nan_pe_when_negative_income(self):
        v = compute_valuation_ratios(1_000_000, 175.0, self._metrics(**{"Net Income": -50_000}))
        assert math.isnan(v.pe_ratio)

    def test_nan_pb_when_negative_equity(self):
        v = compute_valuation_ratios(1_000_000, 175.0, self._metrics(**{"_total_equity": -100_000}))
        assert math.isnan(v.pb_ratio)

    def test_ev_includes_preferred_and_minority(self):
        v = compute_valuation_ratios(
            1_000_000, 175.0,
            self._metrics(**{"_preferred_stock": 30_000, "_minority_interest": 20_000}),
        )
        # EV = 1M + 50k + 200k + 30k + 20k - 100k - 0 = 1_200_000
        assert v.ev_ebitda == pytest.approx(1_200_000 / 150_000)

    def test_ev_subtracts_st_investments(self):
        v = compute_valuation_ratios(
            1_000_000, 175.0,
            self._metrics(**{"_short_term_investments": 40_000}),
        )
        # EV = 1M + 50k + 200k + 0 + 0 - 100k - 40k = 1_110_000
        assert v.ev_ebitda == pytest.approx(1_110_000 / 150_000)
