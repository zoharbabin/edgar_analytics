"""Financial scoring models, per-share metrics, and derived analytics.

Contains:
- Per-share metrics (EPS, BV/share, FCF/share)
- Working capital cycle (DSO, DIO, DPO, CCC)
- ROIC, asset turnover, invested capital
- DuPont decomposition (3-component and 5-component)
- TTM (Trailing Twelve Months) revenue/income stitching
- Piotroski F-Score
- Altman Z-Score
- Beneish M-Score
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from .data_utils import parse_period_label
from .logging_utils import get_logger
from .synonyms import SYNONYMS
from .synonyms_utils import find_synonym_value

logger = get_logger(__name__)

_NAN = float("nan")


# ---------------------------------------------------------------------------
# Per-share metrics (#6)
# ---------------------------------------------------------------------------

@dataclass
class PerShareMetrics:
    eps_basic: float = _NAN
    eps_diluted: float = _NAN
    book_value_per_share: float = _NAN
    fcf_per_share: float = _NAN

    @classmethod
    def compute(
        cls,
        income_df: pd.DataFrame,
        balance_df: pd.DataFrame,
        net_income: float,
        total_equity: float,
        free_cash_flow: float,
    ) -> PerShareMetrics:
        eps_b = find_synonym_value(income_df, SYNONYMS["earnings_per_share_basic"], _NAN, "EPS-Basic")
        eps_d = find_synonym_value(income_df, SYNONYMS["earnings_per_share_diluted"], _NAN, "EPS-Diluted")
        shares = find_synonym_value(balance_df, SYNONYMS["common_shares_outstanding"], 0.0, "Shares")

        bv_ps = (total_equity / shares) if shares > 0 else _NAN
        fcf_ps = (free_cash_flow / shares) if shares > 0 else _NAN

        if pd.isna(eps_b) and shares > 0:
            eps_b = net_income / shares
        if pd.isna(eps_d):
            eps_d = _NAN

        return cls(eps_basic=eps_b, eps_diluted=eps_d, book_value_per_share=bv_ps, fcf_per_share=fcf_ps)


# ---------------------------------------------------------------------------
# Working capital cycle (#7)
# ---------------------------------------------------------------------------

@dataclass
class WorkingCapitalCycle:
    dso: float = _NAN
    dio: float = _NAN
    dpo: float = _NAN
    cash_conversion_cycle: float = _NAN

    @classmethod
    def compute(
        cls,
        revenue: float,
        cost_of_revenue: float,
        accounts_receivable: float,
        inventory: float,
        accounts_payable: float,
    ) -> WorkingCapitalCycle:
        daily_rev = revenue / 365.0 if revenue > 0 else 0.0
        daily_cogs = cost_of_revenue / 365.0 if cost_of_revenue > 0 else 0.0

        dso = (accounts_receivable / daily_rev) if daily_rev > 0 else _NAN
        dio = (inventory / daily_cogs) if daily_cogs > 0 else _NAN
        dpo = (accounts_payable / daily_cogs) if daily_cogs > 0 else _NAN

        if pd.notna(dso) and pd.notna(dio) and pd.notna(dpo):
            ccc = dso + dio - dpo
        else:
            ccc = _NAN

        return cls(dso=dso, dio=dio, dpo=dpo, cash_conversion_cycle=ccc)


# ---------------------------------------------------------------------------
# TTM computation (#8)
# ---------------------------------------------------------------------------

_STOCK_METRICS = frozenset({
    "Total Assets", "Total Equity", "Total Liabilities",
    "Current Assets", "Current Liabilities",
    "Short-term Debt", "Long-term Debt",
    "Debt-to-Equity", "ROE %", "ROA %",
})


def compute_ttm(quarterly_data: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    """Compute trailing twelve months values from quarterly data.

    Flow metrics (Revenue, Net Income, etc.) are summed across the last 4
    quarters.  Stock metrics (Total Assets, Total Equity, etc.) use the
    most recent quarter's value, since summing point-in-time balances is
    nonsensical.

    Args:
        quarterly_data: {metric_name: {period_label: value, ...}, ...}

    Returns:
        {metric_name: ttm_value} for metrics with >= 4 quarters of data
        (flow) or >= 1 quarter (stock).
    """
    ttm = {}
    for metric, periods in quarterly_data.items():
        sorted_periods = sorted(periods.keys(), key=parse_period_label, reverse=True)

        if metric in _STOCK_METRICS:
            if sorted_periods:
                ttm[metric] = periods[sorted_periods[0]]
        else:
            if len(periods) < 4:
                continue
            last_4 = sorted_periods[:4]
            ttm[metric] = sum(periods[p] for p in last_4)
    return ttm


# ---------------------------------------------------------------------------
# ROIC, invested capital, asset turnover (#9)
# ---------------------------------------------------------------------------

@dataclass
class CapitalEfficiency:
    invested_capital: float = _NAN
    roic_pct: float = _NAN
    asset_turnover: float = _NAN
    nopat: float = _NAN

    @classmethod
    def compute(
        cls,
        operating_income: float,
        income_tax_expense: float,
        income_before_taxes: float,
        revenue: float,
        total_assets: float,
        total_equity: float,
        short_term_debt: float,
        long_term_debt: float,
        cash_equiv: float,
    ) -> CapitalEfficiency:
        effective_tax_rate = 0.0
        if pd.notna(income_before_taxes) and income_before_taxes != 0:
            effective_tax_rate = income_tax_expense / income_before_taxes
            effective_tax_rate = max(0.0, min(effective_tax_rate, 1.0))

        nopat = operating_income * (1 - effective_tax_rate)
        invested_capital = total_equity + short_term_debt + long_term_debt - cash_equiv

        if invested_capital <= 0:
            roic = _NAN
        else:
            roic = nopat / invested_capital * 100.0
        asset_turnover = (revenue / total_assets) if total_assets > 0 else _NAN

        return cls(
            invested_capital=invested_capital,
            roic_pct=roic,
            asset_turnover=asset_turnover,
            nopat=nopat,
        )


# ---------------------------------------------------------------------------
# DuPont decomposition (#10)
# ---------------------------------------------------------------------------

@dataclass
class DuPontDecomposition:
    # 3-component
    net_profit_margin: float = _NAN
    asset_turnover: float = _NAN
    equity_multiplier: float = _NAN
    roe_3: float = _NAN

    # 5-component
    tax_burden: float = _NAN
    interest_burden: float = _NAN
    operating_margin: float = _NAN
    roe_5: float = _NAN

    negative_equity_warning: bool = False

    @classmethod
    def compute(
        cls,
        net_income: float,
        revenue: float,
        total_assets: float,
        total_equity: float,
        ebit: float,
        income_before_taxes: float,
    ) -> DuPontDecomposition:
        neg_eq = total_equity < 0

        npm = (net_income / revenue) if revenue else _NAN
        at = (revenue / total_assets) if total_assets else _NAN
        em = (total_assets / total_equity) if total_equity != 0 else _NAN

        if neg_eq:
            roe_3 = _NAN
        elif pd.notna(npm) and pd.notna(at) and pd.notna(em):
            roe_3 = npm * at * em * 100.0
        else:
            roe_3 = _NAN

        tax_burden = (net_income / income_before_taxes) if income_before_taxes else _NAN
        interest_burden = (income_before_taxes / ebit) if ebit else _NAN
        op_margin = (ebit / revenue) if revenue else _NAN

        if neg_eq:
            roe_5 = _NAN
        elif all(pd.notna(x) for x in [tax_burden, interest_burden, op_margin, at, em]):
            roe_5 = tax_burden * interest_burden * op_margin * at * em * 100.0
        else:
            roe_5 = _NAN

        return cls(
            net_profit_margin=npm,
            asset_turnover=at,
            equity_multiplier=em,
            roe_3=roe_3,
            tax_burden=tax_burden,
            interest_burden=interest_burden,
            operating_margin=op_margin,
            roe_5=roe_5,
            negative_equity_warning=neg_eq,
        )


# ---------------------------------------------------------------------------
# Piotroski F-Score (#11)
# ---------------------------------------------------------------------------

@dataclass
class PiotroskiScore:
    score: int = 0
    components: Tuple[str, ...] = ()

    @classmethod
    def compute(
        cls,
        net_income: float,
        total_assets: float,
        total_assets_prev: float,
        operating_cf: float,
        roa: float,
        roa_prev: float,
        long_term_debt: float,
        long_term_debt_prev: float,
        current_ratio: float,
        current_ratio_prev: float,
        shares_outstanding: float,
        shares_outstanding_prev: float,
        gross_margin: float,
        gross_margin_prev: float,
        asset_turnover: float,
        asset_turnover_prev: float,
    ) -> PiotroskiScore:
        checks = []

        # Profitability (4 points)
        if roa > 0:
            checks.append("ROA>0")
        if operating_cf > 0:
            checks.append("CFO>0")
        if pd.notna(roa_prev) and roa > roa_prev:
            checks.append("ROA_increasing")
        if operating_cf > net_income:
            checks.append("Accruals(CFO>NI)")

        # Leverage/Liquidity (3 points)
        if pd.notna(long_term_debt_prev) and long_term_debt < long_term_debt_prev:
            checks.append("LTD_decreasing")
        if pd.notna(current_ratio_prev) and current_ratio > current_ratio_prev:
            checks.append("CR_increasing")
        if pd.notna(shares_outstanding_prev) and shares_outstanding <= shares_outstanding_prev:
            checks.append("No_dilution")

        # Operating efficiency (2 points)
        if pd.notna(gross_margin_prev) and gross_margin > gross_margin_prev:
            checks.append("GM_increasing")
        if pd.notna(asset_turnover_prev) and asset_turnover > asset_turnover_prev:
            checks.append("AT_increasing")

        return cls(score=len(checks), components=tuple(checks))


# ---------------------------------------------------------------------------
# Altman Z-Score (#12) — needs market cap from yfinance
# ---------------------------------------------------------------------------

@dataclass
class AltmanZScore:
    z_score: float = _NAN
    zone: str = ""
    model: str = ""
    components: Dict[str, float] = field(default_factory=dict)

    @classmethod
    def compute(
        cls,
        working_capital: float,
        retained_earnings: float,
        ebit: float,
        market_cap: float,
        total_liabilities: float,
        revenue: float,
        total_assets: float,
        book_value_equity: float = _NAN,
        is_manufacturing: Optional[bool] = None,
    ) -> AltmanZScore:
        if total_assets <= 0:
            return cls()

        a = working_capital / total_assets
        b = retained_earnings / total_assets
        c = ebit / total_assets

        if is_manufacturing is None:
            is_manufacturing = revenue / total_assets > 0.5 if total_assets > 0 else True

        if is_manufacturing and not pd.isna(market_cap) and total_liabilities > 0:
            d = market_cap / total_liabilities
            e = revenue / total_assets
            z = 1.2 * a + 1.4 * b + 3.3 * c + 0.6 * d + 1.0 * e
            model = "Z (manufacturing)"
            if z > 2.99:
                zone = "Safe"
            elif z > 1.81:
                zone = "Grey"
            else:
                zone = "Distress"
            return cls(z_score=z, zone=zone, model=model,
                       components={"A": a, "B": b, "C": c, "D": d, "E": e})

        bve = book_value_equity if pd.notna(book_value_equity) else _NAN
        if pd.isna(bve) or total_liabilities <= 0:
            d_prime = (market_cap / total_liabilities) if (
                not pd.isna(market_cap) and total_liabilities > 0
            ) else _NAN
            if pd.isna(d_prime):
                return cls(components={"A": a, "B": b, "C": c, "D": _NAN})

            z = 1.2 * a + 1.4 * b + 3.3 * c + 0.6 * d_prime
            model = "Z' (partial)"
        else:
            d_prime = bve / total_liabilities
            z = 6.56 * a + 3.26 * b + 6.72 * c + 1.05 * d_prime
            model = "Z'' (non-manufacturing)"

        if "non-manufacturing" in model:
            if z > 2.60:
                zone = "Safe"
            elif z > 1.10:
                zone = "Grey"
            else:
                zone = "Distress"
        else:
            if z > 2.99:
                zone = "Safe"
            elif z > 1.81:
                zone = "Grey"
            else:
                zone = "Distress"

        return cls(z_score=z, zone=zone, model=model,
                   components={"A": a, "B": b, "C": c, "D'": d_prime})


# ---------------------------------------------------------------------------
# Beneish M-Score (#14) — earnings manipulation detection
# ---------------------------------------------------------------------------

@dataclass
class BeneishMScore:
    m_score: float = _NAN
    likely_manipulator: bool = False
    indices: Dict[str, float] = field(default_factory=dict)

    @classmethod
    def compute(
        cls,
        revenue: float, revenue_prev: float,
        receivables: float, receivables_prev: float,
        gross_margin_pct: float, gross_margin_pct_prev: float,
        total_assets: float, total_assets_prev: float,
        current_assets: float, current_assets_prev: float,
        current_liabilities: float, current_liabilities_prev: float,
        long_term_debt: float, long_term_debt_prev: float,
        depreciation_rate: float, depreciation_rate_prev: float,
        sga_pct: float, sga_pct_prev: float,
        operating_cf: float,
        net_income: float,
        ppe: float, ppe_prev: float,
        securities: float = 0.0, securities_prev: float = 0.0,
    ) -> BeneishMScore:
        if revenue_prev <= 0 or total_assets_prev <= 0:
            return cls()

        rev_growth = revenue / revenue_prev

        # DSRI — Days Sales in Receivables Index
        recv_rev = (receivables / revenue) if revenue else 0
        recv_rev_prev = (receivables_prev / revenue_prev) if revenue_prev else 0
        dsri = (recv_rev / recv_rev_prev) if recv_rev_prev else 1.0

        # GMI — Gross Margin Index
        gm = gross_margin_pct / 100.0
        gm_prev = gross_margin_pct_prev / 100.0
        if gm > 0:
            gmi = gm_prev / gm
        elif gm_prev > 0:
            gmi = gm_prev / 0.001
        else:
            gmi = 1.0

        # AQI — Asset Quality Index: proportion of non-hard assets
        # Per Beneish (1999): hard assets = (Current Assets + PP&E + Securities) / TA
        hard_assets = 1 - ((current_assets + ppe + securities) / total_assets) if total_assets else 0
        hard_assets_prev = 1 - ((current_assets_prev + ppe_prev + securities_prev) / total_assets_prev) if total_assets_prev else 0
        aqi = (hard_assets / hard_assets_prev) if hard_assets_prev else 1.0

        # SGI — Sales Growth Index
        sgi = rev_growth

        # DEPI — Depreciation Index
        depi = (depreciation_rate_prev / depreciation_rate) if depreciation_rate else 1.0

        # SGAI — SGA Expense Index
        sgai = (sga_pct / sga_pct_prev) if sga_pct_prev else 1.0

        # LVGI — Leverage Index: (CL + LTD) / TA ratio, current vs prior
        leverage_t = (current_liabilities + long_term_debt) / total_assets if total_assets else 0
        leverage_prev = (current_liabilities_prev + long_term_debt_prev) / total_assets_prev if total_assets_prev else 0
        lvgi = (leverage_t / leverage_prev) if leverage_prev else 1.0

        # TATA — Total Accruals to Total Assets
        tata = ((net_income - operating_cf) / total_assets) if total_assets else 0

        m = (
            -4.84
            + 0.920 * dsri
            + 0.528 * gmi
            + 0.404 * aqi
            + 0.892 * sgi
            + 0.115 * depi
            - 0.172 * sgai
            + 4.679 * tata
            - 0.327 * lvgi
        )

        return cls(
            m_score=m,
            likely_manipulator=m > -1.78,
            indices={
                "DSRI": dsri, "GMI": gmi, "AQI": aqi, "SGI": sgi,
                "DEPI": depi, "SGAI": sgai, "LVGI": lvgi, "TATA": tata,
            },
        )


# ---------------------------------------------------------------------------
# DQC negative-sign checks (#15)
# ---------------------------------------------------------------------------

def compute_all_scores(
    metrics: dict,
    balance_df: pd.DataFrame,
    income_df: pd.DataFrame,
    cash_df: pd.DataFrame,
    market_cap: float = _NAN,
    prior_metrics: Optional[dict] = None,
) -> dict:
    """Compute all scoring models from a metrics dict and raw DataFrames.

    Returns a dict with keys: ``per_share``, ``working_capital``,
    ``capital_efficiency``, ``dupont``.  When *prior_metrics* (a metrics dict
    from the previous annual period) is supplied, also computes ``piotroski``,
    ``altman``, and ``beneish``.

    The function reads balance-sheet values from the underscore-prefixed
    internal keys that :func:`compute_ratios_and_metrics` stores on the
    metrics dict, falling back to DataFrame lookups only for per-share EPS.
    """
    revenue = metrics.get("Revenue", 0.0)
    net_income = metrics.get("Net Income", 0.0)
    cost_rev = metrics.get("CostOfRev", 0.0)
    free_cf = metrics.get("Free Cash Flow", 0.0)
    op_cf = metrics.get("Cash from Operations", 0.0)
    operating_income = metrics.get("Operating Income", metrics.get("EBIT (approx)", 0.0))
    income_tax = metrics.get("Income Tax Expense", 0.0)
    ebit_std = metrics.get("EBIT (standard)", 0.0)
    gross_margin_pct = metrics.get("Gross Margin %", _NAN)

    total_assets = metrics.get("_total_assets", 0.0)
    total_liabs = metrics.get("_total_liabilities", 0.0)
    total_equity = metrics.get("_total_equity", 0.0)
    curr_assets = metrics.get("_current_assets", 0.0)
    curr_liabs = metrics.get("_current_liabilities", 0.0)
    short_debt = metrics.get("_short_term_debt", 0.0)
    long_debt = metrics.get("_long_term_debt", 0.0)
    cash_equiv = metrics.get("_cash_equivalents", 0.0)
    receivables = metrics.get("_accounts_receivable", 0.0)
    inventory = metrics.get("_inventory", 0.0)
    accounts_payable = metrics.get("_accounts_payable", 0.0)
    retained = metrics.get("_retained_earnings", 0.0)
    ppe = metrics.get("_ppe_net", 0.0)
    shares_out = metrics.get("_shares_outstanding", 0.0)
    dep_amort = metrics.get("_dep_amort", 0.0)
    sga = metrics.get("_sga", 0.0)
    income_before_taxes = metrics.get("_income_before_taxes", _NAN)
    if pd.isna(income_before_taxes):
        income_before_taxes = net_income + income_tax

    per_share = PerShareMetrics.compute(
        income_df, balance_df, net_income, total_equity, free_cf,
    )
    working_capital = WorkingCapitalCycle.compute(
        revenue, cost_rev, receivables, inventory, accounts_payable,
    )
    capital_eff = CapitalEfficiency.compute(
        operating_income, income_tax, income_before_taxes,
        revenue, total_assets, total_equity, short_debt, long_debt, cash_equiv,
    )
    dupont = DuPontDecomposition.compute(
        net_income, revenue, total_assets, total_equity,
        ebit_std, income_before_taxes,
    )

    result: dict = {
        "per_share": per_share,
        "working_capital": working_capital,
        "capital_efficiency": capital_eff,
        "dupont": dupont,
    }

    # --- Altman Z-Score: single-period model, no prior data needed ---
    working_capital_val = curr_assets - curr_liabs
    result["altman"] = AltmanZScore.compute(
        working_capital=working_capital_val,
        retained_earnings=retained,
        ebit=ebit_std,
        market_cap=market_cap,
        total_liabilities=total_liabs,
        revenue=revenue,
        total_assets=total_assets,
        book_value_equity=total_equity,
    )

    # --- Scores that require prior-period data ---
    if prior_metrics:
        p = prior_metrics
        p_revenue = p.get("Revenue", 0.0)
        p_total_assets = p.get("_total_assets", 0.0)
        p_long_debt = p.get("_long_term_debt", 0.0)
        p_shares = p.get("_shares_outstanding", 0.0)
        p_roa = p.get("ROA %", _NAN)
        p_curr_ratio = p.get("Current Ratio", _NAN)
        p_gross_margin = p.get("Gross Margin %", _NAN)
        p_receivables = p.get("_accounts_receivable", 0.0)
        p_ppe = p.get("_ppe_net", 0.0)
        p_curr_liabs = p.get("_current_liabilities", 0.0)

        roa = metrics.get("ROA %", _NAN)
        current_ratio = metrics.get("Current Ratio", _NAN)
        asset_turn = capital_eff.asset_turnover if pd.notna(capital_eff.asset_turnover) else _NAN
        p_asset_turn = (p_revenue / p_total_assets) if p_total_assets > 0 else _NAN

        result["piotroski"] = PiotroskiScore.compute(
            net_income=net_income,
            total_assets=total_assets,
            total_assets_prev=p_total_assets,
            operating_cf=op_cf,
            roa=roa,
            roa_prev=p_roa,
            long_term_debt=long_debt,
            long_term_debt_prev=p_long_debt,
            current_ratio=current_ratio,
            current_ratio_prev=p_curr_ratio,
            shares_outstanding=shares_out,
            shares_outstanding_prev=p_shares,
            gross_margin=gross_margin_pct if pd.notna(gross_margin_pct) else _NAN,
            gross_margin_prev=p_gross_margin if pd.notna(p_gross_margin) else _NAN,
            asset_turnover=asset_turn,
            asset_turnover_prev=p_asset_turn,
        )

        dep_rate = (dep_amort / (dep_amort + ppe)) if (dep_amort + ppe) > 0 else 0.0
        p_dep_amort = p.get("_dep_amort", 0.0)
        p_dep_rate = (p_dep_amort / (p_dep_amort + p_ppe)) if (p_dep_amort + p_ppe) > 0 else 0.0
        sga_pct = (sga / revenue) if revenue > 0 else 0.0
        p_sga = p.get("_sga", 0.0)
        p_sga_pct = (p_sga / p_revenue) if p_revenue > 0 else 0.0
        p_gross_margin_pct = p.get("Gross Margin %", _NAN)
        st_investments = metrics.get("_short_term_investments", 0.0)
        p_st_investments = p.get("_short_term_investments", 0.0)
        p_curr_assets = p.get("_current_assets", 0.0)

        result["beneish"] = BeneishMScore.compute(
            revenue=revenue,
            revenue_prev=p_revenue,
            receivables=receivables,
            receivables_prev=p_receivables,
            gross_margin_pct=gross_margin_pct if pd.notna(gross_margin_pct) else 0.0,
            gross_margin_pct_prev=p_gross_margin_pct if pd.notna(p_gross_margin_pct) else 0.0,
            total_assets=total_assets,
            total_assets_prev=p_total_assets,
            current_assets=curr_assets,
            current_assets_prev=p_curr_assets,
            current_liabilities=curr_liabs,
            current_liabilities_prev=p_curr_liabs,
            long_term_debt=long_debt,
            long_term_debt_prev=p_long_debt,
            depreciation_rate=dep_rate,
            depreciation_rate_prev=p_dep_rate,
            sga_pct=sga_pct,
            sga_pct_prev=p_sga_pct,
            operating_cf=op_cf,
            net_income=net_income,
            ppe=ppe,
            ppe_prev=p_ppe,
            securities=st_investments,
            securities_prev=p_st_investments,
        )

    return result


DQC_MUST_BE_NONNEGATIVE = frozenset({
    "Revenue", "Revenues", "Net sales",
    "Total assets", "Total current assets",
    "Cash and cash equivalents",
    "Accounts receivable", "Accounts receivable, net",
    "Inventory", "Inventories",
    "Goodwill", "Intangible assets",
    "Property, plant and equipment, net",
    "Total liabilities", "Total current liabilities",
    "Long-term debt", "Short-term debt",
    "Shares outstanding",
    "Operating lease liabilities",
    "us-gaap:Assets", "us-gaap:AssetsCurrent",
    "us-gaap:Liabilities", "us-gaap:LiabilitiesCurrent",
    "us-gaap:CashAndCashEquivalentsAtCarryingValue",
    "us-gaap:Goodwill",
    "us-gaap:PropertyPlantAndEquipmentNet",
    "us-gaap:InventoryNet",
    "us-gaap:AccountsReceivableNetCurrent",
    "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
    "us-gaap:Revenues",
})


def run_dqc_checks(df: pd.DataFrame, debug_label: str = "DQC") -> list[str]:
    """Check for negative values on line items that should never be negative.

    Returns a list of warning strings for any violations found."""
    if df.empty:
        return []

    warnings = []
    idx_lower_map = {str(label).lower().strip(): str(label) for label in df.index}

    for concept in DQC_MUST_BE_NONNEGATIVE:
        concept_lower = concept.lower().strip()
        original_label = idx_lower_map.get(concept_lower)
        if original_label is None:
            continue
        row = df.loc[original_label]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        for col in row.index:
            val = row[col]
            if pd.notna(val) and val < 0:
                warnings.append(
                    f"DQC: {original_label} is negative ({val:,.0f}) in period {col}"
                )
                break

    return warnings
