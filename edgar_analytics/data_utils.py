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


def parse_period_label(col_name: str) -> datetime.date:
    """
    Attempt to parse '2021-12-31', 'FY2023', '2021' into a date.
    Return 1900-01-01 if parse fails. Used for sorting columns by time.
    """
    patterns = ["%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%Y"]
    if col_name.upper().startswith("FY"):
        try:
            yr = int(col_name[2:])
            return datetime.date(yr, 12, 31)
        except ValueError:
            pass

    for pat in patterns:
        try:
            if pat == "%Y":
                dt = datetime.datetime.strptime(col_name, "%Y")
                return dt.replace(month=12, day=31).date()
            dt = datetime.datetime.strptime(col_name, pat)
            return dt.date()
        except ValueError:
            continue

    year_match = re.search(r"(20[0-9]{2}|19[0-9]{2})", col_name)
    if year_match:
        yr = int(year_match.group(1))
        return datetime.date(yr, 12, 31)

    logger.debug("parse_period_label: Could not parse '%s' -> fallback=1900-01-01", col_name)
    return datetime.date(1900, 1, 1)


def custom_float_format(x):
    """
    Formats numeric x to a short string with K, M, B, T or .2f if <1000.
    Non-numerics are returned as-is.
    """
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


def ensure_dataframe(possible_df, debug_label="(unknown)") -> pd.DataFrame:
    """
    Safely convert various object types to a DataFrame or return empty if not feasible.
    """
    if possible_df is None:
        logger.debug("ensure_dataframe(%s): None -> empty DF", debug_label)
        return pd.DataFrame()

    if isinstance(possible_df, pd.DataFrame):
        logger.debug("ensure_dataframe(%s): already DF shape=%s", debug_label, possible_df.shape)
        return possible_df

    if hasattr(possible_df, "to_dataframe"):
        try:
            df_ = possible_df.to_dataframe()
            if isinstance(df_, pd.DataFrame):
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
    """
    Converts columns to numeric where possible. Logs changes in non-null counts.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        logger.debug("make_numeric_df(%s): invalid or empty DF -> skip", debug_label)
        return df

    numeric_df = df.copy()
    pre_non_null = numeric_df.notnull().sum().sum()
    for col in numeric_df.columns:
        numeric_df[col] = pd.to_numeric(numeric_df[col], errors="coerce")
    post_non_null = numeric_df.notnull().sum().sum()

    logger.debug(
        "make_numeric_df(%s): coerced to numeric. Non-null before=%d, after=%d. shape=%s",
        debug_label, pre_non_null, post_non_null, numeric_df.shape
    )
    return numeric_df
