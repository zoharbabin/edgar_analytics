# EDGAR Analytics

**A Python library for analyzing SEC EDGAR filings, computing financial metrics, generating forecasts (with a strategy-based architecture), and producing clear summary reports.**

---

## Table of Contents
1. [Overview](#overview)
2. [Features](#features)
3. [Installation](#installation)
    - [Using `pip`](#using-pip)
    - [Setting Up a Local Virtual Environment](#setting-up-a-local-virtual-environment)
4. [Quick Start](#quick-start)
5. [Usage](#usage)
    - [CLI Usage](#cli-usage)
    - [Programmatic Usage](#programmatic-usage)
6. [Core Modules](#core-modules)
7. [Detailed Method Reference](#detailed-method-reference)
8. [Logging & Debugging](#logging--debugging)
9. [Extensibility](#extensibility)
10. [Testing](#testing)
11. [Contributing](#contributing)
12. [License](#license)

---

## Overview

**EDGAR Analytics** is a Python library designed to:

- Retrieve and parse financial statements from the SEC's [EDGAR](https://www.sec.gov/edgar.shtml) system (via [edgartools](https://pypi.org/project/edgartools/)).
- Compute key financial metrics (including GAAP, IFRS, intangible, goodwill, net debt, etc.).
- Optionally **forecast revenue** using a **strategy-based** architecture (ARIMA by default).
- Summarize results with rich, colorized console output and optional CSV exports.

It handles complexities such as:

- Multi-year and multi-quarter filing retrieval (10-K and 10-Q).
- Flexible synonyms to accommodate IFRS/GAAP labeling differences.
- Automatic sign-flipping of negative expenses.
- Common ratio calculations (Current Ratio, Debt-to-Equity, Free Cash Flow, etc.).
- Alert detection for negative margins, high leverage, negative free cash flow streaks, spikes in working capital.
- **Strategy-based forecasting** with a default ARIMA approach or customizable forecasting strategy.
- A fully scriptable **CLI** with rich console output.

**IFRS & GAAP Filers**  
Supports both U.S. GAAP and IFRS filers. Foreign private issuers that file IFRS-based statements (e.g., Form 20-F) are automatically handled if synonyms match IFRS-labeled line items.

---

## Features

- **Annual & Quarterly Snapshots**: Retrieve the latest 10-K (annual) and 10-Q (quarterly) metrics for a given company.
- **Multi-Year Analysis**: Pull multiple 10-K and 10-Q statements to compute YoY growth, QoQ growth, and CAGR.
- **Key Ratios & Metrics**: Current Ratio, Debt-to-Equity, Free Cash Flow, margins, intangible ratios, net debt, lease liabilities, and more.
- **Alerts**:
  - Negative net margin
  - High leverage (debt-to-equity above threshold)
  - Consecutive quarters of negative free cash flow
  - Significant quarterly spikes in inventory/receivables
- **Revenue Forecasting**:
  - By default, uses an **ARIMA-based** strategy for annual or quarterly data.
  - Easily swap in your **own forecasting logic** by implementing a custom strategy (see [Extensibility](#extensibility)).
- **Command-Line Interface (CLI)**:
  - Analyze one or more tickers with a single command
  - Rich, colorized console output
  - Configurable logging levels and output formats
  - Optional forecast disabling for faster analysis
- **Comprehensive Logging**:
  - Colorized console output with configurable verbosity
  - Structured JSON logs for debugging and analysis
- **Optional CSV Output**: Save summarized metrics to CSV.

---

## Installation

You can install EDGAR Analytics using `pip` or set it up within a local virtual environment for development.

### Using `pip`

```bash
pip install edgar-analytics
```

### Setting Up a Local Virtual Environment

1. **Create a Virtual Environment**  

    ```bash
    python3 -m venv venv
    source venv/bin/activate   # or venv\Scripts\activate on Windows
    pip install --upgrade pip setuptools wheel
    ```

2. **Install in Editable Mode (for contributing)**  

    ```bash
    pip install -e ".[test]"
    ```

    Make sure you're in the repo's root directory (where `setup.py` is located).

---

## Quick Start

Once installed, **analyze a company** via the CLI:

```bash
edgar-analytics AAPL --csv my_report.csv
```

This command:

- Fetches Apple's latest annual (10-K) and quarterly (10-Q) metrics.
- Retrieves multi-year data for deeper analysis (CAGR, YoY growth, etc.).
- Automatically forecasts next annual and quarterly revenue using the default ARIMA strategy.
- Logs everything to the console with rich, colorized output and saves a CSV summary to `my_report.csv`.

---

## Usage

### CLI Usage

Use the `edgar-analytics` command with various options to customize your analysis:

```bash
edgar-analytics TICKER [PEER1 PEER2...] [OPTIONS]
```

**Options**:
- `--csv PATH`: Save results to a CSV file
- `--years N`: Number of years of 10-K data to retrieve (default: 3)
- `--quarters N`: Number of quarters of 10-Q data to retrieve (default: 10)
- `--log-level LEVEL`: Set console logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- `--debug`: Enable debug mode (shortcut for --log-level DEBUG)
- `--disable-forecast`: Skip revenue forecasting to speed up analysis
- `--identity NAME <EMAIL>`: Override default EDGAR identity for SEC compliance
- `--suppress-logs`: Show only final summary panels for cleaner output

The console output is colorized using [Rich](https://pypi.org/project/rich/), making it easy to read and navigate results.

**Examples**:

1. **Basic Analysis**  
    ```bash
    edgar-analytics AAPL
    ```
    Analyzes AAPL with default settings (3 years, 10 quarters).

2. **Extended Historical Data**  
    ```bash
    edgar-analytics AAPL --years 5 --quarters 12
    ```
    Retrieves 5 years of annual data and 12 quarters of quarterly data.

3. **Multiple Companies with Debug Output**  
    ```bash
    edgar-analytics AAPL MSFT GOOGL --debug --csv results.csv
    ```
    Analyzes multiple companies with full debug logging and CSV output.

4. **Fast Analysis (No Forecasting)**  
    ```bash
    edgar-analytics AAPL --disable-forecast --suppress-logs
    ```
    Quick analysis without forecasting and minimal console output.

### Programmatic Usage

You can also **use the library in your own Python scripts**. For example:

```python
from edgar_analytics.orchestrator import TickerOrchestrator

def main():
    orchestrator = TickerOrchestrator()
    orchestrator.analyze_company(
        ticker="AAPL",
        peers=["MSFT", "GOOGL"],
        csv_path="analysis_outputs/summary.csv",
        n_years=5,                # Optional: override default of 3 years
        n_quarters=8,             # Optional: override default of 10 quarters
        disable_forecast=False,    # Optional: skip forecasting if True
        identity="Name <email>"   # Optional: override default SEC identity
    )

if __name__ == "__main__":
    main()
```

**Key Steps** (inside `analyze_company`):

1. Validates the ticker symbol (e.g., `AAPL`).
2. Fetches annual (10-K) and quarterly (10-Q) snapshots.
3. Retrieves multi-year data, computing YoY, CAGR, etc.
4. **Forecasts annual & quarterly revenue** using the **default ARIMA strategy** (or a custom strategy if configured).
5. Summarizes everything in rich console output and optional CSV.

> Check out the example scripts in [examples](examples) to learn more.  

---

## Core Modules

1. **`metrics.py`**  
   Computes financial metrics (Revenue, Net Income, margins, ROE, Free Cash Flow, IFRS expansions, interest coverage, etc.).

2. **`forecasting.py`**  
   Provides a **strategy-based** system for revenue forecasting.  
   - **`ArimaForecastStrategy`**: Uses ARIMA or SARIMAX if enough data is available.  
   - **`forecast_revenue()`**: A convenience function that calls the chosen strategy.

3. **`multi_period_analysis.py`**  
   Gathers multi-year or multi-quarter data, computing growth rates (YoY, QoQ) and CAGR.

4. **`orchestrator.py`**  
   High-level orchestration (`TickerOrchestrator`) to fetch EDGAR data, compute metrics, run multi-year analysis, forecast, and produce final outputs.

5. **`reporting.py`**  
   Summarizes results in a DataFrame, renders rich console output, and optionally saves to CSV.

6. **`logging_utils.py`**
   Configures dual logging system with rich console output and structured JSON logs.

7. **`data_utils.py`, `synonyms_utils.py`, `synonyms.py`, `config.py`**  
   - Helpers for data parsing, synonyms, numeric formatting, and config thresholds.

8. **`cli.py`**  
   Click-based command-line interface with rich output formatting.

---

## Detailed Method Reference

Below is a select reference for the most commonly used methods. For a deeper or more technical reference, see the in-code docstrings.

| **Method**                                       | **Purpose**                                                                                                                                                        | **Usage**                                                                                                                                                                                   |
|--------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **`cli.main()`**                                 | Entry point for the CLI (`edgar-analytics`).                                                                                                                       | **CLI**: Invoked by console script. Not typically called directly in Python code.                                                                                                            |
| **`TickerOrchestrator.analyze_company()`**       | Orchestrates data retrieval, multi-year analysis, forecasting, and final reporting for a main ticker + optional peers.                                            | **Python**: <br/>```python<br/>orch = TickerOrchestrator()<br/>orch.analyze_company("AAPL", ["MSFT"], csv_path="out.csv")<br/>```                                                           |
| **`metrics.get_single_filing_snapshot()`**       | Retrieves the latest 10-K or 10-Q for a Company, parses it into a dictionary of metrics + filing info.                                                             | **Internally** used by `_analyze_ticker_for_metrics()`.                                                                                                                                     |
| **`multi_period_analysis.retrieve_multi_year_data()`** | Fetches multiple 10-K/10-Q filings for multi-year or multi-quarter growth analysis, CAGR, etc.                                                                    | **Python**: <br/>```python<br/>data = retrieve_multi_year_data("AAPL", 3, 8)<br/>print(data["annual_data"], data["quarterly_data"])<br/>```                                                |
| **`forecasting.forecast_revenue()`**             | **Main entry** for forecasting next revenue (1-step) using a specified or default strategy (`ArimaForecastStrategy`). Clamps negatives to 0.0.                    | **CLI**: Called under the hood by the Orchestrator. <br/>**Python**: <br/>```python<br/>from edgar_analytics.forecasting import forecast_revenue<br/>fcst = forecast_revenue(rev_dict)``` |
| **`forecasting.ArimaForecastStrategy`**          | Default ARIMA-based strategy that tries ARIMA/SARIMAX model candidates and picks one by AIC.                                                                       | **Custom**: <br/>```python<br/>strategy = ArimaForecastStrategy()<br/>fcst = forecast_revenue(rev_data, strategy=strategy)<br/>```                                                         |
| **`reporting.ReportingEngine.summarize_metrics_table()`** | Builds a final summary of metrics for all tickers, renders rich console output, and optionally saves to CSV.                                                      | **Internally** used by `analyze_company()`, though you can call it directly with a valid `metrics_map`.                                                                                      |
| **`TickerDetector.validate_ticker_symbol()`**     | Regex-based validation of ticker format.                                                                                                                           | Used to filter out invalid tickers (e.g., `@@@`).                                                                                                                                           |

---

## Refined FCF Computation

Starting with **v0.1.0+**, EDGAR Analytics applies a smarter fallback when a direct **"capital expenditures"** line item is missing from the cash flow statement. Specifically:

1. **Checks for an explicit "capital expenditures" row** (via synonyms).  
2. **If not found**:  
   - **Takes the net investing outflow** (if negative).  
   - **Subtracts** intangible purchases and business acquisitions (when detected).  
   - The remainder is treated as **approximated "capex."**  

This helps avoid over-counting large M&A deals or intangible acquisitions as ongoing capital expenditures. You can see this improvement in:
- `synonyms_utils.compute_capex_single_period` and `compute_capex_for_column`
- `metrics.py` for single filing snapshots.
- `multi_period_analysis.py` for multi-quarter data.

**Disclaimer**:  
Even with these refinements, certain unusual transactions may still appear in overall investing outflows. Thus, the library's fallback remains an approximation for investor/analyst guidance only.

---

## Logging & Debugging

EDGAR Analytics provides two parallel logging outputs:

1. **Console (Rich)**:
   - Level controlled by `--log-level` (INFO by default) or `--debug`
   - Colorized, minimal, user-friendly log messages
   - Can be suppressed with `--suppress-logs` for cleaner output
   - Supports multiple log levels (DEBUG/INFO/WARNING/ERROR/CRITICAL)

2. **JSON Log File**:
   - Always written to `edgar_analytics_debug.jsonl`
   - Contains all logs at DEBUG level (and above) in structured JSON
   - Ideal for debugging or integration with log management systems
   - Includes detailed context (file, line number, function name)

### Test Logging & Ticker Orchestrator

- The Orchestrator and ReportingEngine now consistently use loggers named `edgar_analytics.orchestrator` and `edgar_analytics.reporting`
- This ensures that test fixtures using `caplog.at_level(..., logger="edgar_analytics.orchestrator")` or `"edgar_analytics.reporting"` will capture and verify expected log lines
- Third-party loggers (edgar, edgartools, httpx) are automatically adjusted based on the chosen log level

---

## Extensibility

**EDGAR Analytics** is modular, letting you add or override behavior easily:

1. **Synonyms**: Extend or override synonyms in `synonyms.py` for custom labeling.
2. **Alert Thresholds**: `config.py` contains thresholds for negative margins, high leverage, and negative FCF streaks.
3. **Additional Metrics**: Add new ratio logic to `metrics.py` or wherever suitable.
4. **Custom Forecast Strategies**:  
   - The library exposes a `ForecastStrategy` abstract base class in `forecasting.py`.
   - By default, we use `ArimaForecastStrategy`. You can **create your own** strategy subclass and pass it to `forecast_revenue()` (or the Orchestrator if you modify its internal logic).
    ```python
    from edgar_analytics.forecasting import ForecastStrategy, forecast_revenue
    from edgar_analytics.data_utils import parse_period_label

    class MyGrowthStrategy(ForecastStrategy):
        def forecast(self, rev_dict: dict, is_quarterly=False) -> float:
            # Example: always increase last known revenue by +5%
            if not rev_dict:
                return 0.0
            sorted_periods = sorted(rev_dict.keys(), key=parse_period_label)
            last_val = rev_dict[sorted_periods[-1]]
            return last_val * 1.05

    # Usage:
    data_map = {"2020": 100, "2021": 200}
    fcst = forecast_revenue(data_map, strategy=MyGrowthStrategy())
    print(fcst)
    ```
5. **Reporting Formats**: `ReportingEngine` supports rich console output and CSV. Extend it for Excel, JSON, or any other output format.

---

## Testing

We use **pytest** to ensure reliability and coverage.  
From the project root (where `pytest` can discover `tests/`):

```bash
pytest -v --cov=edgar_analytics --cov-report=term-missing
```

The test suite includes fixtures for capturing and verifying log outputs, particularly useful for testing the Orchestrator and ReportingEngine components.

---

## Contributing

1. **Fork** & **Clone** the repo.
2. **Create a branch** for your feature or fix.
3. **Write Tests** for your changes; ensure existing tests still pass.
4. **Format your code** to comply with PEP8, PEP20, and PEP257.
5. **Push** to your fork and create a pull request.
6. **Discuss** & **refine** in the PR as needed.

### Coding Standards

- **PEP8**: Style guidelines.
- **PEP20**: Zen of Python (readability counts).
- **PEP257**: Docstring guidelines.
- **Security**: Validate all inputs, use robust error handling, do not trust external data blindly.
- **Tests**: Provide tests for new features or modifications to existing features.

---

## License

**MIT License**  
(See [LICENSE](LICENSE) for details.)

**Disclaimer**:  
This tool extracts data from public SEC filings. Always review official filings directly for investment decisions. The library and its maintainers are not responsible for any inaccuracies or any decisions made based on these outputs.

---

**Happy Analyzing!**
