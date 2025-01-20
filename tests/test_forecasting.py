# tests/test_forecasting.py

import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from edgar_analytics.forecasting import (
    forecast_revenue,
    ArimaForecastStrategy,
    ForecastStrategy,
    MIN_DATA_POINTS
)
from edgar_analytics.data_utils import parse_period_label


class SimpleGrowthStrategy(ForecastStrategy):
    """
    Example custom strategy for testing. 
    Predicts last known revenue * 1.05.
    """

    def forecast(self, rev_dict: dict, is_quarterly: bool = False) -> float:
        if not rev_dict:
            return 0.0
        sorted_periods = sorted(rev_dict.keys(), key=parse_period_label)
        last_val = rev_dict[sorted_periods[-1]]
        return last_val * 1.05


def test_forecast_insufficient_data():
    """
    If len(rev_dict) < MIN_DATA_POINTS => default ArimaForecastStrategy => forecast=0.0
    """
    rev_dict = {"2021": 100}
    result = forecast_revenue(rev_dict, is_quarterly=False)
    assert result == 0.0


def test_forecast_enough_data():
    """
    Provide enough data points;
    mock ARIMA to always return e.g. 500 => forecast=500.0
    """
    rev_dict = {
        "2018": 100,
        "2019": 200,
        "2020": 300,
        "2021": 400,
    }
    with patch("edgar_analytics.forecasting.ARIMA") as mock_arima:
        mock_fit = MagicMock()
        mock_fit.aic = 10.0  # numeric AIC ensures "cand_fit.aic < best_aic" works
        mock_fit.forecast.return_value = np.array([500])
        mock_arima.return_value.fit.return_value = mock_fit

        result = forecast_revenue(rev_dict, is_quarterly=False)
        assert result == 500.0


def test_forecast_arima_fit_error():
    """
    If there's an error in ARIMA model fitting => fallback=0.0
    """
    rev_dict = {
        "2018": 100,
        "2019": 200,
        "2020": 300,
        "2021": 400,
    }
    with patch("edgar_analytics.forecasting.ARIMA") as mock_arima:
        mock_arima.return_value.fit.side_effect = ValueError("Test model error")
        result = forecast_revenue(rev_dict, is_quarterly=False)
        assert result == 0.0


def test_forecast_negative_result():
    """
    If the model forecasts negative => clamp to 0.0 
    """
    rev_dict = {
        "2018": 100,
        "2019": 200,
        "2020": 300,
        "2021": 400,
    }
    with patch("edgar_analytics.forecasting.ARIMA") as mock_arima:
        mock_model = MagicMock()
        mock_model.fit.return_value.forecast.return_value = np.array([-10])
        mock_arima.return_value = mock_model

        result = forecast_revenue(rev_dict, is_quarterly=False)
        assert result == 0.0


def test_forecast_quarterly_sarimax():
    rev_dict = {
        "2019-Q1": 100,
        "2019-Q2": 150,
        "2019-Q3": 180,
        "2019-Q4": 210,
        "2020-Q1": 230,
        "2020-Q2": 240,  # Now 6 data points
    }
    with patch("edgar_analytics.forecasting.SARIMAX") as mock_sarimax, \
         patch("edgar_analytics.forecasting.ARIMA") as mock_arima:

        # ARIMA mock => high AIC => won't be chosen
        mock_arima_fit = MagicMock()
        mock_arima_fit.aic = 999.0
        mock_arima_fit.forecast.return_value = np.array([111.11])
        mock_arima.return_value.fit.return_value = mock_arima_fit

        # SARIMAX mock => low AIC => best
        mock_sarimax_fit = MagicMock()
        mock_sarimax_fit.aic = 5.0
        mock_sarimax_fit.forecast.return_value = np.array([1234.56])
        mock_sarimax.return_value.fit.return_value = mock_sarimax_fit

        result = forecast_revenue(rev_dict, is_quarterly=True)
        assert result == pytest.approx(1234.56, 0.1)
        

def test_custom_forecast_strategy():
    """
    Demonstrate passing a custom ForecastStrategy. 
    In this example, it always grows last known revenue by +5%.
    """
    rev_dict = {
        "2021": 100,
        "2022": 200,
    }
    result = forecast_revenue(rev_dict, is_quarterly=False, strategy=SimpleGrowthStrategy())
    # Last known is 200 => 200 * 1.05 => 210
    assert result == pytest.approx(210.0, 0.01)

    # Also test empty => 0.0 fallback
    result2 = forecast_revenue({}, strategy=SimpleGrowthStrategy())
    assert result2 == 0.0
