# tests/test_data_utils.py

import pytest
import pandas as pd
import numpy as np

from edgar_analytics.data_utils import (
    parse_period_label,
    custom_float_format,
    ensure_dataframe,
    make_numeric_df
)

def test_parse_period_label_valid_dates():
    assert parse_period_label("2021-12-31") == pd.Timestamp("2021-12-31").date()
    assert parse_period_label("FY2023") == pd.Timestamp("2023-12-31").date()
    assert parse_period_label("2021/05/20") == pd.Timestamp("2021-05-20").date()
    assert parse_period_label("2021") == pd.Timestamp("2021-12-31").date()

def test_parse_period_label_invalid_date():
    # Expect fallback to 1900-01-01
    assert parse_period_label("NotADate") == pd.Timestamp("1900-01-01").date()

@pytest.mark.parametrize("value,expected", [
    # With abs_x >= 1e12 => x / 1e12 => "...T"
    (1234567890123.45, "1.23T"),  
    # With abs_x >= 1e9 => x / 1e9 => "...B"
    # But 987654321.12 is < 1e9 => actually 9.8765e8 => so it is x / 1e6 => "987.65M"
    (987654321.12, "987.65M"),
    # With abs_x >= 1e6 => x / 1e6 => "...M"
    (1234567.89, "1.23M"),
    # With abs_x >= 1e3 => x / 1e3 => "...K"
    (1234.56, "1.23K"),
    # < 1e3 => normal 2-decimal
    (12.345, "12.35"),
    # Non-numerical => return original value
    ("not a number", "not a number"),
])
def test_custom_float_format(value, expected):
    from edgar_analytics.data_utils import custom_float_format
    assert custom_float_format(value) == expected

def test_ensure_dataframe_none():
    df = ensure_dataframe(None, debug_label="testNone")
    assert isinstance(df, pd.DataFrame)
    assert df.empty

def test_ensure_dataframe_already_df():
    input_df = pd.DataFrame({"col1": [1, 2]})
    df = ensure_dataframe(input_df, debug_label="testDF")
    assert df is input_df  # same reference
    assert df.shape == (2, 1)

def test_ensure_dataframe_ndarray():
    arr = np.array([[1, 2], [3, 4]])
    df = ensure_dataframe(arr, debug_label="testNDArray")
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (2, 2)

class CustomDFWrapper:
    """Fake object that provides a .to_dataframe() method."""
    def __init__(self, data):
        self._data = data

    def to_dataframe(self):
        return pd.DataFrame(self._data)

def test_ensure_dataframe_with_to_dataframe():
    wrapper = CustomDFWrapper({"col1": [1, 2, 3]})
    df = ensure_dataframe(wrapper, debug_label="testToDF")
    assert not df.empty
    assert list(df.columns) == ["col1"]

def test_ensure_dataframe_with_error_in_to_dataframe():
    class BrokenWrapper:
        def to_dataframe(self):
            raise ValueError("Simulated error")

    broken = BrokenWrapper()
    df = ensure_dataframe(broken, debug_label="testToDFError")
    assert df.empty

def test_ensure_dataframe_unrecognized_type():
    # e.g. a dictionary that doesn't have .to_dataframe() or isn't a DataFrame/NDArray
    df = ensure_dataframe({"something": "bad"}, debug_label="testUnrecognized")
    assert isinstance(df, pd.DataFrame)
    assert df.empty

def test_make_numeric_df_empty():
    empty_df = pd.DataFrame()
    result = make_numeric_df(empty_df, debug_label="testEmpty")
    assert result.empty

def test_make_numeric_df_conversion():
    df = pd.DataFrame({"mixed": ["123", "456", None, "abc"]})
    result = make_numeric_df(df, debug_label="testConversion")
    assert not result.empty
    # "123", "456" => numeric, "abc" => NaN
    actual_list = result["mixed"].tolist()
    assert actual_list[0] == 123.0
    assert actual_list[1] == 456.0
    assert np.isnan(actual_list[2])
    assert np.isnan(actual_list[3])

def test_parse_period_label_fallback_no_digits():
    parsed = parse_period_label("ABCDE")  # no digits, doesn't match "FY"
    assert str(parsed) == "1900-01-01", f"Expected fallback date, got {parsed}"
