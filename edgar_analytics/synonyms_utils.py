# edgar_analytics/synonyms_utils.py

import numpy as np
import pandas as pd
from .synonyms import SYNONYMS
from .data_utils import parse_period_label
from .logging_utils import get_logger

logger = get_logger(__name__)


def get_last_numeric_value(row_series: pd.Series, fallback=np.nan, debug_label="(unknown)") -> float:
    """
    Retrieve the *last* non-NaN numeric value from row_series (right to left).
    """
    if not isinstance(row_series, pd.Series):
        logger.debug(
            "get_last_numeric_value(%s): input not a Series. fallback=%s",
            debug_label, fallback
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
    synonyms_list: list[str],
    fallback: float = 0.0,
    debug_label: str = "(unknown)"
) -> float:
    """
    Search a DataFrame's index for synonyms, first EXACT then PARTIAL match,
    then return the last non-NaN numeric value from that row. If no match
    is found, returns fallback.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        logger.debug(
            "find_synonym_value(%s): DF invalid/empty. fallback=%s",
            debug_label, fallback
        )
        return fallback

    idx_series = pd.Series(df.index, dtype=str).str.lower()
    df_index_str = pd.Series(df.index, dtype=str)

    # EXACT
    for syn in synonyms_list:
        syn_lower = syn.lower()
        match_mask = (idx_series == syn_lower)
        if match_mask.any():
            matched_label = df_index_str[match_mask].iloc[0]
            row_data = df.loc[matched_label]
            val = get_last_numeric_value(
                row_data, fallback=fallback,
                debug_label=f"{debug_label} EXACT [{syn}]"
            )
            logger.debug(
                "find_synonym_value(%s): EXACT match -> row='%s', value=%.2f",
                debug_label, matched_label, val
            )
            return val

    # PARTIAL
    partial_rows = []
    for syn in synonyms_list:
        syn_lower = syn.lower()
        partial_mask = idx_series.str.contains(syn_lower, na=False, regex=False)
        matched_indexes = df_index_str[partial_mask].tolist()
        for row_label in matched_indexes:
            row_data = df.loc[row_label]
            row_val = get_last_numeric_value(
                row_data, fallback=None,
                debug_label=f"{debug_label} PARTIAL [{syn}]"
            )
            if row_val is not None and not pd.isna(row_val):
                partial_rows.append((row_label, row_val))

    if partial_rows:
        # Sort by largest absolute numeric value
        partial_rows.sort(key=lambda x: abs(x[1]), reverse=True)
        best_label, best_val = partial_rows[0]
        logger.debug(
            "find_synonym_value(%s): PARTIAL match -> row='%s', "
            "largest abs val=%.2f among %d partial matches",
            debug_label, best_label, best_val, len(partial_rows)
        )
        return best_val

    logger.debug(
        "find_synonym_value(%s): no synonyms found. fallback=%s",
        debug_label, fallback
    )
    return fallback


def flip_sign_if_negative_expense(value: float, label_key: str) -> float:
    """
    If a known expense is negative, flip it positive (common in some XBRL data).
    """
    if label_key in ("cost_of_revenue", "operating_expenses", "rnd_expenses"):
        if value < 0:
            logger.debug(
                "flip_sign_if_negative_expense: flipping from %.2f to %.2f for %s",
                value, abs(value), label_key
            )
            return abs(value)
    return value
