# EDGAR Analytics

**A Python library for analyzing SEC EDGAR filings, computing financial metrics, generating forecasts, and producing clear summary reports.**

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
8. [Logging](#logging)
9. [Extensibility](#extensibility)
10. [Testing](#testing)
11. [Contributing](#contributing)
12. [License](#license)

---

## Overview

EDGAR Analytics is a Python library designed to retrieve and parse financial statements from the SEC’s [EDGAR](https://www.sec.gov/edgar.shtml) system, compute key financial metrics, forecast revenue (using ARIMA/SARIMAX models), and produce summarized reports in both logs and CSV format. It aims to streamline **fundamental** data analysis and handle complexities such as:

- Multi-year and multi-quarter retrieval
- Flexible XBRL synonyms to accommodate various company-specific row labels
- Automatic detection and flipping of negative expense values
- Common ratio calculations (e.g., Current Ratio, Debt-to-Equity, Margin %)
- Basic alerts (e.g., negative margin, high leverage, negative free cash flow streaks)
- ARIMA-based forecasting for annual and quarterly revenue trends

This library is built on top of [edgartools](https://pypi.org/project/edgartools/) (for SEC data retrieval and partial XBRL parsing), as well as popular Python data-science libraries (`pandas`, `numpy`, `statsmodels`).

---

## Features

- **Annual & Quarterly Snapshots**: Retrieve latest 10-K (annual) and 10-Q (quarterly) metrics for a given company (ticker).
- **Multi-Year Analysis**: Pull multiple 10-K and 10-Q statements to compute YoY (year-over-year), QoQ (quarter-over-quarter) growth, and CAGR (compound annual growth rate).
- **Key Ratios & Metrics**: Compute Revenue, Net Income, Current Ratio, Debt-to-Equity, Free Cash Flow, ROE, ROA, margin percentages, and more.
- **Alerts**:
  - Negative net margin
  - High leverage (debt-to-equity above threshold)
  - Low ROE/ROA
  - Consecutive quarters of negative free cash flow
  - Significant quarterly spikes in inventory or receivables
- **Revenue Forecast**: ARIMA-based model for annual or quarterly series (with fallback if data points are insufficient).
- **Modular & Extensible**: Adjust synonyms, thresholds, or sub-modules easily.
- **Command-Line Interface (CLI)**: Simplify usage with a single command to analyze multiple tickers at once.
- **Optional CSV Output**: Save summarized metrics to a CSV file.

---

## Installation

You can install EDGAR Analytics using `pip` or set it up within a local virtual environment for development purposes. 

### Using `pip`

To install the library directly from PyPI, use the following command:

```bash
pip install edgar-analytics
```

### Setting Up a Local Virtual Environment

1. **Create a Virtual Environment**

   Navigate to your project directory and create a virtual environment named `venv`:

   ```bash
   python3 -m venv venv
   source venv/bin/activate # on windows: venv\Scripts\activate
   pip install --upgrade pip setuptools wheel
   ```

2. **Install the Library in Editable Mode**

   If you're planning to contribute to the library, it's useful to install it in editable mode. This allows you to make changes to the source code and have them immediately reflected without needing to reinstall.

   ```bash
   pip install -e .
   pip install -e .[test] # For running tests and contributing - install the development dependencies.
   ```

   **Note**: Ensure you're in the root directory of the repository (where `setup.py` is located) when running this command.

## Quick Start

Once installed, you can quickly analyze a company from the command line:

```bash
edgar-analytics AAPL --csv my_report.csv
```

This command:

- Fetches AAPL’s latest annual (10-K) and quarterly (10-Q) metrics.
- Retrieves multi-year data for deeper analysis (CAGR, YoY growth, etc.).
- Logs results, alerts, and a final summary table to the console.
- Saves a CSV summary of metrics to `my_report.csv` if requested.

---

## Usage

### CLI Usage

The CLI entry point is `edgar-analytics`. Its usage pattern is:

```bash
edgar-analytics TICKER [PEER1 [PEER2 ...]] [--csv output.csv]
```

**Examples**:

1. **Single Ticker, No CSV**

   ```bash
   edgar-analytics AAPL
   ```

   This fetches data for Apple (AAPL) only and logs it to the console.

2. **Single Ticker + Multiple Peers, With CSV**

   ```bash
   edgar-analytics AAPL MSFT GOOGL --csv analysis_results.csv
   ```

   This compares AAPL to MSFT and GOOGL, logging aggregated results and writing a summary CSV to `analysis_results.csv`.

3. **Invalid Tickers**

   If you pass an invalid ticker (e.g., `@BADTICKER`), the CLI logs a warning and skips it:

   ```bash
   edgar-analytics AAPL @BADTICKER
   ```

**CLI Arguments**:

- `TICKER`: The primary ticker symbol.
- `[PEER1 [PEER2 ...]]`: (Optional) Additional tickers to compare.
- `--csv/-c`: (Optional) A CSV file path to store summarized metrics.

### Programmatic Usage

You can also use EDGAR Analytics within your own Python scripts. Below is a simple example to analyze a single ticker (with no peers) and retrieve the final metrics map:

```python
from edgar_analytics.orchestrator import TickerOrchestrator

def main():
    orchestrator = TickerOrchestrator()
    orchestrator.analyze_company(
        ticker="AAPL",
        peers=[],
        csv_path="analysis_outputs/aapl_summary.csv"
    )

if __name__ == "__main__":
    main()
```

This code:

1. Creates a `TickerOrchestrator` object that orchestrates fetching of EDGAR data, computing metrics, multi-year analysis, revenue forecast, and so forth.
2. Calls `analyze_company()` with `ticker="AAPL"`, no peers, and a CSV output path.
3. Outputs logs to the console and writes the summarized metrics to `analysis_outputs/aapl_summary.csv`.

**Key Steps Internally**:

- Validates the ticker symbol.
- Creates an `edgartools.Company` object (via [edgartools](https://pypi.org/project/edgartools/)).
- Gathers annual and quarterly snapshots (10-K, 10-Q).
- Retrieves multi-year data for YoY growth and CAGR.
- Runs forecasting to get a single-step forecast for annual and quarterly revenue.
- Evaluates additional quarterly alerts (e.g., negative FCF streak).
- Invokes `ReportingEngine` to format results, log alerts, and optionally save a CSV.

---

## Core Modules

1. **`metrics.py`**  
   Computes key financial ratios and metrics from a company's balance sheet, income statement, and cash flow statement.

2. **`forecasting.py`**  
   Provides ARIMA-based forecasting for annual or quarterly revenue time series.

3. **`multi_period_analysis.py`**  
   Gathers multi-year or multi-quarter data and computes growth rates, CAGR, and checks additional alerts for negative free cash flow, spikes in working capital, etc.

4. **`orchestrator.py`**  
   A high-level class (`TickerOrchestrator`) that coordinates ticker validation, data retrieval, ratio computation, multi-year analysis, forecasting, and final reporting.

5. **`reporting.py`**  
   Summarizes all computed metrics (e.g., from multiple tickers), logs them, and optionally saves to CSV.

6. **`data_utils.py` & `synonyms_utils.py`**  
   - **`data_utils.py`**: Helpers to parse textual period labels, ensure data frames, coerce numeric columns, etc.  
   - **`synonyms_utils.py`**: Finds matching synonyms in XBRL-labeled financial statements (e.g., “Revenue,” “Sales,” “us-gaap:Revenues”) and handles sign-flipping for negative expense lines.

7. **`config.py` & `synonyms.py`**  
   - **`config.py`**: Global alert thresholds for margins, leverage, negative FCF streaks, etc.  
   - **`synonyms.py`**: A master dictionary of synonyms for wide coverage of typical and GAAP-labeled lines.

8. **`cli.py`**  
   Implements a Click-based CLI command `edgar-analytics`.

---

## Detailed Method Reference

Below is a comprehensive table detailing the library’s primary methods across modules. For each method, you’ll find:

- **Internal Logic**: Key steps in the method’s implementation.
- **Dependencies**: Other methods and third-party libraries it relies on.
- **Purpose**: Rationale for the method and what it accomplishes.
- **Usage (CLI vs Python)**: How you can invoke or leverage each method via the command-line interface (where applicable) and programmatically in your own code.

> **Note**: Internal or “private” methods (prefixed with `_`) are included for completeness. They are generally intended for internal use and not typically called by end users directly.

| **Method** | **Internal Logic** | **Dependencies** | **Purpose** | **Usage (CLI vs Python)** |
|------------|---------------------|------------------|-------------|---------------------------|
| **1. `cli.main()`** <br/>*(in `cli.py`)* | 1. Uses Click to parse command-line arguments for the main ticker plus optional peers and CSV path.<br/>2. Instantiates a `TickerOrchestrator` and calls `analyze_company()`. | - Built-in Python <br/>- [Click](https://click.palletsprojects.com/) <br/>- `TickerOrchestrator.analyze_company()` from `orchestrator.py` | Provides the command-line entry point (`edgar-analytics`) for analyzing one or more tickers and outputting results. | **CLI**: Invoked automatically via `edgar-analytics TICKER [PEERS...] --csv file.csv`. <br/>**Python**: Not typically called directly; used by the console script defined in `setup.py`. |
| **2. `orchestrator.validate_ticker_symbol(ticker)`** <br/>*(in `orchestrator.py`)* | Checks if the ticker is 1–10 alphanumeric characters. Returns `True` if valid, `False` otherwise. | None (pure Python) | Ensures malformed or suspicious ticker symbols are rejected. | **CLI**: Invoked internally before processing each ticker.<br/>**Python**: Not usually called by end users. Used by `analyze_company()`. |
| **3. `orchestrator.TickerOrchestrator.analyze_company(ticker, peers, csv_path)`** <br/>*(public method)* | 1. Validates main ticker using `validate_ticker_symbol`.<br/>2. Creates a new `Company` object (from `edgartools`).<br/>3. Gathers metrics via `_analyze_ticker_for_metrics()` for main ticker and each valid peer.<br/>4. Aggregates results into a `metrics_map`.<br/>5. Uses `ReportingEngine.summarize_metrics_table()` to produce logs and optional CSV. | - `validate_ticker_symbol()`<br/>- `edgartools.Company`<br/>- `_analyze_ticker_for_metrics()`<br/>- `ReportingEngine` | Primary orchestration method for analyzing a main ticker (and optional peers). Fetches snapshots, multi-year data, forecasts, and runs final reporting. | **CLI**: Called implicitly when you run `edgar-analytics TICKER PEERS...`. <br/>**Python**: Manually instantiate `TickerOrchestrator` and call `.analyze_company()`. Example: <br/>```python<br/>orch = TickerOrchestrator()<br/>orch.analyze_company("AAPL", ["MSFT"], csv_path="out.csv")<br/>``` |
| **4. `orchestrator.TickerOrchestrator._analyze_ticker_for_metrics(ticker)`** <br/>*(private method)* | 1. Instantiates an `edgartools.Company` object.<br/>2. Fetches latest 10-K/10-Q with `get_single_filing_snapshot()`.<br/>3. Calls `retrieve_multi_year_data()` for multi-year stats.<br/>4. Runs `forecast_revenue_arima()` for forecasting.<br/>5. Gathers additional quarterly info (`analyze_quarterly_balance_sheets()`) and checks alerts. | - `edgartools.Company`<br/>- `metrics.get_single_filing_snapshot()`<br/>- `multi_period_analysis.retrieve_multi_year_data()`<br/>- `forecasting.forecast_revenue_arima()`<br/>- `multi_period_analysis.analyze_quarterly_balance_sheets()`<br/>- `multi_period_analysis.check_additional_alerts_quarterly()` | Consolidates data gathering, metric calculations, forecasts, and alert compilation for a single ticker. | **CLI**: Internally used by `analyze_company()`. <br/>**Python**: Not intended for direct use—rely on `analyze_company()`. |
| **5. `orchestrator.TickerOrchestrator.main()`** <br/>*(demonstration method)* | 1. Demonstrates usage by analyzing “AAPL” with peers “MSFT”/”GOOGL.”<br/>2. Writes CSV to `analysis_outputs/summary.csv`. | - `analyze_company()`<br/>- Built-in Python | Simple example if `python orchestrator.py` is run directly; not used in typical workflows. | **CLI**: Not a CLI command by default. <br/>**Python**: Run `python orchestrator.py` to see a usage example. |
| **6. `metrics.compute_ratios_and_metrics(balance_df, income_df, cash_df)`** | 1. Finds relevant rows (Revenue, Net Income, etc.) via `synonyms_utils.find_synonym_value()`. <br/>2. Calculates key ratios (Current Ratio, D/E, margins, FCF, etc.). <br/>3. Constructs a dictionary of standard metrics + any alerts. | - `synonyms_utils.find_synonym_value()` <br/>- `flip_sign_if_negative_expense()`<br/>- `config.ALERTS_CONFIG`<br/>- `numpy`, `pandas` | Core routine to compute financial metrics from 3 DataFrames (Balance, Income, Cash Flow). | **CLI**: Automatically called for each ticker filing snapshot. <br/>**Python**: Call if you have your own data frames:  <br/>```python<br/>metrics_dict = compute_ratios_and_metrics(bs, inc, cf)<br/>``` |
| **7. `metrics.get_filing_info(filing_obj)`** | 1. Extracts `form_type`, `filing_date`, `company`, `accession_no`.<br/>2. Defaults to `"Unknown"` if missing. | - `edgartools.Filing` objects | Provides uniform dictionary of basic filing metadata. | **CLI**: Invoked inside `get_single_filing_snapshot()`. <br/>**Python**: Called automatically; rarely used alone. |
| **8. `metrics.get_single_filing_snapshot(comp, form_type)`** | 1. Retrieves the latest filing of `form_type` using `comp.get_filings(...).latest()`. <br/>2. Converts `.financials` to DataFrames (`balance_df`, `income_df`, `cash_df`). <br/>3. Calls `compute_ratios_and_metrics()` to produce a metric dict. <br/>4. Returns a dict of `{"metrics": {...}, "filing_info": {...}}`. | - `edgartools.Company`<br/>- `compute_ratios_and_metrics()`<br/>- `data_utils.ensure_dataframe()`<br/>- `data_utils.make_numeric_df()` | Fetches one annual or quarterly statement, returning comprehensive metrics + filing metadata. | **CLI**: Used automatically in `_analyze_ticker_for_metrics()`. <br/>**Python**: Helpful if you want a single filing’s metrics, e.g.:  <br/>```python<br/>snapshot = get_single_filing_snapshot(my_company, "10-Q")<br/>``` |
| **9. `forecasting.forecast_revenue_arima(rev_dict, is_quarterly=False)`** | 1. Sorts data points by period. <br/>2. If data points < 4, returns 0.0. <br/>3. Tries ARIMA / SARIMAX models, picks best by AIC. <br/>4. Forecasts one step ahead, clamps negatives to 0.0. | - `statsmodels.arima.model.ARIMA`<br/>- `statsmodels.tsa.statespace.sarimax.SARIMAX`<br/>- `numpy`<br/>- `data_utils.parse_period_label()` | Produces a 1-step forecast of revenue (annual or quarterly). | **CLI**: Invoked automatically during `analyze_company()`. <br/>**Python**: Standalone usage if you have revenue data, e.g.:  <br/>```python<br/>fcst = forecast_revenue_arima({"2018":100, "2019":200, "2020":300}, False)<br/>``` |
| **10. `multi_period_analysis.retrieve_multi_year_data(ticker, n_years, n_quarters)`** | 1. Gets multiple 10-K (`head(n_years)`) & 10-Q (`head(n_quarters)`) via `MultiFinancials`.<br/>2. Extracts statements, numeric conversion.<br/>3. Calls `extract_period_values()` for Revenue/Net Income. <br/>4. Computes growth rates, CAGR. | - `edgartools.Company`, `MultiFinancials`<br/>- `extract_period_values()`<br/>- `compute_growth_series()`<br/>- `compute_cagr()` | Gathers multiple 10-K/10-Q for YoY/QoQ growth analysis, CAGR, etc. | **CLI**: Used in `_analyze_ticker_for_metrics()`. <br/>**Python**: Optionally call:  <br/>```python<br/>data = retrieve_multi_year_data("AAPL", 3, 8)<br/>``` |
| **11. `multi_period_analysis.extract_period_values(df, debug_label)`** | 1. Sorts columns by `parse_period_label()`. <br/>2. Finds best row for “Revenue” & “Net Income” using `find_best_row_for_synonym()`. <br/>3. Returns dict like `{"Revenue": {...}, "Net Income": {...}}`. | - `find_best_row_for_synonym()`<br/>- `data_utils.parse_period_label()`<br/>- `pandas`/`numpy` | Extracts the relevant numeric series for Revenue/Net Income from a multi-column statement. | **CLI**: Runs inside `retrieve_multi_year_data()`. <br/>**Python**: Not typically used alone. |
| **12. `multi_period_analysis.compute_growth_series(values_dict)`** | 1. Sorts keys by `parse_period_label()`. <br/>2. Calculates period-over-period % growth. <br/>3. Returns a dict keyed by the period. | - `data_utils.parse_period_label()`<br/>- `numpy` | Computes YoY or QoQ growth from a series of values. | **CLI**: Automatically in `retrieve_multi_year_data()`. <br/>**Python**: Example usage: <br/>```python<br/>growth = compute_growth_series({"2020":100, "2021":150})<br/># => {"2021":50.0}<br/>``` |
| **13. `multi_period_analysis.compute_cagr(values_dict)`** | 1. Sorts periods by `parse_period_label()`. <br/>2. Does `(last_val / first_val)^(1 / year_span) - 1`. <br/>3. Returns a percentage float. | - `data_utils.parse_period_label()` <br/>- `numpy` | Finds Compound Annual Growth Rate from earliest to latest. | **CLI**: Used in `retrieve_multi_year_data()` for revenue CAGR. <br/>**Python**:  <br/>```python<br/>cagr = compute_cagr({"2018":100, "2021":200})<br/># => ~26%<br/>``` |
| **14. `multi_period_analysis.analyze_quarterly_balance_sheets(comp, n_quarters)`** | 1. Retrieves up to `n_quarters` of 10-Q via `MultiFinancials`.<br/>2. Extracts `inventory`, `receivables`, calculates `free_cf`. <br/>3. Returns a dict for each item keyed by period. | - `edgartools.Company`<br/>- `MultiFinancials`<br/>- `find_multi_col_values()`<br/>- `data_utils.parse_period_label()` | Extracts certain quarterly B/S & C/F data for negative FCF or working capital spikes. | **CLI**: Used by `_analyze_ticker_for_metrics()`. <br/>**Python**: Standalone usage:  <br/>```python<br/>qs = analyze_quarterly_balance_sheets(my_company, 8)<br/>``` |
| **15. `multi_period_analysis.check_additional_alerts_quarterly(data_map)`** | 1. Checks consecutive negative `free_cf`. <br/>2. Checks for >30% spike in `inventory`, `receivables`. <br/>3. Returns alerts as a list of strings. | - `ALERTS_CONFIG` <br/>- `data_utils.parse_period_label()` | Generates red flags about negative FCF streaks, high inventory/receivables. | **CLI**: Called after `analyze_quarterly_balance_sheets()`. <br/>**Python**: Could be used if you have your own data map. |
| **16. `reporting.ReportingEngine.summarize_metrics_table(metrics_map, main_ticker, csv_path)`** <br/>*(public method)* | 1. Builds snapshot dictionary via `_build_snapshot_dict()`. <br/>2. Creates a DataFrame, reorders columns, applies numeric formatting. <br/>3. Logs the table. <br/>4. Saves CSV if `csv_path` given. <br/>5. Logs snapshot alerts, multi-year data, forecasts. | - `_build_snapshot_dict()`<br/>- `_prepare_dataframe_for_presentation()`<br/>- `_maybe_save_csv()`<br/>- `pandas`, `numpy` | Main reporting endpoint, generating final summary (logs + optional CSV). | **CLI**: Called automatically at the end of `analyze_company()`. <br/>**Python**: You can create your own `ReportingEngine` and call it if you have a custom `metrics_map`. |
| **17. `reporting.ReportingEngine._build_snapshot_dict(metrics_map)`** | 1. Iterates each ticker’s data. <br/>2. Pulls “annual_snapshot” or fallback “quarterly_snapshot.” <br/>3. Builds a dictionary for DataFrame creation. | Internal method only. | Gathers high-level metrics for DataFrame usage. | **CLI**: Internal usage in `summarize_metrics_table()`. <br/>**Python**: Not typically called directly. |
| **18. `reporting.ReportingEngine._prepare_dataframe_for_presentation(df_summary, main_ticker)`** | 1. Reorders columns in a desired sequence.<br/>2. Formats numeric columns (e.g., “1.23B”). <br/>3. Places `main_ticker` row first. | - `data_utils.custom_float_format()`<br/>- `pandas` | Readies the summary table for clearer logging & CSV output. | **CLI**: Internal usage for final output formatting. <br/>**Python**: Not used directly. |
| **19. `reporting.ReportingEngine._log_dataframe_snapshot(df_summary)`** | 1. Logs each row with column-aligned formatting. <br/>2. Uses Python’s formatting to align fields. | - Built-in logging<br/>- `pandas` | Neatly prints the DataFrame in the logs. | **CLI**: Always done near the end of `summarize_metrics_table()`. <br/>**Python**: Typically not called by user code. |
| **20. `reporting.ReportingEngine._maybe_save_csv(df_summary, csv_path)`** | 1. Checks `csv_path` validity. <br/>2. Creates parent directories if needed. <br/>3. Writes `df_summary.to_csv()`. | - `pathlib.Path`<br/>- `pandas` | Saves summarized data to CSV if requested. | **CLI**: Invoked if `--csv` is specified. <br/>**Python**: Wrapped in `summarize_metrics_table()`. |
| **21. `reporting.ReportingEngine._log_snapshot_alerts(snapshot_dict)`** | 1. Logs any snapshot-level “Alerts” at WARN level. <br/>2. Logs “No snapshot alerts” if empty. | - Built-in logging | Surfaces negative margin, high leverage, etc., from snapshot. | **CLI**: Done automatically at the end of analysis logs. <br/>**Python**: Internal method. |
| **22. `reporting.ReportingEngine._log_additional_quarterly_alerts(metrics_map)`** | 1. Checks each ticker’s `"extra_alerts"`. <br/>2. Logs them at WARN level. | - Built-in logging | Summarizes negative FCF streak or big spikes from quarterly data. | **CLI**: Automatic near the end of analysis logs. <br/>**Python**: Internal method. |
| **23. `reporting.ReportingEngine._log_multi_year_and_forecast(metrics_map)`** | 1. For each ticker, pulls YoY, CAGR, forecast from `metrics_map["multiyear"]` / `metrics_map["forecast"]`. <br/>2. Prints commentary on growth, contraction, or forecast. | - Built-in logging<br/>- `numpy.mean()` (for YoY average) | Concludes the summary with multi-year trend & forecast data. | **CLI**: Always invoked in `summarize_metrics_table()`. <br/>**Python**: Internal usage. |

---

## Logging

- **Default Logging Level**: The library logs to `stdout` at the **DEBUG** level by default.
- **Customization**: You can customize logging by modifying the `get_logger` function in `logging_utils.py`.
- **Log Levels**:
  - **DEBUG**: Detailed information, typically of interest only when diagnosing problems (e.g., DataFrame shapes, numeric conversions, model fitting details).
  - **INFO**: Confirmation that things are working as expected (e.g., summary tables, multi-year commentary).
  - **WARNING**: An indication that something unexpected happened or indicative of some problem (e.g., alerts like negative margin, high leverage, negative FCF).
  - **ERROR**: Due to a more serious problem, the software has not been able to perform some function (e.g., failures retrieving or parsing data).

**Example Log Output**:

```
[2025-01-18 10:00:00] [INFO] [orchestrator.py:45 - analyze_company()] Analyzing company: AAPL
[2025-01-18 10:00:01] [INFO] [orchestrator.py:50 - analyze_company()] Comparing AAPL with peers: ['MSFT', 'GOOGL']
...
[2025-01-18 10:00:10] [WARNING] [reporting.py:120 - _log_snapshot_alerts()] Alerts for AAPL (snapshot):
  - Debt-to-Equity above 3.0 (high leverage)
```

---

## Extensibility

EDGAR Analytics is designed with modularity and extensibility in mind, allowing developers to customize and extend its functionality seamlessly.

1. **Custom Synonyms**:  
   Extend or override `SYNONYMS` in `synonyms.py` if your target filings use different labels for known items (e.g., "Operating Revenue" vs "Net Sales").

2. **Alert Thresholds**:  
   Adjust `ALERTS_CONFIG` in `config.py` to change triggers for negative margin, high leverage, low ROE/ROA, or negative FCF streaks.

3. **Additional Metrics**:  
   Modify `metrics.py` if you need new metrics (e.g., `EBIT margin`, `DSO`, `Inventory turns`) that require additional synonyms or ratio logic.

4. **Forecasting**:  
   If you need different forecasting methods, you can replace or augment `forecast_revenue_arima()` in `forecasting.py` with your own approach.

5. **Reporting Output**:  
   The `ReportingEngine` in `reporting.py` can be extended to output Excel (`.xlsx`), JSON, or other formats as needed.

6. **Integration with Other Tools**:  
   Incorporate other data sources or analysis tools by creating new modules or extending existing ones, following the established structure and patterns.

7. **Adding New Alerts**:  
   Implement new alert conditions by modifying the alert logic within `metrics.py` or `multi_period_analysis.py` and updating `config.py` accordingly.

8. **Testing Enhancements**:  
   Extend the test suite in the `tests/` directory to cover new features or edge cases as you expand the library.

**Best Practices for Extending the Library**:

- **Maintain Consistency**: Follow the existing coding standards and module structures to ensure maintainability.
- **Comprehensive Testing**: Add tests for new functionalities to maintain the reliability of the library.
- **Documentation**: Update the `README.md` and docstrings to reflect new features and usage instructions.
- **Version Control**: Use branches effectively when developing new features to isolate changes and facilitate collaboration.

---

## Testing

The project uses **pytest** for testing to ensure reliability and correctness.

1. **Install Test Dependencies**

   If you haven't already set up a virtual environment, refer to the [Setting Up a Local Virtual Environment](#setting-up-a-local-virtual-environment) section.

   Then, install the development dependencies:

   ```bash
   pip install -e .[test]
   ```

2. **Run Tests**

   Execute all tests using:

   ```bash
   pytest
   ```

3. **Check Coverage (Optional)**

   To check test coverage, you can integrate with `pytest-cov`:

   ```bash
   pytest --cov=edgar_analytics
   ```

   This will provide a coverage report indicating which parts of the codebase are covered by tests.

---

## Contributing

Contributions, bug reports, and feature requests are welcome! To contribute:

1. **Fork the Repository**  
   Click the "Fork" button at the top-right of the repository page on GitHub to create your own copy.

2. **Clone Your Fork**  
   ```bash
   git clone https://github.com/your-username/edgar_analytics.git
   cd edgar_analytics
   ```

3. **Create a New Branch**  
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Make Your Changes**  
   Implement your feature or fix. Ensure that your code follows the existing style and structure.

5. **Run Tests**  
   Ensure all tests pass and add new tests for your changes:
   ```bash
   pytest
   ```

6. **Commit Your Changes**  
   ```bash
   git add .
   git commit -m "Add feature: your feature description"
   ```

7. **Push to Your Fork**  
   ```bash
   git push origin feature/your-feature-name
   ```

8. **Create a Pull Request**  
   Navigate to the original repository on GitHub and click "Compare & pull request." Provide a clear description of your changes.

**Guidelines**:

- **Code Quality**: 
   - Adhere to PEP8, PEP20, and PEP257.  
   - Provide complete, testable, performant code that is easy to monitor, maintain, and debug.  
   - Consolidate repetitive logic into shared utilities or functions for maintainability and extensibility.  
   - Ensure robust tests coverage, error-handling, edge-cases coverage, and strict security measures.  
- **Documentation**: Update the `README.md` and docstrings to reflect any changes or new features.
- **Testing**: Include tests for new functionalities and ensure existing tests pass.
- **Commit Messages**: Write clear and concise commit messages that describe the changes made.

---

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT). See the [LICENSE](LICENSE) file for details.

**Disclaimer**: This tool extracts data from public SEC filings. Always review official filings directly when making investment decisions. The library and its maintainers are not responsible for any inaccuracies or for decisions made based on these outputs.

---

**Happy Analyzing! 🚀**
