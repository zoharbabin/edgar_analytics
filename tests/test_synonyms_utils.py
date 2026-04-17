# tests/test_synonyms_utils.py

import pytest
import pandas as pd
import numpy as np

from edgar_analytics.synonyms_utils import (
    find_synonym_value,
    find_best_synonym_row,
    flip_sign_if_negative_expense,
    compute_capex_single_period,
    compute_capex_for_column,
)

def test_find_synonym_value_no_match():
    df = pd.DataFrame({
        "Column1": ["Value1", "Value2"],
        "Column2": [100, 200]
    }, index=["Row1", "Row2"])
    synonyms = ["NonExistentRow"]
    fallback = None

    result = find_synonym_value(df, synonyms, fallback=fallback, debug_label="Test")
    assert result == fallback

def test_find_synonym_value_exact_match():
    df = pd.DataFrame({
        "Column1": ["Revenue", "Cost of sales"],
        "Column2": [100, -60]
    }, index=["Revenue", "Cost of sales"])
    synonyms = ["Revenue"]
    fallback = 0.0

    result = find_synonym_value(df, synonyms, fallback=fallback, debug_label="Test")
    assert result == 100.0

def test_flip_sign_if_negative_expense_rnd():
    assert flip_sign_if_negative_expense(-100, "rnd_expenses") == 100
    assert flip_sign_if_negative_expense(0, "rnd_expenses") == 0
    assert flip_sign_if_negative_expense(-5, "operating_expenses") == 5
    # Non-expense label => no flipping
    assert flip_sign_if_negative_expense(-10, "some_other_label") == -10


@pytest.mark.parametrize("capex_val, expected", [
    (-500, 500),
    (500, 500),   # If a 'capex' row is positive, we assume it's already correct
    (None, 0.0),
    (np.nan, 0.0)
])
def test_compute_capex_single_period_direct(capex_val, expected):
    """
    If the DataFrame has a direct 'capital_expenditures' row, compute_capex_single_period
    should return that absolute value. Negative input => flipped to positive.
    """
    df = pd.DataFrame(
        {"Value": [capex_val]},
        index=["Capital expenditures"]
    )
    val = compute_capex_single_period(df, debug_label="TestDirect")
    assert val == pytest.approx(expected)


def test_compute_capex_single_period_fallback():
    """
    If no direct capex row is found:
      - We use net investing outflow minus intangible + M&A outflows.
    """
    # Suppose net investing = -900 (outflow),
    # intangible = -200,
    # M&A = -300
    # => fallback capex = 900 - 200 - 300 = 400
    data = {
        "Value": [
            -900,     # NetCashProvidedByUsedInInvestingActivities
            -200,     # intangible
            -300      # M&A
        ]
    }
    idx = [
        "NetCashProvidedByUsedInInvestingActivities",
        "PaymentsToAcquireIntangibleAssets",
        "PaymentsToAcquireBusinessesNetOfCashAcquired"
    ]
    df = pd.DataFrame(data, index=idx)
    result = compute_capex_single_period(df, debug_label="TestFallback")
    assert result == pytest.approx(400.0)

def test_compute_capex_single_period_fallback_no_intangibles():
    """
    If net invests is negative but intangible or M&A lines are 0 => fallback to entire invests outflow.
    """
    data = {
        "Value": [
            -600,  # invests
            0,     # intangible
            0      # M&A
        ]
    }
    idx = [
        "us-gaap:NetCashProvidedByUsedInInvestingActivities",
        "Purchase of intangible assets",
        "Acquisitions (net of cash acquired)"
    ]
    df = pd.DataFrame(data, index=idx)
    val = compute_capex_single_period(df, debug_label="TestFallbackNoInt")
    assert val == pytest.approx(600.0)

def test_compute_capex_single_period_investing_positive():
    """
    If invests is positive => no net outflow => return 0.0 fallback for capex.
    """
    data = {
        "Value": [
            1000,  # invests is positive => no net outflow
            -200
        ]
    }
    idx = [
        "us-gaap:NetCashProvidedByUsedInInvestingActivities",
        "Purchase of intangible assets"
    ]
    df = pd.DataFrame(data, index=idx)
    val = compute_capex_single_period(df, debug_label="TestPosInvesting")
    assert val == 0.0

def test_compute_capex_single_period_negative_result_clamped():
    """
    If intangible + M&A outflows exceed net invests outflow => fallback is entire invests outflow.
    E.g. invests= -500 => abs=500, intangible=300, M&A=400 => sums=700 => overshoot => final=500
    """
    data = {
        "Value": [-500, -300, -400]
    }
    idx = [
        "us-gaap:NetCashProvidedByUsedInInvestingActivities",
        "PaymentsToAcquireIntangibleAssets",
        "PaymentsToAcquireBusinessesNetOfCashAcquired"
    ]
    df = pd.DataFrame(data, index=idx)
    val = compute_capex_single_period(df, debug_label="TestNegClamp")
    assert val == pytest.approx(500.0)


def test_find_best_synonym_row_exact():
    df = pd.DataFrame(
        {"2023": [100, 200], "2024": [110, 220]},
        index=["Revenue", "Net Income"]
    )
    row = find_best_synonym_row(df, "revenue", debug_label="test-exact")
    assert row is not None
    assert row["2023"] == 100


def test_find_best_synonym_row_partial():
    df = pd.DataFrame(
        {"2023": [500, 300], "2024": [550, 320]},
        index=["Total revenue from operations", "Cost of goods sold"]
    )
    row = find_best_synonym_row(df, "revenue", debug_label="test-partial")
    assert row is not None
    assert row["2023"] == 500


def test_find_best_synonym_row_no_match():
    df = pd.DataFrame(
        {"2023": [100]},
        index=["Something unrelated"]
    )
    row = find_best_synonym_row(df, "revenue", debug_label="test-nomatch")
    assert row is None


def test_find_best_synonym_row_empty_df():
    row = find_best_synonym_row(pd.DataFrame(), "revenue")
    assert row is None


def test_compute_capex_for_column_direct():
    """
    Multi-column scenario. Check direct capex in a single col.
    """
    df = pd.DataFrame(
        {
            "Q1": [None, None],
            "Q2": [-400, -900],
        },
        index=["Capital expenditures", "NetCashProvidedByUsedInInvestingActivities"]
    )
    # For col=Q2 => direct capex row= -400 => returns 400
    capex_q2 = compute_capex_for_column(df, "Q2", debug_label="MultiColTest")
    assert capex_q2 == pytest.approx(400)

def test_compute_capex_for_column_fallback():
    """
    Multi-column scenario. If no direct capex in 'Q2', fallback to invests minus intangible, etc.
    """
    df = pd.DataFrame(
        {
            "Q1": [None, -100],
            "Q2": [-600, -200],
        },
        index=["NetCashProvidedByUsedInInvestingActivities", "PaymentsToAcquireIntangibleAssets"]
    )
    # invests= -600 => abs=600; intangible= -200 => abs=200 => fallback=400
    val_q2 = compute_capex_for_column(df, "Q2", debug_label="FallbackMultiCol")
    assert val_q2 == pytest.approx(400)


def test_find_synonym_value_duplicate_index():
    """When DataFrame has duplicate index entries, should not silently fallback to 0."""
    df = pd.DataFrame(
        {"Value": [100, 200]},
        index=["Revenue", "Revenue"]
    )
    val = find_synonym_value(df, ["Revenue"], fallback=0.0, debug_label="DupIdx")
    assert val == 100.0


def test_find_best_synonym_row_duplicate_index():
    """find_best_synonym_row handles duplicate index entries by taking first row."""
    df = pd.DataFrame(
        {"2023": [500, 999], "2024": [600, 888]},
        index=["Revenue", "Revenue"]
    )
    row = find_best_synonym_row(df, "revenue", debug_label="test-dup")
    assert row is not None
    assert isinstance(row, pd.Series)
    assert row["2023"] == 500


def test_partial_match_prefers_tighter_coverage():
    """Partial matching should prefer 'Revenue' over 'Deferred revenue' for 'revenue' synonym."""
    df = pd.DataFrame(
        {"Value": [5000, 200]},
        index=["Deferred revenue", "Total revenue"]
    )
    val = find_synonym_value(df, ["Revenue"], fallback=0.0, debug_label="CoverageTest")
    assert val == 200.0


def test_partial_match_row_prefers_tighter_coverage():
    """find_best_synonym_row prefers the row whose label is most covered by the synonym."""
    df = pd.DataFrame(
        {"2023": [9000, 300], "2024": [9500, 350]},
        index=["Deferred revenue from contracts", "Total revenue"]
    )
    row = find_best_synonym_row(df, "revenue", debug_label="CoverageRowTest")
    assert row is not None
    assert row["2023"] == 300
