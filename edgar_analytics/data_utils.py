"""
data_utils.py

DataFrame parsing, numeric coercion, date label parsing, and custom float formatting.
Handles both IFRS and GAAP without distinction in code, as all synonyms unify them.
"""

import re
import datetime
import pandas as pd
import numpy as np

from .logging_utils import get_logger

logger = get_logger(__name__)

_YEAR_RE = re.compile(r"(20[0-9]{2}|19[0-9]{2})")
_QUARTER_RE = re.compile(r"Q([1-4])[\s\-_]*((?:20|19)[0-9]{2})", re.IGNORECASE)

_QUARTER_MONTH = {1: 3, 2: 6, 3: 9, 4: 12}
_QUARTER_DAY = {3: 31, 6: 30, 9: 30, 12: 31}


def parse_period_label(col_name: str) -> datetime.date:
    """
    Attempt to parse '2021-12-31', 'FY2023', 'Q1-2023', '2021' into a date.
    Return 1900-01-01 if parse fails. Used for sorting columns by time.
    """
    patterns = ["%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%Y"]
    if col_name.upper().startswith("FY"):
        try:
            yr = int(col_name[2:])
            return datetime.date(yr, 12, 31)
        except ValueError:
            pass

    qtr_match = _QUARTER_RE.match(col_name)
    if qtr_match:
        q_num = int(qtr_match.group(1))
        yr = int(qtr_match.group(2))
        month = _QUARTER_MONTH[q_num]
        return datetime.date(yr, month, _QUARTER_DAY[month])

    for pat in patterns:
        try:
            if pat == "%Y":
                dt = datetime.datetime.strptime(col_name, "%Y")
                return dt.replace(month=12, day=31).date()
            dt = datetime.datetime.strptime(col_name, pat)
            return dt.date()
        except ValueError:
            continue

    year_match = _YEAR_RE.search(col_name)
    if year_match:
        yr = int(year_match.group(1))
        return datetime.date(yr, 12, 31)

    logger.debug("parse_period_label: Could not parse '%s' -> fallback=1900-01-01", col_name)
    return datetime.date(1900, 1, 1)


def custom_float_format(x):
    """Formats numeric x to a short string with K, M, B, T or .2f if <1000."""
    if isinstance(x, float) and (np.isnan(x) or np.isinf(x)):
        return "N/A"
    if isinstance(x, (int, float)):
        abs_x = abs(x)
        if abs_x >= 1e12:
            return f"{x / 1e12:.2f}T"
        if abs_x >= 1e9:
            return f"{x / 1e9:.2f}B"
        if abs_x >= 1e6:
            return f"{x / 1e6:.2f}M"
        if abs_x >= 1e3:
            return f"{x / 1e3:.2f}K"
        return f"{x:.2f}"
    return x


_STATEMENT_META_COLS = frozenset({
    "concept", "label", "standard_concept", "level", "abstract",
    "dimension", "is_breakdown", "dimension_axis", "dimension_member",
    "dimension_member_label", "dimension_label", "balance", "weight",
    "preferred_sign", "parent_concept", "parent_abstract_concept",
})

_PERIOD_SUFFIX_RE = re.compile(r"\s+\((Q[1-4]|YTD|FY)\)$")
_YTD_SUFFIX_RE = re.compile(r"\s+\(YTD\)$")
_QTR_SUFFIX_RE = re.compile(r"\s+\(Q[1-4]\)$")
_FY_SUFFIX_RE = re.compile(r"\s+\(FY\)$")


def _select_value_columns(value_cols: list[str]) -> tuple[list[str], dict[str, str]]:
    """Choose single-quarter columns over YTD when both exist.

    Returns (selected_cols, rename_map) where *rename_map* maps original
    column names to their suffix-stripped versions.
    """
    qtr_cols = [c for c in value_cols if _QTR_SUFFIX_RE.search(c)]
    ytd_cols = [c for c in value_cols if _YTD_SUFFIX_RE.search(c)]
    fy_cols = [c for c in value_cols if _FY_SUFFIX_RE.search(c)]
    plain_cols = [c for c in value_cols if not _PERIOD_SUFFIX_RE.search(c)]

    if qtr_cols:
        selected = qtr_cols + fy_cols + plain_cols
    elif ytd_cols:
        selected = ytd_cols + fy_cols + plain_cols
    else:
        selected = value_cols

    rename_map = {c: _PERIOD_SUFFIX_RE.sub("", c) for c in selected}
    return selected, rename_map


def _convert_statement_df(df: pd.DataFrame, debug_label: str) -> pd.DataFrame:
    """Convert an edgartools Statement-style DataFrame to label-indexed format.

    Statement.to_dataframe() returns rows with integer index, a 'label'
    column, metadata columns, and date-keyed value columns.  This function
    drops abstract/dimension rows, sets 'label' as the index, and keeps
    only the value columns so that synonym matching works.

    When the filing includes both single-quarter ``(Q*)`` and year-to-date
    ``(YTD)`` columns, only the single-quarter columns are kept so that
    downstream TTM computation sums four actual quarters, not cumulative
    YTD figures.

    XBRL concept tags from the 'concept' column are added as duplicate
    rows so that synonym lists containing tags like
    ``us-gaap_PaymentsToAcquirePropertyPlantAndEquipment`` still match.
    """
    if "label" not in df.columns:
        return df

    value_cols = [c for c in df.columns if c not in _STATEMENT_META_COLS]
    if not value_cols:
        return df

    selected_cols, rename_map = _select_value_columns(value_cols)

    filtered = df
    if "abstract" in df.columns:
        filtered = filtered[~filtered["abstract"].astype(bool)]
    if "dimension" in df.columns:
        non_dim = filtered[~filtered["dimension"].astype(bool)]
        if not non_dim.empty:
            filtered = non_dim

    label_df = filtered.set_index("label")[selected_cols]
    label_df = label_df.rename(columns=rename_map)

    if "concept" in filtered.columns:
        concept_df = filtered.set_index("concept")[selected_cols]
        concept_df = concept_df.rename(columns=rename_map)
        concept_df = concept_df[~concept_df.index.isin(label_df.index)]
        result = pd.concat([label_df, concept_df])
    else:
        result = label_df

    logger.debug(
        "ensure_dataframe(%s): converted Statement DF -> label-indexed shape=%s, cols=%s",
        debug_label, result.shape, list(result.columns),
    )
    return result


def decumulate_quarterly(df: pd.DataFrame, debug_label: str = "(unknown)") -> pd.DataFrame:
    """Convert YTD cumulative quarterly values to single-quarter values.

    SEC XBRL 10-Q income statements and cash flow statements report
    year-to-date cumulative figures.  ``MultiFinancials`` stitches these
    into a DataFrame with plain date columns but the values are still
    cumulative within each fiscal year.

    Detection heuristic: within a fiscal year, if values increase
    monotonically (i.e. each column >= the previous), they are cumulative.
    We then compute Q_n = YTD_n - YTD_{n-1} for n>1 within each fiscal
    year.  Q1 values are kept as-is since YTD for Q1 == Q1.

    Balance sheet data is point-in-time and must NOT be de-cumulated.
    Callers should only pass income statement or cash flow DataFrames.
    """
    if df.empty or len(df.columns) < 2:
        return df

    date_cols = sorted(df.columns, key=parse_period_label)
    dates = [parse_period_label(c) for c in date_cols]

    fy_groups: dict[int, list[tuple[str, datetime.date]]] = {}
    for col, dt in zip(date_cols, dates):
        fy = _fiscal_year(dt)
        fy_groups.setdefault(fy, []).append((col, dt))

    is_cumulative = _detect_cumulative(df, fy_groups)
    if not is_cumulative:
        logger.debug("decumulate_quarterly(%s): values don't appear cumulative, returning as-is", debug_label)
        return df

    result = df.copy()
    for fy, col_dates in fy_groups.items():
        col_dates_sorted = sorted(col_dates, key=lambda x: x[1])
        for i in range(len(col_dates_sorted) - 1, 0, -1):
            curr_col = col_dates_sorted[i][0]
            prev_col = col_dates_sorted[i - 1][0]
            result[curr_col] = df[curr_col] - df[prev_col]

    logger.debug("decumulate_quarterly(%s): de-cumulated %d fiscal years", debug_label, len(fy_groups))
    return result


def _fiscal_year(dt: datetime.date) -> int:
    """Estimate the fiscal year for a period-end date.

    Most companies end their fiscal year in December. For Q1-Q3 dates
    (month <= 9 within a calendar year), the fiscal year is the same
    calendar year.  For simplicity, we group by calendar year.  This works
    for calendar-year filers and is a reasonable approximation for
    non-calendar filers (the heuristic still groups correctly because
    SEC filings are chronological).
    """
    return dt.year


def _detect_cumulative(
    df: pd.DataFrame,
    fy_groups: dict[int, list[tuple[str, datetime.date]]],
) -> bool:
    """Heuristic: check if values are monotonically non-decreasing within fiscal years.

    Checks the top several rows (by absolute sum) for the cumulative
    pattern: non-negative, monotonically increasing, and the last value
    is substantially larger than the first.  Checking multiple rows avoids
    false negatives when the largest-sum row is non-cumulative metadata
    (e.g. weighted-average shares outstanding).
    """
    for fy, col_dates in fy_groups.items():
        if len(col_dates) < 2:
            continue
        col_dates_sorted = sorted(col_dates, key=lambda x: x[1])
        cols = [c for c, _ in col_dates_sorted]

        sub = df[cols].apply(pd.to_numeric, errors="coerce")
        abs_sums = sub.abs().sum(axis=1)
        top_indices = abs_sums.nlargest(min(10, len(abs_sums))).index

        for idx in top_indices:
            row = sub.loc[idx]
            vals = [row[c] for c in cols if pd.notna(row[c])]
            if len(vals) < 2:
                continue
            all_non_neg = all(v >= 0 for v in vals)
            monotonic = all(vals[i] <= vals[i + 1] * 1.01 for i in range(len(vals) - 1))
            if all_non_neg and monotonic and vals[-1] > vals[0] * 1.5:
                return True

    return False


def ensure_dataframe(possible_df, debug_label="(unknown)") -> pd.DataFrame:
    """Safely convert various object types to a DataFrame or return empty if not feasible."""
    if possible_df is None:
        logger.debug("ensure_dataframe(%s): None -> empty DF", debug_label)
        return pd.DataFrame()

    if isinstance(possible_df, pd.DataFrame):
        if "label" in possible_df.columns and not isinstance(possible_df.index, pd.RangeIndex):
            logger.debug("ensure_dataframe(%s): already DF shape=%s", debug_label, possible_df.shape)
            return possible_df
        if "label" in possible_df.columns:
            return _convert_statement_df(possible_df, debug_label)
        logger.debug("ensure_dataframe(%s): already DF shape=%s", debug_label, possible_df.shape)
        return possible_df

    if hasattr(possible_df, "to_dataframe"):
        try:
            df_ = possible_df.to_dataframe()
            if isinstance(df_, pd.DataFrame):
                if "label" in df_.columns:
                    return _convert_statement_df(df_, debug_label)
                logger.debug("ensure_dataframe(%s): .to_dataframe() shape=%s", debug_label, df_.shape)
                return df_
            if isinstance(df_, np.ndarray):
                return pd.DataFrame(df_)
            logger.warning("ensure_dataframe(%s): .to_dataframe() returned unknown type -> empty", debug_label)
            return pd.DataFrame()
        except Exception as e:
            logger.exception("ensure_dataframe(%s): error calling .to_dataframe(): %s", debug_label, e)
            return pd.DataFrame()

    if isinstance(possible_df, np.ndarray):
        logger.debug("ensure_dataframe(%s): got ndarray shape=%s -> wrapping in DF", debug_label, possible_df.shape)
        return pd.DataFrame(possible_df)

    logger.warning("ensure_dataframe(%s): unrecognized type=%s -> empty DF", debug_label, type(possible_df))
    return pd.DataFrame()


def make_numeric_df(df: pd.DataFrame, debug_label="(unknown)") -> pd.DataFrame:
    """Converts columns to numeric where possible and deduplicates index rows.

    When duplicate index labels exist (common in XBRL filings with multiple
    frames), the row with the largest absolute sum is kept."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        logger.debug("make_numeric_df(%s): invalid or empty DF -> skip", debug_label)
        return df

    pre_non_null = df.notnull().sum().sum()
    numeric_df = df.apply(pd.to_numeric, errors="coerce")
    post_non_null = numeric_df.notnull().sum().sum()

    if numeric_df.index.duplicated().any():
        n_dups = numeric_df.index.duplicated(keep=False).sum()
        numeric_df["_abs_sum"] = numeric_df.abs().sum(axis=1, skipna=True)
        numeric_df = numeric_df.sort_values("_abs_sum", ascending=False)
        numeric_df = numeric_df[~numeric_df.index.duplicated(keep="first")]
        numeric_df = numeric_df.drop(columns=["_abs_sum"])
        logger.debug("make_numeric_df(%s): deduplicated %d rows with duplicate labels", debug_label, n_dups)

    logger.debug(
        "make_numeric_df(%s): coerced to numeric. Non-null before=%d, after=%d. shape=%s",
        debug_label, pre_non_null, post_non_null, numeric_df.shape
    )
    return numeric_df
