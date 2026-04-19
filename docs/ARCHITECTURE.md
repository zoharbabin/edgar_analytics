# Data Pipeline Architecture

This document explains how edgar_analytics extracts and validates financial metrics from SEC filings, and why the hybrid approach was chosen.

## Pipeline Overview

```
SEC EDGAR filings
      |
      v
edgartools (XBRL rendering)
      |
      v
Structured DataFrames (one row per line item, columns per period)
      |
      v
YTD de-cumulation (data_utils.py — quarterly income/CF only)
      |
      v
Synonym matching (synonyms.py + synonyms_utils.py)
      |
      v
Computed metrics (metrics.py)
      |
      v
CompanyFacts cross-validation (company_facts.py)  <-- advisory, never overrides
      |
      v
Scores, forecasting, reporting
```

## YTD De-Cumulation

SEC XBRL 10-Q income statements and cash flow statements report **year-to-date cumulative** figures, not single-quarter values. A Q3 filing's revenue figure is Q1+Q2+Q3 combined. This is a fundamental property of SEC XBRL that affects all filers.

The library handles this in two places:

1. **Single-filing path** (`_convert_statement_df`): edgartools returns columns with period suffixes like `2025-09-30 (Q3)` and `2025-09-30 (YTD)`. The library prefers `(Q*)` single-quarter columns when both exist, and strips the suffixes.

2. **Multi-period path** (`decumulate_quarterly`): `MultiFinancials` stitches quarterly filings into plain date columns, but the values remain cumulative. A detection heuristic identifies cumulative patterns (monotonically increasing positive values within a fiscal year), then computes `Q_n = YTD_n - YTD_{n-1}` to recover single-quarter figures. This runs before synonym matching and TTM computation.

**Balance sheet data is never de-cumulated** — balance sheets are point-in-time snapshots, not flow statements.

## Two Legs of Validation

### Leg 1: Synonym Matching on Rendered Tables

The primary extraction path. `edgartools` parses XBRL filings into structured financial statement DataFrames where each row is a line item and each column is a period. The synonym engine (`synonyms.py`) maps ~580 label variants across 79 keys to standardized metric names, using a two-pass algorithm:

1. **Exact match** — normalized (NFKC lowercase) comparison against the DataFrame index.
2. **Partial match** — substring containment, ranked by coverage ratio (synonym length / label length) and absolute value as tiebreaker.

**Why this works well:**
- Rendered tables include subtotals, derived rows, and line items that may not have their own XBRL tag. CompanyFacts only returns individually tagged concepts.
- Synonym matching handles label variation naturally. A company that labels revenue as "Net sales," "Total revenues," or "Revenue from contracts" all match the same key.
- Coverage spans both US GAAP and IFRS labels, plus XBRL taxonomy element names (e.g., `us-gaap:Revenues`, `ifrs-full:Revenue`), so it works regardless of whether edgartools emits the raw tag or the human-readable label.

**Where it can fail:**
- Extension taxonomies with non-standard labels (e.g., a company inventing its own revenue line item name).
- Partial match can pick the wrong row when a substring appears in multiple line items (mitigated by coverage ratio ranking).
- Duplicate index entries are resolved by taking the row with the highest absolute sum, which is usually correct but not guaranteed.

### Leg 2: CompanyFacts Cross-Validation

An independent check against `data.sec.gov/api/xbrl/companyfacts/`. After synonym matching produces metrics, the `CompanyFactsClient` fetches the SEC's own aggregated XBRL data for the same company and compares five high-level metrics (Revenue, Net Income, Total Assets, Total Liabilities, Total Equity) with a 1% tolerance.

**Key design choice:** Discrepancies are logged as warnings but **never override** the synonym-parsed values. The pipeline remains authoritative; CompanyFacts is a safety net.

**Why advisory-only:**
- CompanyFacts covers only ~5 top-level concepts. Overriding would help for those five but leave the other 70+ metrics unvalidated and potentially inconsistent with the overridden values.
- A discrepancy might indicate a CompanyFacts staleness issue (different fiscal period, restated filing) rather than a synonym matching error.
- Logging the discrepancy gives operators visibility without silently changing numbers users already see.

**Where it can fail:**
- CompanyFacts may return data from a different fiscal period than the filing being analyzed.
- Some companies have sparse XBRL tagging, so CompanyFacts may have no data for a concept that synonyms successfully extracted from rendered tables.

## Why Hybrid Beats Either Alone

| Failure mode | Synonym-only | CompanyFacts-only | Hybrid |
|---|---|---|---|
| Non-standard label | Misses or wrong row | N/A (uses tags) | CompanyFacts flags discrepancy |
| Extension taxonomy tag | Still matches human label | Misses entirely | Synonym matching succeeds |
| Derived/subtotal rows | Extracted from table | Not available | Synonym matching succeeds |
| Duplicate index rows | Best-sum heuristic (usually right) | N/A | CompanyFacts flags if wrong |
| Sparse XBRL tagging | Falls back to partial match | Returns nothing | Synonym provides data |

Either approach alone has a class of failures the other catches. The hybrid closes both gaps.

## Residual Risk

Filers where **both** paths fail: non-standard labels AND sparse XBRL tagging. This is a small tail, concentrated in micro-cap and foreign private issuers. The library handles this through:

- **Coverage scoring** — metrics that couldn't be extracted are `NaN`, not zero.
- **Alert system** — flags unusual patterns (negative FCF streaks, inventory spikes) that may indicate parsing issues.
- **Debug logging** — every synonym lookup and CompanyFacts comparison is logged at DEBUG level for investigation.

## Cross-Validation Coverage

CompanyFacts currently validates 5 of the 79 synonym keys. The validated metrics are the highest-impact ones (revenue, net income, balance sheet totals), but operational sub-metrics (OpEx, R&D, depreciation, working capital components, cash flow items) rely solely on synonym matching. Extending `_CONCEPT_MAP` in `company_facts.py` to cover more concepts is a straightforward improvement path.

## Key Files

| File | Role |
|---|---|
| `synonyms.py` | Master dictionary: 79 keys, ~580 label variants (GAAP + IFRS + XBRL tags) |
| `synonyms_utils.py` | Matching algorithm: exact/partial, coverage ranking, sign flipping, CapEx fallback |
| `company_facts.py` | Cross-validation client: fetches SEC XBRL data, compares with 1% tolerance |
| `metrics.py` | Single-period metric computation using synonym lookups |
| `multi_period_analysis.py` | Multi-period extraction using `find_best_synonym_row` |
| `data_utils.py` | DataFrame normalization: dedup, numeric coercion, period parsing, YTD de-cumulation |
| `orchestrator.py` | Wires both legs together: synonym extraction, then cross-validation |
