"""
advanced_usage_example.py

Demonstrates advanced usage of EDGAR Analytics, including:
1. Combining multiple CLI options for comprehensive analysis
2. Implementing custom forecasting strategies
3. Using enhanced logging features
4. Handling multiple tickers with different configurations

This example shows how to:
- Create a custom forecasting strategy that combines multiple approaches
- Process multiple tickers with different parameters
- Generate detailed logs and CSV outputs
- Handle SEC compliance requirements
"""

import pandas as pd
from edgar_analytics.forecasting import ForecastStrategy, forecast_revenue
from edgar_analytics.multi_period_analysis import retrieve_multi_year_data
from edgar_analytics.orchestrator import TickerOrchestrator
from edgar_analytics.logging_utils import configure_logging, get_logger
from edgar_analytics.data_utils import parse_period_label
from typing import Dict, Optional
import numpy as np

# Configure logging with Rich console output
logger = get_logger(__name__)


class HybridForecastStrategy(ForecastStrategy):
    """
    A sophisticated forecasting strategy that combines multiple approaches:
    1. Uses ARIMA for stable growth patterns
    2. Falls back to YoY average for volatile patterns
    3. Applies seasonal adjustments for quarterly data
    """

    def __init__(self, volatility_threshold: float = 0.25):
        """
        Args:
            volatility_threshold: Maximum allowed variance in growth rates
                before switching from ARIMA to YoY average approach
        """
        self.volatility_threshold = volatility_threshold
        self.logger = get_logger(self.__class__.__name__)

    def _calculate_growth_volatility(self, growth_rates: list) -> float:
        """Calculate the coefficient of variation of growth rates."""
        if not growth_rates:
            return float('inf')
        return np.std(growth_rates) / abs(np.mean(growth_rates))

    def _compute_yoy_growth_rates(self, rev_dict: Dict[str, float]) -> list:
        """Calculate year-over-year growth rates."""
        sorted_periods = sorted(rev_dict.keys(), key=parse_period_label)
        growth_rates = []
        
        for i in range(1, len(sorted_periods)):
            prev_val = rev_dict[sorted_periods[i-1]]
            curr_val = rev_dict[sorted_periods[i]]
            if prev_val > 0:
                growth_rate = (curr_val - prev_val) / prev_val
                growth_rates.append(growth_rate)
        
        return growth_rates

    def _apply_seasonal_adjustment(
        self,
        forecast: float,
        rev_dict: Dict[str, float],
        is_quarterly: bool
    ) -> float:
        """Apply seasonal adjustments for quarterly data."""
        if not is_quarterly:
            return forecast

        # Extract quarter numbers from period labels
        quarters = [
            int(parse_period_label(period).split('Q')[1][0])
            for period in rev_dict.keys()
        ]
        
        # Calculate average seasonal factors
        seasonal_factors = [1.0] * 4  # Default to no adjustment
        if len(quarters) >= 4:
            values = list(rev_dict.values())
            for q in range(1, 5):
                q_values = [
                    values[i] for i in range(len(values))
                    if quarters[i] == q
                ]
                if q_values:
                    seasonal_factors[q-1] = np.mean(q_values) / np.mean(values)

        # Determine which quarter we're forecasting
        last_quarter = quarters[-1]
        next_quarter = (last_quarter % 4) + 1
        
        # Apply seasonal adjustment
        adjusted_forecast = forecast * seasonal_factors[next_quarter-1]
        
        self.logger.debug(
            "Seasonal adjustment for Q%d: %.2f",
            next_quarter,
            seasonal_factors[next_quarter-1]
        )
        
        return adjusted_forecast

    def forecast(
        self,
        rev_dict: Dict[str, float],
        is_quarterly: bool = False
    ) -> float:
        """
        Generate forecast using the hybrid approach.
        
        Args:
            rev_dict: Dictionary of period labels to revenue values
            is_quarterly: Whether the data is quarterly
            
        Returns:
            float: Forecasted revenue value
        """
        if not rev_dict:
            self.logger.warning("Empty revenue dictionary provided")
            return 0.0

        # Calculate growth rates and their volatility
        growth_rates = self._compute_yoy_growth_rates(rev_dict)
        volatility = self._calculate_growth_volatility(growth_rates)

        self.logger.debug("Growth volatility: %.2f", volatility)

        # Choose forecasting method based on volatility
        if volatility <= self.volatility_threshold:
            try:
                # Try ARIMA for stable patterns
                from edgar_analytics.forecasting import ArimaForecastStrategy
                arima_strategy = ArimaForecastStrategy()
                forecast = arima_strategy.forecast(rev_dict, is_quarterly)
                self.logger.info("Using ARIMA forecast: %.2f", forecast)
            except Exception as e:
                self.logger.warning("ARIMA failed, falling back to YoY: %s", e)
                forecast = self._fallback_forecast(rev_dict, growth_rates)
        else:
            self.logger.info(
                "High volatility (%.2f), using YoY average",
                volatility
            )
            forecast = self._fallback_forecast(rev_dict, growth_rates)

        # Apply seasonal adjustments for quarterly data
        adjusted_forecast = self._apply_seasonal_adjustment(
            forecast, rev_dict, is_quarterly
        )

        return max(0.0, adjusted_forecast)  # Ensure non-negative

    def _fallback_forecast(
        self,
        rev_dict: Dict[str, float],
        growth_rates: list
    ) -> float:
        """Generate forecast using YoY average growth."""
        if not growth_rates:
            self.logger.warning("No growth rates available, using last value")
            return list(rev_dict.values())[-1]

        avg_growth = np.mean(growth_rates)
        last_value = list(rev_dict.values())[-1]
        forecast = last_value * (1 + avg_growth)

        self.logger.info(
            "YoY forecast: %.2f (avg growth: %.2f%%)",
            forecast, avg_growth * 100
        )
        return forecast


def analyze_ticker_advanced(
    ticker: str,
    n_years: int = 5,
    n_quarters: int = 8,
    volatility_threshold: Optional[float] = None,
    output_dir: Optional[str] = None
) -> None:
    """
    Perform advanced analysis on a ticker with custom parameters.

    Args:
        ticker: Stock symbol to analyze
        n_years: Number of years of 10-K data
        n_quarters: Number of quarters of 10-Q data
        volatility_threshold: Optional threshold for HybridForecastStrategy
        output_dir: Directory to save CSV outputs
    """
    logger.info(
        "Analyzing %s (years=%d, quarters=%d)",
        ticker, n_years, n_quarters
    )

    # Get historical data
    results = retrieve_multi_year_data(
        ticker,
        n_years=n_years,
        n_quarters=n_quarters
    )

    # Extract revenue data
    annual_rev = results.get("annual_data", {}).get("Revenue", {})
    quarterly_rev = results.get("quarterly_data", {}).get("Revenue", {})

    # Create and configure hybrid strategy
    strategy = HybridForecastStrategy(
        volatility_threshold=volatility_threshold or 0.25
    )

    # Generate forecasts
    annual_forecast = forecast_revenue(
        annual_rev,
        is_quarterly=False,
        strategy=strategy
    )
    quarterly_forecast = forecast_revenue(
        quarterly_rev,
        is_quarterly=True,
        strategy=strategy
    )

    logger.info("\nForecasts for %s:", ticker)
    logger.info("  Annual: $%.2f million", annual_forecast)
    logger.info("  Quarterly: $%.2f million", quarterly_forecast)

    # Save results if output directory provided
    if output_dir:
        import os
        from pathlib import Path

        # Ensure directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Create DataFrames for the results
        annual_df = pd.DataFrame(
            list(annual_rev.items()),
            columns=['Period', 'Revenue']
        )
        annual_df['Forecast'] = None
        annual_df.loc[len(annual_df)] = [
            'Next Period', None, annual_forecast
        ]

        quarterly_df = pd.DataFrame(
            list(quarterly_rev.items()),
            columns=['Period', 'Revenue']
        )
        quarterly_df['Forecast'] = None
        quarterly_df.loc[len(quarterly_df)] = [
            'Next Quarter', None, quarterly_forecast
        ]

        # Save to CSV
        annual_path = os.path.join(
            output_dir, f"{ticker}_annual_analysis.csv"
        )
        quarterly_path = os.path.join(
            output_dir, f"{ticker}_quarterly_analysis.csv"
        )

        annual_df.to_csv(annual_path, index=False)
        quarterly_df.to_csv(quarterly_path, index=False)

        logger.info("Results saved to:")
        logger.info("  Annual: %s", annual_path)
        logger.info("  Quarterly: %s", quarterly_path)


def main():
    # Configure logging
    configure_logging("DEBUG")

    # Example 1: Basic advanced analysis
    analyze_ticker_advanced("AAPL")

    # Example 2: Analysis with custom parameters
    analyze_ticker_advanced(
        "MSFT",
        n_years=7,
        n_quarters=12,
        volatility_threshold=0.3,
        output_dir="advanced_analysis_outputs"
    )

    # Example 3: Multiple tickers with orchestrator
    orchestrator = TickerOrchestrator()
    tech_tickers = ["GOOGL", "META", "NVDA"]
    
    for ticker in tech_tickers:
        orchestrator.analyze_company(
            ticker=ticker,
            peers=[],  # No peers for this example
            n_years=5,
            n_quarters=8,
            disable_forecast=False,
            identity="Your Name <your.email@example.com>"
        )


if __name__ == "__main__":
    main()