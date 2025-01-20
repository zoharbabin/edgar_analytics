"""
forecasting.py

Implements ARIMA-based forecasting for annual or quarterly revenues.
Falls back to 0.0 if insufficient data or model fit fails.
"""

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

MIN_DATA_POINTS = 4


def forecast_revenue_arima(rev_dict: dict, is_quarterly: bool = False) -> float:
    """
    Forecast next revenue (1-step) using ARIMA or SARIMAX.
    Clamps negative results to 0.0.
    Returns 0.0 if data insufficient or error occurs.
    """
    if not HAS_STATSMODELS or len(rev_dict) < MIN_DATA_POINTS:
        logger.warning("Insufficient data => forecast=0.0")
        return 0.0

    sorted_periods = sorted(rev_dict.keys(), key=parse_period_label)
    series_vals = [rev_dict[p] for p in sorted_periods]
    n_points = len(series_vals)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            if n_points < 6:
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
                if is_quarterly:
                    candidates.append(
                        SARIMAX(series_vals, order=(1, 1, 1),
                                seasonal_order=(1, 1, 1, 4), trend='c',
                                enforce_stationarity=False)
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
                    logger.warning("Candidate model fit error: %s", exc)

            if not best_fit:
                logger.warning("No suitable model found => forecast=0.0")
                return 0.0

            forecast_arr = best_fit.forecast(steps=1)
            forecast_val = float(np.squeeze(forecast_arr))
            forecast_val = max(forecast_val, 0.0)
            logger.debug("Forecasted Revenue=%.2f", forecast_val)
            return forecast_val

    except Exception as exc:
        logger.warning("forecast_revenue_arima error: %s => fallback=0.0", exc)
        return 0.0
