"""
single_ticker_example.py

Demonstrates how to analyze a single ticker (e.g., AAPL) using the
TickerOrchestrator. Fetches both annual and quarterly data, performs
forecasting, logs results, and writes a final CSV summary.
"""

from edgar_analytics.orchestrator import TickerOrchestrator

def main():
    # Instantiate the orchestrator
    orchestrator = TickerOrchestrator()

    # Run analysis on Apple, with no peer comparisons, saving CSV output
    orchestrator.analyze_company(
        ticker="AAPL",
        peers=[],
        csv_path="examples_outputs/aapl_single_ticker_summary.csv"
    )

if __name__ == "__main__":
    main()
