"""
custom_strategy_example.py

Demonstrates creating and using a custom ForecastStrategy subclass,
showing how you can intelligently tailor revenue forecasts beyond
the default ARIMA approach.

Below we define a CustomYoYStrategy that:
 - Calculates an average year-over-year (YoY) growth rate
   based on historical data in rev_dict.
 - Applies that average growth to the last known data point
   to predict the next period’s revenue.

We then pass this strategy to 'forecast_revenue' to see
how it yields a custom forecast.

You can adapt this approach for seasonal logic, additional factors,
machine-learning models, or any specialized forecasting method.
"""

from edgar_analytics.forecasting import ForecastStrategy, forecast_revenue
from edgar_analytics.data_utils import parse_period_label


class CustomYoYStrategy(ForecastStrategy):
    """
    Computes the forecast by averaging YoY growth from the data points
    and applying it to the final known revenue value.
    If there is insufficient data to compute a growth rate, defaults to 0.0.
    """

    def forecast(self, rev_dict: dict, is_quarterly: bool = False) -> float:
        if not rev_dict:
            return 0.0

        # Sort periods by date-like label
        sorted_periods = sorted(rev_dict.keys(), key=parse_period_label)
        if len(sorted_periods) < 2:
            # Not enough data to calculate a growth rate
            # => fallback to the last known revenue
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
            prev_val = curr_val

        if not growth_rates:
            return rev_dict[sorted_periods[-1]]

        # Average growth rate
        avg_growth = sum(growth_rates) / len(growth_rates)
        last_value = rev_dict[sorted_periods[-1]]
        forecast_value = last_value * (1 + avg_growth)

        # If your strategy wants to clamp negative forecasts, do so here:
        if forecast_value < 0:
            return 0.0
        return forecast_value


def main():
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

    print("=== CustomYoYStrategy Example ===")
    print("Historical data:", rev_data)
    print(f"Next period forecast (CustomYoYStrategy) = {my_forecast:.2f}")


if __name__ == "__main__":
    main()
