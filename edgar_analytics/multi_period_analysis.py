# edgar_analytics/multi_period_analysis.py

import numpy as np
import pandas as pd

from edgar import Company, MultiFinancials
from .logging_utils import get_logger
from .synonyms import SYNONYMS
from .data_utils import (
    parse_period_label,
    ensure_dataframe,
    make_numeric_df,
)
from .config import ALERTS_CONFIG

logger = get_logger(__name__)


def retrieve_multi_year_data(ticker: str, n_years=3, n_quarters=10) -> dict:
    """
    Retrieve last n_years 10-K and last n_quarters 10-Q statements for
    building multi-year analyses. Return dict with annual_data, quarterly_data,
    yoy, qoq, etc.
    """
    logger.info(
        "Retrieving multi-year data for %s: last %d 10-K, last %d 10-Q",
        ticker, n_years, n_quarters
    )
    comp = Company(ticker)

    annual_inc_df = pd.DataFrame()
    quarterly_inc_df = pd.DataFrame()

    # 10-K
    try:
        filings_10k = comp.get_filings(form="10-K", is_xbrl=True).head(n_years)
        multi_10k = MultiFinancials(filings_10k)
        inc_10k = multi_10k.get_income_statement()
        if inc_10k is not None:
            annual_inc_df = ensure_dataframe(inc_10k, debug_label=f"{ticker}-multi10K-INC")
            annual_inc_df = make_numeric_df(annual_inc_df, debug_label=f"{ticker}-multi10K-INC")
        else:
            logger.warning("%s: No multi 10-K income statements found.", ticker)
    except Exception as e:
        logger.error("Error retrieving multi 10-K for %s: %s", ticker, e, exc_info=True)

    # 10-Q
    try:
        filings_10q = comp.get_filings(form="10-Q", is_xbrl=True).head(n_quarters)
        multi_10q = MultiFinancials(filings_10q)
        inc_10q = multi_10q.get_income_statement()
        if inc_10q is not None:
            quarterly_inc_df = ensure_dataframe(inc_10q, f"{ticker}-multi10Q-INC")
            quarterly_inc_df = make_numeric_df(quarterly_inc_df, f"{ticker}-multi10Q-INC")
        else:
            logger.warning("%s: No multi 10-Q income statements found.", ticker)
    except Exception as e:
        logger.error("Error retrieving multi 10-Q for %s: %s", ticker, e, exc_info=True)

    annual_data = extract_period_values(annual_inc_df, f"{ticker}-ANN")
    quarterly_data = extract_period_values(quarterly_inc_df, f"{ticker}-QTR")

    yoy_rev = compute_growth_series(annual_data.get("Revenue", {}))
    yoy_net = compute_growth_series(annual_data.get("Net Income", {}))
    qoq_rev = compute_growth_series(quarterly_data.get("Revenue", {}))
    qoq_net = compute_growth_series(quarterly_data.get("Net Income", {}))

    cagr_rev = compute_cagr(annual_data.get("Revenue", {}))

    return {
        "annual_inc_df": annual_inc_df,
        "quarterly_inc_df": quarterly_inc_df,
        "annual_data": annual_data,
        "quarterly_data": quarterly_data,
        "yoy_revenue_growth": yoy_rev,
        "qoq_revenue_growth": qoq_rev,
        "yoy_net_income_growth": yoy_net,
        "qoq_net_income_growth": qoq_net,
        "cagr_revenue": cagr_rev,
    }


def extract_period_values(df: pd.DataFrame, debug_label="(unknown)") -> dict:
    """
    Locates 'Revenue' and 'Net Income' rows in a multi-column statement,
    returning {'Revenue': {...}, 'Net Income': {...}} by period.
    """
    if df.empty:
        logger.debug("extract_period_values(%s): DF empty.", debug_label)
        return {"Revenue": {}, "Net Income": {}}

    df.columns = df.columns.map(str)
    sorted_cols = sorted(df.columns, key=parse_period_label)

    results = {"Revenue": {}, "Net Income": {}}
    rev_val_row = find_best_row_for_synonym(df, "revenue", sorted_cols, f"{debug_label}->Revenue")
    net_val_row = find_best_row_for_synonym(df, "net_income", sorted_cols, f"{debug_label}->NetIncome")

    if rev_val_row is not None:
        for c in sorted_cols:
            val = rev_val_row.get(c, np.nan)
            if pd.notna(val):
                results["Revenue"][c] = float(val)

    if net_val_row is not None:
        for c in sorted_cols:
            val = net_val_row.get(c, np.nan)
            if pd.notna(val):
                results["Net Income"][c] = float(val)

    return results


def find_best_row_for_synonym(df: pd.DataFrame, syn_key: str, columns_order: list, debug_label="(unknown)") -> pd.Series:
    """
    Finds the best row in df for syn_key by scanning synonyms,
    picking the row with largest absolute sum if partial matches exist.
    """
    if df.empty:
        return None
    idx_lower = df.index.str.lower()
    synonyms_list = SYNONYMS.get(syn_key, [])
    candidate_rows = []

    # EXACT
    for syn in synonyms_list:
        mask = (idx_lower == syn.lower())
        if mask.any():
            row_label = df.index[mask][0]
            logger.debug("find_best_row_for_synonym(%s): EXACT match row='%s'", debug_label, row_label)
            return df.loc[row_label]

    # PARTIAL
    for syn in synonyms_list:
        part_mask = idx_lower.str.contains(syn.lower(), na=False, regex=False)
        matched_indexes = df.index[part_mask].tolist()
        for row_label in matched_indexes:
            row_data = df.loc[row_label, columns_order]
            row_sum = row_data.abs().sum(skipna=True)
            if row_sum != 0:
                candidate_rows.append((row_label, row_sum))

    if candidate_rows:
        candidate_rows.sort(key=lambda x: x[1], reverse=True)
        best_label = candidate_rows[0][0]
        logger.debug(
            "find_best_row_for_synonym(%s): PARTIAL best row='%s' sum=%s",
            debug_label, best_label, candidate_rows[0][1]
        )
        return df.loc[best_label]

    logger.debug(
        "find_best_row_for_synonym(%s): no match for '%s'.",
        debug_label, syn_key
    )
    return None


def compute_growth_series(values_dict: dict) -> dict:
    """
    Computes % growth from the previous period to the current, storing in a new dict.
    Returns empty if <2 data points.
    """
    if not values_dict or len(values_dict) < 2:
        return {}
    sorted_periods = sorted(values_dict.keys(), key=parse_period_label)
    growth_map = {}
    prev_val = None
    for p in sorted_periods:
        curr_val = values_dict[p]
        if prev_val is not None and prev_val != 0:
            growth_map[p] = ((curr_val - prev_val) / abs(prev_val)) * 100.0
        prev_val = curr_val
    return growth_map


def compute_cagr(values_dict: dict) -> float:
    """
    Computes compound annual growth rate (CAGR) from earliest to latest period
    in values_dict. Minimum 2 data points required.
    """
    if not values_dict or len(values_dict) < 2:
        return 0.0
    sorted_periods = sorted(values_dict.keys(), key=parse_period_label)
    first_val = values_dict[sorted_periods[0]]
    last_val = values_dict[sorted_periods[-1]]
    n_years = max(
        1,
        parse_period_label(sorted_periods[-1]).year
        - parse_period_label(sorted_periods[0]).year
    )
    if first_val <= 0:
        return 0.0
    cagr = (last_val / first_val) ** (1.0 / n_years) - 1.0
    return cagr * 100.0


def analyze_quarterly_balance_sheets(comp: Company, n_quarters=10) -> dict:
    """
    Retrieve up to n_quarters of 10-Q, extract inventory, receivables, free_cf,
    to detect spikes or negative FCF streaks.
    """
    results = {"inventory": {}, "receivables": {}, "free_cf": {}}
    tkr = comp.tickers[0] if comp.tickers else "UNKNOWN"
    try:
        filings_10q = comp.get_filings(form="10-Q", is_xbrl=True).head(n_quarters)
        multi_10q = MultiFinancials(filings_10q)
        bs_10q = multi_10q.get_balance_sheet()
        cf_10q = multi_10q.get_cash_flow_statement()

        bs_df = make_numeric_df(
            ensure_dataframe(bs_10q, f"{tkr}-multi10Q-BS"), f"{tkr}-multi10Q-BS"
        )
        cf_df = make_numeric_df(
            ensure_dataframe(cf_10q, f"{tkr}-multi10Q-CF"), f"{tkr}-multi10Q-CF"
        )

        if not bs_df.empty:
            bs_df.columns = bs_df.columns.map(str)
            sorted_cols = sorted(bs_df.columns, key=parse_period_label)

            inv_series = find_multi_col_values(bs_df, "inventory", sorted_cols, f"{tkr}->Inventory")
            results["inventory"] = inv_series

            rec_series = find_multi_col_values(bs_df, "accounts_receivable", sorted_cols, f"{tkr}->Receivables")
            results["receivables"] = rec_series

        if not cf_df.empty:
            cf_df.columns = cf_df.columns.map(str)
            sorted_cols_cf = sorted(cf_df.columns, key=parse_period_label)

            op_values = find_multi_col_values(cf_df, "cash_flow_operating", sorted_cols_cf, f"{tkr}->OpCF")
            direct_capex_vals = find_multi_col_values(cf_df, "capital_expenditures", sorted_cols_cf, f"{tkr}->CapEx")

            fcf_map = {}
            if direct_capex_vals:
                for c in sorted_cols_cf:
                    op_cf_val = op_values.get(c, 0.0)
                    capex_val = direct_capex_vals.get(c, 0.0)
                    if capex_val < 0:
                        capex_val = abs(capex_val)
                    fcf_map[c] = op_cf_val - capex_val
            else:
                inv_values = find_multi_col_values(cf_df, "cash_flow_investing", sorted_cols_cf, f"{tkr}->InvCF")
                for c in sorted_cols_cf:
                    op_cf_val = op_values.get(c, 0.0)
                    inv_cf_val = inv_values.get(c, 0.0)
                    capex_guess = min(inv_cf_val, 0.0) * -1
                    fcf_map[c] = op_cf_val - capex_guess

            results["free_cf"] = fcf_map

    except Exception as e:
        logger.error("analyze_quarterly_balance_sheets(%s) error: %s", tkr, e, exc_info=True)
    return results


def find_multi_col_values(
    df: pd.DataFrame, syn_key: str, sorted_cols: list, debug_label="(unknown)"
) -> dict:
    """
    Find row matching syn_key by EXACT or PARTIAL synonyms, then read numeric values
    from sorted_cols into a dict {col_name: value}.
    """
    if df.empty:
        return {}
    idx_lower = df.index.str.lower()
    synonyms_list = SYNONYMS.get(syn_key, [])
    candidate_rows = []

    # EXACT
    for syn in synonyms_list:
        mask = (idx_lower == syn.lower())
        if mask.any():
            row_label = df.index[mask][0]
            logger.debug(
                "find_multi_col_values(%s): EXACT match row='%s' for syn='%s'",
                debug_label, row_label, syn
            )
            return df.loc[row_label, sorted_cols].dropna().to_dict()

    # PARTIAL
    for syn in synonyms_list:
        syn_lower = syn.lower()
        part_mask = idx_lower.str.contains(syn_lower, na=False, regex=False)
        matched_indexes = df.index[part_mask].tolist()
        for row_label in matched_indexes:
            row_data = df.loc[row_label, sorted_cols]
            row_sum = row_data.abs().sum(skipna=True)
            if row_sum > 0:
                candidate_rows.append((row_label, row_sum))

    if candidate_rows:
        candidate_rows.sort(key=lambda x: x[1], reverse=True)
        best_label = candidate_rows[0][0]
        logger.debug(
            "find_multi_col_values(%s): PARTIAL best row='%s' sum=%s",
            debug_label, best_label, candidate_rows[0][1]
        )
        return df.loc[best_label, sorted_cols].dropna().to_dict()

    logger.debug("find_multi_col_values(%s): no match for '%s'", debug_label, syn_key)
    return {}


def check_additional_alerts_quarterly(data_map: dict) -> list:
    """
    Evaluate quarterly-based alerts like negative FCF streak and spikes in inventory/receivables.
    """
    alerts = []
    fcf_dict = data_map.get("free_cf", {})
    if len(fcf_dict) > 1:
        consecutive_neg = 0
        for p in sorted(fcf_dict.keys(), key=parse_period_label):
            if fcf_dict[p] < 0:
                consecutive_neg += 1
            else:
                consecutive_neg = 0
            if consecutive_neg >= ALERTS_CONFIG["SUSTAINED_NEG_FCF_QUARTERS"]:
                alerts.append(
                    f"{consecutive_neg} consecutive quarters of negative FCF (through {p})."
                )
                break

    inv_dict = data_map.get("inventory", {})
    alerts += check_spike(inv_dict, ALERTS_CONFIG["INVENTORY_SPIKE_THRESHOLD"], "Inventory")

    rec_dict = data_map.get("receivables", {})
    alerts += check_spike(rec_dict, ALERTS_CONFIG["RECEIVABLE_SPIKE_THRESHOLD"], "Receivables")

    return alerts


def check_spike(values_dict: dict, threshold: float, label: str) -> list:
    """
    If growth from previous to current > threshold%, add an alert.
    """
    al = []
    if len(values_dict) < 2:
        return al

    sorted_p = sorted(values_dict.keys(), key=parse_period_label)
    prev_val = None
    for p in sorted_p:
        curr_val = values_dict[p]
        if prev_val is not None and prev_val != 0:
            growth_pct = ((curr_val - prev_val) / abs(prev_val)) * 100.0
            if growth_pct > threshold:
                al.append(f"{label} spiked +{growth_pct:.2f}% from previous quarter to {p}.")
        prev_val = curr_val
    return al
