# edgar_analytics/metrics.py

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
    Compute key financial ratios from the given dataframes (Balance, Income, Cash Flow)
    and return them in a dictionary.

    This includes: 
      - Revenue, Gross Profit, Margins
      - Operating Income (EBIT approx), EBITDA (approx)
      - Key Balance Sheet ratios (Current Ratio, Debt-to-Equity, etc.)
      - Free Cash Flow
      - Basic alerts (negative margin, high leverage, etc.)

    :param balance_df: Balance sheet data as a pandas DataFrame
    :param income_df: Income statement data as a pandas DataFrame
    :param cash_df: Cash flow statement data as a pandas DataFrame
    :return: Dictionary of computed metrics.
    """
    metrics = {}

    # -------------- INCOME STATEMENT --------------
    revenue = find_synonym_value(
        income_df, SYNONYMS["revenue"], fallback=0.0, debug_label="INC->Revenue"
    )
    cost_revenue = find_synonym_value(
        income_df, SYNONYMS["cost_of_revenue"], fallback=0.0, debug_label="INC->CostOfRev"
    )
    gross_profit = find_synonym_value(
        income_df, SYNONYMS["gross_profit"], fallback=np.nan, debug_label="INC->GrossProfit"
    )
    op_exp = find_synonym_value(
        income_df, SYNONYMS["operating_expenses"], fallback=0.0, debug_label="INC->OpEx"
    )
    net_income = find_synonym_value(
        income_df, SYNONYMS["net_income"], fallback=0.0, debug_label="INC->NetIncome"
    )

    # Flip negative expenses if needed
    cost_revenue = flip_sign_if_negative_expense(cost_revenue, "cost_of_revenue")
    op_exp = flip_sign_if_negative_expense(op_exp, "operating_expenses")

    # If no explicit 'gross_profit' row is found, compute it
    if pd.isna(gross_profit) and revenue != 0.0:
        gross_profit = revenue - cost_revenue

    metrics["Revenue"] = revenue
    metrics["Gross Profit"] = gross_profit if not pd.isna(gross_profit) else 0.0
    metrics["Gross Margin %"] = (gross_profit / revenue * 100.0) if revenue else 0.0

    operating_income_approx = gross_profit - op_exp
    metrics["Operating Margin %"] = (
        (operating_income_approx / revenue) * 100.0 if revenue else 0.0
    )
    metrics["Operating Expenses"] = op_exp
    metrics["Net Income"] = net_income
    metrics["Net Margin %"] = (net_income / revenue * 100.0) if revenue else 0.0

    # -------------- BALANCE SHEET --------------
    curr_assets = find_synonym_value(
        balance_df, SYNONYMS["current_assets"], 0.0, "BS->CurrAssets"
    )
    curr_liabs = find_synonym_value(
        balance_df, SYNONYMS["current_liabilities"], 0.0, "BS->CurrLiab"
    )
    total_assets = find_synonym_value(
        balance_df, SYNONYMS["total_assets"], 0.0, "BS->TotalAssets"
    )
    total_liabs = find_synonym_value(
        balance_df, SYNONYMS["total_liabilities"], 0.0, "BS->TotalLiab"
    )
    total_equity = find_synonym_value(
        balance_df, SYNONYMS["total_equity"], 0.0, "BS->TotalEquity"
    )

    metrics["Current Ratio"] = (curr_assets / curr_liabs) if curr_liabs else 0.0
    metrics["Debt-to-Equity"] = (total_liabs / total_equity) if total_equity else 0.0
    metrics["Equity Ratio %"] = (
        (total_equity / total_assets) * 100.0 if total_assets else 0.0
    )

    # -------------- CASH FLOW --------------
    op_cf = find_synonym_value(
        cash_df, SYNONYMS["cash_flow_operating"], fallback=0.0, debug_label="CF->OpCF"
    )
    capex_val = find_synonym_value(
        cash_df, SYNONYMS["capital_expenditures"], fallback=None, debug_label="CF->CapEx"
    )

    # If no explicit CapEx is found, fallback to negative portion of 'cash_flow_investing'
    if capex_val is not None and not pd.isna(capex_val):
        if capex_val < 0.0:
            capex_val = abs(capex_val)
    else:
        inv_cf = find_synonym_value(
            cash_df, SYNONYMS["cash_flow_investing"], fallback=0.0, debug_label="CF->InvestCF"
        )
        capex_val = min(inv_cf, 0.0) * -1.0

    if capex_val is None:
        capex_val = 0.0

    free_cf = op_cf - capex_val
    metrics["Cash from Operations"] = op_cf
    metrics["Free Cash Flow"] = free_cf

    # -------------- EBIT vs. EBITDA --------------

    # If there's a dedicated row for D&A, retrieve it and flip if negative
    dep_amort = find_synonym_value(
        income_df,
        SYNONYMS["depreciation_amortization"],
        fallback=0.0,
        debug_label="INC->DepAmort"
    )
    dep_amort = flip_sign_if_negative_expense(dep_amort, "depreciation_amortization")

    # Attempt to find any separate "Depreciation in Cost of Sales" to avoid double counting.
    cost_revenue, dep_amort = adjust_for_dep_in_cogs(
        income_df=income_df,
        cost_of_revenue=cost_revenue,
        dep_amort=dep_amort
    )

    metrics["CostOfRev"] = cost_revenue
    metrics["OpEx"] = op_exp

    # Recompute operating_income_approx if we changed cost_revenue
    operating_income_approx = gross_profit - op_exp
    metrics["EBIT (approx)"] = operating_income_approx
    metrics["EBITDA (approx)"] = operating_income_approx + dep_amort

    # -------------- ROE / ROA --------------
    metrics["ROE %"] = ((net_income / total_equity) * 100.0) if total_equity else 0.0
    metrics["ROA %"] = ((net_income / total_assets) * 100.0) if total_assets else 0.0

    # -------------- ALERTS --------------
    alerts = []
    if metrics["Net Margin %"] < ALERTS_CONFIG["NEGATIVE_MARGIN"]:
        alerts.append(
            f"Net margin below {ALERTS_CONFIG['NEGATIVE_MARGIN']}% (negative)"
        )
    if metrics["Debt-to-Equity"] > ALERTS_CONFIG["HIGH_LEVERAGE"]:
        alerts.append(
            f"Debt-to-Equity above {ALERTS_CONFIG['HIGH_LEVERAGE']} (high leverage)"
        )
    if 0.0 < metrics["ROE %"] < ALERTS_CONFIG["LOW_ROE"]:
        alerts.append(f"ROE < {ALERTS_CONFIG['LOW_ROE']}%")
    if 0.0 < metrics["ROA %"] < ALERTS_CONFIG["LOW_ROA"]:
        alerts.append(f"ROA < {ALERTS_CONFIG['LOW_ROA']}%")

    metrics["Alerts"] = alerts
    return metrics


def adjust_for_dep_in_cogs(
    income_df: pd.DataFrame,
    cost_of_revenue: float,
    dep_amort: float
) -> tuple[float, float]:
    """
    If there's a separate line or XBRL tag indicating Depreciation embedded in 
    Cost of Sales (Cost of Goods Sold), adjust cost_of_revenue and dep_amort 
    to avoid double-counting or missing that portion.

    :param income_df: Income-statement DataFrame
    :param cost_of_revenue: Already-extracted cost_of_revenue value
    :param dep_amort: Already-extracted total depreciation_amortization
    :return: (adjusted_cost_of_revenue, adjusted_dep_amort)
    """
    dep_in_cogs = find_synonym_value(
        income_df,
        SYNONYMS.get("depreciation_in_cost_of_sales", []),
        fallback=0.0,
        debug_label="INC->DepInCOGS"
    )
    if dep_in_cogs != 0.0:
        # If cost_of_revenue is an expense (often negative in raw data):
        #   - cost_of_revenue might already include that depreciation portion
        #   - If so, we remove it from cost_of_revenue and add it to total dep_amort
        logger.debug(
            "Depreciation in Cost of Sales found = %.2f. Adjusting cost_of_revenue & D&A.",
            dep_in_cogs
        )
        # Usually cost_of_revenue is positive (flipped if negative) at this point, 
        # but if your system keeps it negative, adjust logic accordingly.
        # For now, we simply reduce cost_of_revenue by 'dep_in_cogs', 
        # and increase dep_amort by the same amount.
        new_cost_of_revenue = cost_of_revenue - dep_in_cogs
        new_dep_amort = dep_amort + dep_in_cogs
        return new_cost_of_revenue, new_dep_amort
    return cost_of_revenue, dep_amort


def get_filing_info(filing_obj) -> dict:
    """
    Extract form, filing_date, accession_no from the Filing object, defaulting to 'Unknown' if missing.
    """
    info = {}
    if filing_obj:
        info["form_type"] = filing_obj.form if filing_obj.form else "Unknown"
        info["filed_date"] = (
            filing_obj.filing_date if filing_obj.filing_date else "Unknown"
        )
        info["company"] = filing_obj.company if filing_obj.company else "Unknown"
        info["accession_no"] = (
            filing_obj.accession_no if filing_obj.accession_no else "Unknown"
        )
    else:
        info["form_type"] = "Unknown"
        info["filed_date"] = "Unknown"
        info["company"] = "Unknown"
        info["accession_no"] = "Unknown"
    return info


def get_single_filing_snapshot(comp: Company, form_type: str) -> dict:
    """
    Retrieve the latest filing of 'form_type' for the company, parse metrics,
    and store the filing info. If no suitable filing or the financials 
    attribute is missing, return empty structures.
    """
    from .data_utils import ensure_dataframe, make_numeric_df  # local import

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
        logger.warning(
            "%s: The %s filing object has no 'financials'.", tkr, form_type
        )
        result["filing_info"] = filing_info
        return result

    fin = fo.financials
    bs_df = make_numeric_df(
        ensure_dataframe(fin.get_balance_sheet(), f"{tkr}-{form_type}-BS"),
        f"{tkr}-{form_type}-BS"
    )
    inc_df = make_numeric_df(
        ensure_dataframe(fin.get_income_statement(), f"{tkr}-{form_type}-INC"),
        f"{tkr}-{form_type}-INC"
    )
    cf_df = make_numeric_df(
        ensure_dataframe(fin.get_cash_flow_statement(), f"{tkr}-{form_type}-CF"),
        f"{tkr}-{form_type}-CF"
    )

    metrics = compute_ratios_and_metrics(bs_df, inc_df, cf_df)
    result["metrics"] = metrics
    result["filing_info"] = filing_info
    return result
