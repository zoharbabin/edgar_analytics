# Metrics & Concepts Reference

A complete reference for everything edgar_analytics can extract from SEC filings, compute as derived metrics, and score. Organized in three layers: **what the library reads** (extracted concepts), **what it computes** (derived metrics), and **what it scores** (scoring models).

For workflow examples and code recipes, see [USER_GUIDE.md](USER_GUIDE.md). For pipeline architecture, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Table of Contents

1. [Extracted Concepts](#extracted-concepts)
   - [Income Statement](#income-statement)
   - [Balance Sheet](#balance-sheet)
   - [Cash Flow Statement](#cash-flow-statement)
   - [Supplemental & Disclosure](#supplemental--disclosure)
2. [Derived Metrics](#derived-metrics)
   - [Profitability](#profitability)
   - [Liquidity](#liquidity)
   - [Leverage & Solvency](#leverage--solvency)
   - [Cash Flow Analysis](#cash-flow-analysis)
   - [Returns & Efficiency](#returns--efficiency)
   - [Earnings Quality](#earnings-quality)
   - [Balance Sheet Composition](#balance-sheet-composition)
   - [Valuation (optional)](#valuation-optional)
3. [Scoring Models](#scoring-models)
   - [Per-Share Metrics](#per-share-metrics)
   - [Working Capital Cycle](#working-capital-cycle)
   - [Capital Efficiency (ROIC)](#capital-efficiency-roic)
   - [DuPont Decomposition](#dupont-decomposition)
   - [Piotroski F-Score](#piotroski-f-score)
   - [Altman Z-Score](#altman-z-score)
   - [Beneish M-Score](#beneish-m-score)
4. [Multi-Period Analytics](#multi-period-analytics)
5. [Alerts](#alerts)

---

## Extracted Concepts

The library extracts ~79 financial concepts from SEC filings via synonym matching on XBRL-rendered tables. Each concept is matched against multiple label variants (US GAAP tags, IFRS tags, and common text labels). See `synonyms.py` for the full mapping.

### Income Statement

These concepts power profitability analysis, margin trends, and earnings quality scoring.

| Concept | Synonym Key | Use Case |
|---------|-------------|----------|
| **Revenue** | `revenue` | Top-line performance. The starting point for almost every analysis — revenue growth, margins, valuation multiples. |
| **Cost of Revenue** | `cost_of_revenue` | Unit economics. Rising COGS faster than revenue signals margin compression. Input to gross profit, DIO, and Beneish AQI. |
| **Gross Profit** | `gross_profit` | Pricing power. Stable or expanding gross margins indicate competitive moat or pricing leverage. Critical for Beneish GMI. |
| **Operating Expenses** | `operating_expenses` | Cost discipline. OpEx as a percentage of revenue reveals operational efficiency. Includes SGA, R&D, and other operating costs. |
| **R&D Expenses** | `rnd_expenses` | Innovation investment. High R&D/revenue ratio in tech and pharma is expected; declining R&D may signal underinvestment in growth. |
| **SGA Expenses** | `general_administrative` | Overhead efficiency. Beneish SGAI component flags companies where SGA grows faster than revenue (potential empire-building or revenue masking). |
| **Selling & Marketing** | `sales_marketing` | Go-to-market efficiency. Marketing spend relative to revenue growth indicates customer acquisition efficiency. |
| **Operating Income** | `operating_income` | Core business profitability before financing and taxes. Used for operating margin, EBIT computation, and DuPont analysis. |
| **Other Income/Expense** | `other_income_expense` | Non-core items. Large non-operating income or expense distorts net income — check to assess earnings sustainability. |
| **Pretax Income** | `income_before_taxes` | Earnings before government take. Used to compute effective tax rate (needed for ROIC/NOPAT and DuPont 5-component). |
| **Income Tax Expense** | `income_tax_expense` | Tax rate computation. Effective tax rate = Tax / Pretax Income. Input to NOPAT, EBITDA standard, and Piotroski accruals. |
| **D&A** | `depreciation_amortization` | Non-cash charge. Added back to operating income to get EBITDA. A large D&A/revenue ratio indicates capital-intensive operations. |
| **D&A in COGS** | `depreciation_in_cost_of_sales` | Manufacturing D&A. Some companies embed depreciation in cost of sales rather than reporting it separately — needed for accurate EBITDA. |
| **Net Income** | `net_income` | Bottom line. Used in ROE, EPS, Piotroski profitability tests, Beneish TATA, and as the starting point for Sloan Accrual. |
| **EPS (Basic)** | `earnings_per_share_basic` | Per-share profitability. Used in P/E calculation and for comparing companies of different sizes on a per-share basis. |
| **EPS (Diluted)** | `earnings_per_share_diluted` | Diluted profitability. Accounts for stock options, convertible securities. Preferred for P/E ratios and equity valuation. |
| **Interest Expense** | `interest_expense` | Debt cost. Used in interest coverage ratio, EBIT standard, and the DuPont 5-component interest burden factor. |

### Balance Sheet

Balance sheet concepts drive liquidity, leverage, capital structure, and efficiency analyses.

| Concept | Synonym Key | Use Case |
|---------|-------------|----------|
| **Cash & Equivalents** | `cash_equivalents` | Liquidity cushion. Input to cash ratio, net debt, FCF analysis, and enterprise value. Declining cash with rising debt is a red flag. |
| **Short-term Investments** | `short_term_investments` | Near-cash. Added to cash for net debt calculation and subtracted in enterprise value. Less liquid than cash but available within a year. |
| **Accounts Receivable** | `accounts_receivable` | Collection efficiency. Rising A/R faster than revenue (DSO increasing) may signal channel stuffing. Input to Beneish DSRI and working capital cycle. |
| **Inventory** | `inventory` | Working capital efficiency. Inventory build-ups relative to COGS (DIO increasing) may indicate demand softening or obsolescence risk. Spike alerts flag >30% QoQ jumps. |
| **Other Current Assets** | `other_current_assets` | Prepaid expenses, deposits. Usually immaterial but can obscure trends if growing rapidly. |
| **Current Assets** | `current_assets` | Short-term resource base. Denominator for current ratio, quick ratio. Used in Beneish AQI and working capital computation. |
| **Long-term Investments** | `long_term_investments` | Strategic holdings. Not readily available for operations. Subtracted from net debt for a more conservative leverage view. |
| **PP&E (Net)** | `ppe_net` | Physical asset base. Capital-intensive businesses have high PP&E/assets. Input to Beneish AQI (hard assets) and depreciation rate. |
| **Intangible Assets** | `intangible_assets` | Non-physical assets (patents, customer lists, software). High intangible ratio may indicate acquisition-driven growth or vulnerable asset base. |
| **Goodwill** | `goodwill` | Acquisition premium. Goodwill/total assets > 30% signals significant acquisition risk — impairment risk in downturns. |
| **Total Assets** | `total_assets` | Scale and asset intensity. Denominator for ROA, asset turnover, Altman Z components, and Beneish AQI. CompanyFacts cross-validated. |
| **Accounts Payable** | `accounts_payable` | Supplier financing. DPO (Days Payable Outstanding) shows how long the company takes to pay suppliers — input to cash conversion cycle. |
| **Accrued Expenses** | `accrued_expenses` | Short-term obligations already incurred. Part of current liabilities but more granular than the total. |
| **Current Liabilities** | `current_liabilities` | Short-term obligations. Denominator for current/quick ratio. Used in Altman working capital component and Beneish LVGI. |
| **Deferred Revenue** | `deferred_revenue` | Cash received for goods/services not yet delivered. Growth signals strong forward demand (SaaS subscription prepayments). Decline may signal churn. |
| **Short-term Debt** | `short_term_debt` | Near-term refinancing risk. Includes current portion of long-term debt. Input to net debt, enterprise value, and leverage ratios. |
| **Long-term Debt** | `long_term_debt` | Core financial leverage. Input to D/E, net debt/EBITDA, Altman Z, Piotroski leverage test, and Beneish LVGI. |
| **Operating Lease Liabilities** | `operating_lease_liabilities` | Off-balance-sheet obligation (now on-sheet per ASC 842). Lease liabilities ratio shows exposure. Excluded from financial net debt numerator for Net Debt/EBITDA. |
| **Finance Lease Liabilities** | `finance_lease_liabilities` | Capital lease obligations. Unlike operating leases, these are financing arrangements — treated similarly to debt in some analyses. |
| **Total Liabilities** | `total_liabilities` | All obligations. Used in equity ratio, D/E, Altman Z, and the accounting identity check (Assets = Liabilities + Equity). CompanyFacts cross-validated. |
| **Total Equity** | `total_equity` | Shareholders' claim. Denominator for ROE, D/E, equity ratio. Used in book value per share and DuPont equity multiplier. CompanyFacts cross-validated. |
| **Common Stock & APIC** | `common_stock_and_apic` | Paid-in capital. Large increases may indicate equity issuance (dilution). |
| **Treasury Stock** | `treasury_stock` | Shares repurchased. Growing treasury stock signals shareholder-friendly capital allocation. Reduces equity, so it inflates ROE — check if ROE is leveraged by buybacks rather than operational improvement. |
| **Retained Earnings** | `retained_earnings` | Cumulative profits reinvested. Negative retained earnings (accumulated deficit) indicates historical losses. Input to Altman Z component B. |
| **Preferred Stock** | `preferred_stock` | Senior equity. Subtracted when computing common equity. Included in enterprise value calculation. |
| **Minority Interest** | `minority_interest` | Non-controlling interests in subsidiaries. Part of total equity but not attributable to common shareholders. Included in EV. |
| **Accumulated OCI** | `accumulated_oci` | Unrealized gains/losses (FX, available-for-sale securities, pension). Volatile but doesn't flow through net income — can mask balance sheet deterioration. |
| **Shares Outstanding** | `common_shares_outstanding` | Share count for per-share metrics (EPS, book value/share, FCF/share). Piotroski checks for dilution (shares increasing). |

### Cash Flow Statement

Cash flow concepts drive FCF analysis, accrual quality, and CapEx-related metrics.

| Concept | Synonym Key | Use Case |
|---------|-------------|----------|
| **Operating Cash Flow** | `cash_flow_operating` | Cash generation from core operations. OCF > Net Income indicates high earnings quality. Input to FCF, cash flow coverage, Beneish TATA, and Piotroski CFO test. |
| **Investing Cash Flow** | `cash_flow_investing` | Capital deployment. Large negative investing CF indicates growth investment (CapEx, acquisitions). Used as CapEx fallback when direct CapEx line isn't available. |
| **Financing Cash Flow** | `cash_flow_financing` | Capital structure changes. Positive = raising capital (debt/equity); negative = returning capital (dividends, buybacks, debt repayment). |
| **Capital Expenditures** | `capital_expenditures` | Investment in physical assets. Subtracted from OCF to get FCF. High CapEx/Revenue = capital-intensive business. Multi-level fallback: direct line, then investing CF minus intangibles and acquisitions. |
| **Purchase of Intangibles** | `purchase_of_intangibles` | Investment in non-physical assets. Subtracted from investing CF in the CapEx fallback calculation to isolate physical asset investment. |
| **Business Acquisitions** | `business_acquisitions_net` | M&A spending. Subtracted from investing CF in the CapEx fallback. Large acquisitions distort organic growth metrics. |
| **Share-Based Compensation** | `share_based_compensation` | Non-cash employee comp. Added back in operating CF but represents real economic cost (dilution). SBC/revenue reveals true compensation burden. |
| **Dividends** | `dividends` | Cash returned to shareholders. Dividend coverage = FCF / Dividends. Coverage < 1x means dividends exceed free cash flow (unsustainable without debt). |
| **Share Repurchase** | `share_repurchase` | Buyback spending. Combined with dividends for total shareholder return. Consistent buybacks reduce share count (positive for Piotroski no-dilution test). |

### Supplemental & Disclosure

These concepts are extracted but primarily used for context, not ratio computation.

| Concept | Synonym Key | Use Case |
|---------|-------------|----------|
| **Comprehensive Income** | `comprehensive_income` | Net income + OCI items. Divergence from net income reveals hidden volatility (FX, pension, AFS securities). |
| **Deferred Tax Assets/Liabilities** | `deferred_tax_assets`, `deferred_tax_liabilities` | Timing differences. Large DTA may indicate NOL carryforwards (future tax shield). Large DTL signals taxes owed on unrealized gains. |
| **Unrecognized Tax Benefits** | `unrecognized_tax_benefits` | Uncertain tax positions. Material amounts indicate potential IRS/tax authority exposure. |
| **Right-of-Use Assets** | `right_of_use_assets` | ASC 842 lease assets. Compare to lease liabilities to assess net lease position. |
| **Contract Assets/Liabilities** | `contract_assets`, `contract_liabilities` | Revenue recognition staging. Contract assets = recognized but not yet billed. Contract liabilities = billed but not yet recognized (deferred revenue). Growing contract liabilities is a positive signal for subscription businesses. |
| **Financial Instruments (FVPL/FVOCI)** | `financial_assets_fvpl`, `financial_assets_fvoci` | Securities measured at fair value. FVPL gains/losses hit the income statement; FVOCI goes through OCI. Material holdings introduce market risk. |
| **Derivatives & Hedging** | `derivatives_hedging` | Risk management instruments. Presence indicates FX, interest rate, or commodity exposure. Hedge effectiveness matters for earnings predictability. |
| **Segment Reporting** | `segment_reporting` | Business unit breakdown. Currently extracted as a label detection (existence check). Per-segment metrics are a planned feature ([#6](https://github.com/zoharbabin/edgar_analytics/issues/6)). |
| **Commitments & Contingencies** | `commitments_contingencies` | Off-balance-sheet obligations. Purchase commitments, guarantees, and pending litigation that could become material. |
| **Litigation** | `litigation_legal` | Legal exposure. Large pending settlements or fines can materially impact cash flow and equity. |
| **Lease Disclosures** | `lease_disclosures` | Lease cost tables, maturity schedules. Useful for understanding future cash obligations beyond what's on the balance sheet. |
| **Business Combinations** | `business_combinations` | M&A disclosure. Integration risks, contingent consideration, purchase price allocation details. |

---

## Derived Metrics

Computed from extracted concepts. Available in `result.main.annual_snapshot.metrics`.

### Profitability

| Metric | Output Key | Formula | When to Use |
|--------|-----------|---------|-------------|
| **Gross Margin %** | `Gross Margin %` | Gross Profit / Revenue x 100 | Compare pricing power across peers. Stable >40% is typical for software; <20% for hardware/retail. Declining gross margin is the earliest signal of competitive pressure. |
| **Operating Margin %** | `Operating Margin %` | Operating Income / Revenue x 100 | Operational efficiency including overhead. Higher = better cost control. Compare within industries (airline 5-10% vs software 25-40%). |
| **Net Margin %** | `Net Margin %` | Net Income / Revenue x 100 | Bottom-line profitability after all costs. Low or negative triggers an alert. Influenced by tax rate and financing costs, so less comparable across capital structures than operating margin. |
| **EBIT (approx)** | `EBIT (approx)` | Net Income + Interest + Tax | Quick EBIT estimate. Use when detailed operating income isn't available. Less accurate than the standard method. |
| **EBIT (standard)** | `EBIT (standard)` | Operating Income (from filing) | Preferred EBIT measure. Directly from the income statement, avoids adding back items that weren't separately disclosed. Used in DuPont, Altman Z, and interest coverage. |
| **EBITDA (approx)** | `EBITDA (approx)` | EBIT (approx) + D&A | Rough cash earnings proxy. Used when operating income isn't available. |
| **EBITDA (standard)** | `EBITDA (standard)` | EBIT (standard) + D&A | Preferred EBITDA measure. Used in Net Debt/EBITDA and EV/EBITDA. Standard method avoids double-counting when D&A is already embedded in operating expenses. |

**When to use approx vs. standard**: Always prefer the standard variant. The library computes both because some filers don't report operating income as a separate line item, making the approximation the only option. When both are available, the standard version is used in all ratios.

### Liquidity

| Metric | Output Key | Formula | When to Use |
|--------|-----------|---------|-------------|
| **Current Ratio** | `Current Ratio` | Current Assets / Current Liabilities | Basic liquidity. >1.5 is comfortable; <1.0 means short-term obligations exceed short-term assets. Too high (>3) may indicate idle capital. Input to Piotroski liquidity test. |
| **Quick Ratio** | `Quick Ratio` | (Current Assets - Inventory) / Current Liabilities | Stringent liquidity. Excludes inventory (which may be slow to convert to cash). More meaningful for manufacturers with large inventory balances. >1.0 is generally healthy. |
| **Cash Ratio** | `Cash Ratio` | Cash / Current Liabilities | Most conservative liquidity measure. Only counts cash on hand. Useful for stress-testing: could the company pay all short-term debts from cash alone? >0.5 is conservative; >1.0 is very liquid. |

### Leverage & Solvency

| Metric | Output Key | Formula | When to Use |
|--------|-----------|---------|-------------|
| **Debt-to-Equity** | `Debt-to-Equity` | Total Liabilities / Total Equity | Overall leverage. >3.0 triggers a high-leverage alert (default). Financial companies (banks) naturally run 10-15x — suppress this alert for them. Compare within industries. |
| **Debt/Total Capital** | `Debt/Total Capital` | (ST Debt + LT Debt) / (ST Debt + LT Debt + Equity) | Financial debt as a share of total capitalization. Ignores operating liabilities, so gives a cleaner picture of financial leverage than D/E. >50% means more debt than equity funding. |
| **Equity Ratio %** | `Equity Ratio %` | Total Equity / Total Assets x 100 | Inverse perspective on leverage. Higher = more equity-funded = lower risk. <20% indicates heavy leverage. Banks typically 5-10%. |
| **Interest Coverage** | `Interest Coverage` | EBIT (standard) / Interest Expense | Can the company service its debt? <2.0 triggers an alert. <1.0 means operating income doesn't cover interest — distress signal. Investment grade companies typically >5x. |
| **Net Debt** | `Net Debt` | ST Debt + LT Debt + Lease Liabilities - Cash | Total indebtedness net of cash. Negative net debt means the company has more cash than debt — a strong position. Lease liabilities included per balance sheet convention. |
| **Net Debt/EBITDA** | `Net Debt/EBITDA` | Financial Net Debt / EBITDA (standard) | Leverage relative to cash earnings. >3.5x triggers an alert. >6x is aggressive leverage. **Note**: Numerator uses financial debt only (ST + LT debt minus cash), excluding lease liabilities, because EBITDA doesn't add back lease expense. Denominator uses EBITDA (standard). |
| **Lease Liabilities Ratio %** | `Lease Liabilities Ratio %` | (Operating + Finance Leases) / Total Assets x 100 | Off-balance-sheet exposure (now on-sheet). High ratio in airlines, retail, restaurants. >10% warrants understanding the lease maturity profile. |

### Cash Flow Analysis

| Metric | Output Key | Formula | When to Use |
|--------|-----------|---------|-------------|
| **Cash from Operations** | `Cash from Operations` | From cash flow statement | Core cash generation. OCF consistently below net income signals aggressive accruals. Used in Piotroski CFO>0 test and earnings quality. |
| **Free Cash Flow** | `Free Cash Flow` | OCF - CapEx | Cash available to shareholders after reinvestment. The most important single metric for equity investors. Negative FCF streak (2+ quarters) triggers an alert. Used in FCF/share, dividend coverage, and EV/FCF. |
| **Cash Flow Coverage** | `Cash Flow Coverage` | OCF / Current Liabilities | Can operating cash cover near-term obligations? >1.0 is healthy. Unlike current ratio, uses actual cash flow rather than balance sheet assets. |
| **Fixed Charge Coverage** | `Fixed Charge Coverage` | (EBIT + Lease Expense) / (Interest + Lease Expense) | Debt service capacity including lease obligations. More conservative than interest coverage alone. Critical for companies with significant lease obligations (retail, airlines). |

### Returns & Efficiency

| Metric | Output Key | Formula | When to Use |
|--------|-----------|---------|-------------|
| **ROE %** | `ROE %` | Net Income / Total Equity x 100 | Shareholder return. >15% is strong. DuPont decomposition reveals whether ROE comes from margins, asset efficiency, or leverage. Can be inflated by buybacks (reducing equity) or debt — cross-check with ROIC. |
| **ROA %** | `ROA %` | Net Income / Total Assets x 100 | Asset productivity. Less susceptible to leverage distortion than ROE. <2% triggers an alert. Compare within asset-intensity tiers (banks 0.5-1.5%, software 15-25%). Input to Piotroski ROA tests. |

### Earnings Quality

These metrics detect whether reported earnings are backed by real cash or accounting accruals.

| Metric | Output Key | Formula | When to Use |
|--------|-----------|---------|-------------|
| **Accruals Ratio** | `Accruals Ratio` | (Net Income - OCF) / Total Assets | Cash vs. accrual divergence. Positive = earnings exceed cash flow (aggressive accounting). <-5% to +5% is normal. >10% warrants investigation. Used in Beneish TATA component. |
| **Earnings Quality** | `Earnings Quality` | OCF / Net Income | Cash backing of earnings. >1.0 means cash flow exceeds reported income (conservative accounting). <0.5 is a red flag for accrual-heavy earnings. Piotroski awards a point when OCF > NI. |
| **Sloan Accrual** | `Sloan Accrual` | (Change in Working Capital - Change in Cash - D&A) / Avg Total Assets | Academic accrual measure. High positive Sloan Accrual historically predicts lower future returns. Requires prior-year data. Richard Sloan (1996) showed high-accrual firms underperform. |

### Balance Sheet Composition

| Metric | Output Key | Formula | When to Use |
|--------|-----------|---------|-------------|
| **Intangible Ratio %** | `Intangible Ratio %` | Intangible Assets / Total Assets x 100 | Asset tangibility. High intangible ratio means the asset base is patents, software, customer lists — potentially volatile in impairment. >30% warrants scrutiny of impairment risk. |
| **Goodwill Ratio %** | `Goodwill Ratio %` | Goodwill / Total Assets x 100 | Acquisition premium exposure. High goodwill means the company paid above book value for acquisitions. Impairment risk in downturns. >40% is significant. |
| **Tangible Equity** | `Tangible Equity` | Total Equity - Intangible Assets - Goodwill | Hard asset coverage. Negative tangible equity means goodwill and intangibles exceed total equity — the company's net worth is entirely dependent on soft asset valuations. |

### Valuation (optional)

Requires `pip install edgar-analytics[valuation]` (yfinance). Computed from market data + filing metrics.

| Metric | Output Key | Formula | When to Use |
|--------|-----------|---------|-------------|
| **P/E Ratio** | `pe_ratio` | Share Price / Diluted EPS (or Market Cap / Net Income) | Growth expectations. High P/E (>25) indicates market expects growth; low P/E (<12) may signal value or distress. Compare within sector — tech P/E is structurally higher than utilities. |
| **P/B Ratio** | `pb_ratio` | Market Cap / Total Equity | Asset-based value. P/B <1 means market values the company below book — potential deep value or justified (declining business). Banks and industrials use P/B more than tech (which has few tangible assets). |
| **EV/EBITDA** | `ev_ebitda` | Enterprise Value / EBITDA (standard) | Capital-structure-neutral valuation. Preferred over P/E for M&A analysis and cross-border comparison (not distorted by tax, debt, or depreciation differences). EV = Market Cap + Debt + Preferred + Minority - Cash. |
| **Earnings Yield** | `earnings_yield` | 1 / P/E (or EPS / Price) | Inverse P/E, expressed as a yield. Comparable to bond yields. Earnings yield > 10-year Treasury yield is a classic value signal (the "Fed Model"). |

---

## Scoring Models

Multi-factor models accessed via `metrics.scores`. Each produces a dataclass with the score, interpretation, and individual components.

### Per-Share Metrics

**Access**: `scores.per_share`

| Field | Formula | Use Case |
|-------|---------|----------|
| `eps_basic` | Net Income / Shares Outstanding | Basic per-share profitability. |
| `eps_diluted` | From filing (includes options, convertibles) | Primary EPS for valuation. Preferred for P/E ratios. |
| `book_value_per_share` | Total Equity / Shares Outstanding | Tangible worth per share. Compare to share price for P/B. Below share price means market assigns franchise/growth value. |
| `fcf_per_share` | FCF / Shares Outstanding | Cash generation per share. More conservative than EPS. Growing FCF/share with flat EPS may indicate improving earnings quality. |

### Working Capital Cycle

**Access**: `scores.working_capital` (suppressed for financial companies)

| Field | Formula | Use Case |
|-------|---------|----------|
| `dso` (Days Sales Outstanding) | A/R / (Revenue / 365) | Collection speed. Rising DSO = customers paying slower. DSO increasing faster than peers is a Beneish DSRI red flag. |
| `dio` (Days Inventory Outstanding) | Inventory / (COGS / 365) | Inventory turnover. Rising DIO = inventory building up. Could mean demand softening, new product launches, or supply chain buffering. |
| `dpo` (Days Payable Outstanding) | A/P / (COGS / 365) | Payment speed to suppliers. Rising DPO = stretching supplier terms (preserves cash but may indicate cash pressure). |
| `cash_conversion_cycle` | DSO + DIO - DPO | Days between paying suppliers and collecting from customers. Lower (or negative) = more cash-efficient. Amazon has negative CCC (collects before it pays). Increasing CCC requires more working capital to fund growth. |

### Capital Efficiency (ROIC)

**Access**: `scores.capital_efficiency`

| Field | Formula | Use Case |
|-------|---------|----------|
| `nopat` | Operating Income x (1 - Effective Tax Rate) | After-tax operating profit. Strips out financing effects. Better than net income for comparing operational performance across capital structures. |
| `invested_capital` | Equity + ST Debt + LT Debt - Cash | Capital deployed in operations. Denominator for ROIC. |
| `roic_pct` | NOPAT / Invested Capital x 100 | True return on capital. >15% suggests competitive moat. 10-15% is good. <5% indicates poor capital allocation. Unlike ROE, ROIC is not inflated by leverage — the most reliable single measure of management effectiveness. |
| `asset_turnover` | Revenue / Total Assets | Revenue generated per dollar of assets. Higher = more efficient. Retail 2-3x; software 0.5-1x; banks 0.05-0.1x. |

### DuPont Decomposition

**Access**: `scores.dupont`

Decomposes ROE to reveal which driver dominates.

**3-component**: ROE = Net Profit Margin x Asset Turnover x Equity Multiplier

| Component | What It Reveals | Concern If |
|-----------|----------------|------------|
| `net_profit_margin` (NI/Revenue) | Pricing power, cost control | Declining — competitive pressure or cost creep |
| `asset_turnover` (Revenue/Assets) | Asset efficiency | Declining — assets growing faster than revenue (overinvestment?) |
| `equity_multiplier` (Assets/Equity) | Financial leverage | Rising — ROE growth from leverage, not operations |

**5-component**: Extends by splitting margin into Tax Burden x Interest Burden x Operating Margin

| Component | What It Reveals |
|-----------|----------------|
| `tax_burden` (NI/Pretax Income) | Tax efficiency. Near 1.0 = low effective tax rate. |
| `interest_burden` (Pretax Income/EBIT) | Debt cost impact. Near 1.0 = minimal interest drag. |
| `operating_margin` (EBIT/Revenue) | Pre-tax, pre-interest profitability. |

**When to use**: Two companies both have 20% ROE — DuPont shows one achieves it through 15% margins (sustainable), the other through 8x leverage (risky). Critical for quality-vs-leverage differentiation.

### Piotroski F-Score

**Access**: `scores.piotroski` (requires prior-year data)

Nine binary tests awarding 0 or 1 point each. Score ranges 0-9.

| Category | Test | Point If |
|----------|------|----------|
| Profitability | ROA > 0 | Company is profitable |
| Profitability | OCF > 0 | Operations generate cash |
| Profitability | ROA increasing vs. prior year | Profitability improving |
| Profitability | OCF > Net Income | Earnings backed by cash (low accruals) |
| Leverage | Long-term debt decreasing | Deleveraging |
| Liquidity | Current ratio increasing | Better short-term coverage |
| Leverage | No share dilution (shares stable or decreasing) | No equity dilution |
| Efficiency | Gross margin increasing | Pricing power or cost reduction |
| Efficiency | Asset turnover increasing | More revenue per dollar of assets |

**Interpretation**: 8-9 = strong fundamentals (historically outperforms). 5-7 = average. 0-3 = weak fundamentals. Best used for value stock screening — Piotroski designed it to separate winners from losers among cheap (high book-to-market) stocks.

### Altman Z-Score

**Access**: `scores.altman` (suppressed for financial companies, SIC 6000-6999)

Predicts bankruptcy probability. Three model variants, auto-selected.

**Z (manufacturing)** — asset-heavy companies (revenue/assets > 0.5):

Z = 1.2A + 1.4B + 3.3C + 0.6D + 1.0E

| Component | Formula | What It Captures |
|-----------|---------|-----------------|
| A | Working Capital / Total Assets | Short-term liquidity relative to firm size |
| B | Retained Earnings / Total Assets | Cumulative profitability and firm age |
| C | EBIT / Total Assets | Operating productivity of assets |
| D | Market Cap / Total Liabilities | Market confidence relative to obligations |
| E | Revenue / Total Assets | Asset utilization (revenue generation) |

Zones: Safe > 2.99; Grey 1.81-2.99; Distress < 1.81

**Z'' (non-manufacturing)** — service, tech companies:

Z'' = 6.56A + 3.26B + 6.72C + 1.05D'

Where D' = Book Value Equity / Total Liabilities (replaces market-cap-based D).

Zones: Safe > 2.60; Grey 1.10-2.60; Distress < 1.10

**Best used for**: Credit analysis, distress screening, portfolio risk monitoring. Check `scores.altman.model` to see which variant was applied. Not suitable for banks and insurers.

### Beneish M-Score

**Access**: `scores.beneish` (requires prior-year data)

Detects potential earnings manipulation using 8 financial indices.

M = -4.84 + 0.920(DSRI) + 0.528(GMI) + 0.404(AQI) + 0.892(SGI) + 0.115(DEPI) - 0.172(SGAI) + 4.679(TATA) - 0.327(LVGI)

| Index | Full Name | Formula | Red Flag If |
|-------|-----------|---------|-------------|
| DSRI | Days Sales in Receivables Index | (A/R_t/Rev_t) / (A/R_t-1/Rev_t-1) | >1.0 (receivables growing faster than revenue — potential channel stuffing) |
| GMI | Gross Margin Index | GM_t-1 / GM_t | >1.0 (margins declining — pressure to manipulate) |
| AQI | Asset Quality Index | Soft assets ratio change | >1.0 (more non-hard assets — potential capitalization of expenses) |
| SGI | Sales Growth Index | Rev_t / Rev_t-1 | High growth (growth companies have more opportunity and pressure to manipulate) |
| DEPI | Depreciation Index | Dep_rate_t-1 / Dep_rate_t | >1.0 (slowing depreciation to inflate earnings) |
| SGAI | SGA Expense Index | SGA%_t / SGA%_t-1 | <1.0 (actually reduces M-Score — model expects manipulation + rising SGA) |
| LVGI | Leverage Index | Leverage_t / Leverage_t-1 | >1.0 (increasing leverage) |
| TATA | Total Accruals to Total Assets | (NI - OCF) / Total Assets | >0 (earnings exceed cash — accrual-heavy) |

**Interpretation**: M-Score > -1.78 flags as "likely manipulator." This is a screening threshold from Beneish (1999) — it identifies accounting patterns consistent with historical manipulation cases. Not a conviction; always investigate which component indices are driving the score.

---

## Multi-Period Analytics

Available in `result.main.multiyear`.

| Feature | Access | Description | Use Case |
|---------|--------|-------------|----------|
| **Annual/Quarterly Data** | `.annual_data`, `.quarterly_data` | `{metric: {period: value}}` for every extracted and derived metric | Trend analysis, building factor timeseries |
| **YoY Growth** | `.yoy_growth` | Period-over-period % change | Identify acceleration or deceleration in any metric |
| **CAGR** | `.cagr` | Compound annual growth rate over the full period | Normalize multi-year growth into a single rate. Revenue CAGR >10% signals strong growth. |
| **TTM** | `.ttm` | Trailing twelve months from quarterly data | Most current annualized view. Flow metrics (revenue, NI, FCF) are summed over last 4 quarters; stock metrics (assets, equity) use the latest quarter value. |
| **Revenue Forecast** | `.forecast` | ARIMA statistical projection | Directional guidance only. Works best for stable, trending revenue. Not reliable for cyclical or volatile businesses. |

---

## Alerts

Alerts are strings in `metrics.alerts` (single-filing) and `ta.extra_alerts` (multi-period). They flag conditions that warrant attention but aren't definitive problems.

| Alert | Default Threshold | Override Key | What It Signals |
|-------|-------------------|-------------|-----------------|
| Negative net margin | 0% | `NEGATIVE_MARGIN` | Company is losing money on a net basis. Always concerning unless in a planned investment phase. |
| High leverage | D/E > 3.0 | `HIGH_LEVERAGE` | Financial risk. Raise to 5-10 for utilities, REITs, and banks where high leverage is structural. |
| Low ROE | < 5% | `LOW_ROE` | Weak shareholder returns. Lower for defensive/dividend stocks. Raise for growth screens. |
| Low ROA | < 2% | `LOW_ROA` | Poor asset productivity. Lower for capital-intensive industries (utilities, mining). |
| Net Debt/EBITDA | > 3.5x | `NET_DEBT_EBITDA_THRESHOLD` | Heavy leverage relative to earnings. Raise for leveraged sectors (infrastructure, telecom). |
| Interest coverage | < 2.0x | `INTEREST_COVERAGE_THRESHOLD` | Debt service strain. <1.0 means earnings don't cover interest. |
| Negative FCF streak | 2 quarters | `SUSTAINED_NEG_FCF_QUARTERS` | Cash burn. Raise to 4 for high-growth pre-profit companies. |
| Inventory spike | > 30% QoQ | `INVENTORY_SPIKE_THRESHOLD` | Demand softening or channel stuffing. Lower for retail (seasonal), raise for manufacturing. |
| Receivables spike | > 30% QoQ | `RECEIVABLE_SPIKE_THRESHOLD` | Collection problems or revenue timing. Lower when screening for aggressive revenue recognition. |
| Accounting identity | Assets != Liabilities + Equity | (not configurable) | Filing data quality issue. May indicate XBRL tagging error or parsing mismatch. |

```python
result = ea.analyze("AAPL", alerts_config={
    "HIGH_LEVERAGE": 5.0,
    "LOW_ROE": 10.0,
    "SUSTAINED_NEG_FCF_QUARTERS": 4,
})
```

---

*For workflow examples, see [USER_GUIDE.md](USER_GUIDE.md). For pipeline architecture, see [ARCHITECTURE.md](ARCHITECTURE.md). For contributing, see [CONTRIBUTING.md](../CONTRIBUTING.md).*
