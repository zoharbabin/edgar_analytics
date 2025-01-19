"""
tests/test_synonyms_utils.py

Tests for synonyms_utils helper functions.
"""

import pytest
import pandas as pd

from edgar_analytics.synonyms_utils import find_synonym_value
from edgar_analytics.synonyms_utils import flip_sign_if_negative_expense


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

def test_partial_match_multiple_synonyms():
    # Suppose we're searching synonyms for "revenue" => includes "Revenue", "Revenues", etc.
    # We'll craft rows that partially contain the word 'Revenue' in different ways.
    df = pd.DataFrame({
        "Q1": [50, -100, 300],
        "Q2": [60,  -90, 1000],
    }, index=[
        "TotalRevenueMisc",       # partial match, sum= (50+60)=110 => abs=110
        "RevenueFromSubsidiaries",# partial match, sum=(-100 + -90)= -190 => abs=190
        "NonOperatingRevenue",    # partial match, sum= (300+1000)=1300 => abs=1300
    ])

    synonyms_list = ["Revenue"]  # typical for the 'revenue' synonyms

    val = find_synonym_value(df, synonyms_list, fallback=0.0, debug_label="TestPartial")
    # We expect it to pick the row with the largest absolute sum => "NonOperatingRevenue"
    # last numeric value in row => Q2=1000
    assert val == 1000, f"Should pick NonOperatingRevenue row's last col=1000 (largest abs sum)."
