"""
multi_period_analysis_example.py

Shows how to fetch multiple 10-K or 10-Q filings, then compute YoY growth,
CAGR, and other multi-year insights. 
Useful if you just want the multi-year data logic outside the main orchestrator.
"""

from edgar_analytics.multi_period_analysis import retrieve_multi_year_data

def main():
    ticker = "AAPL"
    # Retrieve 3 years of annual data (3 x 10-K) + 8 quarters of 10-Q
    results = retrieve_multi_year_data(ticker, n_years=3, n_quarters=8)

    annual_data = results.get("annual_data", {})
    yoy_growth = results.get("yoy_revenue_growth", {})
    cagr_revenue = results.get("cagr_revenue", 0.0)

    print(f"=== {ticker} Multi-Year Analysis ===")
    print("Annual Data:", annual_data)
    print("YoY Revenue Growth:", yoy_growth)
    print(f"CAGR Revenue: {cagr_revenue:.2f}%")

if __name__ == "__main__":
    main()
