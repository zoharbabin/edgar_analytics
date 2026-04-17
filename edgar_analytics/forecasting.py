"""
forecasting.py

Implements a strategy-based design for forecasting revenue data.
Includes a default ArimaForecastStrategy for annual or quarterly revenues
and a general forecast_revenue() function that can accept any custom
ForecastStrategy implementation.
"""

import abc
import warnings
import numpy as np

from .data_utils import parse_period_label
from .logging_utils import get_logger

logger = get_logger(__name__)

try:
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    from statsmodels.tsa.arima.model import ARIMA
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

MIN_DATA_POINTS = 6
MIN_SEASONAL_DATA_POINTS = 12


class ForecastStrategy(abc.ABC):
    """
    Abstract base class for forecasting strategies.

    Each strategy must implement the .forecast(rev_dict, is_quarterly) method
    and return a single float representing the 1-step-ahead forecast.
    """

    @abc.abstractmethod
    def forecast(self, rev_dict: dict, is_quarterly: bool = False) -> float:
        """
        Compute a 1-step revenue forecast from rev_dict,
        optionally considering is_quarterly for seasonal dynamics.

        :param rev_dict:      {period_label -> revenue}, e.g. {'2020': 100, '2021': 200}
        :param is_quarterly:  Whether to assume quarterly seasonality or logic
        :return: A float forecast of next period's revenue.
        """


class ArimaForecastStrategy(ForecastStrategy):
    """
    Default ARIMA-based forecasting strategy.

    - Uses statsmodels ARIMA or SARIMAX for seasonal logic.
    - Requires >= MIN_DATA_POINTS or returns 0.0.
    - Negative forecasts are preserved to surface declining trends.
    - Logs warning if statsmodels is missing or ARIMA model fails.
    """

    def forecast(self, rev_dict: dict, is_quarterly: bool = False) -> float:
        """
        Forecast next revenue (1-step) using ARIMA or SARIMAX.

        :param rev_dict:      Dictionary of {period_label -> revenue_value}
        :param is_quarterly:  If True, we may attempt a seasonal_order=(...,4) for quarterly data.
        :return: Forecast value (may be negative for declining trends), or naive fallback on error.
        """
        sorted_periods = sorted(rev_dict.keys(), key=parse_period_label)
        series_vals = [rev_dict[p] for p in sorted_periods]
        naive_fallback = series_vals[-1] if series_vals else 0.0

        if not HAS_STATSMODELS or len(rev_dict) < MIN_DATA_POINTS:
            logger.warning(
                "ArimaForecastStrategy: insufficient data (%d pts) or statsmodels missing => naive fallback=%.2f",
                len(rev_dict), naive_fallback,
            )
            return naive_fallback

        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning)
                warnings.filterwarnings("ignore", message=".*convergence.*")

                candidates = []
                if len(series_vals) < 8:
                    candidates = [
                        ARIMA(series_vals, order=(0, 1, 1)),
                        ARIMA(series_vals, order=(1, 1, 0)),
                    ]
                else:
                    candidates = [
                        ARIMA(series_vals, order=(1, 1, 1)),
                        ARIMA(series_vals, order=(1, 1, 0)),
                        ARIMA(series_vals, order=(0, 1, 1)),
                    ]
                    if is_quarterly and len(series_vals) >= MIN_SEASONAL_DATA_POINTS:
                        candidates.append(
                            SARIMAX(
                                series_vals,
                                order=(1, 1, 1),
                                seasonal_order=(1, 0, 1, 4),
                                trend='c',
                                enforce_stationarity=True,
                                enforce_invertibility=True,
                            )
                        )

                best_aic = float("inf")
                best_fit = None
                for cand in candidates:
                    try:
                        cand_fit = cand.fit()
                        if cand_fit.aic < best_aic:
                            best_aic = cand_fit.aic
                            best_fit = cand_fit
                    except Exception as exc:
                        logger.warning(
                            "ArimaForecastStrategy: model fit error: %s", exc
                        )

                if not best_fit:
                    logger.warning(
                        "ArimaForecastStrategy: no suitable model found => naive fallback=%.2f",
                        naive_fallback,
                    )
                    return naive_fallback

                forecast_arr = best_fit.forecast(steps=1)
                forecast_val = float(np.squeeze(forecast_arr))

                if not np.isfinite(forecast_val):
                    logger.warning(
                        "ArimaForecastStrategy: non-finite forecast (NaN/Inf) => naive fallback=%.2f",
                        naive_fallback,
                    )
                    return naive_fallback

                if forecast_val < 0.0:
                    logger.warning(
                        "ArimaForecastStrategy: negative forecast=%.2f (declining revenue trend)",
                        forecast_val,
                    )
                return forecast_val

        except Exception as exc:
            logger.warning(
                "ArimaForecastStrategy: exception during forecast => %s => naive fallback=%.2f",
                exc, naive_fallback,
            )
            return naive_fallback


def forecast_revenue(
    rev_dict: dict,
    is_quarterly: bool = False,
    strategy: ForecastStrategy = None
) -> float:
    """
    Main entry point to forecast the next revenue value. By default, uses ArimaForecastStrategy
    unless a custom ForecastStrategy is provided.

    :param rev_dict:      Dictionary of {period_label -> float}, e.g. {'2018': 1000, '2019': 1500}
    :param is_quarterly:  If True, the strategy may assume or handle quarterly seasonality.
    :param strategy:      Custom ForecastStrategy instance. Defaults to ArimaForecastStrategy.
    :return: A float representing the next period forecast.
    """
    if strategy is None:
        strategy = ArimaForecastStrategy()
    return strategy.forecast(rev_dict, is_quarterly)
