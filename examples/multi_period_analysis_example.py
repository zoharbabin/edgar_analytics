"""
multi_period_analysis_example.py

Shows how to fetch multiple 10-K or 10-Q filings, then compute YoY growth,
CAGR, and other multi-year insights. 
Useful if you just want the multi-year data logic outside the main orchestrator.

This example demonstrates:
1. Retrieving multi-year data with configurable ranges
2. Computing growth metrics
3. Using the enhanced logging system
4. Working with the forecast disabling feature
"""

from edgar_analytics.multi_period_analysis import retrieve_multi_year_data
from edgar_analytics.forecasting import forecast_revenue
from edgar_analytics.logging_utils import configure_logging, get_logger

# Get a logger for this module
logger = get_logger(__name__)


def analyze_ticker(
    ticker: str,
    n_years: int = 3,
    n_quarters: int = 8,
    disable_forecast: bool = False
) -> None:
    """
    Analyze a ticker's multi-year performance with configurable parameters.

    Args:
        ticker: The stock symbol to analyze
        n_years: Number of years of 10-K data to retrieve
        n_quarters: Number of quarters of 10-Q data to retrieve
        disable_forecast: Whether to skip revenue forecasting
    """
    logger.info(
        "Analyzing %s (years=%d, quarters=%d, forecast=%s)",
        ticker, n_years, n_quarters, (not disable_forecast)
    )

    # Retrieve historical data with configurable ranges
    results = retrieve_multi_year_data(
        ticker,
        n_years=n_years,
        n_quarters=n_quarters
    )

    # Extract different data components
    annual_data = results.get("annual_data", {})
    quarterly_data = results.get("quarterly_data", {})
    yoy_growth = results.get("yoy_revenue_growth", {})
    cagr_revenue = results.get("cagr_revenue", 0.0)

    # Log the multi-year analysis results
    logger.info("\n=== %s Multi-Year Analysis ===", ticker)
    logger.info("Annual Revenue Data:")
    for year, revenue in annual_data.get("Revenue", {}).items():
        logger.info("  %s: $%.2f million", year, revenue)

    logger.info("\nQuarterly Revenue Data:")
    for quarter, revenue in quarterly_data.get("Revenue", {}).items():
        logger.info("  %s: $%.2f million", quarter, revenue)

    logger.info("\nYear-over-Year Revenue Growth:")
    for year, growth in yoy_growth.items():
        logger.info("  %s: %.2f%%", year, growth)

    logger.info("Revenue CAGR: %.2f%%", cagr_revenue)

    # Demonstrate forecast disabling feature
    if not disable_forecast:
        # Generate forecasts using the revenue data
        annual_forecast = forecast_revenue(
            annual_data.get("Revenue", {}),
            is_quarterly=False
        )
        quarterly_forecast = forecast_revenue(
            quarterly_data.get("Revenue", {}),
            is_quarterly=True
        )

        logger.info("\nRevenue Forecasts:")
        logger.info("  Next Annual Period: $%.2f million", annual_forecast)
        logger.info("  Next Quarter: $%.2f million", quarterly_forecast)
    else:
        logger.info("\nForecasting disabled - skipping predictions")


def main():
    # Configure logging with Rich console output
    configure_logging("INFO")  # You can change to "DEBUG" for more details

    # Example 1: Basic analysis with defaults
    analyze_ticker("AAPL")

    # Example 2: Extended historical range
    analyze_ticker("MSFT", n_years=5, n_quarters=12)

    # Example 3: Analysis without forecasting
    analyze_ticker("GOOGL", disable_forecast=True)


if __name__ == "__main__":
    main()
