# EDGAR Analytics User Guide

A practical guide for equity analysts, portfolio managers, quant researchers, and individual investors who want to turn SEC EDGAR filings into actionable financial intelligence.

---

## Table of Contents

1. [Who Is This For?](#who-is-this-for)
2. [Real-World Workflows](#real-world-workflows)
   - [Earnings Season Prep](#1-earnings-season-prep)
   - [Stock Screening & Watchlist Triage](#2-stock-screening--watchlist-triage)
   - [Due Diligence Deep Dive](#3-due-diligence-deep-dive)
   - [Factor Research & Quant Screens](#4-factor-research--quant-screens)
   - [Portfolio Monitoring](#5-portfolio-monitoring)
3. [Understanding the Output](#understanding-the-output)
   - [Snapshot Metrics](#snapshot-metrics)
   - [Multi-Year Trends](#multi-year-trends)
   - [Scoring Models](#scoring-models)
   - [Alerts](#alerts)
4. [Interpreting Scoring Models](#interpreting-scoring-models)
   - [Piotroski F-Score](#piotroski-f-score-0-9)
   - [Altman Z-Score](#altman-z-score)
   - [Beneish M-Score](#beneish-m-score)
   - [DuPont Decomposition](#dupont-decomposition)
   - [Capital Efficiency (ROIC)](#capital-efficiency-roic)
5. [Alert Thresholds Reference](#alert-thresholds-reference)
6. [Working with Financial Companies](#working-with-financial-companies)
7. [Common Patterns & Recipes](#common-patterns--recipes)
8. [Caveats & Limitations](#caveats--limitations)

---

## Who Is This For?

| Role | Typical Use Case |
|------|-----------------|
| **Equity Analyst** | Earnings prep, comp analysis, red-flag screening before a pitch |
| **Portfolio Manager** | Quarterly holdings review, peer comparison, risk monitoring |
| **Quant Researcher** | Factor construction (value, quality, momentum), backtesting signals |
| **Individual Investor** | Due diligence before buying, watchlist monitoring |
| **Auditor / Risk Analyst** | Earnings manipulation screening (Beneish), distress detection (Altman) |
| **Student / Educator** | Learning financial statement analysis with real SEC data |

---

## Real-World Workflows

### 1. Earnings Season Prep

**Scenario**: Apple reports earnings next week. You want a quick snapshot of trailing fundamentals and how they compare to peers, so you're ready to evaluate the earnings release.

```bash
edgar-analytics AAPL MSFT GOOGL META --csv earnings_prep.csv
```

```python
import edgar_analytics as ea

result = ea.analyze("AAPL", peers=["MSFT", "GOOGL", "META"])

# Quick health check
m = result.main.annual_snapshot.metrics
print(f"Revenue:        ${m.revenue:,.0f}")
print(f"Net Margin:     {m.net_margin_pct:.1f}%")
print(f"ROE:            {m.roe_pct:.1f}%")
print(f"Free Cash Flow: ${m.free_cash_flow:,.0f}")
print(f"Debt/Equity:    {m.debt_to_equity:.2f}")

# Compare peer margins
for ticker, peer in result.peers.items():
    pm = peer.annual_snapshot.metrics
    print(f"{ticker}: Net Margin {pm.net_margin_pct:.1f}%, ROE {pm.roe_pct:.1f}%")

# Check for red flags
if m.alerts:
    print("Alerts:", m.alerts)
```

**What to look for**: Is the margin trajectory stable? Is D/E rising? Are there any alerts about accounting identity mismatches or negative FCF streaks?

---

### 2. Stock Screening & Watchlist Triage

**Scenario**: You have a list of 10 stocks and want to quickly identify the strongest and weakest. Sort by Piotroski score, flag any Beneish manipulation concerns, and find the most capital-efficient.

```python
import edgar_analytics as ea

tickers = ["AAPL", "MSFT", "JNJ", "JPM", "XOM", "AMZN", "TSLA", "PFE", "BA", "GE"]
results = {}

for t in tickers:
    try:
        r = ea.analyze(t)
        results[t] = r.main
    except ea.TickerFetchError:
        print(f"Skipping {t} (fetch failed)")

# Rank by Piotroski score
ranked = []
for t, ta in results.items():
    scores = ta.annual_snapshot.metrics.scores
    piotroski = scores.piotroski.score if scores and scores.piotroski else None
    beneish_flag = scores.beneish.likely_manipulator if scores and scores.beneish else None
    ranked.append((t, piotroski, beneish_flag, ta.annual_snapshot.metrics.roe_pct))

ranked.sort(key=lambda x: x[1] or 0, reverse=True)

print(f"{'Ticker':<8} {'Piotroski':>10} {'Beneish Flag':>13} {'ROE %':>8}")
print("-" * 42)
for t, pio, ben, roe in ranked:
    pio_str = str(pio) if pio is not None else "N/A"
    ben_str = "WARNING" if ben else "OK" if ben is not None else "N/A"
    print(f"{t:<8} {pio_str:>10} {ben_str:>13} {roe:>8.1f}")
```

**Rule of thumb**: Piotroski 7-9 = strong fundamentals, 0-3 = weak. Beneish `likely_manipulator=True` means M-Score > -1.78 (warrants further investigation, not a conviction).

---

### 3. Due Diligence Deep Dive

**Scenario**: You're considering a significant position in a mid-cap industrial company. You want to understand the full financial picture over the last 5 years.

```python
import edgar_analytics as ea

result = ea.analyze("CMI", n_years=5, n_quarters=12)
ta = result.main

# 5-year revenue trajectory
annual = ta.multiyear.annual_data
print("Revenue by year:", annual.get("Revenue", {}))
print("Revenue CAGR:", f"{ta.multiyear.cagr.get('Revenue', float('nan')):.1f}%")

# Margin stability
for metric in ["Gross Margin %", "Operating Margin %", "Net Margin %"]:
    series = annual.get(metric, {})
    if series:
        vals = list(series.values())
        print(f"{metric}: {min(vals):.1f}% - {max(vals):.1f}% (range)")

# Balance sheet health over time
for metric in ["Debt-to-Equity", "Free Cash Flow", "ROE %"]:
    series = annual.get(metric, {})
    print(f"{metric} by year: {series}")

# Scoring models
scores = ta.annual_snapshot.metrics.scores
if scores:
    if scores.altman:
        print(f"Altman Z-Score: {scores.altman.z_score:.2f} ({scores.altman.zone})")
    if scores.dupont:
        dp = scores.dupont
        print(f"DuPont ROE: {dp.roe_3:.1f}% = {dp.net_profit_margin:.1%} margin "
              f"x {dp.asset_turnover:.2f} turns x {dp.equity_multiplier:.2f} leverage")
    if scores.capital_efficiency:
        print(f"ROIC: {scores.capital_efficiency.roic_pct:.1f}%")

# TTM (trailing twelve months from quarterly data)
ttm = ta.multiyear.ttm
if ttm:
    print(f"TTM Revenue: ${ttm.get('Revenue', 0):,.0f}")
    print(f"TTM FCF: ${ttm.get('Free Cash Flow', 0):,.0f}")
```

**What you're checking**: Is revenue growing? Are margins stable or compressing? Is the company overleveraged (Altman Z Grey/Distress zone)? Is ROIC above cost of capital (10%+ is generally strong)?

---

### 4. Factor Research & Quant Screens

**Scenario**: You're building a quality + value factor screen. You need structured panel data for multiple companies across time.

```python
import edgar_analytics as ea

result = ea.analyze("AAPL", peers=["MSFT", "GOOGL", "META", "AMZN"])

# Panel data: MultiIndex DataFrame (ticker x period x metric)
panel = result.to_panel(frequency="annual")
print(panel.head(20))

# Filter for quality factor: high ROE, low leverage, positive FCF
snapshot_df = result.to_dataframe()
quality = snapshot_df[["ROE %", "Debt-to-Equity", "Free Cash Flow", "Accruals Ratio"]]
print(quality)

# Save for offline analysis
result.to_parquet("tech_analysis.parquet")

# Or JSON for pipelines
import json
with open("tech_analysis.json", "w") as f:
    json.dump(result.to_json_dict(), f, indent=2)

# Reload later
with open("tech_analysis.json") as f:
    restored = ea.AnalysisResult.from_json_dict(json.load(f))
```

**Output formats**:
- `to_dataframe()` — One row per ticker, good for cross-sectional comparison
- `to_panel()` — Ticker x period x metric, good for time-series analysis and backtesting
- `to_parquet()` — Three Parquet files (snapshot, panel, scores) for large-scale analysis
- `to_json_dict()` / `from_json_dict()` — JSON round-trip for API pipelines

---

### 5. Portfolio Monitoring

**Scenario**: You hold 5 positions. Every quarter, you want to run a health check and flag anything that's deteriorated.

```python
import edgar_analytics as ea
import json
from pathlib import Path

PORTFOLIO = ["AAPL", "MSFT", "JNJ", "PG", "V"]
ALERT_FILE = Path("portfolio_alerts.json")

all_alerts = {}
for ticker in PORTFOLIO:
    try:
        r = ea.analyze(ticker, alerts_config={
            "HIGH_LEVERAGE": 4.0,       # More lenient than default 3.0
            "LOW_ROE": 8.0,             # Higher bar for your holdings
        })
        ta = r.main
        m = ta.annual_snapshot.metrics
        alerts = list(m.alerts) + list(ta.extra_alerts)

        # Add scoring flags
        if m.scores and m.scores.altman and m.scores.altman.zone == "Distress":
            alerts.append(f"Altman Z in Distress zone ({m.scores.altman.z_score:.2f})")
        if m.scores and m.scores.beneish and m.scores.beneish.likely_manipulator:
            alerts.append(f"Beneish M-Score flags manipulation risk ({m.scores.beneish.m_score:.2f})")

        if alerts:
            all_alerts[ticker] = alerts
            print(f"  {ticker}: {len(alerts)} alert(s)")
            for a in alerts:
                print(f"    - {a}")
        else:
            print(f"  {ticker}: Clean")
    except ea.TickerFetchError as e:
        all_alerts[ticker] = [f"Fetch failed: {e}"]

with open(ALERT_FILE, "w") as f:
    json.dump(all_alerts, f, indent=2)
```

**Customizing thresholds**: Pass `alerts_config` to override any default. Common overrides:
- Raise `HIGH_LEVERAGE` for capital-intensive industries (utilities, REITs)
- Lower `LOW_ROE` for defensive/dividend stocks
- Raise `SUSTAINED_NEG_FCF_QUARTERS` for growth companies burning cash intentionally

---

## Understanding the Output

### Snapshot Metrics

Each ticker produces an annual snapshot (from the latest 10-K) and a quarterly snapshot (from the latest 10-Q). Key metrics:

| Category | Metrics | What They Tell You |
|----------|---------|-------------------|
| **Profitability** | Revenue, Gross Margin %, Operating Margin %, Net Margin % | Is the company making money, and how efficiently? |
| **Returns** | ROE %, ROA % | How well is equity/assets being deployed? |
| **Liquidity** | Current Ratio, Quick Ratio, Cash Ratio | Can the company pay its short-term obligations? |
| **Leverage** | Debt-to-Equity, Debt/Total Capital, Interest Coverage | How much debt risk is there? |
| **Cash Flow** | Cash from Operations, Free Cash Flow, Cash Flow Coverage | Is the company generating real cash? |
| **Quality** | Accruals Ratio, Earnings Quality, Sloan Accrual | Are earnings backed by cash or accounting tricks? |
| **Balance Sheet** | Net Debt, Net Debt/EBITDA, Tangible Equity | What does the real balance sheet look like? |

### Multi-Year Trends

`result.main.multiyear` contains:
- **annual_data** / **quarterly_data** — Time series for every metric (`{"Revenue": {"2021": 100, "2022": 110, ...}}`)
- **yoy_growth** — Year-over-year growth rates for each metric
- **cagr** — Compound annual growth rate over the full period
- **ttm** — Trailing twelve months (flow metrics summed, stock metrics latest quarter)

### Scoring Models

Accessed via `metrics.scores`:
- `.piotroski` — Fundamental strength (0-9)
- `.altman` — Bankruptcy risk (z_score, zone, model)
- `.beneish` — Earnings manipulation risk (m_score, likely_manipulator)
- `.dupont` — ROE decomposition into margin, turnover, leverage
- `.capital_efficiency` — ROIC, NOPAT, invested capital
- `.per_share` — EPS (basic/diluted), book value per share, FCF per share
- `.working_capital` — DSO, DIO, DPO, cash conversion cycle

### Alerts

Alerts are strings in `metrics.alerts` and `ta.extra_alerts`. They flag conditions that warrant attention:
- Accounting identity mismatches (Assets != Liabilities + Equity)
- Negative margins, low returns
- High leverage, poor interest coverage
- Consecutive negative FCF quarters
- Inventory or receivables spikes (potential channel stuffing)

---

## Interpreting Scoring Models

### Piotroski F-Score (0-9)

A binary scoring model that awards one point for each of 9 fundamental signals:

| Points | Signal | Category |
|--------|--------|----------|
| 1 | ROA > 0 | Profitability |
| 1 | Operating cash flow > 0 | Profitability |
| 1 | ROA increasing vs prior year | Profitability |
| 1 | Cash flow > net income (accrual quality) | Profitability |
| 1 | Long-term debt decreasing | Leverage |
| 1 | Current ratio increasing | Liquidity |
| 1 | No share dilution | Leverage |
| 1 | Gross margin increasing | Efficiency |
| 1 | Asset turnover increasing | Efficiency |

**Interpretation**:
- **8-9**: Strong fundamentals. Historically outperforms.
- **5-7**: Average. No strong signal either way.
- **0-3**: Weak fundamentals. Exercise caution.

**Best used for**: Value stock screening. Piotroski designed this to separate winners from losers within high book-to-market (cheap) stocks.

### Altman Z-Score

Predicts bankruptcy probability. The library auto-selects the appropriate model variant:

**Manufacturing model (Z)** — for asset-heavy companies (revenue/assets > 0.5):

| Zone | Z-Score | Interpretation |
|------|---------|---------------|
| Safe | > 2.99 | Low bankruptcy risk |
| Grey | 1.81 - 2.99 | Uncertain, monitor closely |
| Distress | < 1.81 | Elevated bankruptcy risk |

**Non-manufacturing model (Z'')** — for service, tech, and financial companies:

| Zone | Z-Score | Interpretation |
|------|---------|---------------|
| Safe | > 2.60 | Low bankruptcy risk |
| Grey | 1.10 - 2.60 | Uncertain, monitor closely |
| Distress | < 1.10 | Elevated bankruptcy risk |

**Check which model was used** via `scores.altman.model` ("Manufacturing Z" or "Non-manufacturing Z''").

**Best used for**: Credit analysis, distress screening, portfolio risk monitoring. Not appropriate for financial companies (banks, insurers) — the library automatically suppresses it for SIC 6000-6999.

### Beneish M-Score

Detects potential earnings manipulation using 8 financial ratios:

| M-Score | Interpretation |
|---------|---------------|
| < -1.78 | Unlikely manipulator |
| > -1.78 | Likely manipulator (warrants investigation) |

The 8 component indices (DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA) are available via `scores.beneish.indices` for deeper analysis.

**Important**: A high M-Score is a screening flag, not a conviction. It indicates accounting patterns consistent with historical manipulation cases. Always investigate the specific components that are elevated.

**Best used for**: Red-flag screening before taking a position. Particularly useful for companies with aggressive revenue recognition or unusual accruals.

### DuPont Decomposition

Breaks ROE into its drivers to understand *why* ROE is high or low:

**3-component**: ROE = Net Profit Margin x Asset Turnover x Equity Multiplier

| Driver | High Value Means | Example |
|--------|-----------------|---------|
| Net Profit Margin | Pricing power / cost control | Software companies |
| Asset Turnover | Efficient asset utilization | Retailers, asset-light models |
| Equity Multiplier | Financial leverage | Banks, leveraged companies |

Two companies can have the same ROE for very different reasons. A company with 25% ROE from high margins is fundamentally different from one with 25% ROE from 10x leverage.

**5-component** extends this by further decomposing the margin into tax burden, interest burden, and operating margin.

### Capital Efficiency (ROIC)

Return on Invested Capital measures how effectively a company generates returns on the capital invested in its operations:

| ROIC | Interpretation |
|------|---------------|
| > 15% | Excellent capital allocation, likely has a moat |
| 10-15% | Good, generating returns above typical cost of capital |
| 5-10% | Mediocre, may not be covering cost of capital |
| < 5% | Poor capital efficiency, potentially destroying value |

**Best used for**: Comparing companies across different capital structures. Unlike ROE, ROIC is not inflated by leverage.

---

## Alert Thresholds Reference

Default thresholds and when you might want to change them:

| Alert | Default | Override Key | When to Adjust |
|-------|---------|-------------|---------------|
| Negative net margin | 0% | `NEGATIVE_MARGIN` | Rarely — negative margins are almost always concerning |
| High leverage (D/E) | 3.0 | `HIGH_LEVERAGE` | Raise to 5-10 for utilities, REITs, banks |
| Low ROE | 5% | `LOW_ROE` | Lower for defensive stocks, raise for growth screens |
| Low ROA | 2% | `LOW_ROA` | Lower for capital-intensive industries |
| Net Debt/EBITDA | 3.5 | `NET_DEBT_EBITDA_THRESHOLD` | Raise for leveraged sectors |
| Interest coverage | 2.0 | `INTEREST_COVERAGE_THRESHOLD` | Standard, rarely adjusted |
| Negative FCF streak | 2 quarters | `SUSTAINED_NEG_FCF_QUARTERS` | Raise to 4 for high-growth pre-profit companies |
| Inventory spike | 30% QoQ | `INVENTORY_SPIKE_THRESHOLD` | Lower for retail (seasonal), raise for manufacturing |
| Receivables spike | 30% QoQ | `RECEIVABLE_SPIKE_THRESHOLD` | Lower if screening for channel stuffing |

```python
result = ea.analyze("AAPL", alerts_config={
    "HIGH_LEVERAGE": 5.0,
    "LOW_ROE": 10.0,
    "SUSTAINED_NEG_FCF_QUARTERS": 4,
})
```

---

## Working with Financial Companies

Banks, insurers, and other financial institutions (SIC 6000-6999) have fundamentally different financial structures. The library automatically:

- **Detects financial companies** via SIC code from the SEC Company object
- **Suppresses Altman Z-Score** — the model was not designed for financial companies
- **Suppresses Working Capital Cycle** (DSO/DIO/DPO) — receivables/inventory have different meanings for banks
- **Sets `is_financial=True`** flag on the snapshot metrics

When analyzing banks or insurers, focus on:
- Net interest margin (computed from income statement)
- ROE and ROA (most important for banks)
- Debt-to-Equity (typically very high for banks by design)
- Piotroski and Beneish scores (still computed, still useful)

---

## Common Patterns & Recipes

**Save and reload analysis results**:
```python
import json, edgar_analytics as ea

result = ea.analyze("AAPL")
with open("aapl.json", "w") as f:
    json.dump(result.to_json_dict(), f)

# Later...
with open("aapl.json") as f:
    result = ea.AnalysisResult.from_json_dict(json.load(f))
```

**Compare two companies side by side**:
```python
result = ea.analyze("HD", peers=["LOW"])
df = result.to_dataframe()
print(df[["Revenue", "Net Margin %", "ROE %", "Debt-to-Equity", "Free Cash Flow"]].T)
```

**Export 5-year panel for quant analysis**:
```python
result = ea.analyze("AAPL", peers=["MSFT"], n_years=5)
panel = result.to_panel(frequency="annual")
panel.to_csv("panel_data.csv")
```

**Use as a context manager (long-running processes)**:
```python
from edgar_analytics.orchestrator import TickerOrchestrator

with TickerOrchestrator() as orch:
    for ticker in large_ticker_list:
        result = orch.analyze(ticker)
        # Process result...
# Cache file descriptors released automatically
```

---

## Caveats & Limitations

1. **Data source**: All data comes from SEC EDGAR XBRL filings. If a company uses non-standard XBRL tags not in the synonym dictionary, some metrics may be zero or NaN.

2. **IFRS filers**: Foreign private issuers filing 20-F with IFRS labels are supported, but coverage depends on synonym matching. A warning alert is added noting figures may be in non-USD currency.

3. **Amended filings**: The library prefers 10-K/A (amended) over 10-K when the amendment was filed more recently. However, some restatements may not be captured if they use the same form type.

4. **Financial companies**: Scoring models are automatically suppressed for banks/insurers, but some ratios (current ratio, quick ratio) may still be meaningless for these companies. Interpret with caution.

5. **Forecasting**: ARIMA revenue forecasts are statistical extrapolations, not fundamental models. They work best for companies with stable, trending revenue. Volatile or cyclical companies may produce unreliable forecasts.

6. **NaN values**: When a ratio is undefined (e.g., debt-to-equity with zero equity), the library returns `NaN` rather than a misleading number. Always check for NaN before using ratios in calculations.

7. **SEC rate limits**: The SEC allows 10 requests per second. The library enforces this automatically. Analyzing many tickers in rapid succession may be slow due to rate limiting.

8. **Scoring model requirements**: Piotroski, Altman, and Beneish require prior-year data for comparison. They will be `None` if only one year of data is available.

9. **Cache security**: The disk cache uses pickle serialization. The cache directory is created with owner-only permissions (0o700), but if you're concerned about untrusted cache files, disable caching with `enable_cache=False`.

---

*For a complete list of every supported concept and metric with formulas and business context, see [METRICS_REFERENCE.md](METRICS_REFERENCE.md). For pipeline architecture, see [ARCHITECTURE.md](ARCHITECTURE.md). For API reference, see [README.md](../README.md). For contributing, see [CONTRIBUTING.md](../CONTRIBUTING.md).*
