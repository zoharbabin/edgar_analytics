# edgar_analytics/synonyms_utils.py

import numpy as np
import pandas as pd

from .logging_utils import get_logger

logger = get_logger(__name__)


def get_last_numeric_value(
    row_series: pd.Series,
    fallback: float = np.nan,
    debug_label: str = "(unknown)"
) -> float:
    """
    Retrieve the *last* non-NaN numeric value from row_series (right-to-left).
    If none found, return fallback.

    :param row_series: A row (pd.Series) from a DataFrame
    :param fallback: Value to return if no valid floats are found
    :param debug_label: Used for logging context
    :return: The last numeric float found, or fallback
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
    Search a DataFrame's index for any of the given synonyms:
      1) EXACT match
      2) PARTIAL match (largest absolute numeric sum if multiple partials)
    Returns the last non-NaN numeric value from the matched row or fallback.

    :param df: The DataFrame to search
    :param synonyms_list: A list of possible synonyms/labels
    :param fallback: Value if no row is found
    :param debug_label: For logging context
    :return: Found numeric value or fallback
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        logger.debug(
            "find_synonym_value(%s): DF invalid/empty. fallback=%s",
            debug_label, fallback
        )
        return fallback

    idx_series = pd.Series(df.index, dtype=str).str.lower()
    df_index_str = pd.Series(df.index, dtype=str)

    # 1) EXACT match
    for syn in synonyms_list:
        syn_lower = syn.lower()
        match_mask = (idx_series == syn_lower)
        if match_mask.any():
            matched_label = df_index_str[match_mask].iloc[0]
            row_data = df.loc[matched_label]
            val = get_last_numeric_value(
                row_data,
                fallback=fallback,
                debug_label=f"{debug_label} EXACT [{syn}]"
            )
            logger.debug(
                "find_synonym_value(%s): EXACT match row='%s', value=%s",
                debug_label, matched_label, val
            )
            return val

    # 2) PARTIAL match
    partial_rows = []
    for syn in synonyms_list:
        syn_lower = syn.lower()
        partial_mask = idx_series.str.contains(syn_lower, na=False, regex=False)
        matched_indexes = df_index_str[partial_mask].tolist()
        for row_label in matched_indexes:
            row_data = df.loc[row_label]
            row_val = get_last_numeric_value(
                row_data, fallback=None, debug_label=f"{debug_label} PARTIAL [{syn}]"
            )
            if row_val is not None and not pd.isna(row_val):
                partial_rows.append((row_label, row_val))

    if partial_rows:
        partial_rows.sort(key=lambda x: abs(x[1]), reverse=True)
        best_label, best_val = partial_rows[0]
        logger.debug(
            "find_synonym_value(%s): PARTIAL match row='%s', abs=%.2f (among %d matches)",
            debug_label, best_label, best_val, len(partial_rows)
        )
        return best_val

    logger.debug(
        "find_synonym_value(%s): no synonyms matched. returning fallback=%s",
        debug_label, fallback
    )
    return fallback


def flip_sign_if_negative_expense(value: float, label_key: str) -> float:
    """
    Flip sign if a known expense is negative (common in XBRL).
    E.g., if 'cost_of_revenue' is -500, make it +500.

    :param value: The numeric value to examine
    :param label_key: The conceptual label, e.g. "cost_of_revenue"
    :return: Possibly flipped value
    """
    if label_key in ("cost_of_revenue", "operating_expenses", "rnd_expenses"):
        if value < 0.0:
            logger.debug(
                "flip_sign_if_negative_expense: flipping from %.2f to %.2f for key=%s",
                value, abs(value), label_key
            )
            return abs(value)
    return value
