"""
metrics.py

Computes key financial metrics (GAAP + IFRS expansions) from Balance, Income, and Cash Flow statements.
Handles intangible assets, goodwill, lease liabilities, net debt, intangible/goodwill ratios,
free cash flow, EBIT, EBITDA, net margin, etc.

Uses 'synonyms_utils.compute_capex_single_period' for safer fallback when explicit 'capital_expenditures' is absent.
"""

from typing import List, Optional, TypedDict

import numpy as np
import pandas as pd
from edgar import Company


class RawMetrics(TypedDict, total=False):
    """Schema for the internal metrics dict flowing through the pipeline.

    All keys are optional (``total=False``). Public metric keys use
    human-readable names; internal balance-sheet values use ``_`` prefixed
    keys to avoid collisions.
    """

    Revenue: float
    CostOfRev: float
    Net_Income: float  # stored as "Net Income" at runtime
    Operating_Income: float
    Free_Cash_Flow: float
    Cash_from_Operations: float
    Income_Tax_Expense: float
    EBIT_standard: float
    EBITDA_standard: float
    Gross_Margin_pct: float
    Net_Margin_pct: float
    Operating_Margin_pct: float
    Current_Ratio: float
    Debt_to_Equity: float
    ROE_pct: float
    ROA_pct: float
    Interest_Coverage: float
    Net_Debt: float
    Net_Debt_EBITDA: float
    Alerts: List[str]
    _total_assets: float
    _total_liabilities: float
    _total_equity: float
    _current_assets: float
    _current_liabilities: float
    _short_term_debt: float
    _long_term_debt: float
    _cash_equivalents: float
    _accounts_receivable: float
    _inventory: float
    _accounts_payable: float
    _retained_earnings: float
    _ppe_net: float
    _shares_outstanding: float
    _dep_amort: float
    _sga: float
    _short_term_investments: float
    _long_term_investments: float
    _capex: float
    _income_before_taxes: float
    _IdentityCheck: str
    _is_financial: bool
    _scores: dict

from .config import ALERTS_CONFIG, get_alerts_config
from .scores import compute_all_scores, run_dqc_checks
from .synonyms import SYNONYMS
from .synonyms_utils import (
    find_synonym_value,
    flip_sign_if_negative_expense,
    compute_capex_single_period
)
from .data_utils import ensure_dataframe, make_numeric_df
from .logging_utils import get_logger

logger = get_logger(__name__)


def _get_financial_statement(financials, statement_type: str):
    """Retrieve a financial statement, handling both old method-based and new
    property-based edgartools APIs transparently."""
    method_name = f"get_{statement_type}"
    if hasattr(financials, method_name) and callable(getattr(financials, method_name)):
        return getattr(financials, method_name)()
    return getattr(financials, statement_type, None)


def compute_ratios_and_metrics(
    balance_df: pd.DataFrame,
    income_df: pd.DataFrame,
    cash_df: pd.DataFrame,
    alerts_config: Optional[dict] = None,
    is_financial: bool = False,
) -> RawMetrics:
    """
    Compute key financial ratios from the provided DataFrames (Balance, Income, Cash Flow).
    Includes expanded IFRS/GAAP coverage:
      - Net Income, Revenue, Margins
      - Free Cash Flow (OpCF - CapEx)
      - Operating Income, EBITDA
      - IFRS expansions: intangible ratio, goodwill ratio, net debt, net debt/EBITDA, lease liabilities, etc.

    :param balance_df: Balance sheet data as a DataFrame
    :param income_df: Income statement data as a DataFrame
    :param cash_df:   Cash flow statement data as a DataFrame
    :return: A dictionary of computed metrics and alerts.
    """
    cfg = get_alerts_config(alerts_config)
    metrics = {}

    # ========== INCOME STATEMENT ==========
    revenue = find_synonym_value(income_df, SYNONYMS["revenue"], 0.0, "INC->Revenue")
    cost_rev = find_synonym_value(income_df, SYNONYMS["cost_of_revenue"], 0.0, "INC->CostOfRev")
    gross_profit = find_synonym_value(income_df, SYNONYMS["gross_profit"], np.nan, "INC->GrossProfit")
    op_exp = find_synonym_value(income_df, SYNONYMS["operating_expenses"], 0.0, "INC->OpEx")
    net_income = find_synonym_value(income_df, SYNONYMS["net_income"], 0.0, "INC->NetIncome")

    # Flip sign if negative expenses
    cost_rev = flip_sign_if_negative_expense(cost_rev, "cost_of_revenue")
    op_exp = flip_sign_if_negative_expense(op_exp, "operating_expenses")

    # ========== DEPRECIATION & D&A-IN-COGS ADJUSTMENT ==========
    dep_amort = find_synonym_value(income_df, SYNONYMS["depreciation_amortization"], 0.0, "INC->DepAmort")
    dep_amort = flip_sign_if_negative_expense(dep_amort, "depreciation_amortization")
    orig_cost_rev = cost_rev
    cost_rev, dep_amort = adjust_for_dep_in_cogs(income_df, cost_rev, dep_amort)
    dep_in_cogs_adjusted = cost_rev != orig_cost_rev

    if pd.isna(gross_profit) or dep_in_cogs_adjusted:
        gross_profit = revenue - cost_rev

    metrics["Revenue"] = revenue
    metrics["CostOfRev"] = cost_rev
    metrics["Gross Profit"] = gross_profit
    metrics["Gross Margin %"] = (gross_profit / revenue * 100.0) if revenue else np.nan
    metrics["OpEx"] = op_exp
    metrics["Net Income"] = net_income
    metrics["Net Margin %"] = ((net_income / revenue) * 100.0) if revenue else np.nan

    reported_op_income = find_synonym_value(income_df, SYNONYMS["operating_income"], np.nan, "INC->OpIncome")
    if pd.notna(reported_op_income):
        operating_income = reported_op_income
    else:
        operating_income = gross_profit - op_exp
    metrics["Operating Income"] = operating_income
    metrics["Operating Margin %"] = ((operating_income / revenue) * 100.0) if revenue else np.nan
    metrics["EBIT (approx)"] = operating_income
    metrics["EBITDA (approx)"] = operating_income + dep_amort

    # ========== BALANCE SHEET ==========
    curr_assets = find_synonym_value(balance_df, SYNONYMS["current_assets"], 0.0, "BS->CurrAssets")
    curr_liabs = find_synonym_value(balance_df, SYNONYMS["current_liabilities"], 0.0, "BS->CurrLiab")
    total_assets = find_synonym_value(balance_df, SYNONYMS["total_assets"], 0.0, "BS->TotalAssets")
    total_liabs = find_synonym_value(balance_df, SYNONYMS["total_liabilities"], 0.0, "BS->TotalLiab")
    total_equity = find_synonym_value(balance_df, SYNONYMS["total_equity"], 0.0, "BS->TotalEquity")

    metrics["Current Ratio"] = (curr_assets / curr_liabs) if curr_liabs else np.nan

    if total_equity < 0:
        metrics["Debt-to-Equity"] = np.nan
    elif total_equity == 0:
        metrics["Debt-to-Equity"] = np.nan
    else:
        metrics["Debt-to-Equity"] = total_liabs / total_equity
    metrics["Equity Ratio %"] = ((total_equity / total_assets) * 100.0) if total_assets else np.nan

    # ========== CASH FLOW STATEMENT ==========
    op_cf = find_synonym_value(cash_df, SYNONYMS["cash_flow_operating"], 0.0, "CF->OpCF")
    capex_val = compute_capex_single_period(cash_df, debug_label="CF->CapExSingle")

    free_cf = op_cf - capex_val
    metrics["Cash from Operations"] = op_cf
    metrics["Free Cash Flow"] = free_cf

    # ========== ROE / ROA ==========
    if total_equity > 0:
        metrics["ROE %"] = (net_income / total_equity) * 100.0
    else:
        metrics["ROE %"] = np.nan
    metrics["ROA %"] = ((net_income / total_assets) * 100.0) if total_assets else np.nan

    # ========== IFRS/GAAP EXPANSIONS ==========
    intangible_val = find_synonym_value(balance_df, SYNONYMS["intangible_assets"], 0.0, "BS->Intangibles")
    goodwill_val = find_synonym_value(balance_df, SYNONYMS["goodwill"], 0.0, "BS->Goodwill")
    oper_lease_val = find_synonym_value(balance_df, SYNONYMS["operating_lease_liabilities"], 0.0, "BS->OperLeaseLiab")
    fin_lease_val = find_synonym_value(balance_df, SYNONYMS["finance_lease_liabilities"], 0.0, "BS->FinLeaseLiab")
    short_debt_val = find_synonym_value(balance_df, SYNONYMS["short_term_debt"], 0.0, "BS->ShortTermDebt")
    long_debt_val = find_synonym_value(balance_df, SYNONYMS["long_term_debt"], 0.0, "BS->LongTermDebt")
    cash_equiv_val = find_synonym_value(balance_df, SYNONYMS["cash_equivalents"], 0.0, "BS->CashEq")

    if total_assets > 0:
        metrics["Intangible Ratio %"] = (intangible_val / total_assets) * 100.0
        metrics["Goodwill Ratio %"] = (goodwill_val / total_assets) * 100.0
    else:
        metrics["Intangible Ratio %"] = np.nan
        metrics["Goodwill Ratio %"] = np.nan

    net_intangibles = intangible_val + goodwill_val
    tangible_equity = total_equity - net_intangibles
    metrics["Tangible Equity"] = tangible_equity

    st_invest_val = find_synonym_value(balance_df, SYNONYMS["short_term_investments"], 0.0, "BS->STInvest")
    lt_invest_val = find_synonym_value(balance_df, SYNONYMS["long_term_investments"], 0.0, "BS->LTInvest")

    total_leases = oper_lease_val + fin_lease_val
    gross_debt = short_debt_val + long_debt_val + total_leases
    net_debt = gross_debt - cash_equiv_val - st_invest_val - lt_invest_val
    metrics["Net Debt"] = net_debt
    metrics["Lease Liabilities Ratio %"] = ((total_leases / total_assets) * 100.0) if total_assets else np.nan

    # ========== INTEREST EXPENSE / TAX EXPENSE / STANDARD EBIT & EBITDA ==========
    interest_exp = find_synonym_value(income_df, SYNONYMS["interest_expense"], 0.0, "INC->InterestExpense")
    interest_exp = flip_sign_if_negative_expense(interest_exp, "interest_expense")
    metrics["Interest Expense"] = interest_exp

    income_tax_val = find_synonym_value(income_df, SYNONYMS["income_tax_expense"], 0.0, "INC->TaxExpense")
    metrics["Income Tax Expense"] = income_tax_val

    ebit_standard = net_income + interest_exp + income_tax_val
    metrics["EBIT (standard)"] = ebit_standard
    ebitda_standard = ebit_standard + dep_amort
    metrics["EBITDA (standard)"] = ebitda_standard
    metrics["Interest Coverage"] = (ebit_standard / interest_exp) if interest_exp > 0.0 else np.nan

    # Net Debt/EBITDA uses the standard (bottom-up) EBITDA for consistency
    if pd.notna(ebitda_standard) and ebitda_standard > 0:
        metrics["Net Debt/EBITDA"] = net_debt / ebitda_standard
    else:
        metrics["Net Debt/EBITDA"] = np.nan

    # ========== QUALITY / ACCRUALS FACTORS ==========
    metrics["Accruals Ratio"] = ((net_income - op_cf) / total_assets) if total_assets else np.nan
    metrics["Earnings Quality"] = (op_cf / net_income) if net_income != 0 else np.nan
    total_debt = short_debt_val + long_debt_val
    metrics["Cash Flow Coverage"] = (op_cf / total_debt) if total_debt > 0 else np.nan

    # ========== EXTENDED LEVERAGE RATIOS ==========
    inventory_val = find_synonym_value(balance_df, SYNONYMS["inventory"], 0.0, "BS->InvQR")
    metrics["Quick Ratio"] = ((curr_assets - inventory_val) / curr_liabs) if curr_liabs else np.nan
    metrics["Cash Ratio"] = (cash_equiv_val / curr_liabs) if curr_liabs else np.nan
    total_capital = total_debt + total_equity
    metrics["Debt/Total Capital"] = (total_debt / total_capital) if total_capital > 0 else np.nan
    metrics["Fixed Charge Coverage"] = (
        (ebit_standard + total_leases) / (interest_exp + total_leases)
        if (interest_exp + total_leases) > 0 else np.nan
    )

    # ========== INTERNAL VALUES FOR SCORING MODELS ==========
    # Underscore-prefixed keys carry raw balance-sheet / income values needed
    # by compute_all_scores and YoY score comparisons without re-reading DataFrames.
    sga_val = find_synonym_value(income_df, SYNONYMS["general_administrative"], 0.0, "INC->SGA")
    sga_val = flip_sign_if_negative_expense(sga_val, "general_administrative")
    ppe_val = find_synonym_value(balance_df, SYNONYMS["ppe_net"], 0.0, "BS->PPE")
    shares_out = find_synonym_value(balance_df, SYNONYMS["common_shares_outstanding"], 0.0, "BS->Shares")
    retained_val = find_synonym_value(balance_df, SYNONYMS["retained_earnings"], 0.0, "BS->RetainedEarnings")
    income_before_taxes = find_synonym_value(income_df, SYNONYMS["income_before_taxes"], np.nan, "INC->PreTax")

    metrics["_total_assets"] = total_assets
    metrics["_total_liabilities"] = total_liabs
    metrics["_total_equity"] = total_equity
    metrics["_current_assets"] = curr_assets
    metrics["_current_liabilities"] = curr_liabs
    metrics["_short_term_debt"] = short_debt_val
    metrics["_long_term_debt"] = long_debt_val
    metrics["_cash_equivalents"] = cash_equiv_val
    metrics["_accounts_receivable"] = find_synonym_value(balance_df, SYNONYMS["accounts_receivable"], 0.0, "BS->AR")
    metrics["_inventory"] = find_synonym_value(balance_df, SYNONYMS["inventory"], 0.0, "BS->Inv")
    metrics["_accounts_payable"] = find_synonym_value(balance_df, SYNONYMS["accounts_payable"], 0.0, "BS->AP")
    metrics["_retained_earnings"] = retained_val
    metrics["_ppe_net"] = ppe_val
    metrics["_shares_outstanding"] = shares_out
    metrics["_dep_amort"] = dep_amort
    metrics["_sga"] = sga_val
    metrics["_short_term_investments"] = st_invest_val
    metrics["_long_term_investments"] = lt_invest_val
    metrics["_capex"] = capex_val
    metrics["_income_before_taxes"] = income_before_taxes if pd.notna(income_before_taxes) else net_income + income_tax_val
    metrics["_preferred_stock"] = find_synonym_value(balance_df, SYNONYMS["preferred_stock"], 0.0, "BS->Preferred")
    metrics["_minority_interest"] = find_synonym_value(balance_df, SYNONYMS["minority_interest"], 0.0, "BS->Minority")

    # ========== ACCOUNTING IDENTITY VALIDATION ==========
    identity_check = _validate_accounting_identity(total_assets, total_liabs, total_equity)
    metrics["_IdentityCheck"] = identity_check
    metrics["_is_financial"] = is_financial

    # ========== ALERTS ==========
    alerts = []
    if identity_check and identity_check != "ok":
        alerts.append(identity_check)
    net_margin = metrics["Net Margin %"]
    if pd.notna(net_margin) and net_margin < cfg["NEGATIVE_MARGIN"]:
        alerts.append(f"Net margin below {cfg['NEGATIVE_MARGIN']}% (negative)")

    de_ratio = metrics["Debt-to-Equity"]
    if pd.notna(de_ratio) and de_ratio > cfg["HIGH_LEVERAGE"]:
        alerts.append(f"Debt-to-Equity above {cfg['HIGH_LEVERAGE']} (high leverage)")
    if total_equity < 0:
        alerts.append("Negative shareholders' equity (potential insolvency)")

    roe = metrics["ROE %"]
    if pd.notna(roe) and total_equity > 0 and roe < cfg["LOW_ROE"]:
        alerts.append(f"ROE < {cfg['LOW_ROE']}%")
    roa = metrics["ROA %"]
    if pd.notna(roa) and roa < cfg["LOW_ROA"]:
        alerts.append(f"ROA < {cfg['LOW_ROA']}%")

    if tangible_equity < 0:
        alerts.append("Negative tangible equity (intangibles exceed equity)")

    net_debt_ebitda = metrics["Net Debt/EBITDA"]
    net_debt_threshold = cfg["NET_DEBT_EBITDA_THRESHOLD"]
    if metrics["Net Debt"] > 0:
        if pd.isna(net_debt_ebitda):
            alerts.append("Net Debt positive but EBITDA non-positive => leverage ratio undefined.")
        elif net_debt_ebitda > net_debt_threshold:
            alerts.append(f"Net Debt/EBITDA above {net_debt_threshold} (heavy leverage).")

    interest_cov = metrics["Interest Coverage"]
    interest_cov_threshold = cfg["INTEREST_COVERAGE_THRESHOLD"]
    if pd.notna(interest_cov) and interest_cov < interest_cov_threshold:
        alerts.append(f"Interest coverage below {interest_cov_threshold} => potential default risk.")

    # ========== DQC SIGN CHECKS ==========
    for stmt_df, label in [(balance_df, "BS"), (income_df, "INC")]:
        dqc_warnings = run_dqc_checks(stmt_df, debug_label=label)
        alerts.extend(dqc_warnings)

    metrics["Alerts"] = alerts

    # ========== SCORING MODELS ==========
    scores = compute_all_scores(metrics, balance_df, income_df, cash_df, is_financial=is_financial)
    metrics["_scores"] = scores

    return metrics


def adjust_for_dep_in_cogs(
    income_df: pd.DataFrame,
    cost_of_revenue: float,
    dep_amort: float
) -> tuple[float, float]:
    """
    If there's a separate 'Depreciation in cost of sales' row, remove it from cost_of_revenue
    (already flipped to positive) and add it to total Dep/Amort. Avoids double counting.

    :param income_df: Income statement DataFrame
    :param cost_of_revenue: cost_of_revenue float (already sign-flipped if negative)
    :param dep_amort: total depreciation & amortization previously found
    :return: (adjusted_cost_of_revenue, adjusted_dep_amort)
    """
    dep_in_cogs = find_synonym_value(
        income_df, SYNONYMS.get("depreciation_in_cost_of_sales", []), 0.0, "INC->DepInCOGS"
    )
    if dep_in_cogs != 0.0:
        dep_in_cogs_abs = abs(dep_in_cogs)
        logger.debug(
            "Depreciation in cost of sales found = %.2f (abs=%.2f). Adjusting cost_of_revenue & D&A.",
            dep_in_cogs, dep_in_cogs_abs
        )
        cost_of_revenue -= dep_in_cogs_abs
        dep_amort += dep_in_cogs_abs

    return cost_of_revenue, dep_amort


def _validate_accounting_identity(
    total_assets: float, total_liabilities: float, total_equity: float
) -> str:
    """Check Assets = Liabilities + Equity within 1% tolerance.
    Returns 'ok' if valid, a warning string if not, or '' if data is missing."""
    expected = total_liabilities + total_equity
    if total_assets == 0.0 and expected == 0.0:
        return ""
    denominator = max(abs(total_assets), abs(expected), 1.0)
    diff_pct = abs(total_assets - expected) / denominator * 100.0
    if diff_pct > 1.0:
        return (
            f"Accounting identity mismatch: Assets ({total_assets:,.0f}) != "
            f"Liabilities ({total_liabilities:,.0f}) + Equity ({total_equity:,.0f}), "
            f"diff={diff_pct:.1f}%"
        )
    return "ok"


def get_filing_info(filing_obj) -> dict:
    """Extract form, filing_date, company name, and accession_no from an edgar.Filing object."""
    fields = {"form_type": "form", "filed_date": "filing_date", "company": "company", "accession_no": "accession_no"}
    if not filing_obj:
        return {k: "Unknown" for k in fields}
    return {k: getattr(filing_obj, attr, None) or "Unknown" for k, attr in fields.items()}


ANNUAL_FORM_TYPES = ("10-K", "10-K/A", "20-F", "20-F/A")
QUARTERLY_FORM_TYPES = ("10-Q", "10-Q/A")


def get_filing_snapshot_with_fallback(
    comp: Company, form_types: tuple,
    alerts_config: Optional[dict] = None,
    is_financial: bool = False,
) -> dict:
    """Try each form type in order, returning the first successful snapshot."""
    for ft in form_types:
        snap = get_single_filing_snapshot(
            comp, ft, alerts_config=alerts_config, is_financial=is_financial,
        )
        if snap.get("metrics"):
            return snap
    return {"metrics": {}, "filing_info": {}}


def get_single_filing_snapshot(
    comp: Company, form_type: str,
    alerts_config: Optional[dict] = None,
    is_financial: bool = False,
) -> dict:
    """
    Retrieve the latest 'form_type' filing for a given company,
    parse metrics, and attach filing info. If missing or any error, return empty structures.

    :param comp: edgar.Company object
    :param form_type: e.g. "10-K", "20-F", or "10-Q"
    :return: dict with "metrics" and "filing_info" sub-dicts
    """
    result = {"metrics": {}, "filing_info": {}}
    tkr = comp.tickers[0] if comp.tickers else "UNKNOWN"

    try:
        filing = comp.get_filings(form=form_type, is_xbrl=True).latest()
    except Exception as exc:
        logger.warning("%s: Could not get latest %s filing -> %s", tkr, form_type, exc)
        return result

    if not filing:
        logger.warning("%s: No %s filing found.", tkr, form_type)
        return result

    filing_info = get_filing_info(filing)
    fo = filing.obj()
    if not hasattr(fo, "financials"):
        logger.warning("%s: The %s filing object has no 'financials'.", tkr, form_type)
        result["filing_info"] = filing_info
        return result

    fin = fo.financials
    bs_df = make_numeric_df(ensure_dataframe(_get_financial_statement(fin, "balance_sheet"), f"{tkr}-{form_type}-BS"), f"{tkr}-{form_type}-BS")
    inc_df = make_numeric_df(ensure_dataframe(_get_financial_statement(fin, "income_statement"), f"{tkr}-{form_type}-INC"), f"{tkr}-{form_type}-INC")
    cf_df = make_numeric_df(ensure_dataframe(_get_financial_statement(fin, "cash_flow_statement"), f"{tkr}-{form_type}-CF"), f"{tkr}-{form_type}-CF")

    metrics = compute_ratios_and_metrics(
        bs_df, inc_df, cf_df, alerts_config=alerts_config, is_financial=is_financial,
    )
    if form_type in ("20-F", "20-F/A"):
        metrics.setdefault("Alerts", []).append(
            "20-F filer: figures may be in a non-USD reporting currency"
        )
    result["metrics"] = metrics
    result["filing_info"] = filing_info
    return result


def get_prior_annual_metrics(
    comp: Company, alerts_config: Optional[dict] = None,
    is_financial: bool = False,
) -> dict:
    """Fetch the second-most-recent annual filing's metrics for YoY comparisons.

    Returns an empty dict if no prior-year filing is available.
    """
    tkr = comp.tickers[0] if comp.tickers else "UNKNOWN"
    for ft in ANNUAL_FORM_TYPES:
        try:
            filings = comp.get_filings(form=ft, is_xbrl=True).head(2)
            if filings is None or len(filings) < 2:
                continue
            prior_filing = filings[1]
            fo = prior_filing.obj()
            if not hasattr(fo, "financials"):
                continue
            fin = fo.financials
            bs = make_numeric_df(ensure_dataframe(_get_financial_statement(fin, "balance_sheet"), f"{tkr}-prior-BS"), f"{tkr}-prior-BS")
            inc = make_numeric_df(ensure_dataframe(_get_financial_statement(fin, "income_statement"), f"{tkr}-prior-INC"), f"{tkr}-prior-INC")
            cf = make_numeric_df(ensure_dataframe(_get_financial_statement(fin, "cash_flow_statement"), f"{tkr}-prior-CF"), f"{tkr}-prior-CF")
            metrics = compute_ratios_and_metrics(bs, inc, cf, alerts_config=alerts_config, is_financial=is_financial)
            if metrics:
                logger.info("%s: Loaded prior-year metrics from %s for YoY scores.", tkr, ft)
                return metrics
        except Exception as exc:
            logger.debug("%s: Failed to get prior %s filing: %s", tkr, ft, exc)
    return {}
