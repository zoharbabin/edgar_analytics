# CLI Usage Examples

The EDGAR Analytics library provides a command-line tool `edgar-analytics`.  
Install the library with `pip install edgar-analytics`, then run:

```bash
# 1) Analyze a single ticker and log results
edgar-analytics AAPL

# 2) Analyze a main ticker with peers
edgar-analytics AAPL MSFT GOOGL

# 3) Save a CSV summary
edgar-analytics AAPL MSFT --csv analysis_outputs/aapl_msft_summary.csv
```
