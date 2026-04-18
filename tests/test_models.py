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


class TestMultiYearDataTTM:
    def test_ttm_field_round_trip(self):
        d = {
            "annual_data": {"Revenue": {"2022": 100}},
            "quarterly_data": {},
            "ttm": {"Revenue": 400, "Net Income": 80},
        }
        my = MultiYearData.from_dict(d)
        assert my.ttm["Revenue"] == 400
        assert my.ttm["Net Income"] == 80
        rt = my.to_dict()
        assert rt["ttm"] == {"Revenue": 400, "Net Income": 80}

    def test_ttm_default_empty(self):
        my = MultiYearData()
        assert my.ttm == {}


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

    def test_to_dataframe(self):
        result = AnalysisResult(
            main_ticker="AAPL",
            tickers={
                "AAPL": TickerAnalysis(
                    ticker="AAPL",
                    annual_snapshot=FilingSnapshot(
                        metrics=SnapshotMetrics(revenue=1000, net_income=200),
                    ),
                ),
                "MSFT": TickerAnalysis(
                    ticker="MSFT",
                    annual_snapshot=FilingSnapshot(
                        metrics=SnapshotMetrics(revenue=5000, net_income=1500),
                    ),
                ),
            },
        )
        import pandas as pd
        df = result.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert set(df.index) == {"AAPL", "MSFT"}
        assert df.loc["AAPL", "Revenue"] == 1000
        assert df.loc["MSFT", "Net Income"] == 1500
        assert "Alerts" not in df.columns

    def test_to_panel(self):
        result = AnalysisResult(
            main_ticker="AAPL",
            tickers={
                "AAPL": TickerAnalysis(
                    ticker="AAPL",
                    multiyear=MultiYearData(
                        annual_data={"Revenue": {"2022": 100, "2023": 120}},
                    ),
                ),
            },
        )
        import pandas as pd
        panel = result.to_panel()
        assert isinstance(panel, pd.DataFrame)
        assert ("AAPL", "2023") in panel.index
        assert panel.loc[("AAPL", "2023"), "Revenue"] == 120

    def test_to_panel_empty(self):
        result = AnalysisResult(main_ticker="X", tickers={"X": TickerAnalysis(ticker="X")})
        import pandas as pd
        panel = result.to_panel()
        assert isinstance(panel, pd.DataFrame)
        assert panel.empty

    def test_to_panel_quarterly(self):
        result = AnalysisResult(
            main_ticker="AAPL",
            tickers={
                "AAPL": TickerAnalysis(
                    ticker="AAPL",
                    multiyear=MultiYearData(
                        quarterly_data={"Revenue": {"2023-Q1": 90, "2023-Q2": 95}},
                    ),
                ),
            },
        )
        import pandas as pd
        panel = result.to_panel(frequency="quarterly")
        assert isinstance(panel, pd.DataFrame)
        assert ("AAPL", "2023-Q2") in panel.index
        assert panel.loc[("AAPL", "2023-Q2"), "Revenue"] == 95

    def test_to_panel_default_is_annual(self):
        result = AnalysisResult(
            main_ticker="AAPL",
            tickers={
                "AAPL": TickerAnalysis(
                    ticker="AAPL",
                    multiyear=MultiYearData(
                        annual_data={"Revenue": {"2022": 100}},
                        quarterly_data={"Revenue": {"2023-Q1": 25}},
                    ),
                ),
            },
        )
        panel = result.to_panel()
        assert ("AAPL", "2022") in panel.index

    def test_to_parquet(self, tmp_path):
        result = AnalysisResult(
            main_ticker="AAPL",
            tickers={
                "AAPL": TickerAnalysis(
                    ticker="AAPL",
                    annual_snapshot=FilingSnapshot(
                        metrics=SnapshotMetrics(revenue=1000),
                    ),
                ),
            },
        )
        path = str(tmp_path / "test.parquet")
        result.to_parquet(path)
        import pandas as pd
        df = pd.read_parquet(path)
        assert df.loc["AAPL", "Revenue"] == 1000

    def test_to_parquet_writes_panel_file(self, tmp_path):
        result = AnalysisResult(
            main_ticker="AAPL",
            tickers={
                "AAPL": TickerAnalysis(
                    ticker="AAPL",
                    annual_snapshot=FilingSnapshot(metrics=SnapshotMetrics(revenue=500)),
                    multiyear=MultiYearData(
                        annual_data={"Revenue": {"2022": 400, "2023": 500}},
                    ),
                ),
            },
        )
        path = str(tmp_path / "out.parquet")
        result.to_parquet(path)
        panel_path = tmp_path / "out_panel.parquet"
        assert panel_path.exists()
        import pandas as pd
        panel = pd.read_parquet(panel_path)
        assert ("AAPL", "2023") in panel.index

    def test_to_parquet_writes_scores_file(self, tmp_path):
        scores = ScoresResult(
            altman=AltmanZScore(z_score=3.5, zone="Safe", model="Z (manufacturing)"),
            dupont=DuPontDecomposition(roe_3=15.0, roe_5=14.5),
        )
        result = AnalysisResult(
            main_ticker="AAPL",
            tickers={
                "AAPL": TickerAnalysis(
                    ticker="AAPL",
                    annual_snapshot=FilingSnapshot(
                        metrics=SnapshotMetrics(revenue=1000, scores=scores),
                    ),
                ),
            },
        )
        path = str(tmp_path / "out.parquet")
        result.to_parquet(path)
        scores_path = tmp_path / "out_scores.parquet"
        assert scores_path.exists()
        import pandas as pd
        df = pd.read_parquet(scores_path)
        assert df.loc["AAPL", "altman_z"] == pytest.approx(3.5)

    def test_is_financial_round_trip(self):
        m = SnapshotMetrics.from_dict({"Revenue": 1000, "_is_financial": True})
        assert m.is_financial is True
        d = m.to_dict()
        assert d["_is_financial"] is True

    def test_valuation_round_trip(self):
        from edgar_analytics.market_data import ValuationRatios
        v = ValuationRatios(pe_ratio=25.0, pb_ratio=8.0)
        m = SnapshotMetrics.from_dict({"Revenue": 1000, "_valuation": v})
        assert m.valuation.pe_ratio == 25.0
        d = m.to_dict()
        assert d["_valuation"]["pe_ratio"] == 25.0
