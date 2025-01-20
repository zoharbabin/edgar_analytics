"""
synonyms_utils.py

Helpers for matching synonyms (both GAAP and IFRS labels) in DataFrames.
Handles partial matches, largest absolute sums, flipping negative expenses, etc.
Includes a reusable function that computes capital expenditures
(“capex”) in a single-period DataFrame scenario, falling back intelligently to
investing activities minus intangible/business acquisition outflows if direct
capex is not found.
"""

import numpy as np
import pandas as pd
import unicodedata
from .logging_utils import get_logger
from .synonyms import SYNONYMS

logger = get_logger(__name__)


def get_last_numeric_value(row_series: pd.Series, fallback: float = np.nan, debug_label: str = "(unknown)") -> float:
    """
    Retrieve the last non-NaN numeric value from a row Series (right-to-left).
    If none is found, return fallback.
    """
    if not isinstance(row_series, pd.Series):
        logger.debug(
            "get_last_numeric_value(%s): input not a Series -> fallback=%s", debug_label, fallback
        )
        return fallback

    for col in reversed(row_series.index):
        val = row_series[col]
        if pd.notna(val):
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return fallback


def find_synonym_value(
    df: pd.DataFrame,
    synonyms_list: list,
    fallback: float = 0.0,
    debug_label: str = "(unknown)"
) -> float:
    """
    Search a DataFrame's index for synonyms, returning the last numeric found in that row.
    1) EXACT match
    2) PARTIAL match => pick row with largest absolute sum.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        logger.debug("find_synonym_value(%s): DF invalid/empty. fallback=%s", debug_label, fallback)
        return fallback

    idx_lower = df.index.astype(str).str.lower().str.strip()
    df_index_str = df.index.astype(str)

    # 1) EXACT
    for syn in synonyms_list:
        syn_lower = normalize_text(syn)
        match_mask = (idx_lower == syn_lower)
        if match_mask.any():
            matched_label = df_index_str[match_mask][0]
            row_data = df.loc[matched_label]
            val = get_last_numeric_value(row_data, fallback, f"{debug_label} EXACT [{syn}]")
            # ---------------- NEW SAFE LOGGING ----------------
            if val is None or pd.isna(val):
                logger.debug(
                    "find_synonym_value(%s): EXACT row='%s', value=None", 
                    debug_label, 
                    matched_label
                )
            else:
                # valid numeric => safely do "%.2f"
                logger.debug(
                    "find_synonym_value(%s): EXACT row='%s', value=%.2f",
                    debug_label,
                    matched_label,
                    val
                )
            return val

    # 2) PARTIAL
    partial_rows = []
    for syn in synonyms_list:
        syn_lower = normalize_text(syn)
        part_mask = idx_lower.str.contains(syn_lower, na=False, regex=False)
        matched_indexes = df_index_str[part_mask].tolist()
        for row_label in matched_indexes:
            row_data = df.loc[row_label]
            row_val = get_last_numeric_value(row_data, fallback=None, debug_label=f"{debug_label} PARTIAL [{syn}]")
            if row_val is not None and not pd.isna(row_val):
                partial_rows.append((row_label, row_val))

    if partial_rows:
        partial_rows.sort(key=lambda x: abs(x[1]), reverse=True)
        best_label, best_val = partial_rows[0]
        logger.debug(
            "find_synonym_value(%s): PARTIAL row='%s', abs=%.2f among %d matches",
            debug_label, best_label, best_val, len(partial_rows)
        )
        return best_val

    logger.debug("find_synonym_value(%s): no synonyms matched. fallback=%s", debug_label, fallback)
    return fallback


def normalize_text(s: str) -> str:
    """
    Converts text to lower case, strips whitespace, and normalizes Unicode forms
    to handle accented or unusual characters consistently.
    """
    s = unicodedata.normalize('NFKC', s)
    return s.lower().strip()


def flip_sign_if_negative_expense(value: float, label_key: str) -> float:
    """
    Flip sign if a known expense is negative.
    IFRS or GAAP calls often store these lines as negative amounts.
    """
    if label_key in ("cost_of_revenue", "operating_expenses", "rnd_expenses", "interest_expense", "depreciation_amortization"):
        if value < 0.0:
            logger.debug("flip_sign_if_negative_expense: flipping from %.2f to %.2f for %s", value, abs(value), label_key)
            return abs(value)
    return value


def compute_capex_single_period(cf_df: pd.DataFrame, debug_label: str = "CapEx") -> float:
    """
    Computes capital expenditures (capex) for a SINGLE-PERIOD cash flow DataFrame,
    which typically has one numeric column labeled "Value".
    1) First tries to locate "capital_expenditures" directly.
    2) If absent, uses "cash_flow_investing" outflow minus intangible/business acquisition items (if found).
    3) Negative results are clamped to 0.0, as a safety measure.

    :param cf_df:      Cash flow DataFrame with a single column named e.g. "Value".
    :param debug_label: Used for logging context.
    :return: A float representing the best estimate of "capex."
    """
    # Direct
    direct_capex = find_synonym_value(cf_df, SYNONYMS["capital_expenditures"], fallback=None, debug_label=f"{debug_label}-DirectCapex")
    if direct_capex is not None and not np.isnan(direct_capex):
        if direct_capex < 0:
            direct_capex = abs(direct_capex)
        logger.debug("%s: direct capex found=%.2f", debug_label, direct_capex)
        return direct_capex

    # Fallback path: investing outflow minus intangible & acquisitions
    invest_cf = find_synonym_value(cf_df, SYNONYMS["cash_flow_investing"], fallback=0.0, debug_label=f"{debug_label}-InvestCF")
    if invest_cf > 0.0:
        # If it's positive, there's no net outflow
        logger.debug("%s: invests is positive=%.2f => returning 0.0 capex fallback", debug_label, invest_cf)
        return 0.0

    # intangible purchases
    intangible_val = find_synonym_value(cf_df, SYNONYMS["purchase_of_intangibles"], fallback=0.0, debug_label=f"{debug_label}-Intangibles")
    # acquisitions net
    acquisitions_val = find_synonym_value(cf_df, SYNONYMS["business_acquisitions_net"], fallback=0.0, debug_label=f"{debug_label}-Acquisitions")

    invest_outflow = abs(invest_cf)   # e.g., -500 => 500 outflow
    intangible_outflow = abs(intangible_val) if intangible_val < 0 else intangible_val
    acquisitions_outflow = abs(acquisitions_val) if acquisitions_val < 0 else acquisitions_val

    # Subtract intangible + M&A outflow from total invests (so we approximate "pure" capex)
    fallback_capex = invest_outflow - intangible_outflow - acquisitions_outflow
    if fallback_capex < 0.0:
        # If we overshoot, revert to entire invests as rough fallback
        fallback_capex = invest_outflow

    logger.debug(
        "%s: fallback invests=%.2f, intangible=%.2f, acquisitions=%.2f => final capex=%.2f",
        debug_label, invest_outflow, intangible_outflow, acquisitions_outflow, fallback_capex
    )
    return max(fallback_capex, 0.0)


def compute_capex_for_column(cf_df: pd.DataFrame, period_col: str, debug_label: str = "CapEx(Col)") -> float:
    """
    Like compute_capex_single_period, but for multi-period CF DataFrame columns.
    Extracts a single column from cf_df, then applies compute_capex_single_period logic.

    :param cf_df:       A multi-column DataFrame (index= line items, columns= periods).
    :param period_col:  The column name to be analyzed.
    :param debug_label: Logging context.
    :return: A float best estimate for capex in that specific column's data.
    """
    if period_col not in cf_df.columns:
        logger.debug("%s: period_col=%s not in df => returning 0.0", debug_label, period_col)
        return 0.0

    # Build a sub-DF with just the single column
    sub_df = pd.DataFrame(cf_df[period_col]).rename(columns={period_col: "Value"})
    return compute_capex_single_period(sub_df, debug_label=f"{debug_label}-{period_col}")
