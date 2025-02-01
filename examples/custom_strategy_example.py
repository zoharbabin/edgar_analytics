"""
custom_strategy_example.py

Demonstrates creating and using a custom ForecastStrategy subclass,
showing how you can intelligently tailor revenue forecasts beyond
the default ARIMA approach.

Below we define a CustomYoYStrategy that:
 - Calculates an average year-over-year (YoY) growth rate
   based on historical data in rev_dict.
 - Applies that average growth to the last known data point
   to predict the next period's revenue.

We then pass this strategy to 'forecast_revenue' to see
how it yields a custom forecast.

You can adapt this approach for seasonal logic, additional factors,
machine-learning models, or any specialized forecasting method.
"""

from edgar_analytics.forecasting import ForecastStrategy, forecast_revenue
from edgar_analytics.data_utils import parse_period_label
from edgar_analytics.logging_utils import configure_logging, get_logger

# Get a logger for this module
logger = get_logger(__name__)


class CustomYoYStrategy(ForecastStrategy):
    """
    Computes the forecast by averaging YoY growth from the data points
    and applying it to the final known revenue value.
    If there is insufficient data to compute a growth rate, defaults to 0.0.
    """

    def forecast(self, rev_dict: dict, is_quarterly: bool = False) -> float:
        if not rev_dict:
            logger.debug("Empty revenue dictionary provided")
            return 0.0

        # Sort periods by date-like label
        sorted_periods = sorted(rev_dict.keys(), key=parse_period_label)
        if len(sorted_periods) < 2:
            logger.warning(
                "Not enough data points for YoY calculation. Using last known value."
            )
            return rev_dict[sorted_periods[-1]]

        # Gather consecutive pairs to compute yoy growth
        # For simplicity, we just treat each label as ~1 year apart
        # In reality, you'd handle partial years or consistent intervals
        growth_rates = []
        prev_period = sorted_periods[0]
        prev_val = rev_dict[prev_period]

        for current_period in sorted_periods[1:]:
            curr_val = rev_dict[current_period]
            if prev_val > 0:
                yoy_growth_pct = (curr_val - prev_val) / prev_val
                growth_rates.append(yoy_growth_pct)
                logger.debug(
                    "YoY growth %s -> %s: %.2f%%",
                    prev_period, current_period, yoy_growth_pct * 100
                )
            prev_val = curr_val

        if not growth_rates:
            logger.warning("No valid growth rates computed")
            return rev_dict[sorted_periods[-1]]

        # Average growth rate
        avg_growth = sum(growth_rates) / len(growth_rates)
        last_value = rev_dict[sorted_periods[-1]]
        forecast_value = last_value * (1 + avg_growth)

        logger.info(
            "Average YoY growth: %.2f%%, Last value: %.2f, Forecast: %.2f",
            avg_growth * 100, last_value, forecast_value
        )

        # If your strategy wants to clamp negative forecasts, do so here:
        if forecast_value < 0:
            logger.warning("Negative forecast (%.2f) clamped to 0.0", forecast_value)
            return 0.0
        return forecast_value


def main():
    # Configure logging with Rich console output
    configure_logging("DEBUG")  # Set to DEBUG to see detailed calculations
    logger.info("Starting CustomYoYStrategy example")

    # Example historical revenue data (annual)
    rev_data = {
        "2019": 100.0,
        "2020": 120.0,  # ~20% growth from 2019
        "2021": 132.0,  # ~10% growth from 2020
        "2022": 158.4,  # ~20% growth from 2021
    }

    # Use our custom strategy
    custom_strategy = CustomYoYStrategy()

    # Forecast the next period (2023?), based on average YoY growth
    my_forecast = forecast_revenue(rev_data, is_quarterly=False, strategy=custom_strategy)

    logger.info("=== CustomYoYStrategy Example ===")
    logger.info("Historical data: %s", rev_data)
    logger.info("Next period forecast (CustomYoYStrategy) = %.2f", my_forecast)

    # Example of disabling forecasts (new feature)
    logger.info("\nTesting forecast disabling:")
    disabled_forecast = forecast_revenue(
        rev_data,
        is_quarterly=False,
        strategy=custom_strategy,
        disable_forecast=True  # New parameter
    )
    logger.info(
        "Forecast when disabled = %.2f (should be 0.0)",
        disabled_forecast
    )


if __name__ == "__main__":
    main()
