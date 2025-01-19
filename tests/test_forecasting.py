# tests/test_forecasting.py

import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from edgar_analytics.forecasting import forecast_revenue_arima

def test_forecast_insufficient_data():
    """
    If len(rev_dict) < MIN_DATA_POINTS (4), we expect 0.0 fallback.
    """
    rev_dict = { "2021": 100 }  # Only 1 data point
    forecast = forecast_revenue_arima(rev_dict, is_quarterly=False)
    assert forecast == 0.0

@pytest.mark.parametrize("is_quarterly", [True, False])
def test_forecast_enough_data(is_quarterly):
    """
    Provide enough data points and ensure a forecast is returned >= 0.0
    We'll mock the actual ARIMA fitting to avoid complexities.
    """
    rev_dict = {
        "2018": 100,
        "2019": 200,
        "2020": 300,
        "2021": 400,
    }
    # Mock the ARIMA fit to always return a forecast of e.g. 500
    with patch("edgar_analytics.forecasting.ARIMA") as mock_arima:
        mock_model = MagicMock()
        mock_model.fit.return_value.forecast.return_value = np.array([500])
        mock_model.fit.return_value.aic = 123.45  # Real float
        mock_arima.return_value = mock_model

        forecast = forecast_revenue_arima(rev_dict, is_quarterly=is_quarterly)
        assert forecast == 500.0

def test_forecast_arima_fit_error():
    """
    If there's an error in ARIMA model fitting, we should return 0.0 fallback.
    """
    rev_dict = {
        "2018": 100,
        "2019": 200,
        "2020": 300,
        "2021": 400,
    }
    with patch("edgar_analytics.forecasting.ARIMA") as mock_arima:
        mock_arima.return_value.fit.side_effect = ValueError("Test model error")
        forecast = forecast_revenue_arima(rev_dict, is_quarterly=False)
        assert forecast == 0.0

def test_forecast_negative_result():
    """
    If the model forecast is negative, the code clamps it to 0.0
    """
    rev_dict = {
        "2018": 100,
        "2019": 200,
        "2020": 300,
        "2021": 400,
    }
    with patch("edgar_analytics.forecasting.ARIMA") as mock_arima:
        mock_model = MagicMock()
        # Force a negative forecast
        mock_model.fit.return_value.forecast.return_value = np.array([-50])
        mock_arima.return_value = mock_model

        forecast = forecast_revenue_arima(rev_dict, is_quarterly=False)
        assert forecast == 0.0
