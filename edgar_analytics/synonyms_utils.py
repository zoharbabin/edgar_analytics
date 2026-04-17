"""
synonyms_utils.py

Helpers for matching synonyms (both GAAP and IFRS labels) in DataFrames.
Handles partial matches, largest absolute sums, flipping negative expenses, etc.
Includes a reusable function that computes capital expenditures
("capex") in a single-period DataFrame scenario, falling back intelligently to
investing activities minus intangible/business acquisition outflows if direct
capex is not found.
"""

from typing import Optional

import numpy as np
import pandas as pd
import unicodedata
from .logging_utils import get_logger
from .synonyms import SYNONYMS

logger = get_logger(__name__)

_EXPENSE_LABELS = frozenset((
    "cost_of_revenue", "operating_expenses", "rnd_expenses",
    "interest_expense", "depreciation_amortization",
))


class NormalizedIndex:
    """Caches normalized index representations for a DataFrame to avoid
    recomputing str.lower().strip() on every synonym lookup."""

    __slots__ = ("_lower", "_str")

    def __init__(self, df: pd.DataFrame) -> None:
        idx_str = df.index.astype(str)
        self._str = idx_str
        self._lower = idx_str.str.lower().str.strip()

    @property
    def lower(self) -> pd.Index:
        return self._lower

    @property
    def raw(self) -> pd.Index:
        return self._str


_norm_idx_cache: dict = {}


def get_normalized_index(df: pd.DataFrame) -> NormalizedIndex:
    """Return a NormalizedIndex, using a cached instance if the DataFrame's
    index object hasn't changed since the last call.  Keyed by id(df.index)."""
    key = id(df.index)
    cached = _norm_idx_cache.get(key)
    if cached is not None and cached[0] is df.index:
        return cached[1]
    ni = NormalizedIndex(df)
    _norm_idx_cache[key] = (df.index, ni)
    if len(_norm_idx_cache) > 64:
        oldest_key = next(iter(_norm_idx_cache))
        del _norm_idx_cache[oldest_key]
    return ni


def get_last_numeric_value(row_series, fallback: float = np.nan, debug_label: str = "(unknown)") -> float:
    """Retrieve the last non-NaN numeric value from a row Series (right-to-left).
    If a DataFrame is passed (duplicate index), uses the first row."""
    if isinstance(row_series, pd.DataFrame):
        logger.debug("get_last_numeric_value(%s): got DataFrame (duplicate index), using first row", debug_label)
        row_series = row_series.iloc[0]

    if not isinstance(row_series, pd.Series):
        logger.debug("get_last_numeric_value(%s): input not a Series -> fallback=%s", debug_label, fallback)
        return fallback

    for col in reversed(row_series.index):
        val = row_series[col]
        if pd.notna(val):
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return fallback


def normalize_text(s: str) -> str:
    """Normalize to lowercase, stripped, NFKC-normalized form."""
    return unicodedata.normalize('NFKC', s).lower().strip()


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

    ni = get_normalized_index(df)
    idx_lower = ni.lower
    df_index_str = ni.raw

    for syn in synonyms_list:
        syn_lower = normalize_text(syn)
        match_mask = (idx_lower == syn_lower)
        if match_mask.any():
            matched_label = df_index_str[match_mask][0]
            row_data = df.loc[matched_label]
            val = get_last_numeric_value(row_data, fallback, f"{debug_label} EXACT [{syn}]")
            logger.debug(
                "find_synonym_value(%s): EXACT row='%s', value=%s",
                debug_label, matched_label,
                "None" if (val is None or pd.isna(val)) else f"{val:.2f}"
            )
            return val

    partial_rows = []
    seen_labels = set()
    for syn in synonyms_list:
        syn_lower = normalize_text(syn)
        part_mask = idx_lower.str.contains(syn_lower, na=False, regex=False)
        for i, row_label in enumerate(df_index_str[part_mask]):
            if row_label in seen_labels:
                continue
            seen_labels.add(row_label)
            row_data = df.loc[row_label]
            row_val = get_last_numeric_value(row_data, fallback=None, debug_label=f"{debug_label} PARTIAL [{syn}]")
            if row_val is not None and not pd.isna(row_val):
                label_lower = idx_lower[df_index_str == row_label][0] if (df_index_str == row_label).any() else row_label.lower()
                coverage = len(syn_lower) / max(len(label_lower), 1)
                partial_rows.append((row_label, row_val, coverage))

    if partial_rows:
        partial_rows.sort(key=lambda x: (x[2], abs(x[1])), reverse=True)
        best_label, best_val, _ = partial_rows[0]
        logger.debug(
            "find_synonym_value(%s): PARTIAL row='%s', val=%.2f among %d matches",
            debug_label, best_label, best_val, len(partial_rows)
        )
        return best_val

    logger.debug("find_synonym_value(%s): no synonyms matched. fallback=%s", debug_label, fallback)
    return fallback


def flip_sign_if_negative_expense(value: float, label_key: str) -> float:
    """Flip sign if a known expense is negative (common in IFRS/GAAP filings)."""
    if label_key in _EXPENSE_LABELS and value < 0.0:
        logger.debug("flip_sign_if_negative_expense: flipping %.2f for %s", value, label_key)
        return abs(value)
    return value


def find_best_synonym_row(
    df: pd.DataFrame,
    syn_key: str,
    value_cols: Optional[list] = None,
    debug_label: str = "(unknown)"
) -> Optional[pd.Series]:
    """
    Locate the best-matching row in df for the given synonym key.
    Uses the standard two-pass algorithm: EXACT match first, then PARTIAL
    with largest absolute sum as tiebreaker.

    Args:
        df: DataFrame with financial line items as index.
        syn_key: Key into SYNONYMS dict (e.g. "revenue", "net_income").
        value_cols: Columns to consider for the abs-sum tiebreaker. If None,
                    uses all columns.
        debug_label: Context string for logging.

    Returns:
        The matched row as a Series, or None if no match found.
    """
    if df.empty:
        return None

    synonyms_list = SYNONYMS.get(syn_key, [])
    if not synonyms_list:
        return None

    ni = get_normalized_index(df)
    idx_lower = ni.lower
    cols = value_cols if value_cols is not None else df.columns.tolist()

    for syn in synonyms_list:
        syn_lower = normalize_text(syn)
        mask = (idx_lower == syn_lower)
        if mask.any():
            row_label = df.index[mask][0]
            logger.debug("find_best_synonym_row(%s): EXACT match '%s'", debug_label, row_label)
            result = df.loc[row_label]
            if isinstance(result, pd.DataFrame):
                result = result.iloc[0]
            return result

    candidate_rows = []
    seen_labels = set()
    for syn in synonyms_list:
        syn_lower = normalize_text(syn)
        part_mask = idx_lower.str.contains(syn_lower, na=False, regex=False)
        for row_label in df.index[part_mask]:
            if row_label in seen_labels:
                continue
            seen_labels.add(row_label)
            row_data = df.loc[row_label]
            if isinstance(row_data, pd.DataFrame):
                row_data = row_data.iloc[0]
            row_sum = row_data[cols].abs().sum(skipna=True)
            if row_sum > 0:
                label_lower = normalize_text(str(row_label))
                coverage = len(syn_lower) / max(len(label_lower), 1)
                candidate_rows.append((row_label, coverage, row_sum))

    if candidate_rows:
        candidate_rows.sort(key=lambda x: (x[1], x[2]), reverse=True)
        best_label = candidate_rows[0][0]
        logger.debug(
            "find_best_synonym_row(%s): PARTIAL match '%s' among %d candidates",
            debug_label, best_label, len(candidate_rows)
        )
        result = df.loc[best_label]
        if isinstance(result, pd.DataFrame):
            result = result.iloc[0]
        return result

    logger.debug("find_best_synonym_row(%s): no match for '%s'", debug_label, syn_key)
    return None


def compute_capex_single_period(cf_df: pd.DataFrame, debug_label: str = "CapEx") -> float:
    """
    Computes capital expenditures (capex) for a SINGLE-PERIOD cash flow DataFrame.
    1) First tries to locate "capital_expenditures" directly.
    2) If absent, uses "cash_flow_investing" outflow minus intangible/business acquisition items.
    3) Negative results are clamped to 0.0.
    """
    direct_capex = find_synonym_value(cf_df, SYNONYMS["capital_expenditures"], fallback=None, debug_label=f"{debug_label}-DirectCapex")
    if direct_capex is not None and not pd.isna(direct_capex):
        if direct_capex < 0:
            direct_capex = abs(direct_capex)
        logger.debug("%s: direct capex found=%.2f", debug_label, direct_capex)
        return direct_capex

    invest_cf = find_synonym_value(cf_df, SYNONYMS["cash_flow_investing"], fallback=0.0, debug_label=f"{debug_label}-InvestCF")
    if invest_cf > 0.0:
        logger.debug("%s: invests is positive=%.2f => returning 0.0 capex fallback", debug_label, invest_cf)
        return 0.0

    intangible_val = find_synonym_value(cf_df, SYNONYMS["purchase_of_intangibles"], fallback=0.0, debug_label=f"{debug_label}-Intangibles")
    acquisitions_val = find_synonym_value(cf_df, SYNONYMS["business_acquisitions_net"], fallback=0.0, debug_label=f"{debug_label}-Acquisitions")

    invest_outflow = abs(invest_cf)
    intangible_outflow = abs(intangible_val) if intangible_val < 0 else intangible_val
    acquisitions_outflow = abs(acquisitions_val) if acquisitions_val < 0 else acquisitions_val

    fallback_capex = invest_outflow - intangible_outflow - acquisitions_outflow
    if fallback_capex < 0.0:
        fallback_capex = invest_outflow

    logger.debug(
        "%s: fallback invests=%.2f, intangible=%.2f, acquisitions=%.2f => final capex=%.2f",
        debug_label, invest_outflow, intangible_outflow, acquisitions_outflow, fallback_capex
    )
    return max(fallback_capex, 0.0)


def compute_capex_for_column(cf_df: pd.DataFrame, period_col: str, debug_label: str = "CapEx(Col)") -> float:
    """Like compute_capex_single_period, but extracts a single column first."""
    if period_col not in cf_df.columns:
        logger.debug("%s: period_col=%s not in df => returning 0.0", debug_label, period_col)
        return 0.0

    sub_df = pd.DataFrame(cf_df[period_col]).rename(columns={period_col: "Value"})
    return compute_capex_single_period(sub_df, debug_label=f"{debug_label}-{period_col}")
