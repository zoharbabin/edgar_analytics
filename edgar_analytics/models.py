"""Typed data models for edgar_analytics analysis results.

All analysis results are returned as dataclasses with typed fields.
Financial ratios that are undefined (e.g. zero denominator) use ``float('nan')``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, fields as dc_fields
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING, get_type_hints

if TYPE_CHECKING:
    from .scores import (
        PerShareMetrics,
        WorkingCapitalCycle,
        CapitalEfficiency,
        DuPontDecomposition,
        PiotroskiScore,
        AltmanZScore,
        BeneishMScore,
    )

_NAN = float("nan")


def _sanitize_for_json(obj: Any) -> Any:
    """Recursively convert NaN/Inf floats to None for JSON-safe output."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(v) for v in obj]
    return obj


_METRICS_KEY_TO_FIELD = {
    "Revenue": "revenue",
    "CostOfRev": "cost_of_revenue",
    "Gross Profit": "gross_profit",
    "Gross Margin %": "gross_margin_pct",
    "OpEx": "operating_expenses",
    "Net Income": "net_income",
    "Net Margin %": "net_margin_pct",
    "Operating Margin %": "operating_margin_pct",
    "Operating Income": "operating_income",
    "EBIT (approx)": "ebit_approx",
    "EBITDA (approx)": "ebitda_approx",
    "Current Ratio": "current_ratio",
    "Debt-to-Equity": "debt_to_equity",
    "Equity Ratio %": "equity_ratio_pct",
    "Cash from Operations": "cash_from_operations",
    "Free Cash Flow": "free_cash_flow",
    "ROE %": "roe_pct",
    "ROA %": "roa_pct",
    "Intangible Ratio %": "intangible_ratio_pct",
    "Goodwill Ratio %": "goodwill_ratio_pct",
    "Tangible Equity": "tangible_equity",
    "Net Debt": "net_debt",
    "Net Debt/EBITDA": "net_debt_to_ebitda",
    "Lease Liabilities Ratio %": "lease_liabilities_ratio_pct",
    "Interest Expense": "interest_expense",
    "Income Tax Expense": "income_tax_expense",
    "EBIT (standard)": "ebit_standard",
    "EBITDA (standard)": "ebitda_standard",
    "Interest Coverage": "interest_coverage",
}
_METRICS_FIELD_TO_KEY = {v: k for k, v in _METRICS_KEY_TO_FIELD.items()}


def _reconstruct_dataclass(dc_cls: type, raw: dict) -> Any:
    """Reconstruct a dataclass from a plain dict (e.g. after JSON round-trip).

    Handles ``list`` → ``tuple`` coercion for fields typed as ``Tuple``
    (JSON serialization converts tuples to arrays).
    """
    fixed = {}
    field_types = {f.name: f.type for f in dc_fields(dc_cls)}
    for key, value in raw.items():
        if key not in field_types:
            continue
        ftype = field_types[key]
        if isinstance(value, list) and "Tuple" in str(ftype):
            fixed[key] = tuple(value)
        else:
            fixed[key] = value
    return dc_cls(**fixed)


@dataclass
class ScoresResult:
    """Typed container for all scoring model results.

    Fields are ``None`` when the corresponding score was not computed
    (e.g. Piotroski/Altman/Beneish require prior-year data).
    """

    per_share: Optional[PerShareMetrics] = None
    working_capital: Optional[WorkingCapitalCycle] = None
    capital_efficiency: Optional[CapitalEfficiency] = None
    dupont: Optional[DuPontDecomposition] = None
    piotroski: Optional[PiotroskiScore] = None
    altman: Optional[AltmanZScore] = None
    beneish: Optional[BeneishMScore] = None

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> Optional[ScoresResult]:
        if not d:
            return None
        from .scores import (
            PerShareMetrics,
            WorkingCapitalCycle,
            CapitalEfficiency,
            DuPontDecomposition,
            PiotroskiScore,
            AltmanZScore,
            BeneishMScore,
        )
        _TYPE_MAP = {
            "per_share": PerShareMetrics,
            "working_capital": WorkingCapitalCycle,
            "capital_efficiency": CapitalEfficiency,
            "dupont": DuPontDecomposition,
            "piotroski": PiotroskiScore,
            "altman": AltmanZScore,
            "beneish": BeneishMScore,
        }
        kwargs = {}
        for name, dc_cls in _TYPE_MAP.items():
            raw = d.get(name)
            if isinstance(raw, dc_cls):
                kwargs[name] = raw
            elif isinstance(raw, dict):
                kwargs[name] = _reconstruct_dataclass(dc_cls, raw)
            else:
                kwargs[name] = None
        return cls(**kwargs)

    def to_dict(self) -> dict:
        from dataclasses import asdict
        result = {}
        for name in ("per_share", "working_capital", "capital_efficiency",
                      "dupont", "piotroski", "altman", "beneish"):
            obj = getattr(self, name)
            if obj is not None:
                result[name] = asdict(obj)
        return result


@dataclass
class FilingInfo:
    """Metadata about an SEC filing."""

    form_type: str = "Unknown"
    filed_date: str = ""
    company: str = "Unknown"
    accession_no: str = "Unknown"

    @classmethod
    def from_dict(cls, d: dict) -> FilingInfo:
        return cls(
            form_type=d.get("form_type", "Unknown"),
            filed_date=d.get("filed_date", ""),
            company=d.get("company", "Unknown"),
            accession_no=d.get("accession_no", "Unknown"),
        )

    def to_dict(self) -> dict:
        return {
            "form_type": self.form_type,
            "filed_date": self.filed_date,
            "company": self.company,
            "accession_no": self.accession_no,
        }


@dataclass
class SnapshotMetrics:
    """Financial metrics computed from a single filing's financial statements."""

    revenue: float = 0.0
    cost_of_revenue: float = 0.0
    gross_profit: float = 0.0
    gross_margin_pct: float = _NAN
    operating_expenses: float = 0.0
    net_income: float = 0.0
    net_margin_pct: float = _NAN
    operating_margin_pct: float = _NAN
    operating_income: float = 0.0
    ebit_approx: float = 0.0
    ebitda_approx: float = 0.0
    current_ratio: float = _NAN
    debt_to_equity: float = _NAN
    equity_ratio_pct: float = _NAN
    cash_from_operations: float = 0.0
    free_cash_flow: float = 0.0
    roe_pct: float = _NAN
    roa_pct: float = _NAN
    intangible_ratio_pct: float = _NAN
    goodwill_ratio_pct: float = _NAN
    tangible_equity: float = 0.0
    net_debt: float = 0.0
    net_debt_to_ebitda: float = _NAN
    lease_liabilities_ratio_pct: float = _NAN
    interest_expense: float = 0.0
    income_tax_expense: float = 0.0
    ebit_standard: float = 0.0
    ebitda_standard: float = 0.0
    interest_coverage: float = _NAN
    alerts: Tuple[str, ...] = ()
    identity_check: str = ""
    scores: Optional[ScoresResult] = None

    @classmethod
    def from_dict(cls, d: dict) -> SnapshotMetrics:
        kwargs: dict = {}
        for dict_key, field_name in _METRICS_KEY_TO_FIELD.items():
            if dict_key in d:
                kwargs[field_name] = d[dict_key]
        raw_alerts = d.get("Alerts", [])
        kwargs["alerts"] = tuple(raw_alerts) if isinstance(raw_alerts, list) else raw_alerts
        kwargs["identity_check"] = d.get("_IdentityCheck", "")
        raw_scores = d.get("_scores")
        if isinstance(raw_scores, ScoresResult):
            kwargs["scores"] = raw_scores
        elif isinstance(raw_scores, dict):
            kwargs["scores"] = ScoresResult.from_dict(raw_scores)
        return cls(**kwargs)

    def to_dict(self) -> dict:
        result: dict = {}
        for field_name, dict_key in _METRICS_FIELD_TO_KEY.items():
            result[dict_key] = getattr(self, field_name)
        result["Alerts"] = list(self.alerts)
        result["_IdentityCheck"] = self.identity_check
        if self.scores is not None:
            result["_scores"] = self.scores.to_dict() if isinstance(self.scores, ScoresResult) else self.scores
        return result


@dataclass
class FilingSnapshot:
    """A single filing's metrics and metadata."""

    metrics: SnapshotMetrics = field(default_factory=SnapshotMetrics)
    filing_info: FilingInfo = field(default_factory=FilingInfo)

    @classmethod
    def from_dict(cls, d: dict) -> FilingSnapshot:
        metrics_d = d.get("metrics", {})
        filing_d = d.get("filing_info", {})
        return cls(
            metrics=SnapshotMetrics.from_dict(metrics_d) if metrics_d else SnapshotMetrics(),
            filing_info=FilingInfo.from_dict(filing_d) if filing_d else FilingInfo(),
        )

    def to_dict(self) -> dict:
        return {
            "metrics": self.metrics.to_dict(),
            "filing_info": self.filing_info.to_dict(),
        }


@dataclass
class MultiYearData:
    """Multi-year trend data including growth rates and CAGR."""

    annual_data: Dict[str, Dict[str, float]] = field(default_factory=dict)
    quarterly_data: Dict[str, Dict[str, float]] = field(default_factory=dict)
    yoy_revenue_growth: Dict[str, float] = field(default_factory=dict)
    cagr_revenue: float = 0.0
    yoy_growth: Dict[str, Dict[str, float]] = field(default_factory=dict)
    cagr: Dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> MultiYearData:
        return cls(
            annual_data=d.get("annual_data", {}),
            quarterly_data=d.get("quarterly_data", {}),
            yoy_revenue_growth=d.get("yoy_revenue_growth", {}),
            cagr_revenue=d.get("cagr_revenue", 0.0),
            yoy_growth=d.get("yoy_growth", {}),
            cagr=d.get("cagr", {}),
        )

    def to_dict(self) -> dict:
        return {
            "annual_data": self.annual_data,
            "quarterly_data": self.quarterly_data,
            "yoy_revenue_growth": self.yoy_revenue_growth,
            "cagr_revenue": self.cagr_revenue,
            "yoy_growth": self.yoy_growth,
            "cagr": self.cagr,
        }


@dataclass
class ForecastResult:
    """Revenue forecast results."""

    annual_rev_forecast: float = 0.0
    quarterly_rev_forecast: float = 0.0

    @classmethod
    def from_dict(cls, d: dict) -> ForecastResult:
        return cls(
            annual_rev_forecast=d.get("annual_rev_forecast", 0.0),
            quarterly_rev_forecast=d.get("quarterly_rev_forecast", 0.0),
        )

    def to_dict(self) -> dict:
        return {
            "annual_rev_forecast": self.annual_rev_forecast,
            "quarterly_rev_forecast": self.quarterly_rev_forecast,
        }


@dataclass
class TickerAnalysis:
    """Complete analysis for a single ticker."""

    ticker: str = ""
    annual_snapshot: FilingSnapshot = field(default_factory=FilingSnapshot)
    quarterly_snapshot: FilingSnapshot = field(default_factory=FilingSnapshot)
    multiyear: MultiYearData = field(default_factory=MultiYearData)
    forecast: ForecastResult = field(default_factory=ForecastResult)
    extra_alerts: Tuple[str, ...] = ()
    market_cap: float = _NAN

    @classmethod
    def from_dict(cls, ticker: str, d: dict) -> TickerAnalysis:
        return cls(
            ticker=ticker,
            annual_snapshot=FilingSnapshot.from_dict(d.get("annual_snapshot", {})),
            quarterly_snapshot=FilingSnapshot.from_dict(d.get("quarterly_snapshot", {})),
            multiyear=MultiYearData.from_dict(d.get("multiyear", {})),
            forecast=ForecastResult.from_dict(d.get("forecast", {})),
            extra_alerts=tuple(d.get("extra_alerts", [])),
            market_cap=d.get("market_cap", _NAN),
        )

    def to_dict(self) -> dict:
        return {
            "annual_snapshot": self.annual_snapshot.to_dict(),
            "quarterly_snapshot": self.quarterly_snapshot.to_dict(),
            "multiyear": self.multiyear.to_dict(),
            "forecast": self.forecast.to_dict(),
            "extra_alerts": list(self.extra_alerts),
            "market_cap": self.market_cap,
        }


@dataclass
class AnalysisResult:
    """Top-level result from ``analyze()``, containing data for all tickers."""

    main_ticker: str = ""
    tickers: Dict[str, TickerAnalysis] = field(default_factory=dict)

    def __getitem__(self, ticker: str) -> TickerAnalysis:
        return self.tickers[ticker]

    @property
    def main(self) -> TickerAnalysis:
        """The primary ticker's analysis."""
        return self.tickers[self.main_ticker]

    @property
    def peers(self) -> Dict[str, TickerAnalysis]:
        """Peer tickers' analyses (excluding main)."""
        return {k: v for k, v in self.tickers.items() if k != self.main_ticker}

    def to_json_dict(self) -> dict:
        """Serialize to a JSON-safe dict (NaN/Inf → ``None``)."""
        raw = {
            "main_ticker": self.main_ticker,
            "tickers": {t: ta.to_dict() for t, ta in self.tickers.items()},
        }
        return _sanitize_for_json(raw)
