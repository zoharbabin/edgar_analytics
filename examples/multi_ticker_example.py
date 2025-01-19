"""
multi_ticker_example.py

Illustrates comparing a main ticker (e.g., AAPL) with multiple peers 
(e.g., MSFT, GOOGL). The orchestrator fetches each company's EDGAR data,
performs ratio calculations, forecasting, and logs a comparative summary.
"""

from edgar_analytics.orchestrator import TickerOrchestrator

def main():
    orchestrator = TickerOrchestrator()

    # Main ticker with two peers
    main_ticker = "AAPL"
    peer_tickers = ["MSFT", "GOOGL"]

    # Output CSV path
    csv_output = "examples_outputs/tech_comparison_summary.csv"

    orchestrator.analyze_company(
        ticker=main_ticker,
        peers=peer_tickers,
        csv_path=csv_output
    )

if __name__ == "__main__":
    main()
