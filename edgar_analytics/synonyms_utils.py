"""
synonyms_utils.py

Helpers for matching synonyms (both GAAP and IFRS labels) in DataFrames.
Handles partial matches, largest absolute sums, flipping negative expenses, etc.
"""

import numpy as np
import pandas as pd
import unicodedata
from .logging_utils import get_logger

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
            logger.debug("find_synonym_value(%s): EXACT row='%s', value=%.2f", debug_label, matched_label, val)
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
    # Lower, strip, then decompose Unicode forms to handle weird spaces/accents
    s = unicodedata.normalize('NFKC', s)
    return s.lower().strip()


def flip_sign_if_negative_expense(value: float, label_key: str) -> float:
    """
    Flip sign if a known expense is negative. e.g., 'cost_of_revenue' or 'operating_expenses'.
    IFRS or GAAP calls often store these lines as negative amounts.
    """
    if label_key in ("cost_of_revenue", "operating_expenses", "rnd_expenses"):
        if value < 0.0:
            logger.debug("flip_sign_if_negative_expense: flipping from %.2f to %.2f for %s", value, abs(value), label_key)
            return abs(value)
    return value
