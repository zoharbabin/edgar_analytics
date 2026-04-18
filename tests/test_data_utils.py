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


def test_parse_period_label_quarter_formats():
    """Quarter-based labels should parse to the quarter-end date."""
    assert parse_period_label("Q1-2023") == pd.Timestamp("2023-03-31").date()
    assert parse_period_label("Q2-2023") == pd.Timestamp("2023-06-30").date()
    assert parse_period_label("Q3-2023") == pd.Timestamp("2023-09-30").date()
    assert parse_period_label("Q4-2023") == pd.Timestamp("2023-12-31").date()
    assert parse_period_label("Q1 2022") == pd.Timestamp("2022-03-31").date()
    assert parse_period_label("Q4_2021") == pd.Timestamp("2021-12-31").date()


def test_parse_period_label_quarter_sorting():
    """Quarters within the same year should sort chronologically."""
    labels = ["Q3-2023", "Q1-2023", "Q4-2023", "Q2-2023"]
    sorted_labels = sorted(labels, key=parse_period_label)
    assert sorted_labels == ["Q1-2023", "Q2-2023", "Q3-2023", "Q4-2023"]


def test_custom_float_format_nan():
    assert custom_float_format(float("nan")) == "N/A"
    assert custom_float_format(float("inf")) == "N/A"


def test_make_numeric_df_deduplicates_index():
    """When duplicate index labels exist, keep the row with largest absolute values."""
    df = pd.DataFrame(
        {"2023": [100, 500, 200], "2024": [110, 550, 210]},
        index=["Revenue", "Revenue", "Net Income"],
    )
    result = make_numeric_df(df, debug_label="testDedup")
    assert not result.index.duplicated().any()
    assert result.loc["Revenue", "2023"] == 500


class TestStatementDFConversion:
    """Tests for converting edgartools Statement-style DataFrames."""

    def _make_statement_df(self):
        """Create a DataFrame mimicking edgartools Statement.to_dataframe()."""
        return pd.DataFrame({
            "concept": [
                "us-gaap_Abstract", "us-gaap_Revenue", "us-gaap_CostOfRevenue",
                "us-gaap_Revenue",
            ],
            "label": ["Income:", "Net sales", "Cost of sales", "Products"],
            "standard_concept": [np.nan, "Revenue", "CostOfRevenue", np.nan],
            "2024-09-28": [np.nan, 391035e6, 210352e6, 200000e6],
            "2023-09-30": [np.nan, 383285e6, 214137e6, 190000e6],
            "level": [1, 2, 2, 3],
            "abstract": [True, False, False, False],
            "dimension": [False, False, False, True],
        })

    def test_converts_label_to_index(self):
        df = self._make_statement_df()
        result = ensure_dataframe(df, "test-stmt")
        assert "Net sales" in result.index
        assert "Cost of sales" in result.index

    def test_drops_abstract_rows(self):
        df = self._make_statement_df()
        result = ensure_dataframe(df, "test-stmt")
        assert "Income:" not in result.index

    def test_drops_dimension_rows(self):
        df = self._make_statement_df()
        result = ensure_dataframe(df, "test-stmt")
        assert "Products" not in result.index

    def test_adds_concept_tag_rows(self):
        df = self._make_statement_df()
        result = ensure_dataframe(df, "test-stmt")
        assert "us-gaap_CostOfRevenue" in result.index

    def test_keeps_only_value_columns(self):
        df = self._make_statement_df()
        result = ensure_dataframe(df, "test-stmt")
        assert "2024-09-28" in result.columns
        assert "concept" not in result.columns
        assert "abstract" not in result.columns

    def test_values_are_correct(self):
        df = self._make_statement_df()
        result = ensure_dataframe(df, "test-stmt")
        assert result.loc["Net sales", "2024-09-28"] == pytest.approx(391035e6)

    def test_falls_back_to_dimension_rows_if_all_filtered(self):
        """If filtering out dimension rows leaves nothing, keep them."""
        df = pd.DataFrame({
            "label": ["Products", "Services"],
            "concept": ["us-gaap_ProductRevenue", "us-gaap_ServiceRevenue"],
            "2024-09-28": [200e6, 100e6],
            "abstract": [False, False],
            "dimension": [True, True],
        })
        result = ensure_dataframe(df, "test-all-dim")
        assert len(result) > 0
        assert "Products" in result.index


class TestGetFinancialStatementCallable:
    """Test that _get_financial_statement calls methods."""

    def test_calls_method(self):
        from edgar_analytics.metrics import _get_financial_statement
        from unittest.mock import MagicMock

        mock_fin = MagicMock()
        mock_fin.income_statement.return_value = "called_result"
        result = _get_financial_statement(mock_fin, "income_statement")
        assert result == "called_result"
        mock_fin.income_statement.assert_called_once()

    def test_returns_property_directly(self):
        from edgar_analytics.metrics import _get_financial_statement

        class FakeFinancials:
            balance_sheet = pd.DataFrame({"val": [1]})

        result = _get_financial_statement(FakeFinancials(), "balance_sheet")
        assert isinstance(result, pd.DataFrame)

    def test_returns_none_for_missing(self):
        from edgar_analytics.metrics import _get_financial_statement
        from unittest.mock import MagicMock

        mock_fin = MagicMock(spec=[])
        result = _get_financial_statement(mock_fin, "nonexistent")
        assert result is None
