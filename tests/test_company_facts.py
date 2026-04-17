"""tests/test_company_facts.py — unit tests for CompanyFactsClient."""

import json
import pytest
from unittest.mock import patch, MagicMock

from edgar_analytics.company_facts import CompanyFactsClient


@pytest.fixture
def client():
    return CompanyFactsClient()


@pytest.fixture
def sample_facts():
    return {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {"end": "2023-09-30", "val": 383285000000, "form": "10-K"},
                            {"end": "2022-09-24", "val": 394328000000, "form": "10-K"},
                        ]
                    }
                },
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            {"end": "2023-09-30", "val": 96995000000, "form": "10-K"},
                        ]
                    }
                },
                "Assets": {
                    "units": {
                        "USD": [
                            {"end": "2023-09-30", "val": 352583000000, "form": "10-K"},
                        ]
                    }
                },
            }
        }
    }


class TestGetLatestValue:
    def test_extracts_latest_annual(self, client, sample_facts):
        val = client.get_latest_value(sample_facts, "us-gaap:Revenues")
        assert val == 383285000000

    def test_returns_none_for_missing_concept(self, client, sample_facts):
        val = client.get_latest_value(sample_facts, "us-gaap:NonexistentConcept")
        assert val is None

    def test_returns_none_for_empty_facts(self, client):
        assert client.get_latest_value(None, "us-gaap:Revenues") is None
        assert client.get_latest_value({}, "us-gaap:Revenues") is None


class TestValidateMetrics:
    def test_no_discrepancies_within_tolerance(self, client, sample_facts):
        metrics = {
            "Revenue": 383285000000,
            "Net Income": 96995000000,
        }
        discrepancies = client.validate_metrics(sample_facts, metrics, ticker="AAPL")
        assert discrepancies == []

    def test_discrepancy_detected(self, client, sample_facts):
        metrics = {
            "Revenue": 300000000000,
        }
        discrepancies = client.validate_metrics(sample_facts, metrics, ticker="AAPL")
        assert len(discrepancies) == 1
        assert "Revenue" in discrepancies[0]
        assert "AAPL" in discrepancies[0]

    def test_skips_zero_local_values(self, client, sample_facts):
        metrics = {"Revenue": 0, "Net Income": 0}
        discrepancies = client.validate_metrics(sample_facts, metrics)
        assert discrepancies == []

    def test_none_facts_returns_empty(self, client):
        discrepancies = client.validate_metrics(None, {"Revenue": 1000})
        assert discrepancies == []


class TestCikForTicker:
    def test_resolves_ticker(self, client):
        with patch("edgar.Company") as mock_company:
            mock_instance = MagicMock()
            mock_instance.cik = 320193
            mock_company.return_value = mock_instance
            cik = client.cik_for_ticker("AAPL")
        assert cik == "0000320193"

    def test_returns_none_on_failure(self, client):
        with patch("edgar.Company", side_effect=Exception("not found")):
            cik = client.cik_for_ticker("INVALID")
        assert cik is None


class TestValidateMetricsFallbackConcept:
    def test_revenue_falls_back_to_revenues(self, client, sample_facts):
        """_CONCEPT_MAP tries RevenueFromContract... first, falls back to Revenues."""
        metrics = {"Revenue": 383285000000}
        discrepancies = client.validate_metrics(sample_facts, metrics, ticker="AAPL")
        assert discrepancies == []

    def test_equity_falls_back_to_nci_variant(self, client):
        facts = {
            "facts": {
                "us-gaap": {
                    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest": {
                        "units": {"USD": [{"end": "2023-09-30", "val": 62146000000, "form": "10-K"}]}
                    }
                }
            }
        }
        metrics = {"Total shareholders' equity": 62146000000}
        discrepancies = client.validate_metrics(facts, metrics, ticker="TEST")
        assert discrepancies == []


class TestRetryBackoff:
    def test_retries_on_429(self, client):
        from urllib.error import HTTPError
        err = HTTPError("url", 429, "Too Many Requests", {}, None)
        with patch("edgar_analytics.company_facts.urlopen", side_effect=err), \
             patch("edgar_analytics.company_facts.time") as mock_time:
            result = client._get_json("https://example.com/test")
        assert result is None
        assert mock_time.sleep.call_count == 2

    def test_no_retry_on_403(self, client):
        from urllib.error import HTTPError
        err = HTTPError("url", 403, "Forbidden", {}, None)
        with patch("edgar_analytics.company_facts.urlopen", side_effect=err), \
             patch("edgar_analytics.company_facts.time") as mock_time:
            result = client._get_json("https://example.com/test")
        assert result is None
        assert mock_time.sleep.call_count == 0


class TestFetch:
    def test_fetch_returns_none_on_missing_cik(self, client):
        with patch.object(client, "cik_for_ticker", return_value=None):
            result = client.fetch("INVALID")
        assert result is None

    def test_fetch_calls_api(self, client, sample_facts):
        with patch.object(client, "cik_for_ticker", return_value="0000320193"), \
             patch.object(client, "_get_json", return_value=sample_facts):
            result = client.fetch("AAPL")
        assert result == sample_facts
