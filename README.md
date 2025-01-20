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
8. [Logging](#logging)
9. [Extensibility](#extensibility)
10. [Testing](#testing)
11. [Contributing](#contributing)
12. [License](#license)

---

## Overview

**EDGAR Analytics** is a Python library designed to:

- Retrieve and parse financial statements from the SEC’s [EDGAR](https://www.sec.gov/edgar.shtml) system (via [edgartools](https://pypi.org/project/edgartools/)).
- Compute key financial metrics (including GAAP, IFRS, intangible, goodwill, net debt, etc.).
- Optionally **forecast revenue** using a **strategy-based** architecture (ARIMA by default).
- Summarize results (logging + CSV outputs).

It handles complexities such as:

- Multi-year and multi-quarter filing retrieval (10-K and 10-Q).
- Flexible synonyms to accommodate IFRS/GAAP labeling differences.
- Automatic sign-flipping of negative expenses.
- Common ratio calculations (Current Ratio, Debt-to-Equity, Free Cash Flow, etc.).
- Alert detection for negative margins, high leverage, negative free cash flow streaks, spikes in working capital.
- **Strategy-based forecasting** with a default ARIMA approach or customizable forecasting strategy.
- A fully scriptable **CLI**.

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
- **Command-Line Interface (CLI)**: Analyze one or more tickers with a single command.
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
   pip install -e .[test]
   ```

   Make sure you’re in the repo’s root directory (where `setup.py` is located).

---

## Quick Start

Once installed, **analyze a company** via the CLI:

```bash
edgar-analytics AAPL --csv my_report.csv
```

This command:

- Fetches Apple’s latest annual (10-K) and quarterly (10-Q) metrics.
- Retrieves multi-year data for deeper analysis (CAGR, YoY growth, etc.).
- Automatically forecasts next annual and quarterly revenue using the default ARIMA strategy.
- Logs everything to the console and saves a CSV summary to `my_report.csv`.

---

## Usage

### CLI Usage

Use the `edgar-analytics` command, with arguments for the main ticker, optional peers, and an optional `--csv` path:

```bash
edgar-analytics TICKER [PEER1 [PEER2 ...]] [--csv output.csv]
```

**Examples**:

1. **Single Ticker**  
   ```bash
   edgar-analytics AAPL
   ```
   Fetches data for AAPL, logs results to the console.

2. **With Peers + CSV**  
   ```bash
   edgar-analytics AAPL MSFT GOOGL --csv analysis_results.csv
   ```
   Compares AAPL to MSFT & GOOGL, logs aggregated results, and writes a CSV to `analysis_results.csv`.

3. **Invalid Tickers**  
   If any ticker is invalid (e.g., `@BADTICKER`), the CLI logs a warning and skips it.

### Programmatic Usage

You can also **use the library in your own Python scripts**. For example:

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

**Key Steps** (inside `analyze_company`):

1. Validates the ticker symbol (e.g., `AAPL`).
2. Fetches annual (10-K) and quarterly (10-Q) snapshots.
3. Retrieves multi-year data, computing YoY, CAGR, etc.
4. **Forecasts annual & quarterly revenue** using the **default ARIMA strategy** (or a custom strategy if configured).
5. Summarizes everything in the console logs or an optional CSV.

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
   Summarizes results in a DataFrame, logs them, and optionally saves to CSV.

6. **`data_utils.py`, `synonyms_utils.py`, `synonyms.py`, `config.py`, `logging_utils.py`**  
   - Helpers for data parsing, synonyms, logging, numeric formatting, and config thresholds.

7. **`cli.py`**  
   Click-based command-line interface for `edgar-analytics`.

---

## Detailed Method Reference

Below is a select reference for the most commonly used methods. For a deeper or more technical reference, see the in-code docstrings.

| **Method**                                       | **Purpose**                                                                                                                                                        | **Usage**                                                                                                                                                                                   |
|--------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **`cli.main()`**                                 | Entry point for the CLI (`edgar-analytics`).                                                                                                                       | **CLI**: Invoked by console script. Not typically called directly in Python code.                                                                                                            |
| **`TickerOrchestrator.analyze_company()`**       | Orchestrates data retrieval, multi-year analysis, forecasting, and final reporting for a main ticker + optional peers.                                            | **Python**: <br/>```python<br/>orch = TickerOrchestrator()<br/>orch.analyze_company("AAPL", ["MSFT"], csv_path="out.csv")<br/>```                                                           |
| **`metrics.get_single_filing_snapshot()`**       | Retrieves the latest 10-K or 10-Q for a Company, parses it into a dictionary of metrics + filing info.                                                             | **Internally** used by `_analyze_ticker_for_metrics()`.                                                                                                                                     |
| **`multi_period_analysis.retrieve_multi_year_data()`** | Fetches multiple 10-K/10-Q filings for multi-year or multi-quarter growth analysis, CAGR, etc.                                                                    | **Python**: <br/>```python<br/>data = retrieve_multi_year_data("AAPL", 3, 8)<br/>print(data["annual_data"], data["quarterly_data"])<br/>```                                                |
| **`forecasting.forecast_revenue()`**             | **Main entry** for forecasting next revenue (1-step) using a specified or default strategy (`ArimaForecastStrategy`). Clamps negatives to 0.0.                    | **CLI**: Called under the hood by the Orchestrator. <br/>**Python**: <br/>```python<br/>from edgar_analytics.forecasting import forecast_revenue<br/>fcst = forecast_revenue(rev_dict)``` |
| **`forecasting.ArimaForecastStrategy`**          | Default ARIMA-based strategy that tries ARIMA/SARIMAX model candidates and picks one by AIC.                                                                       | **Custom**: <br/>```python<br/>strategy = ArimaForecastStrategy()<br/>fcst = forecast_revenue(rev_data, strategy=strategy)<br/>```                                                         |
| **`reporting.ReportingEngine.summarize_metrics_table()`** | Builds a final summary of metrics for all tickers, logs them, and optionally saves to CSV.                                                                         | **Internally** used by `analyze_company()`, though you can call it directly with a valid `metrics_map`.                                                                                      |
| **`TickerDetector.validate_ticker_symbol()`**     | Regex-based validation of ticker format.                                                                                                                           | Used to filter out invalid tickers (e.g., `@@@`).                                                                                                                                           |

---

## Logging

- **Default Logging Level**: DEBUG (to stdout).
- Customize by editing `logging_utils.py` or adjusting the logger in your own script.
- Key log levels used:
  - **INFO**: Summaries, important progress messages.
  - **WARNING**: Alerts or potential issues (e.g., negative margin, high leverage).
  - **ERROR**: Failures in retrieval or parsing.

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
5. **Reporting Formats**: `ReportingEngine` logs and optionally writes CSV. Extend it for Excel, JSON, or any other output.

---

## Testing

We use **pytest** to ensure reliability and coverage.  
From the project root (where `pytest` can discover `tests/`):

```bash
pytest -v --cov=edgar_analytics --cov-report=term-missing
```

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
