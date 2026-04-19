# Changelog

## [1.0.6] - 2026-04-18

### Critical Fix
- **YTD cumulative values treated as single-quarter**: SEC XBRL 10-Q income statements and cash flow statements report year-to-date cumulative figures. The library was treating these as single-quarter values, causing TTM Revenue to be ~3x the correct value (e.g. KLTR showed $407M instead of $180M).

### Two-Part Fix
- **Single-filing path**: When edgartools returns columns with `(Q3)`, `(YTD)`, `(FY)` suffixes, `_convert_statement_df()` now prefers single-quarter `(Q*)` columns over `(YTD)` cumulative columns and strips the suffixes. This ensures `find_synonym_value()` picks the actual quarter's value, not the year-to-date total.
- **Multi-period path**: New `decumulate_quarterly()` function detects YTD cumulative patterns in `MultiFinancials` stitched data (plain date columns) and converts to single-quarter values: `Q_n = YTD_n - YTD_{n-1}` within each fiscal year. Applied to quarterly income statements and cash flow statements in `retrieve_multi_year_data()` and `analyze_quarterly_balance_sheets()`. Balance sheet data (point-in-time) is never de-cumulated.

### Detection Heuristic
- Cumulative detection checks the top 10 rows (by absolute sum) within each fiscal year for monotonically non-decreasing positive values where the last value exceeds the first by >50%. This avoids false positives from non-cumulative metadata rows (e.g. weighted-average shares outstanding).

### Testing
- Added 18 new tests: `TestSelectValueColumns` (5), `TestConvertStatementDFWithSuffixes` (1), `TestDecumulateQuarterly` (6), plus existing tests updated.
- Test count: 427 (423 pass, 4 pre-existing MagicMock pickling failures in CLI/orchestrator tests).

## [1.0.5] - 2026-04-18

### Critical Fixes
- **Financial statements returned empty DataFrames**: `_get_financial_statement()` returned bound methods instead of calling them. edgartools `Financials` and `MultiFinancials` expose `balance_sheet`, `income_statement`, `cash_flow_statement` as methods — `getattr()` now calls the result when callable.
- **Statement DataFrame format mismatch**: edgartools `Statement.to_dataframe()` returns integer-indexed DataFrames with labels in a `label` column, but synonym matching searched the index. New `_convert_statement_df()` sets `label` as the index and appends XBRL concept tags as duplicate rows so both human-readable labels and XBRL tags match.
- **MultiFinancials constructor change**: `MultiFinancials(filings)` no longer works — constructor now requires `XBRLS`, not `EntityFilings`. All 5 call sites changed to `MultiFinancials.extract(filings)`.
- **D&A missing for many filers**: Depreciation & amortization was only searched in the income statement. Many filers (including AAPL) report D&A only in the cash flow statement. Added fallback to check cash flow when income statement yields zero.
- **CapEx synonym gap**: Added "Payments for acquisition of property, plant and equipment" (AAPL's label) to `capital_expenditures` synonyms.

### Integration Tests
- Added SEC API retry with exponential backoff (2s–16s) for GitHub Actions, where runner IPs get 403 Forbidden from SEC EDGAR.
- Tests skip gracefully after retries exhaust instead of failing the suite.
- Integration tests pass pre-warmed `Company` objects to `retrieve_multi_year_data()` to avoid internal `Company()` calls that bypass retry logic.

## [1.0.4] - 2026-04-18

### Fixes
- **Resource leak in `analyze()`**: Top-level convenience function now uses `with TickerOrchestrator() as orch:` so the disk cache is always closed, even on exceptions.
- **Redundant SEC API call**: `retrieve_multi_year_data()` now accepts an optional `comp` parameter. The orchestrator passes its existing `Company` object, eliminating a redundant `Company(ticker)` instantiation per ticker.
- **Dead code removal**: `_get_financial_statement()` no longer tries a non-existent `get_*` method before falling back to the property-based API that edgartools actually provides.

### Dependencies
- **rich**: Ceiling bumped `<15` → `<16` (rich 15.0.0 released).
- **yfinance**: Ceiling bumped `<1` → `<2` (yfinance 1.3.0 released).
- **pyarrow**: Ceiling bumped `<18` → `<24` (pyarrow 23.0.1 released).

### CI
- **Lint and typecheck enforced**: Removed `continue-on-error: true` from ruff and mypy CI steps. Fixed all 65 pre-existing ruff errors and 25+ mypy errors across 27 files so enforcement wouldn't break the build.

### Documentation
- **`docs/ARCHITECTURE.md`** (new): Data pipeline design — why the hybrid approach (synonym matching + CompanyFacts cross-validation) is stronger than either leg alone.
- **`docs/METRICS_REFERENCE.md`** (new): Complete reference for 79 extracted concepts, 42 derived metrics, and 7 scoring models — each with formula, business use case, and interpretation guidance.
- **`docs/USER_GUIDE.md`** (new): Real-world workflows (earnings prep, stock screening, due diligence, factor research, portfolio monitoring), scoring model interpretation with thresholds, and alert tuning.
- **README.md**: Updated for v1.0.4 features with cross-links to all docs.
- **CONTRIBUTING.md**: Added pointer to architecture doc.

### Testing
- Removed obsolete `test_get_financial_statement_old_api` (tested dead code path).
- Updated mock setups in `test_multi_period_analysis.py` and `test_cli.py` to use property-style attributes matching actual edgartools API.
- Test count: 401 → 399 (−2 tests: 1 dead-code test removed, 1 redundant).

## [1.0.3] - 2026-04-17

### Security
- **Cache directory permissions**: Cache directory is now created with `0o700` (owner-only) permissions, mitigating pickle deserialization risks from tampered cache files. Deserialization errors are caught and logged instead of propagating.
- **Path traversal checks**: `_save_csv_if_requested()` now validates `..` in path components *before* `resolve()` (previously the check was dead code). `to_parquet()` also rejects `..` traversal.

### Architecture
- **CacheLayer resource management**: Added `__del__`, `__enter__`/`__exit__` context manager protocol. `close()` is now idempotent (sets `_cache = None`).
- **TickerOrchestrator context manager**: Added `close()`, `__enter__`/`__exit__` so file descriptors from the cache are released in long-running processes.
- **Identity lock**: `_set_identity()` now serialized via `_IDENTITY_LOCK` to prevent races when concurrent `analyze()` calls use different identities.

### Testing
- Added cache directory permission test (0o700 on creation).
- Added cache corrupt-entry graceful-return test.
- Added CacheLayer context manager + close idempotency + `__del__` tests (3 tests).
- Added CSV path traversal rejection + normal path acceptance tests (2 tests).
- Added Parquet path traversal rejection + normal path acceptance tests (2 tests).
- Added TickerOrchestrator context manager test.
- Added identity lock existence test.
- Test count: 390 → 401 (+11 tests).

## [1.0.2] - 2026-04-17

### Financial Accuracy
- **Net Debt/EBITDA consistency**: Ratio numerator now uses financial debt only (short-term + long-term debt minus cash/investments), excluding lease liabilities. Standard EBITDA doesn't add back lease expense, so including leases in the numerator was inconsistent.
- **Amendment preference**: `get_filing_snapshot_with_fallback` now checks if an amended filing (10-K/A, 20-F/A, 10-Q/A) was filed more recently than the base filing, and uses the amendment since it supersedes the original.

### Pipeline Fixes
- **Dropped metrics in model**: Added 8 metrics to `_METRICS_KEY_TO_FIELD` and `SnapshotMetrics` that were computed by `metrics.py` but never serialized: Quick Ratio, Cash Ratio, Debt/Total Capital, Cash Flow Coverage, Fixed Charge Coverage, Accruals Ratio, Earnings Quality, Sloan Accrual.
- **JSON round-trip NaN**: `SnapshotMetrics.from_dict()` now coerces `None` values back to `NaN` (JSON serializes `NaN` → `null` → `None`; previously `None` was stored as-is, breaking downstream float math).
- **`AnalysisResult.from_json_dict()`**: New classmethod for reconstructing an `AnalysisResult` from the dict produced by `to_json_dict()`, completing the serialization round-trip.

### Testing
- Added dropped-metrics presence and round-trip tests (3 tests).
- Added JSON NaN→None→NaN round-trip tests (3 tests).
- Added `AnalysisResult.from_json_dict()` round-trip tests (3 tests).
- Added Net Debt/EBITDA lease-exclusion consistency test.
- Added amendment preference tests (newer amendment, older amendment, no amendment) (3 tests).
- Updated Net Debt/EBITDA existing test for financial-debt-only numerator.
- Test count: 377 → 390 (+13 tests).

## [1.0.1] - 2026-04-17

### XBRL Coverage (High Priority)
- **Net income synonyms**: Added `NetIncomeLossAvailableToCommonStockholdersBasic`, `NetIncomeLossAttributableToParent`, and `ifrs-full:ProfitLossAttributableToOwnersOfParent`. Apple, Microsoft, and many large-cap filers use these concepts — net income was 0 for these filings, corrupting ROE, EPS, margins, Piotroski, and Beneish.
- **D&A without Depletion**: Added `us-gaap:DepreciationAndAmortization` (without "Depletion") to `depreciation_amortization`. Many tech companies use this tag exclusively — D&A was 0, producing wrong EBITDA and Beneish DEPI.

### Financial Accuracy
- **Current/Quick/Cash Ratio guards**: Changed `if curr_liabs:` to `if curr_liabs > 0:` for all three ratios. Negative current liabilities (rare but possible from reclassifications) previously produced nonsensical negative ratios instead of NaN.

### Pipeline Fixes
- **CompanyFacts validation keys**: Restructured `_CONCEPT_MAP` so validation keys match actual metrics dict keys (`_total_assets`, `_total_liabilities`, `_total_equity`) instead of display names that never appeared in the dict. Previously 3 of 5 cross-validation checks silently skipped.
- **Reporting numeric coercion**: `_prepare_dataframe_for_presentation` and `_prepare_dataframe_for_csv` now skip string columns (`_FormType`, `_FilingDate`, `Alerts`) when coercing to numeric. Previously these columns were destroyed (converted to NaN).

### Testing
- Added net income synonym tests (AvailableToCommonStockholdersBasic, AttributableToParent, IFRS parent attribution).
- Added D&A synonym test (DepreciationAndAmortization without Depletion).
- Added negative current liabilities ratio guard test.
- Added CompanyFacts _total_assets validation + discrepancy tests.
- Added reporting string column preservation tests (presentation + CSV).
- Updated CompanyFacts equity fallback test for new `_total_equity` key.
- Test count: 369 → 377 (+8 tests).

## [1.0.0] - 2026-04-17

### XBRL Coverage (High Priority)
- **Short-term debt synonyms**: Added `ShortTermBorrowings` and `LongTermDebtCurrent` (current portion of long-term debt) to `short_term_debt`. Many filers use these tags exclusively — their absence systematically understated short-term debt, corrupting Current Ratio, Net Debt, D/E, and Altman Z working capital.
- **Pre-ASC 606 revenue**: Added `SalesRevenueGoodsNet` and `SalesRevenueServicesNet` to `revenue`. Historical multi-year analysis (pre-2018 filings) missed revenue for filers using these legacy GAAP tags.
- **Preferred stock & minority interest synonyms**: New `preferred_stock` and `minority_interest` synonym groups for EV computation.

### Financial Accuracy
- **Beneish GMI negative margin**: When gross margin drops from positive to negative (e.g., +30% → -5%), GMI now correctly signals high manipulation risk. Previously, the `gm > 0` check caused the code to use a floor divisor only for zero margins; negative margins now also produce a high GMI proportional to the margin decline.
- **EV/EBITDA formula**: Enterprise Value now includes preferred stock and minority interest, and subtracts short-term investments alongside cash equivalents. Previously EV was understated for companies with preferred stock (banks, BRK) and inconsistent with the net debt treatment of short-term investments.

### Pipeline Fixes
- **Mutable global config**: `get_alerts_config()` now returns `.copy()` of `ALERTS_CONFIG` when no overrides are provided. Previously returned the mutable global dict by reference — any caller mutating the result would corrupt defaults for the process lifetime.

### Testing
- Added short-term debt synonym tests (ShortTermBorrowings, LongTermDebtCurrent present).
- Added pre-ASC 606 revenue synonym tests (SalesRevenueGoodsNet, SalesRevenueServicesNet).
- Added preferred stock and minority interest synonym existence tests.
- Added Beneish GMI negative-margin test (+30% → -5% produces high GMI).
- Added EV/EBITDA tests (preferred stock, minority interest, ST investments in EV).
- Added mutable config mutation-safety test.
- Updated config no-override test (returns copy, not reference).
- Test count: 360 → 369 (+9 tests).

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
