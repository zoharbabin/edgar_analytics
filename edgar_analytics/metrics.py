"""
metrics.py

Computes key financial metrics (GAAP + IFRS expansions) from Balance, Income, and Cash Flow statements.
Handles intangible assets, goodwill, lease liabilities, net debt, intangible/goodwill ratios,
free cash flow, EBIT, EBITDA, net margin, etc.

Uses 'synonyms_utils.compute_capex_single_period' for safer fallback when explicit 'capital_expenditures' is absent.
"""

import numpy as np
import pandas as pd
from edgar import Company

from .config import ALERTS_CONFIG
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
    cash_df: pd.DataFrame
) -> dict:
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
    cost_rev, dep_amort = adjust_for_dep_in_cogs(income_df, cost_rev, dep_amort)

    if pd.isna(gross_profit):
        gross_profit = revenue - cost_rev if revenue != 0.0 else 0.0

    metrics["Revenue"] = revenue
    metrics["CostOfRev"] = cost_rev
    metrics["Gross Profit"] = gross_profit
    metrics["Gross Margin %"] = (gross_profit / revenue * 100.0) if revenue else np.nan
    metrics["OpEx"] = op_exp
    metrics["Net Income"] = net_income
    metrics["Net Margin %"] = ((net_income / revenue) * 100.0) if revenue else np.nan

    operating_income_approx = gross_profit - op_exp
    metrics["Operating Margin %"] = ((operating_income_approx / revenue) * 100.0) if revenue else np.nan
    metrics["EBIT (approx)"] = operating_income_approx
    metrics["EBITDA (approx)"] = operating_income_approx + dep_amort

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

    ebitda_approx = metrics["EBITDA (approx)"]
    if pd.notna(ebitda_approx) and ebitda_approx > 0:
        metrics["Net Debt/EBITDA"] = net_debt / ebitda_approx
    else:
        metrics["Net Debt/EBITDA"] = np.nan
    metrics["Lease Liabilities Ratio %"] = ((total_leases / total_assets) * 100.0) if total_assets else np.nan

    # ========== INTEREST EXPENSE / TAX EXPENSE / STANDARD EBIT & EBITDA ==========
    interest_exp = find_synonym_value(income_df, SYNONYMS["interest_expense"], 0.0, "INC->InterestExpense")
    interest_exp = flip_sign_if_negative_expense(interest_exp, "interest_expense")
    metrics["Interest Expense"] = interest_exp

    income_tax_val = find_synonym_value(income_df, SYNONYMS["income_tax_expense"], 0.0, "INC->TaxExpense")
    # Tax expense is kept as-is: positive = expense, negative = benefit (e.g. deferred tax).
    # EBIT = NI + Interest + Tax uses the signed value for financial accuracy.
    metrics["Income Tax Expense"] = income_tax_val

    ebit_standard = net_income + interest_exp + income_tax_val
    metrics["EBIT (standard)"] = ebit_standard
    metrics["EBITDA (standard)"] = ebit_standard + dep_amort
    metrics["Interest Coverage"] = (ebit_standard / interest_exp) if interest_exp > 0.0 else np.nan

    # ========== ALERTS ==========
    alerts = []
    net_margin = metrics["Net Margin %"]
    if pd.notna(net_margin) and net_margin < ALERTS_CONFIG["NEGATIVE_MARGIN"]:
        alerts.append(f"Net margin below {ALERTS_CONFIG['NEGATIVE_MARGIN']}% (negative)")

    de_ratio = metrics["Debt-to-Equity"]
    if pd.notna(de_ratio) and de_ratio > ALERTS_CONFIG["HIGH_LEVERAGE"]:
        alerts.append(f"Debt-to-Equity above {ALERTS_CONFIG['HIGH_LEVERAGE']} (high leverage)")
    if total_equity < 0:
        alerts.append("Negative shareholders' equity (potential insolvency)")

    roe = metrics["ROE %"]
    if pd.notna(roe) and roe < ALERTS_CONFIG["LOW_ROE"]:
        alerts.append(f"ROE < {ALERTS_CONFIG['LOW_ROE']}%")
    roa = metrics["ROA %"]
    if pd.notna(roa) and roa < ALERTS_CONFIG["LOW_ROA"]:
        alerts.append(f"ROA < {ALERTS_CONFIG['LOW_ROA']}%")

    if tangible_equity < 0:
        alerts.append("Negative tangible equity (intangibles exceed equity)")

    net_debt_ebitda = metrics["Net Debt/EBITDA"]
    net_debt_threshold = ALERTS_CONFIG["NET_DEBT_EBITDA_THRESHOLD"]
    if metrics["Net Debt"] > 0:
        if pd.isna(net_debt_ebitda):
            alerts.append("Net Debt positive but EBITDA non-positive => leverage ratio undefined.")
        elif net_debt_ebitda > net_debt_threshold:
            alerts.append(f"Net Debt/EBITDA above {net_debt_threshold} (heavy leverage).")

    interest_cov = metrics["Interest Coverage"]
    interest_cov_threshold = ALERTS_CONFIG["INTEREST_COVERAGE_THRESHOLD"]
    if pd.notna(interest_cov) and interest_cov < interest_cov_threshold:
        alerts.append(f"Interest coverage below {interest_cov_threshold} => potential default risk.")

    metrics["Alerts"] = alerts
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


def get_filing_info(filing_obj) -> dict:
    """Extract form, filing_date, company name, and accession_no from an edgar.Filing object."""
    fields = {"form_type": "form", "filed_date": "filing_date", "company": "company", "accession_no": "accession_no"}
    if not filing_obj:
        return {k: "Unknown" for k in fields}
    return {k: getattr(filing_obj, attr, None) or "Unknown" for k, attr in fields.items()}


ANNUAL_FORM_TYPES = ("10-K", "20-F")
QUARTERLY_FORM_TYPES = ("10-Q",)


def get_filing_snapshot_with_fallback(comp: Company, form_types: tuple) -> dict:
    """Try each form type in order, returning the first successful snapshot."""
    for ft in form_types:
        snap = get_single_filing_snapshot(comp, ft)
        if snap.get("metrics"):
            return snap
    return {"metrics": {}, "filing_info": {}}


def get_single_filing_snapshot(comp: Company, form_type: str) -> dict:
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

    metrics = compute_ratios_and_metrics(bs_df, inc_df, cf_df)
    result["metrics"] = metrics
    result["filing_info"] = filing_info
    return result
