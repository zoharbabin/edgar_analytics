"""tests/test_models.py — unit tests for typed data models."""

import math
import pytest
from edgar_analytics.models import (
    AnalysisResult,
    TickerAnalysis,
    FilingSnapshot,
    SnapshotMetrics,
    ScoresResult,
    FilingInfo,
    MultiYearData,
    ForecastResult,
)
from edgar_analytics.scores import (
    PerShareMetrics,
    WorkingCapitalCycle,
    CapitalEfficiency,
    DuPontDecomposition,
    PiotroskiScore,
    AltmanZScore,
    BeneishMScore,
)


class TestSnapshotMetrics:
    def test_defaults_are_nan_for_ratios(self):
        m = SnapshotMetrics()
        assert math.isnan(m.gross_margin_pct)
        assert math.isnan(m.net_margin_pct)
        assert math.isnan(m.roe_pct)
        assert math.isnan(m.debt_to_equity)

    def test_defaults_are_zero_for_absolutes(self):
        m = SnapshotMetrics()
        assert m.revenue == 0.0
        assert m.net_income == 0.0
        assert m.free_cash_flow == 0.0

    def test_defaults_alerts_empty_tuple(self):
        m = SnapshotMetrics()
        assert m.alerts == ()

    def test_from_dict_round_trip(self):
        original = {
            "Revenue": 1_000_000,
            "Net Income": 200_000,
            "Gross Margin %": 45.5,
            "ROE %": 18.3,
            "Alerts": ["Low ROA", "High leverage"],
        }
        m = SnapshotMetrics.from_dict(original)
        assert m.revenue == 1_000_000
        assert m.net_income == 200_000
        assert m.gross_margin_pct == 45.5
        assert m.roe_pct == 18.3
        assert m.alerts == ("Low ROA", "High leverage")

        d = m.to_dict()
        assert d["Revenue"] == 1_000_000
        assert d["Net Income"] == 200_000
        assert d["Alerts"] == ["Low ROA", "High leverage"]

    def test_from_dict_empty(self):
        m = SnapshotMetrics.from_dict({})
        assert m.revenue == 0.0
        assert m.alerts == ()


class TestFilingInfo:
    def test_from_dict_round_trip(self):
        d = {"form_type": "10-K", "filed_date": "2024-03-15", "company": "Apple Inc.", "accession_no": "0000320193-24-000"}
        fi = FilingInfo.from_dict(d)
        assert fi.form_type == "10-K"
        assert fi.filed_date == "2024-03-15"
        assert fi.to_dict() == d

    def test_defaults(self):
        fi = FilingInfo()
        assert fi.form_type == "Unknown"
        assert fi.filed_date == ""


class TestFilingSnapshot:
    def test_from_dict_round_trip(self):
        d = {
            "metrics": {"Revenue": 500, "Alerts": []},
            "filing_info": {"form_type": "10-Q", "filed_date": "2024-06-30"},
        }
        snap = FilingSnapshot.from_dict(d)
        assert snap.metrics.revenue == 500
        assert snap.filing_info.form_type == "10-Q"
        rt = snap.to_dict()
        assert rt["metrics"]["Revenue"] == 500
        assert rt["filing_info"]["form_type"] == "10-Q"

    def test_empty_snapshot(self):
        snap = FilingSnapshot.from_dict({})
        assert snap.metrics.revenue == 0.0
        assert snap.filing_info.form_type == "Unknown"


class TestMultiYearData:
    def test_from_dict(self):
        d = {
            "annual_data": {"Revenue": {"2022": 100, "2023": 120}},
            "cagr_revenue": 10.5,
            "yoy_revenue_growth": {"2023": 20.0},
        }
        my = MultiYearData.from_dict(d)
        assert my.annual_data["Revenue"]["2023"] == 120
        assert my.cagr_revenue == 10.5


class TestForecastResult:
    def test_from_dict(self):
        fr = ForecastResult.from_dict({"annual_rev_forecast": 150.0, "quarterly_rev_forecast": 40.0})
        assert fr.annual_rev_forecast == 150.0
        assert fr.to_dict()["quarterly_rev_forecast"] == 40.0


class TestTickerAnalysis:
    def test_from_dict(self):
        d = {
            "annual_snapshot": {"metrics": {"Revenue": 1000, "Alerts": ["Low ROE"]}, "filing_info": {"form_type": "10-K"}},
            "quarterly_snapshot": {"metrics": {"Revenue": 250, "Alerts": []}, "filing_info": {}},
            "multiyear": {"annual_data": {}, "cagr_revenue": 5.0},
            "forecast": {"annual_rev_forecast": 1100.0},
            "extra_alerts": ["Neg FCF"],
        }
        ta = TickerAnalysis.from_dict("AAPL", d)
        assert ta.ticker == "AAPL"
        assert ta.annual_snapshot.metrics.revenue == 1000
        assert ta.annual_snapshot.metrics.alerts == ("Low ROE",)
        assert ta.quarterly_snapshot.metrics.revenue == 250
        assert ta.multiyear.cagr_revenue == 5.0
        assert ta.forecast.annual_rev_forecast == 1100.0
        assert ta.extra_alerts == ("Neg FCF",)

    def test_to_dict_round_trip(self):
        ta = TickerAnalysis(
            ticker="MSFT",
            annual_snapshot=FilingSnapshot(
                metrics=SnapshotMetrics(revenue=5000),
                filing_info=FilingInfo(form_type="10-K"),
            ),
            extra_alerts=("alert1",),
        )
        d = ta.to_dict()
        assert d["annual_snapshot"]["metrics"]["Revenue"] == 5000
        assert d["extra_alerts"] == ["alert1"]


class TestScoresResult:
    def test_from_dict_with_dataclass_objects(self):
        d = {
            "per_share": PerShareMetrics(eps_basic=2.5),
            "working_capital": WorkingCapitalCycle(dso=30.0),
            "capital_efficiency": CapitalEfficiency(roic_pct=15.0),
            "dupont": DuPontDecomposition(roe_3=12.0),
            "piotroski": PiotroskiScore(score=7),
            "altman": AltmanZScore(z_score=3.5, zone="Safe"),
        }
        sr = ScoresResult.from_dict(d)
        assert sr.per_share.eps_basic == 2.5
        assert sr.piotroski.score == 7
        assert sr.altman.zone == "Safe"
        assert sr.beneish is None

    def test_to_dict_round_trip(self):
        sr = ScoresResult(
            per_share=PerShareMetrics(eps_basic=1.0),
            dupont=DuPontDecomposition(roe_3=10.0),
        )
        d = sr.to_dict()
        assert d["per_share"]["eps_basic"] == 1.0
        assert d["dupont"]["roe_3"] == 10.0
        assert "piotroski" not in d

    def test_from_dict_none(self):
        assert ScoresResult.from_dict(None) is None
        assert ScoresResult.from_dict({}) is None

    def test_snapshot_metrics_scores_round_trip(self):
        sr = ScoresResult(per_share=PerShareMetrics(eps_basic=3.0))
        sm = SnapshotMetrics(revenue=1000, scores=sr)
        d = sm.to_dict()
        assert d["_scores"]["per_share"]["eps_basic"] == 3.0

        sm2 = SnapshotMetrics.from_dict(d)
        assert isinstance(sm2.scores, ScoresResult)

    def test_from_dict_deserializes_nested_dicts(self):
        """ScoresResult.from_dict reconstructs dataclasses from plain dicts (JSON round-trip)."""
        sr = ScoresResult(
            per_share=PerShareMetrics(eps_basic=2.0, eps_diluted=1.9),
            piotroski=PiotroskiScore(score=7, components=("ROA>0", "CFO>0")),
        )
        serialized = sr.to_dict()
        assert isinstance(serialized["per_share"], dict)

        restored = ScoresResult.from_dict(serialized)
        assert restored.per_share.eps_basic == 2.0
        assert restored.piotroski.score == 7
        assert restored.piotroski.components == ("ROA>0", "CFO>0")


class TestAnalysisResult:
    def test_main_and_peers(self):
        result = AnalysisResult(
            main_ticker="AAPL",
            tickers={
                "AAPL": TickerAnalysis(ticker="AAPL"),
                "MSFT": TickerAnalysis(ticker="MSFT"),
                "GOOGL": TickerAnalysis(ticker="GOOGL"),
            },
        )
        assert result.main.ticker == "AAPL"
        assert set(result.peers.keys()) == {"MSFT", "GOOGL"}
        assert result["MSFT"].ticker == "MSFT"

    def test_getitem_missing_raises(self):
        result = AnalysisResult(main_ticker="AAPL", tickers={"AAPL": TickerAnalysis(ticker="AAPL")})
        with pytest.raises(KeyError):
            _ = result["NOPE"]

    def test_to_json_dict_nan_becomes_none(self):
        """NaN values are converted to None for JSON-safe output."""
        import json
        result = AnalysisResult(
            main_ticker="TEST",
            tickers={"TEST": TickerAnalysis(
                ticker="TEST",
                annual_snapshot=FilingSnapshot(
                    metrics=SnapshotMetrics(revenue=1000, gross_margin_pct=float("nan")),
                ),
                market_cap=float("nan"),
            )},
        )
        d = result.to_json_dict()
        serialized = json.dumps(d)
        parsed = json.loads(serialized)
        assert parsed["tickers"]["TEST"]["annual_snapshot"]["metrics"]["Gross Margin %"] is None
        assert parsed["tickers"]["TEST"]["market_cap"] is None
        assert parsed["tickers"]["TEST"]["annual_snapshot"]["metrics"]["Revenue"] == 1000
