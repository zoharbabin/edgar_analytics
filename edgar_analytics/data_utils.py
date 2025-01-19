# edgar_analytics/data_utils.py

import re
import datetime
import pandas as pd
import numpy as np

from .logging_utils import get_logger

logger = get_logger(__name__)


def parse_period_label(col_name: str) -> datetime.date:
    """
    Attempt to parse a column name like '2021-12-31' or 'FY2021' into a date.
    Fallback to 1900-01-01 if parse fails, allowing chronological sorting.
    """
    patterns = [
        "%Y-%m-%d", "%Y/%m/%d", "%Y-%m",
        "%Y",
    ]
    # ---------------------------------------------------
    # 1) Check if col_name starts with "FY" explicitly:
    # ---------------------------------------------------
    if col_name.upper().startswith("FY"):
        # e.g. col_name = "FY2023" => parse year digits
        try:
            yr_str = col_name[2:]  # "2023"
            yr = int(yr_str)
            return datetime.date(yr, 12, 31)
        except ValueError:
            pass  # fallback to main approach if needed

    # ---------------------------------------------------
    # 2) Try the remaining patterns
    # ---------------------------------------------------
    for pat in patterns:
        try:
            if pat == "%Y":
                dt = datetime.datetime.strptime(col_name, "%Y")
                # Force Dec 31
                dt = dt.replace(month=12, day=31)
                return dt.date()
            else:
                dt = datetime.datetime.strptime(col_name, pat)
            return dt.date()
        except ValueError:
            pass

    # ---------------------------------------------------
    # 3) Lastly, custom regex for any year mention
    # ---------------------------------------------------
    year_match = re.search(r"(20[0-9]{2}|19[0-9]{2})", col_name)
    if year_match:
        yr = int(year_match.group(1))
        return datetime.date(yr, 12, 31)

    logger.debug(
        "parse_period_label: Could not parse '%s' -> fallback to 1900-01-01.",
        col_name
    )
    return datetime.date(1900, 1, 1)


def custom_float_format(x):
    """
    Formats a float or integer to a more readable string, e.g., 394.33B, etc.
    Returns the original value if not a number.
    """
    if isinstance(x, (int, float)):
        abs_x = abs(x)
        if abs_x >= 1e12:
            return f"{x / 1e12:.2f}T"
        elif abs_x >= 1e9:
            return f"{x / 1e9:.2f}B"
        elif abs_x >= 1e6:
            return f"{x / 1e6:.2f}M"
        elif abs_x >= 1e3:
            return f"{x / 1e3:.2f}K"
        else:
            return f"{x:.2f}"
    return x


def ensure_dataframe(possible_df, debug_label="(unknown)") -> pd.DataFrame:
    """
    Safely convert various object types to a DataFrame.
    """
    if possible_df is None:
        logger.debug(
            "ensure_dataframe(%s): received None -> empty DataFrame.",
            debug_label
        )
        return pd.DataFrame()

    if isinstance(possible_df, pd.DataFrame):
        logger.debug(
            "ensure_dataframe(%s): already DF shape=%s",
            debug_label, possible_df.shape
        )
        return possible_df

    if isinstance(possible_df, np.ndarray):
        logger.debug(
            "ensure_dataframe(%s): got ndarray shape=%s -> wrapping in DataFrame",
            debug_label, possible_df.shape
        )
        return pd.DataFrame(possible_df)

    if hasattr(possible_df, "to_dataframe"):
        try:
            df_ = possible_df.to_dataframe()
            if isinstance(df_, pd.DataFrame):
                logger.debug(
                    "ensure_dataframe(%s): .to_dataframe() -> shape=%s",
                    debug_label, df_.shape
                )
                return df_
            if isinstance(df_, np.ndarray):
                logger.debug(
                    "ensure_dataframe(%s): .to_dataframe() returned ndarray "
                    "shape=%s", debug_label, df_.shape
                )
                return pd.DataFrame(df_)
            logger.warning(
                "ensure_dataframe(%s): .to_dataframe() returned unrecognized "
                "type -> empty DF.",
                debug_label
            )
            return pd.DataFrame()
        except Exception as e:
            logger.exception(
                "ensure_dataframe(%s): error calling .to_dataframe(): %s",
                debug_label, e
            )
            return pd.DataFrame()

    logger.warning(
        "ensure_dataframe(%s): unrecognized object type=%s -> empty DF.",
        debug_label, type(possible_df)
    )
    return pd.DataFrame()


def make_numeric_df(df: pd.DataFrame, debug_label="(unknown)") -> pd.DataFrame:
    """
    Force columns to numeric, logging changes in non-null counts.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        logger.debug(
            "make_numeric_df(%s): input not DF or empty -> skipping conversion.",
            debug_label
        )
        return df

    numeric_df = df.copy()
    pre_non_null_count = numeric_df.notnull().sum().sum()

    for col in numeric_df.columns:
        numeric_df[col] = pd.to_numeric(numeric_df[col], errors="coerce")

    post_non_null_count = numeric_df.notnull().sum().sum()
    logger.debug(
        "make_numeric_df(%s): coerced %d columns to numeric. "
        "Non-null cells before=%d, after=%d. shape=%s",
        debug_label, numeric_df.shape[1], pre_non_null_count,
        post_non_null_count, numeric_df.shape
    )
    return numeric_df
