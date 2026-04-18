# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them responsibly via one of these channels:

1. **GitHub Security Advisories**: Use the [Report a vulnerability](https://github.com/zoharbabin/edgar_analytics/security/advisories/new) button on the Security tab.
2. **Email**: Send details to **z.babin@gmail.com** with the subject line `[SECURITY] edgar_analytics`.

### What to include

- Description of the vulnerability and its potential impact
- Steps to reproduce or a proof of concept
- Affected version(s)
- Any suggested fix (optional but appreciated)

### What to expect

- **Acknowledgment** within 48 hours of your report
- **Status update** within 7 days with an assessment and expected timeline
- **Credit** in the release notes (unless you prefer to remain anonymous)

We will work with you to understand and address the issue before any public disclosure.

## Scope

This policy covers:

- The `edgar-analytics` Python package published on PyPI
- The source code in this repository
- The GitHub Actions CI/CD pipeline configuration

### Out of scope

- The SEC EDGAR API itself or data accuracy of SEC filings
- Third-party dependencies (please report those to their respective maintainers)
- The `edgartools` library (report to [edgartools](https://github.com/dgunning/edgartools))

## Security Best Practices for Users

- **SEC Identity**: The SEC requires a User-Agent identity when accessing EDGAR. Use the `--identity` flag or set the `EDGAR_IDENTITY` environment variable. Never share credentials in bug reports or issues.
- **API Keys**: Do not commit API keys, tokens, or credentials to the repository.
- **Dependencies**: Keep dependencies up to date (`pip install --upgrade edgar-analytics`).
- **Log Files**: The `edgar_analytics_debug.jsonl` log file may contain ticker symbols and financial data from your analysis. Handle it according to your data sensitivity requirements.
