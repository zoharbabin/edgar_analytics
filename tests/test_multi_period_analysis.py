# tests/test_multi_period_analysis.py

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from edgar_analytics.multi_period_analysis import (
    retrieve_multi_year_data,
    analyze_quarterly_balance_sheets,
    extract_period_values,
    compute_growth_series,
    compute_cagr
)

def test_retrieve_multi_year_data_no_10k():
    """
    If get_filings(form="10-K") returns an empty list or None, we skip that part.
    """
    mock_company = MagicMock()
    mock_company.get_filings.return_value.head.return_value = []  # No 10-K
    with patch("edgar_analytics.multi_period_analysis.MultiFinancials") as mock_mf:
        data = retrieve_multi_year_data("FAKE", n_years=2, n_quarters=2)
        assert data["annual_inc_df"].empty

def test_extract_period_values():
    df = pd.DataFrame({
        "2020-12-31": [100, 50],
        "2021-12-31": [200, 80],
    }, index=["Revenue", "Net Income"])
    results = extract_period_values(df, debug_label="test")
    assert results["Revenue"]["2020-12-31"] == 100
    assert results["Net Income"]["2021-12-31"] == 80

def test_extract_period_values_empty():
    df = pd.DataFrame()
    results = extract_period_values(df)
    assert results == {"Revenue": {}, "Net Income": {}}

def test_compute_growth_series():
    data = {"2020-12-31": 100, "2021-12-31": 200, "2022-12-31": 180}
    growth = compute_growth_series(data)
    # 2021 => 100 to 200 => +100%
    # 2022 => 200 to 180 => -10%
    assert growth["2021-12-31"] == pytest.approx(100.0)
    assert growth["2022-12-31"] == pytest.approx(-10.0)

def test_compute_growth_series_insufficient():
    data = {"2020-12-31": 100}
    growth = compute_growth_series(data)
    assert growth == {}

def test_compute_cagr():
    data = {"2020": 100, "2023": 200}
    # 3 years difference (2023 - 2020)
    # CAGR = (200/100)^(1/3) - 1 => ~26%
    result = compute_cagr(data)
    assert result == pytest.approx(26.0, abs=5.0)  # within reason

def test_analyze_quarterly_balance_sheets_no_filings():
    mock_company = MagicMock()
    mock_company.get_filings.return_value.head.return_value = []

    results = analyze_quarterly_balance_sheets(mock_company, n_quarters=2)
    # Should yield empty dictionary values
    assert results["inventory"] == {}
    assert results["receivables"] == {}
    assert results["free_cf"] == {}

@pytest.mark.parametrize("negative_cf", [False, True])
def test_analyze_quarterly_balance_sheets_partials(negative_cf):
    """
    Provide partial DataFrames for BS, CF to test coverage.
    """
    # We'll mock the MultiFinancials so we can define
    # a small DataFrame returning from get_balance_sheet() & get_cash_flow_statement()
    mock_filings = MagicMock()
    mock_mf = MagicMock()

    # Simple 2-quarter scenario
    bs_df = pd.DataFrame({
        "Q1-2023": [100, 200],
        "Q2-2023": [150, 250],
    }, index=["inventory", "accounts receivable"])
    cf_df = pd.DataFrame({
        "Q1-2023": [300, -50],
        "Q2-2023": [400, -60],
    }, index=["NetCashProvidedByUsedInOperatingActivities", "PaymentsToAcquirePropertyPlantAndEquipment"])

    mock_mf.get_balance_sheet.return_value = bs_df
    mock_mf.get_cash_flow_statement.return_value = cf_df

    with patch("edgar_analytics.multi_period_analysis.MultiFinancials", return_value=mock_mf):
        mock_company = MagicMock()
        mock_company.get_filings.return_value.head.return_value = mock_filings

        results = analyze_quarterly_balance_sheets(mock_company, n_quarters=2)
        # Check if it properly extracts inventory, receivables, free_cf
        assert list(results["inventory"].keys()) == ["Q1-2023", "Q2-2023"]
        assert list(results["receivables"].keys()) == ["Q1-2023", "Q2-2023"]
        assert list(results["free_cf"].keys()) == ["Q1-2023", "Q2-2023"]

def test_check_additional_alerts_quarterly_consecutive_negative_fcf():
    """
    Provide a data_map with at least 2 consecutive negative FCF quarters
    and verify the correct alert is generated.
    """
    from edgar_analytics.multi_period_analysis import check_additional_alerts_quarterly

    data_map = {
        "free_cf": {
            "2022-Q1": -10.0,
            "2022-Q2": -5.0,   # 2 consecutive negative => should trigger an alert
            "2022-Q3": 20.0,  # back positive
        },
        "inventory": {},
        "receivables": {},
    }

    alerts = check_additional_alerts_quarterly(data_map)
    assert any("2 consecutive quarters of negative FCF" in a for a in alerts), \
        "Expected an alert for 2 consecutive negative FCF quarters"

def test_inventory_receivables_spike():
    """
    Provide quarterly data with a >30% spike in inventory and receivables
    to ensure we trigger the alert lines.
    """
    from edgar_analytics.multi_period_analysis import check_additional_alerts_quarterly

    # Q1 => 100, Q2 => 140 => +40% => triggers alert
    # Q3 => 170 => also triggers alert
    data_map = {
        "inventory": {
            "Q1-2023": 100,
            "Q2-2023": 140,
            "Q3-2023": 170,
        },
        "receivables": {
            "Q1-2023": 200,
            "Q2-2023": 261,  # ~30.5%, triggers alert
            "Q3-2023": 260,  # no spike from Q2
        },
        "free_cf": {}
    }
    alerts = check_additional_alerts_quarterly(data_map)
    # Should catch at least one inventory spike and one receivables spike
    assert any("Inventory spiked +40.00%" in a for a in alerts), "Expected an inventory spike alert."
    assert any("Receivables spiked +30." in a for a in alerts), "Expected a receivables spike alert."
