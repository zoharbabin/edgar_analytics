## Summary

<!-- What does this PR do? 1-3 bullet points. -->

-

## Motivation

<!-- Why is this change needed? Link to an issue if applicable. -->

Fixes #

## Changes

<!-- List the key changes. Reviewers should be able to understand the PR from this list. -->

-

## Test plan

<!-- How did you verify this works? -->

- [ ] All existing tests pass (`pytest -v -n auto`)
- [ ] New/updated tests cover the changed behavior
- [ ] Tested with a real ticker via CLI (`edgar-analytics AAPL --debug`) *(if applicable)*
- [ ] Verified metric accuracy against actual SEC filing numbers *(if changing metrics/synonyms)*

## Checklist

- [ ] Code follows existing patterns and style (PEP 8, PEP 257)
- [ ] No credentials, API keys, or sensitive data included
- [ ] No new dependencies added (or discussed and justified in this PR)
- [ ] `CONTRIBUTING.md` / `README.md` updated if behavior changed
- [ ] Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) format

## Security considerations

<!-- Does this PR introduce any security concerns? Check all that apply: -->

- [ ] No user input is passed unsanitized to external APIs or shell commands
- [ ] No credentials or secrets are logged or exposed
- [ ] N/A — this PR has no security implications

## Financial accuracy

<!-- If this PR changes metrics, ratios, or financial computations: -->

- [ ] Undefined ratios return `np.nan`, not `0.0` or misleading defaults
- [ ] Sign conventions are respected (expenses positive after flip)
- [ ] No double-counting of line items in parent totals
- [ ] N/A — this PR does not change financial computations
