# CLI Usage Examples

The EDGAR Analytics library provides a command-line tool `edgar-analytics`.  
Install the library with `pip install edgar-analytics`, then run:

```bash
# Basic Usage Examples

# 1) Analyze a single ticker with default settings
edgar-analytics AAPL

# 2) Analyze a main ticker with peers
edgar-analytics AAPL MSFT GOOGL

# 3) Save a CSV summary
edgar-analytics AAPL MSFT --csv analysis_outputs/aapl_msft_summary.csv

# Advanced Usage with New Options

# 4) Specify data ranges (5 years of 10-K data, 8 quarters of 10-Q data)
edgar-analytics AAPL --years 5 --quarters 8

# 5) Enable detailed logging
edgar-analytics AAPL --log-level DEBUG  # Set specific log level
edgar-analytics AAPL --debug            # Shortcut for --log-level=DEBUG

# 6) Speed up analysis by disabling forecasting
edgar-analytics AAPL --disable-forecast

# 7) Override SEC identity
edgar-analytics AAPL --identity "Your Name <your.email@example.com>"

# 8) Minimize console output
edgar-analytics AAPL --suppress-logs

# 9) Combine multiple options
edgar-analytics AAPL MSFT GOOGL \
    --years 5 \
    --quarters 8 \
    --csv analysis_outputs/tech_analysis.csv \
    --log-level INFO \
    --identity "Your Name <your.email@example.com>"
```

## CLI Options

- `TICKER`: Main ticker symbol to analyze (required)
- `[PEER1 [PEER2 ...]]`: Optional peer tickers for comparison

### Data Range Options
- `--years`, `-y`: Number of years of 10-K data to retrieve (default: 3)
- `--quarters`, `-q`: Number of quarters of 10-Q data to retrieve (default: 10)

### Output Options
- `--csv`: Path to save the CSV summary (optional)
- `--suppress-logs`: Suppress all console logs except final summary panels

### Logging Options
- `--log-level`, `-l`: Set console logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- `--debug`: Shortcut for `--log-level=DEBUG`

### Performance Options
- `--disable-forecast`: Skip revenue forecasting to speed up analysis

### SEC Compliance
- `--identity`: Override default identity for SEC API compliance
