# Changelog

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
