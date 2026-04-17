# Changelog

## [0.9.1] - 2026-04-17

### Engineering
- **Time-based SEC rate limiter**: Replaced `Semaphore(10)` with a time-based lock enforcing 100ms minimum interval between requests (10 req/sec), matching SEC's actual rate-limit policy.
- **Thread-safe `_norm_idx_cache`**: Added `threading.Lock` around the global normalized-index cache to prevent data races during concurrent peer analysis.
- **CI lint and type-check**: Added ruff lint (`E,F,W`) and mypy type-check steps to the GitHub Actions workflow (non-blocking with `continue-on-error`).
- **20-F currency warning**: Snapshots from 20-F/20-F/A filings now include an alert noting figures may be in a non-USD reporting currency.
- **`sales_marketing` in `_EXPENSE_LABELS`**: Added missing label so negative selling & marketing expenses are correctly sign-flipped.

### Testing
- Added Sloan Accrual test with known input/output values (verifies formula correctness).
- Added Sloan Accrual absent-when-no-prior-year test.
- Added 20-F currency warning test.
- Added `sales_marketing` in `_EXPENSE_LABELS` assertion.
- Added `_norm_idx_lock` thread-safety assertion.
- Test count: 355 → 360 (+5 tests).

## [0.9.0] - 2026-04-17

### XBRL Coverage (High Priority)
- **NCI equity synonym**: Added `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` to `total_equity`. Companies with noncontrolling interests (subsidiaries) previously got equity=0, breaking D/E, ROE, Altman Z, and accounting identity checks.
- **Revenue with assessed tax**: Added `RevenueFromContractWithCustomerIncludingAssessedTax` to `revenue`. Telecom/utility filers that include assessed taxes in revenue previously got revenue=0.
- **Long-term debt noncurrent**: Added `LongTermDebtNoncurrent` to `long_term_debt`. Companies reporting only the noncurrent portion previously got LTD=0, understating leverage ratios.
- **TextBlock tag cleanup**: Removed `CostOfSalesPolicyTextBlock`, `InventoryDisclosureTextBlock`, `AdvertisingCostsPolicyTextBlock`, and `ResearchAndDevelopmentExpensePolicy` from quantitative synonym groups. These are disclosure-only tags that could match before real numeric tags.

### Pipeline Fixes
- **alerts_config threaded to quarterly alerts**: `check_additional_alerts_quarterly()` now accepts `alerts_config` parameter, threaded from orchestrator. User overrides for `SUSTAINED_NEG_FCF_QUARTERS`, `INVENTORY_SPIKE_THRESHOLD`, `RECEIVABLE_SPIKE_THRESHOLD` are no longer silently ignored.
- **CompanyFacts multi-concept validation**: Cross-validation now tries `RevenueFromContractWithCustomerExcludingAssessedTax` before `Revenues`, and includes the NCI equity variant. Covers post-2018 filers that don't use the older `us-gaap:Revenues` tag.
- **HTTP retry with backoff**: `CompanyFactsClient._get_json()` retries on SEC 429/503 with exponential backoff (1s → 2s → 4s). 403 (IP blocklist) is not retried.

### Testing
- Added synonym integrity tests: no TextBlock in quantitative groups, NCI equity present, assessed-tax revenue present, LTD noncurrent present.
- Added CompanyFacts retry/backoff tests (429 retries, 403 does not).
- Added CompanyFacts multi-concept fallback tests.
- Added alerts_config override test for `check_additional_alerts_quarterly`.
- Test count: 346 → 355 (+9 tests).

## [0.8.2] - 2026-04-17

### Financial Accuracy (Significant)
- **Beneish AQI securities fix**: AQI now includes both short-term AND long-term investments/securities (per Beneish 1999). Previously only short-term investments were passed, inflating AQI for companies with significant long-term securities holdings.
- **CAGR consistency**: Returns NaN (not 0.0) for insufficient data and too-short periods. Semantically correct — NaN means "cannot compute," not "no growth."
- **ROE consistency**: `metrics.py` now returns NaN for negative equity, matching DuPont decomposition behavior. Previously metrics.py computed a misleading negative-equity ROE while DuPont returned NaN for the same input.

### Engineering (Significant)
- **CLI catches TickerFetchError**: CLI now catches `EdgarAnalyticsError` (parent of `TickerFetchError`) and exits with code 1. Previously, network/resolution failures produced unhandled tracebacks.
- **Prior-year financial suppression**: `get_prior_annual_metrics()` now accepts `is_financial` parameter, threaded from orchestrator. Banks' prior-year metrics correctly suppress inapplicable models.
- **CI matrix includes Python 3.13**: Test workflow now runs on 3.10, 3.11, 3.12, and 3.13 — matching the setup.py classifier.
- **requirements.txt aligned with setup.py**: Removed statsmodels from mandatory dependencies (it's an optional `[forecast]` extra).

### Testing
- Added CLI TickerFetchError catch test.
- Added CAGR insufficient-data NaN test.
- Updated negative-equity test (ROE now NaN, consistent with DuPont).
- Updated prior-year metrics mock to verify is_financial threading.
- Test count: 344 → 346 (+2 tests).

## [0.8.1] - 2026-04-17

### Fixes
- **P/E ratio uses diluted EPS**: `compute_valuation_ratios()` now computes P/E as `share_price / eps_diluted` when diluted EPS is available, falling back to `market_cap / net_income` otherwise. Standard practice for conservative valuation.
- **`RawMetrics` return annotation**: `compute_ratios_and_metrics()` now returns `-> RawMetrics` so type checkers enforce the TypedDict schema at the function boundary.
- **`share_price` parameter active**: The `share_price` parameter in `compute_valuation_ratios()` is now used for diluted-EPS-based P/E (previously accepted but unused).

### Testing
- Updated valuation ratio tests: P/E diluted-EPS path + market_cap/NI fallback path both covered.
- Test count: 343 → 344 (+1 test).

## [0.8.0] - 2026-04-17

### Financial Intelligence
- **Financial company detection**: Auto-detects banks/insurers via SIC code (6000-6999) from the SEC Company object. Suppresses inapplicable models (Altman Z-Score, working capital cycle DSO/DIO/DPO) that produce garbage for financial institutions. Adds `is_financial` flag to `SnapshotMetrics`.
- **Valuation ratios**: New `ValuationRatios` dataclass with P/E, P/B, EV/EBITDA, and Earnings Yield. Computed from yfinance market data + filing metrics. Guards behind `HAS_YFINANCE`.
- **TTM ratio fix**: Percentage metrics (Gross Margin %, Operating Margin %, Net Margin %, ROE %, ROA %, etc.) now use the latest quarter's value instead of incorrectly summing 4 quarters.

### Engineering
- **alerts_config fully wired**: The `alerts_config` parameter now flows end-to-end from `analyze()` through `get_prior_annual_metrics()` to `compute_ratios_and_metrics()`. Previously accepted but silently ignored.
- **Peer exception narrowing**: Peer analysis futures loop now catches `(TickerFetchError, OSError, ValueError, KeyError)` instead of bare `Exception`, with `exc_info=True` for debuggable tracebacks.
- **RawMetrics TypedDict**: Internal metrics dict schema enforced via `TypedDict` — typos in underscore-prefixed keys (`_total_assets`, `_sga`, etc.) are now caught by type checkers.
- **Version in SEC user-agent**: Default identity string now includes `edgar-analytics/{version}` so SEC can identify library version in request logs.

### Data Export
- **to_parquet() multi-file**: Writes three Parquet files — snapshot metrics, annual panel data, and per-ticker scores — instead of just the flat snapshot.
- **to_panel(frequency=)**: New `frequency` parameter (`"annual"` or `"quarterly"`) for panel data export. Default `"annual"` preserves backward compatibility.

### Altman Z-Score
- **Docstring**: Added comprehensive docstring documenting the three model variants (Z, Z'', Z'), the auto-detection heuristic (revenue/total_assets > 0.5), and the `is_manufacturing` override.

### Testing
- Added alerts_config end-to-end test (verifies HIGH_LEVERAGE override actually suppresses alert)
- Added financial company detection tests (SIC 6020 bank vs SIC 3571 hardware)
- Added valuation ratio tests (P/E, P/B, EV/EBITDA, edge cases)
- Added TTM ratio metric tests (Gross Margin % not summed)
- Added to_panel quarterly frequency test
- Added to_parquet multi-file tests (panel + scores files)
- Added SnapshotMetrics is_financial and valuation round-trip tests
- Added version-in-identity test
- Added synonym coverage integration test (AAPL CompanyFacts vs synonym lists)
- Test count: 317 -> 343 (+26 tests).

## [0.7.0] - 2026-04-17

### Critical Fixes
- **TTM computation**: Balance sheet (stock) metrics now use the latest quarter's value instead of nonsensically summing 4 quarters. Flow metrics (Revenue, Net Income, etc.) still sum correctly.
- **SGA synonym coverage**: Added `us-gaap:SellingGeneralAndAdministrativeExpense` (the most common combined SGA tag) to the synonym dictionary. Previously, SGA defaulted to 0 for many companies, making Beneish SGAI always neutral.
- **Main ticker failure handling**: `analyze()` now raises `TickerFetchError` when the primary ticker cannot be resolved, instead of silently returning empty results.

### Financial Accuracy
- **Altman Z-Score**: Added Z'' (double-prime) model for non-manufacturing/service companies. The original Z-Score manufacturing model is inappropriate for ~60% of S&P 500 companies. Model selection is automatic based on asset turnover, with an explicit `is_manufacturing` override.
- **DuPont decomposition**: ROE is now NaN when equity is negative, with a `negative_equity_warning` flag. Previously, sign inversions produced misleading results.
- **Beneish GMI**: When current gross margin drops to zero (but was previously positive), GMI now correctly signals high manipulation risk instead of defaulting to neutral (1.0).
- **EPS fallback**: Diluted EPS is NaN when not separately reported, instead of silently duplicating the basic EPS value.
- **Pro-forma synonyms removed**: `BusinessAcquisitionsProFormaRevenue` and `BusinessAcquisitionsProFormaNetIncomeLoss` removed from revenue and net income synonym lists (M&A disclosure items, not actual reported values).
- **IFRS D&A British spelling**: Added "amortisation" variants to the depreciation & amortization synonym list for better IFRS coverage.

### Engineering
- **Specific exception types**: Main ticker path now raises `TickerFetchError` (a subclass of `EdgarAnalyticsError`) instead of catching broad `Exception`. CompanyFacts validation catches `(OSError, ValueError, KeyError)` specifically.
- **Reduced public API surface**: `__all__` trimmed from 45+ names to ~20 essential exports. Internal utilities (`find_synonym_value`, `make_numeric_df`, etc.) remain importable from their submodules but are no longer in the top-level namespace.
- **File logging opt-in**: Library usage no longer writes log files to disk by default. The CLI enables file logging automatically. Library consumers can opt in via `configure_logging(level, enable_file_logging=True)`.
- **Configurable alert thresholds**: `analyze()` now accepts an `alerts_config` parameter for runtime threshold overrides (e.g., `alerts_config={"HIGH_LEVERAGE": 5.0}`).
- **Version attribute**: Added `edgar_analytics.__version__`.
- **Python 3.13**: Added to supported versions in setup.py classifiers.

### Testing
- Added synonym dictionary integrity tests (all keys exist, non-empty, no duplicates, no pro-forma tags, SGA combined tag present, British spelling present).
- Added config module tests (defaults exist, overrides merge correctly, originals not mutated).
- Added market_data module tests (yfinance present/absent, API errors, missing fields).
- Added layout_strategy and panel_layout tests (abstract class, rendering, value formatting).
- Added comprehensive regression tests for all v0.7.0 fixes (TTM flow vs stock, Z'', GMI, DuPont, EPS, alerts config, version, public surface).
- Test count: 250 -> 317 (+67 tests).

## [0.6.1] - Previous release

Wire cache + CompanyFacts into pipeline, expand multi-period to BS/CF ratios.

## [0.6.0] - Previous release

Quality ratios, concurrent peers, caching, CompanyFacts, output formats.
