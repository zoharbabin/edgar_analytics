# Contributing to EDGAR Analytics

Thank you for your interest in contributing! This guide will help you get started.

## Ways to Contribute

- **Report bugs** — found incorrect metrics or a crash? [Open a bug report](https://github.com/zoharbabin/edgar_analytics/issues/new?template=bug_report.yml)
- **Report data accuracy issues** — wrong financial numbers? [Open a data accuracy report](https://github.com/zoharbabin/edgar_analytics/issues/new?template=data_accuracy.yml)
- **Suggest features** — have an idea? [Open a feature request](https://github.com/zoharbabin/edgar_analytics/issues/new?template=feature_request.yml)
- **Improve documentation** — fix typos, add examples, clarify explanations
- **Submit code** — fix bugs, add features, improve test coverage
- **Ask questions** — [open an issue](https://github.com/zoharbabin/edgar_analytics/issues/new) for Q&A

## Development Setup

1. **Fork and clone** the repository:

    ```bash
    git clone https://github.com/YOUR_USERNAME/edgar_analytics.git
    cd edgar_analytics
    ```

2. **Create a virtual environment** and install dependencies:

    ```bash
    python3 -m venv venv
    source ./venv/bin/activate   # or venv\Scripts\activate on Windows
    pip install --upgrade pip setuptools wheel
    pip install -e ".[test]"
    ```

3. **Verify** everything works:

    ```bash
    pytest -v -n auto
    ```

## Making Changes

1. **Create a branch** from `main`:

    ```bash
    git checkout -b my-feature-branch
    ```

2. **Make your changes**, following the coding standards below.

3. **Write or update tests** for your changes.

4. **Run the test suite** and make sure everything passes:

    ```bash
    pytest -v -n auto
    ```

5. **Test with a real ticker** if you changed metrics, synonyms, or reporting:

    ```bash
    edgar-analytics AAPL --debug
    ```

6. **Commit** with a clear message (see [Commit Messages](#commit-messages)).

7. **Push** and [open a pull request](https://github.com/zoharbabin/edgar_analytics/compare).

## Coding Standards

### Style

- **PEP 8** — standard Python style
- **PEP 257** — docstring conventions (one-line summary for simple functions, multi-line for complex ones)
- Keep functions focused and small
- Prefer clear variable names over comments

### Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the data pipeline design and why the hybrid validation approach (synonym matching + CompanyFacts cross-validation) was chosen.

- **`metrics.py`** — single-period financial ratio computation
- **`multi_period_analysis.py`** — multi-period growth, CAGR, alerts
- **`forecasting.py`** — strategy-based revenue forecasting
- **`synonyms.py` / `synonyms_utils.py`** — GAAP/IFRS line-item matching
- **`orchestrator.py`** — high-level workflow coordination
- **`reporting.py`** — output formatting (Rich console, CSV)
- **`data_utils.py`** — shared parsing and formatting helpers
- **`config.py`** — alert thresholds and constants
- **`cli.py`** — Click-based CLI entry point

When adding a new metric, add synonyms in `synonyms.py`, computation in `metrics.py`, and tests in `tests/test_metrics.py`.

### Testing

- All new code must have tests
- Use `pytest` with fixtures — see existing tests for patterns
- Mock external API calls (SEC EDGAR) — never hit the network in tests
- Test edge cases: zero denominators, negative values, missing data, NaN propagation
- For financial accuracy, verify against a known filing's actual numbers when possible

### Security

- **Never commit credentials**, API keys, or tokens
- Validate all external data (SEC filings can have unexpected formats)
- Use `np.nan` for undefined ratios — never return misleading zeros
- Be careful with user-supplied ticker symbols (they're passed to external APIs)
- Do not add dependencies without discussion — each dependency is an attack surface

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(metrics): add interest coverage ratio
fix(synonyms): handle duplicate index in IFRS filings
docs: update CLI usage examples
test: add edge cases for negative equity
chore: bump edgartools to 5.30
```

Prefix types: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `perf`.

Scope is optional but helpful: `metrics`, `forecasting`, `cli`, `synonyms`, `reporting`, `ci`.

## Pull Request Guidelines

- Keep PRs focused — one feature or fix per PR
- Fill out the PR template completely
- Link to the related issue (e.g., `Fixes #12`)
- Ensure all CI checks pass (Python 3.10, 3.11, 3.12, 3.13)
- Be responsive to review feedback
- Squash-merge is preferred for clean history

### What makes a good PR

- Clear description of what and why
- Tests that prove the change works
- No unrelated changes mixed in
- Passes CI on all Python versions

## Financial Accuracy Guidelines

This library computes financial metrics that people may use for analysis. Accuracy matters.

- **Always prefer `np.nan` over `0.0`** for undefined or meaningless ratios (e.g., Debt-to-Equity when equity is zero)
- **Respect sign conventions**: expenses are typically positive after sign-flipping; use `flip_sign_if_negative_expense` consistently
- **Avoid double-counting**: check whether a line item is already included in a parent total before adding it
- **Document assumptions**: if a computation uses an approximation (e.g., FCF fallback when CapEx is missing), note it in the docstring
- **Test with real filings**: when possible, verify your metric against a known company's actual SEC filing numbers
- **Handle IFRS and GAAP**: both standards use different labels for similar concepts — add synonyms for both

## Getting Help

- **Questions about the code**: [Open an issue](https://github.com/zoharbabin/edgar_analytics/issues/new)
- **Bug reports**: [Issue tracker](https://github.com/zoharbabin/edgar_analytics/issues)
- **Security issues**: See [SECURITY.md](SECURITY.md)

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
