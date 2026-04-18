"""
multi_period_analysis.py

Retrieves multi-year or multi-quarter data, computing growth rates (YoY, QoQ),
CAGR, negative FCF streaks, inventory/receivables spikes, etc.
"""

import numpy as np
import pandas as pd

from edgar import Company, MultiFinancials
from .logging_utils import get_logger
from .data_utils import parse_period_label, ensure_dataframe, make_numeric_df
from .synonyms_utils import find_best_synonym_row, compute_capex_for_column
from .metrics import _get_financial_statement, ANNUAL_FORM_TYPES, QUARTERLY_FORM_TYPES

logger = get_logger(__name__)


def retrieve_multi_year_data(ticker: str, n_years=3, n_quarters=10, comp=None) -> dict:
    """
    Retrieve up to n_years of 10-K and n_quarters of 10-Q statements,
    building annual and quarterly data for multi-year analysis (growth, CAGR, etc.).

    :param comp: Optional pre-constructed ``Company`` object to avoid a
        redundant SEC API call.
    """
    logger.info("Retrieving multi-year data for %s: last %d annual, %d 10-Q", ticker, n_years, n_quarters)
    if comp is None:
        comp = Company(ticker)

    annual_inc_df = pd.DataFrame()
    quarterly_inc_df = pd.DataFrame()

    for form_type in ANNUAL_FORM_TYPES:
        try:
            filings = comp.get_filings(form=form_type, is_xbrl=True).head(n_years)
            multi = MultiFinancials(filings)
            inc = _get_financial_statement(multi, "income_statement")
            if inc is not None:
                annual_inc_df = make_numeric_df(ensure_dataframe(inc, f"{ticker}-multi{form_type}-INC"), f"{ticker}-multi{form_type}-INC")
                logger.info("%s: Found multi-year income statements via %s", ticker, form_type)
                break
        except Exception as e:
            logger.debug("No multi %s for %s: %s", form_type, ticker, e)
    else:
        logger.warning("%s: No annual income statements found (tried %s)", ticker, ", ".join(ANNUAL_FORM_TYPES))

    for qtr_form in QUARTERLY_FORM_TYPES:
        try:
            filings_10q = comp.get_filings(form=qtr_form, is_xbrl=True).head(n_quarters)
            multi_10q = MultiFinancials(filings_10q)
            inc_10q = _get_financial_statement(multi_10q, "income_statement")
            if inc_10q is not None:
                quarterly_inc_df = make_numeric_df(ensure_dataframe(inc_10q, f"{ticker}-multi{qtr_form}-INC"), f"{ticker}-multi{qtr_form}-INC")
                logger.info("%s: Found multi-quarter income statements via %s", ticker, qtr_form)
                break
        except Exception as e:
            logger.debug("No multi %s for %s: %s", qtr_form, ticker, e)
    else:
        logger.warning("%s: No quarterly income statements found (tried %s)", ticker, ", ".join(QUARTERLY_FORM_TYPES))

    annual_bs_df = pd.DataFrame()
    annual_cf_df = pd.DataFrame()
    for form_type in ANNUAL_FORM_TYPES:
        try:
            filings = comp.get_filings(form=form_type, is_xbrl=True).head(n_years)
            multi = MultiFinancials(filings)
            bs = _get_financial_statement(multi, "balance_sheet")
            cf = _get_financial_statement(multi, "cash_flow_statement")
            if bs is not None:
                annual_bs_df = make_numeric_df(ensure_dataframe(bs, f"{ticker}-multi{form_type}-BS"), f"{ticker}-multi{form_type}-BS")
            if cf is not None:
                annual_cf_df = make_numeric_df(ensure_dataframe(cf, f"{ticker}-multi{form_type}-CF"), f"{ticker}-multi{form_type}-CF")
            if not annual_bs_df.empty or not annual_cf_df.empty:
                break
        except Exception as e:
            logger.debug("No multi %s BS/CF for %s: %s", form_type, ticker, e)

    quarterly_bs_df = pd.DataFrame()
    quarterly_cf_df = pd.DataFrame()
    for qtr_form in QUARTERLY_FORM_TYPES:
        try:
            filings_q = comp.get_filings(form=qtr_form, is_xbrl=True).head(n_quarters)
            multi_q = MultiFinancials(filings_q)
            bs_q = _get_financial_statement(multi_q, "balance_sheet")
            cf_q = _get_financial_statement(multi_q, "cash_flow_statement")
            if bs_q is not None:
                quarterly_bs_df = make_numeric_df(ensure_dataframe(bs_q, f"{ticker}-multi{qtr_form}-BS"), f"{ticker}-multi{qtr_form}-BS")
            if cf_q is not None:
                quarterly_cf_df = make_numeric_df(ensure_dataframe(cf_q, f"{ticker}-multi{qtr_form}-CF"), f"{ticker}-multi{qtr_form}-CF")
            if not quarterly_bs_df.empty or not quarterly_cf_df.empty:
                break
        except Exception as e:
            logger.debug("No multi %s BS/CF for %s: %s", qtr_form, ticker, e)

    annual_data = extract_period_values(annual_inc_df, f"{ticker}-ANN")
    quarterly_data = extract_period_values(quarterly_inc_df, f"{ticker}-QTR")

    _extract_bs_cf_values(annual_data, annual_bs_df, annual_cf_df, f"{ticker}-ANN")
    _extract_bs_cf_values(quarterly_data, quarterly_bs_df, quarterly_cf_df, f"{ticker}-QTR")

    _compute_derived_ratios(annual_data)
    _compute_derived_ratios(quarterly_data)
    _compute_derived_bs_ratios(annual_data)
    _compute_derived_bs_ratios(quarterly_data)

    yoy_rev = compute_growth_series(annual_data.get("Revenue", {}))
    cagr_rev = compute_cagr(annual_data.get("Revenue", {}))

    _ALL_GROWTH_LABELS = (
        [label for label, _ in _TRACKED_METRICS]
        + ["Gross Margin %", "Operating Margin %", "Net Margin %"]
        + list(_BS_CF_METRICS.keys())
        + ["Free Cash Flow", "CapEx", "ROE %", "ROA %", "Debt-to-Equity"]
    )

    yoy_growth = {"Revenue": yoy_rev}
    cagr = {"Revenue": cagr_rev}
    for label in _ALL_GROWTH_LABELS:
        if label == "Revenue":
            continue
        series = annual_data.get(label, {})
        if series:
            yoy_growth[label] = compute_growth_series(series)
            cagr[label] = compute_cagr(series)

    return {
        "annual_data": annual_data,
        "quarterly_data": quarterly_data,
        "yoy_revenue_growth": yoy_rev,
        "cagr_revenue": cagr_rev,
        "yoy_growth": yoy_growth,
        "cagr": cagr,
    }


_TRACKED_METRICS = (
    ("Revenue", "revenue"),
    ("Net Income", "net_income"),
    ("Gross Profit", "gross_profit"),
    ("Operating Income", "operating_income"),
    ("Cost of Revenue", "cost_of_revenue"),
    ("Interest Expense", "interest_expense"),
    ("Income Tax Expense", "income_tax_expense"),
)


def _compute_derived_ratios(data: dict) -> None:
    """Add derived margin % series from raw income statement values in-place."""
    revenue = data.get("Revenue", {})
    gross = data.get("Gross Profit", {})
    op_inc = data.get("Operating Income", {})
    ni = data.get("Net Income", {})

    for label, numerator in [
        ("Gross Margin %", gross),
        ("Operating Margin %", op_inc),
        ("Net Margin %", ni),
    ]:
        series = {}
        for period in numerator:
            rev = revenue.get(period)
            if rev and rev != 0:
                series[period] = (numerator[period] / rev) * 100.0
        if series:
            data[label] = series


_BS_CF_METRICS = {
    "Total Assets": "total_assets",
    "Total Equity": "total_equity",
    "Total Liabilities": "total_liabilities",
    "Current Assets": "current_assets",
    "Current Liabilities": "current_liabilities",
    "Short-term Debt": "short_term_debt",
    "Long-term Debt": "long_term_debt",
    "Cash from Operations": "cash_flow_operating",
}


def _extract_bs_cf_values(data: dict, bs_df: pd.DataFrame, cf_df: pd.DataFrame, debug_label: str) -> None:
    """Extract balance sheet and cash flow values into the multi-period data dict."""
    for label, syn_key in _BS_CF_METRICS.items():
        source_df = cf_df if syn_key == "cash_flow_operating" else bs_df
        if source_df.empty:
            continue
        source_df.columns = source_df.columns.map(str)
        sorted_cols = sorted(source_df.columns, key=parse_period_label)
        row = find_best_synonym_row(source_df, syn_key, value_cols=sorted_cols, debug_label=f"{debug_label}->{label}")
        if row is None:
            continue
        period_vals = {}
        for c in sorted_cols:
            val = row.get(c, np.nan)
            if pd.notna(val):
                period_vals[c] = float(val)
        if period_vals:
            data[label] = period_vals

    if not cf_df.empty:
        cf_df.columns = cf_df.columns.map(str)
        sorted_cf_cols = sorted(cf_df.columns, key=parse_period_label)
        op_values = data.get("Cash from Operations", {})
        capex_map = {}
        fcf_map = {}
        for col in sorted_cf_cols:
            capex = compute_capex_for_column(cf_df, col, debug_label=f"{debug_label}->CapEx")
            if capex > 0:
                capex_map[col] = capex
            opcf = op_values.get(col)
            if opcf is not None:
                fcf_map[col] = opcf - capex
        if capex_map:
            data["CapEx"] = capex_map
        if fcf_map:
            data["Free Cash Flow"] = fcf_map


def _compute_derived_bs_ratios(data: dict) -> None:
    """Compute ROE%, ROA%, D/E time series from extracted balance sheet + income data."""
    ni = data.get("Net Income", {})
    total_assets = data.get("Total Assets", {})
    total_equity = data.get("Total Equity", {})
    total_liabs = data.get("Total Liabilities", {})

    roe_series = {}
    roa_series = {}
    de_series = {}
    for period in ni:
        eq = total_equity.get(period)
        ta = total_assets.get(period)
        tl = total_liabs.get(period)
        if eq and eq != 0:
            roe_series[period] = (ni[period] / eq) * 100.0
        if ta and ta != 0:
            roa_series[period] = (ni[period] / ta) * 100.0
        if eq and eq > 0 and tl is not None:
            de_series[period] = tl / eq
    if roe_series:
        data["ROE %"] = roe_series
    if roa_series:
        data["ROA %"] = roa_series
    if de_series:
        data["Debt-to-Equity"] = de_series


def extract_period_values(df: pd.DataFrame, debug_label="(unknown)") -> dict:
    """
    Locates key income statement rows in a multi-column statement,
    returning { metric_name: {period: value, ...}, ... } by period label.
    """
    empty: dict = {label: {} for label, _ in _TRACKED_METRICS}
    if df.empty:
        logger.debug("extract_period_values(%s): DF empty -> returning empty dict", debug_label)
        return empty

    df.columns = df.columns.map(str)
    sorted_cols = sorted(df.columns, key=parse_period_label)

    results = {}
    for label, syn_key in _TRACKED_METRICS:
        row = find_best_row_for_synonym(df, syn_key, sorted_cols, f"{debug_label}->{label}")
        period_vals = {}
        if row is not None:
            for c in sorted_cols:
                val = row.get(c, np.nan)
                if pd.notna(val):
                    period_vals[c] = float(val)
        results[label] = period_vals

    return results


def find_best_row_for_synonym(df: pd.DataFrame, syn_key: str, columns_order: list, debug_label="(unknown)") -> pd.Series:
    """Finds the best row in df for syn_key. Delegates to the shared
    find_best_synonym_row in synonyms_utils."""
    return find_best_synonym_row(df, syn_key, value_cols=columns_order, debug_label=debug_label)  # type: ignore[return-value]


def compute_growth_series(values_dict: dict) -> dict:
    """
    Computes period-over-period % growth. Minimum 2 data points needed.
    """
    if len(values_dict) < 2:
        return {}
    sorted_periods = sorted(values_dict.keys(), key=parse_period_label)
    growth_map = {}
    prev_val = None
    for p in sorted_periods:
        curr_val = values_dict[p]
        if prev_val is not None and prev_val != 0:
            growth_map[p] = ((curr_val - prev_val) / abs(prev_val)) * 100.0
        prev_val = curr_val
    return growth_map


def compute_cagr(values_dict: dict) -> float:
    """Compound Annual Growth Rate from earliest to latest.

    Returns NaN when CAGR cannot be meaningfully computed: fewer than
    2 data points, non-positive values, or period shorter than ~3 months.
    """
    if len(values_dict) < 2:
        return np.nan
    sorted_periods = sorted(values_dict.keys(), key=parse_period_label)
    first_val = values_dict[sorted_periods[0]]
    last_val = values_dict[sorted_periods[-1]]
    if first_val <= 0 or last_val <= 0:
        return np.nan
    first_date = parse_period_label(sorted_periods[0])
    last_date = parse_period_label(sorted_periods[-1])
    n_years = (last_date - first_date).days / 365.25
    if n_years < 0.25:
        return np.nan
    return ((last_val / first_val) ** (1.0 / n_years) - 1.0) * 100.0


def analyze_quarterly_balance_sheets(comp: Company, n_quarters=10) -> dict:
    """
    Retrieve up to n_quarters of 10-Q for inventory, receivables, free_cf detection.
    Now uses compute_capex_for_column(...) to better approximate each period's capex.
    """
    results: dict = {"inventory": {}, "receivables": {}, "free_cf": {}}
    tkr = comp.tickers[0] if comp.tickers else "UNKNOWN"
    try:
        filings_10q = None
        for qtr_form in QUARTERLY_FORM_TYPES:
            try:
                filings_10q = comp.get_filings(form=qtr_form, is_xbrl=True).head(n_quarters)
                if filings_10q:
                    break
            except Exception:
                continue
        if not filings_10q:
            return results
        multi_10q = MultiFinancials(filings_10q)
        bs_10q = _get_financial_statement(multi_10q, "balance_sheet")
        cf_10q = _get_financial_statement(multi_10q, "cash_flow_statement")

        bs_df = make_numeric_df(ensure_dataframe(bs_10q, f"{tkr}-multi10Q-BS"), f"{tkr}-multi10Q-BS")
        cf_df = make_numeric_df(ensure_dataframe(cf_10q, f"{tkr}-multi10Q-CF"), f"{tkr}-multi10Q-CF")

        if not bs_df.empty:
            bs_df.columns = bs_df.columns.map(str)
            sorted_cols = sorted(bs_df.columns, key=parse_period_label)
            results["inventory"] = find_multi_col_values(bs_df, "inventory", sorted_cols, f"{tkr}->Inventory")
            results["receivables"] = find_multi_col_values(bs_df, "accounts_receivable", sorted_cols, f"{tkr}->Receivables")

        if not cf_df.empty:
            cf_df.columns = cf_df.columns.map(str)
            sorted_cf_cols = sorted(cf_df.columns, key=parse_period_label)

            # Operating CF row
            op_values = find_multi_col_values(cf_df, "cash_flow_operating", sorted_cf_cols, f"{tkr}->OpCF")

            fcf_map = {}
            for col in sorted_cf_cols:
                opcf = op_values.get(col)
                if opcf is None:
                    logger.debug("%s: no operating CF for period %s, skipping FCF", tkr, col)
                    continue
                capex_for_period = compute_capex_for_column(cf_df, col, debug_label=f"{tkr}->CapExCol")
                fcf_map[col] = opcf - capex_for_period

            results["free_cf"] = fcf_map

    except Exception as e:
        logger.error("analyze_quarterly_balance_sheets(%s) error: %s", tkr, e, exc_info=True)
    return results


def find_multi_col_values(df: pd.DataFrame, syn_key: str, sorted_cols: list, debug_label="(unknown)") -> dict:
    """Identify best row for syn_key and return {period_col: val}, ignoring NaNs.
    Delegates row-matching to find_best_synonym_row in synonyms_utils."""
    row = find_best_synonym_row(df, syn_key, value_cols=sorted_cols, debug_label=debug_label)
    if row is None:
        return {}
    return {k: float(v) for k, v in row[sorted_cols].dropna().items()}


def check_additional_alerts_quarterly(data_map: dict, alerts_config: dict | None = None) -> list:
    """Evaluate negative FCF streaks, inventory/receivables spikes, etc.

    Return a list of alert strings.  Accepts optional *alerts_config*
    overrides; falls back to ``ALERTS_CONFIG`` defaults.
    """
    from .config import get_alerts_config
    cfg = get_alerts_config(alerts_config)

    alerts = []
    fcf_dict = data_map.get("free_cf", {})
    if len(fcf_dict) > 1:
        consecutive_neg = 0
        sorted_keys = sorted(fcf_dict.keys(), key=parse_period_label)
        for p in sorted_keys:
            if fcf_dict[p] < 0:
                consecutive_neg += 1
            else:
                consecutive_neg = 0
            if consecutive_neg >= cfg["SUSTAINED_NEG_FCF_QUARTERS"]:
                alerts.append(f"{consecutive_neg} consecutive quarters of negative FCF (through {p}).")
                break

    inv_dict = data_map.get("inventory", {})
    alerts += check_spike(inv_dict, cfg["INVENTORY_SPIKE_THRESHOLD"], "Inventory")

    rec_dict = data_map.get("receivables", {})
    alerts += check_spike(rec_dict, cfg["RECEIVABLE_SPIKE_THRESHOLD"], "Receivables")

    return alerts


def check_spike(values_dict: dict, threshold: float, label: str) -> list:
    """If period-over-period growth exceeds threshold %, add an alert."""
    growth = compute_growth_series(values_dict)
    return [
        f"{label} spiked +{pct:.2f}% from previous quarter to {period}."
        for period, pct in growth.items()
        if pct > threshold
    ]
