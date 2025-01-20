"""
metrics.py

Computes key financial metrics (GAAP + IFRS expansions) from Balance, Income, and Cash Flow statements.
Handles intangible assets, goodwill, lease liabilities, net debt, intangible/goodwill ratios,
free cash flow, EBIT, EBITDA, net margin, etc.
Supports robust sign-flipping logic and IFRS expansions.
"""

import numpy as np
import pandas as pd
from edgar import Company

from .config import ALERTS_CONFIG
from .synonyms import SYNONYMS
from .synonyms_utils import find_synonym_value, flip_sign_if_negative_expense
from .logging_utils import get_logger

logger = get_logger(__name__)


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

    # 1) ---------- INCOME STATEMENT ----------
    revenue = find_synonym_value(income_df, SYNONYMS["revenue"], 0.0, "INC->Revenue")
    cost_rev = find_synonym_value(income_df, SYNONYMS["cost_of_revenue"], 0.0, "INC->CostOfRev")
    gross_profit = find_synonym_value(income_df, SYNONYMS["gross_profit"], np.nan, "INC->GrossProfit")
    op_exp = find_synonym_value(income_df, SYNONYMS["operating_expenses"], 0.0, "INC->OpEx")
    net_income = find_synonym_value(income_df, SYNONYMS["net_income"], 0.0, "INC->NetIncome")

    # flip negative cost of revenue, Opex if discovered as negative
    cost_rev = flip_sign_if_negative_expense(cost_rev, "cost_of_revenue")
    op_exp = flip_sign_if_negative_expense(op_exp, "operating_expenses")

    if pd.isna(gross_profit) and revenue != 0.0:
        gross_profit = revenue - cost_rev

    metrics["Revenue"] = revenue
    metrics["Gross Profit"] = 0.0 if pd.isna(gross_profit) else gross_profit
    metrics["Gross Margin %"] = (gross_profit / revenue * 100.0) if revenue else 0.0

    # Operating Income (approx)
    operating_income_approx = gross_profit - op_exp
    metrics["Operating Margin %"] = ((operating_income_approx / revenue) * 100.0) if revenue else 0.0
    metrics["Operating Expenses"] = op_exp
    metrics["Net Income"] = net_income
    metrics["Net Margin %"] = ((net_income / revenue) * 100.0) if revenue else 0.0

    # 2) ---------- BALANCE SHEET ----------
    curr_assets = find_synonym_value(balance_df, SYNONYMS["current_assets"], 0.0, "BS->CurrAssets")
    curr_liabs = find_synonym_value(balance_df, SYNONYMS["current_liabilities"], 0.0, "BS->CurrLiab")
    total_assets = find_synonym_value(balance_df, SYNONYMS["total_assets"], 0.0, "BS->TotalAssets")
    total_liabs = find_synonym_value(balance_df, SYNONYMS["total_liabilities"], 0.0, "BS->TotalLiab")
    total_equity = find_synonym_value(balance_df, SYNONYMS["total_equity"], 0.0, "BS->TotalEquity")

    metrics["Current Ratio"] = (curr_assets / curr_liabs) if curr_liabs else 0.0
    metrics["Debt-to-Equity"] = (total_liabs / total_equity) if total_equity else 0.0
    metrics["Equity Ratio %"] = ((total_equity / total_assets) * 100.0) if total_assets else 0.0

    # 3) ---------- CASH FLOW ----------
    op_cf = find_synonym_value(cash_df, SYNONYMS["cash_flow_operating"], 0.0, "CF->OpCF")
    capex_val = find_synonym_value(cash_df, SYNONYMS["capital_expenditures"], None, "CF->CapEx")

    if capex_val is not None and not pd.isna(capex_val):
        # If capex is negative, flip it
        if capex_val < 0.0:
            capex_val = abs(capex_val)
    else:
        # fallback: guess capex from investing CF
        inv_cf = find_synonym_value(cash_df, SYNONYMS["cash_flow_investing"], 0.0, "CF->InvestCF")
        capex_val = min(inv_cf, 0.0) * -1.0
        if capex_val is None:
            capex_val = 0.0

    free_cf = op_cf - capex_val
    metrics["Cash from Operations"] = op_cf
    metrics["Free Cash Flow"] = free_cf

    # 4) ---------- DEPRECIATION + COST-OF-SALES ADJUST ----------
    dep_amort = find_synonym_value(income_df, SYNONYMS["depreciation_amortization"], 0.0, "INC->DepAmort")
    dep_amort = flip_sign_if_negative_expense(dep_amort, "depreciation_amortization")
    cost_rev, dep_amort = adjust_for_dep_in_cogs(income_df, cost_rev, dep_amort)

    metrics["CostOfRev"] = cost_rev
    metrics["OpEx"] = op_exp

    operating_income_approx = (gross_profit - op_exp)
    metrics["EBIT (approx)"] = operating_income_approx
    metrics["EBITDA (approx)"] = operating_income_approx + dep_amort

    # 5) ---------- ROE / ROA ----------
    metrics["ROE %"] = ((net_income / total_equity) * 100.0) if total_equity else 0.0
    metrics["ROA %"] = ((net_income / total_assets) * 100.0) if total_assets else 0.0

    # 6) ---------- IFRS/GAAP EXPANSIONS ----------
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
        metrics["Intangible Ratio %"] = 0.0
        metrics["Goodwill Ratio %"] = 0.0

    net_intangibles = intangible_val + goodwill_val
    tangible_equity = total_equity - net_intangibles
    metrics["Tangible Equity"] = max(tangible_equity, 0.0)

    total_leases = oper_lease_val + fin_lease_val
    gross_debt = short_debt_val + long_debt_val + total_leases
    net_debt = gross_debt - cash_equiv_val
    metrics["Net Debt"] = net_debt

    ebitda_approx = metrics["EBITDA (approx)"]
    if ebitda_approx != 0:
        metrics["Net Debt/EBITDA"] = net_debt / ebitda_approx
    else:
        metrics["Net Debt/EBITDA"] = 0.0

    if total_assets > 0:
        metrics["Lease Liabilities Ratio %"] = (total_leases / total_assets) * 100.0
    else:
        metrics["Lease Liabilities Ratio %"] = 0.0

    # 7) ---------- NEW: INTEREST EXPENSE, INCOME TAX, STANDARD EBIT/EBITDA, INTEREST COVERAGE ----------
    interest_exp = find_synonym_value(income_df, SYNONYMS["interest_expense"], 0.0, "INC->InterestExpense")
    interest_exp = flip_sign_if_negative_expense(interest_exp, "interest_expense")
    metrics["Interest Expense"] = interest_exp

    # We do parse 'income_tax_expense' synonyms in synonyms.py
    # to get standard EBIT if you want:
    income_tax_val = find_synonym_value(income_df, SYNONYMS["income_tax_expense"], 0.0, "INC->TaxExpense")
    # If the reported tax was negative, flip it
    if income_tax_val < 0.0:
        income_tax_val = abs(income_tax_val)
    metrics["Income Tax Expense"] = income_tax_val

    # "Standard" EBIT = Net Income + Interest Expense + Income Tax
    ebit_standard = net_income + interest_exp + income_tax_val
    metrics["EBIT (standard)"] = ebit_standard

    # "Standard" EBITDA = EBIT (standard) + Dep/Amort
    ebitda_standard = ebit_standard + dep_amort
    metrics["EBITDA (standard)"] = ebitda_standard

    # Interest Coverage => EBIT / Interest Expense
    if interest_exp != 0.0:
        metrics["Interest Coverage"] = ebit_standard / interest_exp
    else:
        metrics["Interest Coverage"] = 0.0

    # 8) ---------- ALERTS ----------
    alerts = []
    if metrics["Net Margin %"] < ALERTS_CONFIG["NEGATIVE_MARGIN"]:
        alerts.append(f"Net margin below {ALERTS_CONFIG['NEGATIVE_MARGIN']}% (negative)")
    if metrics["Debt-to-Equity"] > ALERTS_CONFIG["HIGH_LEVERAGE"]:
        alerts.append(f"Debt-to-Equity above {ALERTS_CONFIG['HIGH_LEVERAGE']} (high leverage)")
    if 0.0 < metrics["ROE %"] < ALERTS_CONFIG["LOW_ROE"]:
        alerts.append(f"ROE < {ALERTS_CONFIG['LOW_ROE']}%")
    if 0.0 < metrics["ROA %"] < ALERTS_CONFIG["LOW_ROA"]:
        alerts.append(f"ROA < {ALERTS_CONFIG['LOW_ROA']}%")
    if metrics["Net Debt"] > 0 and metrics["Net Debt/EBITDA"] > 3.5:
        alerts.append("Net Debt/EBITDA above 3.5 (heavy leverage).")

    # Optional: interest coverage alert if <2.0
    if metrics["Interest Coverage"] != 0.0 and metrics["Interest Coverage"] < 2.0:
        alerts.append("Interest coverage below 2.0 => potential default risk.")

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
        logger.debug(
            "Depreciation in cost of sales found = %.2f. Adjusting cost_of_revenue & D&A.",
            dep_in_cogs
        )
        cost_of_revenue -= dep_in_cogs
        dep_amort += dep_in_cogs

    return cost_of_revenue, dep_amort


def get_filing_info(filing_obj) -> dict:
    """
    Extract form, filing_date, company name, and accession_no from an edgar.Filing object.

    :param filing_obj: The Filing object from 'edgar' library
    :return: A dict with 'form_type', 'filed_date', 'company', 'accession_no'.
    """
    info = {}
    if filing_obj:
        info["form_type"] = filing_obj.form if filing_obj.form else "Unknown"
        info["filed_date"] = filing_obj.filing_date if filing_obj.filing_date else "Unknown"
        info["company"] = filing_obj.company if filing_obj.company else "Unknown"
        info["accession_no"] = filing_obj.accession_no if filing_obj.accession_no else "Unknown"
    else:
        info = {
            "form_type": "Unknown",
            "filed_date": "Unknown",
            "company": "Unknown",
            "accession_no": "Unknown",
        }
    return info


def get_single_filing_snapshot(comp: Company, form_type: str) -> dict:
    """
    Retrieve the latest 'form_type' (10-K or 10-Q) filing for a given company,
    parse metrics, and attach filing info. If missing or any error, return empty structures.

    :param comp: edgar.Company object
    :param form_type: e.g. "10-K" or "10-Q"
    :return: dict with "metrics" and "filing_info" sub-dicts
    """
    from .data_utils import ensure_dataframe, make_numeric_df

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
    bs_df = make_numeric_df(ensure_dataframe(fin.get_balance_sheet(), f"{tkr}-{form_type}-BS"), f"{tkr}-{form_type}-BS")
    inc_df = make_numeric_df(ensure_dataframe(fin.get_income_statement(), f"{tkr}-{form_type}-INC"), f"{tkr}-{form_type}-INC")
    cf_df = make_numeric_df(ensure_dataframe(fin.get_cash_flow_statement(), f"{tkr}-{form_type}-CF"), f"{tkr}-{form_type}-CF")

    metrics = compute_ratios_and_metrics(bs_df, inc_df, cf_df)
    result["metrics"] = metrics
    result["filing_info"] = filing_info
    return result
