"""
forecasting.py

Revenue forecasting using ARIMA/SARIMAX models from statsmodels.
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

MIN_DATA_POINTS = 4  # Minimum required data points for ARIMA/SARIMAX


def forecast_revenue_arima(rev_dict: dict, is_quarterly: bool = False) -> float:
    """
    Generate a single-step revenue forecast using ARIMA/SARIMAX with
    multi-stage fallback & model selection.

    Ensures non-negative forecast and handles insufficient data gracefully.
    """
    if not HAS_STATSMODELS or len(rev_dict) < MIN_DATA_POINTS:
        logger.warning("Insufficient data for forecasting. Returning 0.0.")
        return 0.0

    sorted_periods = sorted(rev_dict.keys(), key=parse_period_label)
    series_vals = [rev_dict[p] for p in sorted_periods]
    n_points = len(series_vals)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            # Candidate models
            if n_points < 6:
                candidate_models = [
                    ARIMA(series_vals, order=(0, 1, 1)),
                    ARIMA(series_vals, order=(1, 1, 0)),
                ]
            else:
                candidate_models = [
                    ARIMA(series_vals, order=(1, 1, 1)),
                    ARIMA(series_vals, order=(1, 1, 0)),
                    ARIMA(series_vals, order=(0, 1, 1)),
                ]
                if is_quarterly:
                    candidate_models.append(
                        SARIMAX(
                            series_vals, order=(1, 1, 1),
                            seasonal_order=(1, 1, 1, 4),
                            trend='c',
                            enforce_stationarity=False
                        )
                    )

            best_aic = float("inf")
            best_model_fit = None
            for cand in candidate_models:
                try:
                    cand_fit = cand.fit()
                    cand_aic = cand_fit.aic
                    if cand_aic < best_aic:
                        best_aic = cand_aic
                        best_model_fit = cand_fit
                except Exception as exc:
                    logger.warning("Candidate model fit error: %s", exc)
                    continue

            if best_model_fit is None:
                logger.warning("No suitable model found. Returning 0.0.")
                return 0.0

            forecast_result = best_model_fit.forecast(steps=1)
            forecast_val = float(np.squeeze(forecast_result))
            # Ensure non-negative
            forecast_val = max(forecast_val, 0.0)
            logger.debug("Forecasted Revenue: %.2f", forecast_val)
            return forecast_val

    except Exception as exc:
        logger.warning("forecast_revenue_arima error: %s. Returning 0.0.", exc)
        return 0.0
