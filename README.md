# EDGAR Analytics

[![PyPI version](https://img.shields.io/pypi/v/edgar-analytics)](https://pypi.org/project/edgar-analytics/)
[![CI](https://github.com/zoharbabin/edgar_analytics/actions/workflows/workflow.yml/badge.svg)](https://github.com/zoharbabin/edgar_analytics/actions/workflows/workflow.yml)
[![Python 3.10+](https://img.shields.io/pypi/pyversions/edgar-analytics)](https://pypi.org/project/edgar-analytics/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/zoharbabin/edgar_analytics?style=social)](https://github.com/zoharbabin/edgar_analytics/stargazers)

**Analyze SEC EDGAR filings in seconds.** Retrieve 10-K and 10-Q financial statements, compute 40+ GAAP/IFRS metrics and scoring models, forecast revenue with ARIMA/SARIMAX, and get actionable alerts — all from a single CLI command or Python import.

```bash
pip install edgar-analytics
edgar-analytics AAPL MSFT GOOGL --csv report.csv
```

```python
import edgar_analytics as ea
result = ea.analyze("AAPL", peers=["MSFT", "GOOGL"])
print(result.main.annual_snapshot.metrics.revenue)
df = result.to_dataframe()  # One row per ticker
```

---

> **New to the library?** See the **[User Guide](docs/USER_GUIDE.md)** for real-world workflows, scoring model interpretation, and practical recipes.

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
12. [Star History](#star-history)
13. [License](#license)

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

- **Typed Programmatic API**: `ea.analyze("AAPL", peers=["MSFT"])` returns an `AnalysisResult` dataclass with typed fields — no more dict-diving.
- **Annual & Quarterly Snapshots**: Retrieve the latest 10-K (annual) and 10-Q (quarterly) metrics for a given company.
- **Multi-Year Analysis**: Pull multiple 10-K and 10-Q statements (income, balance sheet, cash flow) to compute YoY growth, QoQ growth, and CAGR for all metrics including FCF, CapEx, ROE, ROA, and D/E.
- **40+ Financial Ratios & Metrics**:
  - Margins: Gross, Operating, Net
  - Liquidity: Current Ratio, Quick Ratio, Cash Ratio
  - Leverage: Debt-to-Equity, Debt/Total Capital, Fixed Charge Coverage, Interest Coverage
  - Quality: Accruals Ratio, Earnings Quality, Cash Flow Coverage, Sloan Accrual
  - Profitability: ROE, ROA, EBIT, EBITDA (both approximate and standard)
  - Balance sheet: Intangible ratio, goodwill ratio, net debt, lease liabilities, tangible equity
- **Scoring Models**: Piotroski F-Score, Altman Z-Score (manufacturing + non-manufacturing Z'' variants with auto-detection), Beneish M-Score, DuPont Decomposition, Capital Efficiency (ROIC/WACC), Per-Share Metrics (basic + diluted EPS), Working Capital Cycle (DSO/DIO/DPO).
- **Financial Company Detection**: Auto-detects banks and insurers via SIC code (6000-6999) and suppresses inapplicable models (Altman Z, working capital cycle) that produce garbage for financial institutions.
- **Valuation Ratios**: P/E, P/B, EV/EBITDA, and Earnings Yield from live market data (requires `pip install edgar-analytics[valuation]`).
- **TTM (Trailing Twelve Months)**: Automatically computed from quarterly data and included in results.
- **Alerts**:
  - Negative net margin
  - High leverage (debt-to-equity above threshold)
  - Consecutive quarters of negative free cash flow
  - Significant quarterly spikes in inventory/receivables
  - Accounting identity mismatch (Assets ≠ Liabilities + Equity)
- **Revenue Forecasting**:
  - By default, uses an **ARIMA-based** strategy for annual or quarterly data.
  - Easily swap in your **own forecasting logic** by implementing a custom strategy (see [Extensibility](#extensibility)).
- **Disk Caching**: SQLite-backed caching with TTL support. Past filings cached forever, current filings cached 24h. Install with `pip install edgar-analytics[cache]`.
- **CompanyFacts Cross-Validation**: Automatic cross-check against SEC XBRL CompanyFacts API. Discrepancies logged as warnings, never modifies parsed values.
- **Concurrent Peer Fetching**: Peers analyzed in parallel with `ThreadPoolExecutor` and SEC rate-limit compliance (time-based 10 req/sec limiter).
- **Output Formats**:
  - `result.to_dataframe()` — One row per ticker, columns for metrics
  - `result.to_panel()` — MultiIndex DataFrame (ticker × period × metric) for quant research
  - `result.to_parquet(path)` — Write to Parquet (`pip install edgar-analytics[parquet]`)
  - `result.to_json_dict()` / `AnalysisResult.from_json_dict()` — JSON serialization round-trip
  - CSV export via CLI
- **Command-Line Interface (CLI)**:
  - Analyze one or more tickers with a single command
  - Rich, colorized console output
  - Configurable logging levels and output formats
  - Optional forecast disabling for faster analysis
- **Comprehensive Logging**:
  - Colorized console output with configurable verbosity
  - Structured JSON logs for debugging and analysis
- **Type-Safe**: PEP 561 `py.typed` marker — full type checking support for downstream consumers.

---

## Installation

You can install EDGAR Analytics using `pip` or set it up within a local virtual environment for development.

### Using `pip`

```bash
pip install edgar-analytics

# With optional extras:
pip install edgar-analytics[cache]      # Disk caching (diskcache)
pip install edgar-analytics[parquet]    # Parquet output (pyarrow)
pip install edgar-analytics[forecast]   # Revenue forecasting (statsmodels)
pip install edgar-analytics[valuation]  # Market data & valuation ratios (yfinance)
pip install edgar-analytics[cache,parquet,forecast,valuation]  # All extras
```

### Setting Up a Local Virtual Environment

1. **Create a Virtual Environment**  

    ```bash
    python3 -m venv venv
    source ./venv/bin/activate   # or venv\Scripts\activate on Windows
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

The recommended entry point is `ea.analyze()`, which returns typed dataclasses:

```python
import edgar_analytics as ea

# Full analysis with peers — returns AnalysisResult dataclass
result = ea.analyze("AAPL", peers=["MSFT", "GOOGL"])

# Access typed fields directly
metrics = result.main.annual_snapshot.metrics
print(f"Revenue: {metrics.revenue:,.0f}")
print(f"Net Margin: {metrics.net_margin_pct:.1f}%")
print(f"Piotroski Score: {metrics.scores.piotroski.score}")

# TTM data (trailing twelve months from quarterly)
print(f"TTM Revenue: {result.main.multiyear.ttm.get('Revenue', 0):,.0f}")

# Multi-period trends (FCF, ROE, D/E over time)
annual = result.main.multiyear.annual_data
print(f"ROE % by year: {annual.get('ROE %', {})}")
print(f"FCF by year: {annual.get('Free Cash Flow', {})}")

# Export to various formats
df = result.to_dataframe()         # One row per ticker
panel = result.to_panel()          # MultiIndex: ticker × period × metric
result.to_parquet("output.parquet")  # Requires: pip install edgar-analytics[parquet]
```

**Serialization round-trip** (save/load results as JSON):

```python
import json
import edgar_analytics as ea

result = ea.analyze("AAPL")
# Serialize (NaN/Inf safely converted to null)
with open("analysis.json", "w") as f:
    json.dump(result.to_json_dict(), f)
# Deserialize
with open("analysis.json") as f:
    restored = ea.AnalysisResult.from_json_dict(json.load(f))
```

For CLI-style console output with optional CSV export:

```python
from edgar_analytics.orchestrator import TickerOrchestrator

# Context manager ensures cache file descriptors are released
with TickerOrchestrator() as orchestrator:
    result = orchestrator.analyze_company(
        ticker="AAPL",
        peers=["MSFT", "GOOGL"],
        csv_path="summary.csv",
        n_years=5,
        n_quarters=8,
        identity="Name <email>"
    )
```

---

## Core Modules

1. **`models.py`**  
   Typed dataclass models: `AnalysisResult`, `TickerAnalysis`, `FilingSnapshot`, `SnapshotMetrics`, `ScoresResult`, etc.

2. **`metrics.py`**  
   Computes 40+ financial metrics (Revenue, margins, ROE/ROA, liquidity, leverage, quality factors, EBIT/EBITDA, interest coverage, etc.).

3. **`scores.py`**  
   Scoring models: Piotroski F-Score, Altman Z-Score, Beneish M-Score, DuPont Decomposition, Capital Efficiency (ROIC), Per-Share Metrics, Working Capital Cycle, TTM computation.

4. **`forecasting.py`**  
   Strategy-based revenue forecasting. Default: `ArimaForecastStrategy` (ARIMA/SARIMAX).

5. **`multi_period_analysis.py`**  
   Multi-year/quarter data retrieval across income, balance sheet, and cash flow statements. Computes YoY growth, CAGR, FCF/CapEx/ROE/ROA/D/E time series, and derived margin ratios.

6. **`orchestrator.py`**  
   High-level orchestration with disk caching, concurrent peer fetching, CompanyFacts cross-validation, and TTM integration.

7. **`cache.py`**  
   SQLite-backed disk caching with TTL support (requires `diskcache`). Transparent no-op when not installed.

8. **`company_facts.py`**  
   SEC XBRL CompanyFacts API cross-validation. Logs discrepancies, never modifies parsed values.

9. **`reporting.py`**  
   Rich console output, CSV export, multi-year trend display with TTM.

10. **`cli.py`**  
    Click-based CLI with rich output formatting.

11. **`market_data.py`**  
    Valuation ratios (P/E, P/B, EV/EBITDA, Earnings Yield) from yfinance market data. Guards behind optional `yfinance` dependency.

12. **`logging_utils.py`, `data_utils.py`, `synonyms_utils.py`, `synonyms.py`, `config.py`**  
    Logging, data parsing, synonyms, numeric formatting, and config thresholds.

---

## Detailed Method Reference

Below is a select reference for the most commonly used methods. For a deeper or more technical reference, see the in-code docstrings.

| **Method**                                       | **Purpose**                                                                                                                                                        | **Usage**                                                                                                                                                                                   |
|--------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **`cli.main()`**                                 | Entry point for the CLI (`edgar-analytics`).                                                                                                                       | **CLI**: Invoked by console script. Not typically called directly in Python code.                                                                                                            |
| **`TickerOrchestrator.analyze_company()`**       | Orchestrates data retrieval, multi-year analysis, forecasting, and final reporting for a main ticker + optional peers.                                            | **Python**: <br/>```python<br/>orch = TickerOrchestrator()<br/>orch.analyze_company("AAPL", ["MSFT"], csv_path="out.csv")<br/>```                                                           |
| **`metrics.get_single_filing_snapshot()`**       | Retrieves the latest 10-K or 10-Q for a Company, parses it into a dictionary of metrics + filing info.                                                             | **Internally** used by `_analyze_ticker_for_metrics()`.                                                                                                                                     |
| **`multi_period_analysis.retrieve_multi_year_data()`** | Fetches multiple 10-K/10-Q filings for multi-year or multi-quarter growth analysis, CAGR, etc. Returns `annual_data`, `quarterly_data`, `yoy_revenue_growth`, and `cagr_revenue`. | **Python**: <br/>```python<br/>data = retrieve_multi_year_data("AAPL", 3, 8)<br/>print(data["annual_data"], data["cagr_revenue"])<br/>```                                                |
| **`forecasting.forecast_revenue()`**             | **Main entry** for forecasting next revenue (1-step) using a specified or default strategy (`ArimaForecastStrategy`). Negative forecasts are preserved to surface declining trends; NaN/Inf results fall back to the last known value. | **CLI**: Called under the hood by the Orchestrator. <br/>**Python**: <br/>```python<br/>from edgar_analytics.forecasting import forecast_revenue<br/>fcst = forecast_revenue(rev_dict)``` |
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

2. **JSON Log File** (opt-in for library users, automatic for CLI):
   - Written to `edgar_analytics_debug.jsonl` when enabled
   - Contains all logs at DEBUG level (and above) in structured JSON
   - Uses `RotatingFileHandler` (10 MB max, 3 backups) to prevent unbounded growth
   - Ideal for debugging or integration with log management systems
   - Includes detailed context (file, line number, function name)
   - Handlers are flushed and closed on process exit via `atexit`
   - Library users can opt in via `configure_logging(level, enable_file_logging=True)`

### Test Logging & Ticker Orchestrator

- The Orchestrator and ReportingEngine now consistently use loggers named `edgar_analytics.orchestrator` and `edgar_analytics.reporting`
- This ensures that test fixtures using `caplog.at_level(..., logger="edgar_analytics.orchestrator")` or `"edgar_analytics.reporting"` will capture and verify expected log lines
- Third-party loggers (edgar, edgartools, httpx) are automatically adjusted based on the chosen log level

---

## Extensibility

**EDGAR Analytics** is modular, letting you add or override behavior easily:

1. **Synonyms**: Extend or override synonyms in `synonyms.py` for custom labeling.
2. **Alert Thresholds**: `config.py` contains all alert thresholds (negative margins, high leverage, net debt/EBITDA, interest coverage, FCF streaks, inventory/receivables spikes). Override at runtime via `ea.analyze("AAPL", alerts_config={"HIGH_LEVERAGE": 5.0})`.
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
# To run in parallel threads: pytest --maxfail=1 --disable-warnings -v -n auto tests
```

The test suite includes fixtures for capturing and verifying log outputs, particularly useful for testing the Orchestrator and ReportingEngine components.

---

## Contributing

We welcome contributions! See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the full guide, including development setup, coding standards, and financial accuracy guidelines.

Quick links:
- [Report a bug](https://github.com/zoharbabin/edgar_analytics/issues/new?template=bug_report.yml)
- [Report a data accuracy issue](https://github.com/zoharbabin/edgar_analytics/issues/new?template=data_accuracy.yml)
- [Request a feature](https://github.com/zoharbabin/edgar_analytics/issues/new?template=feature_request.yml)
- [Ask a question](https://github.com/zoharbabin/edgar_analytics/issues/new)
- [Security policy](SECURITY.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)

---

## Star History

<a href="https://star-history.com/#zoharbabin/edgar_analytics&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=zoharbabin/edgar_analytics&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=zoharbabin/edgar_analytics&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=zoharbabin/edgar_analytics&type=Date" width="100%" />
 </picture>
</a>

---

## License

**MIT License**  
(See [LICENSE](LICENSE) for details.)

**Disclaimer**:  
This tool extracts data from public SEC filings. Always review official filings directly for investment decisions. The library and its maintainers are not responsible for any inaccuracies or any decisions made based on these outputs.

---

**Happy Analyzing!** If you find this useful, please [give us a star](https://github.com/zoharbabin/edgar_analytics) — it helps others discover the project.
