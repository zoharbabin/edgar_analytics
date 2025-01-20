"""
reporting.py

Generates final summary for each ticker's data, logs results, 
and optionally writes a CSV.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

import numpy as np
import pandas as pd

from .data_utils import custom_float_format, get_logger


class ReportingEngine:
    """
    Summarizes and logs final metrics for each ticker. 
    Optionally saves to CSV. Also logs multi-year and forecast data.
    """

    def __init__(self) -> None:
        self.logger: logging.Logger = get_logger(self.__class__.__name__)

    def summarize_metrics_table(
        self,
        metrics_map: Dict[str, Dict[str, Any]],
        main_ticker: str,
        csv_path: Optional[str] = None
    ) -> None:
        """
        Build a summary table from metrics_map, 
        log it, save CSV if requested, log alerts & forecasts.
        """
        snapshot_dict = self._build_snapshot_dict(metrics_map)
        if not snapshot_dict:
            self.logger.info("No snapshot data to summarize.")
            return

        df_summary = pd.DataFrame(snapshot_dict).T
        df_summary = self._prepare_dataframe_for_presentation(df_summary, main_ticker)
        self._log_dataframe_snapshot(df_summary)
        self._maybe_save_csv(df_summary, csv_path)
        self._log_snapshot_alerts(snapshot_dict)
        self._log_additional_quarterly_alerts(metrics_map)
        self._log_multi_year_and_forecast(metrics_map)

    def _build_snapshot_dict(self, metrics_map: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Extract annual or fallback quarterly snapshot for each ticker
        into a dictionary for DataFrame creation.
        """
        snapshot_dict = {}
        for ticker, data in metrics_map.items():
            annual_snap = data.get("annual_snapshot", {})
            q_snap = data.get("quarterly_snapshot", {})

            snap = {}
            if annual_snap.get("metrics"):
                snap.update(annual_snap["metrics"])
                snap["_FormType"] = annual_snap["filing_info"].get("form_type", "Unknown")
                snap["_FilingDate"] = annual_snap["filing_info"].get("filed_date", "")
            elif q_snap.get("metrics"):
                snap.update(q_snap["metrics"])
                snap["_FormType"] = q_snap["filing_info"].get("form_type", "Unknown")
                snap["_FilingDate"] = q_snap["filing_info"].get("filed_date", "")

            snapshot_dict[ticker] = snap
        return snapshot_dict

    def _prepare_dataframe_for_presentation(self, df_summary: pd.DataFrame, main_ticker: str) -> pd.DataFrame:
        """
        Reorder columns for clarity, place main_ticker row first,
        custom float formatting, etc.
        """
        if df_summary.empty:
            return df_summary

        ordered_cols = [
            "_FormType", "_FilingDate", "Revenue", "Net Income", "Gross Margin %",
            "Net Margin %", "Operating Expenses", "Debt-to-Equity", "Equity Ratio %",
            "ROE %", "ROA %", "Free Cash Flow", "EBITDA (approx)", "Alerts",
            "Intangible Ratio %", "Goodwill Ratio %", "Tangible Equity", "Net Debt",
            "Net Debt/EBITDA", "Lease Liabilities Ratio %"
        ]
        existing_cols = [c for c in ordered_cols if c in df_summary.columns]
        df_summary = df_summary[existing_cols]

        all_tickers = df_summary.index.tolist()
        if main_ticker in all_tickers:
            new_order = [main_ticker] + [t for t in all_tickers if t != main_ticker]
            df_summary = df_summary.loc[new_order]

        numeric_cols = df_summary.select_dtypes(include=["number"]).columns
        for col in numeric_cols:
            df_summary[col] = df_summary[col].apply(custom_float_format)

        return df_summary

    def _log_dataframe_snapshot(self, df_summary: pd.DataFrame) -> None:
        """Print the summary DataFrame to logs."""
        if df_summary.empty:
            self.logger.info("df_summary is empty.")
            return

        pd.set_option("display.width", 1000)
        pd.set_option("display.max_columns", None)

        self.logger.info("==== Snapshot (Latest) ====")
        lines = []
        header = " | ".join(f"{col:>18}" for col in df_summary.columns)
        lines.append(header)
        lines.append("-" * len(header))

        for ticker, row in df_summary.iterrows():
            row_vals = [f"{str(row[col]):>18}" for col in df_summary.columns]
            lines.append(f"{ticker:>6} | " + " | ".join(row_vals))

        self.logger.info("\n%s", "\n".join(lines))

    def _maybe_save_csv(self, df_summary: pd.DataFrame, csv_path: Optional[str]) -> None:
        """Save the summary DataFrame to CSV if csv_path is provided and not empty."""
        if not csv_path or df_summary.empty:
            return

        try:
            path_obj = Path(csv_path).resolve()
            if str(path_obj) == "/" or ".." in path_obj.parts:
                self.logger.error("CSV path invalid or insecure: %s", csv_path)
                return
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            df_summary.to_csv(path_obj, index=True)
            self.logger.info("Snapshot summary saved to %s", path_obj)
        except Exception as exc:
            self.logger.exception("Failed to save CSV %s: %s", csv_path, exc)

    def _log_snapshot_alerts(self, snapshot_dict: Dict[str, Dict[str, Any]]) -> None:
        self.logger.info("\n==== Snapshot Alerts ====")
        for ticker, snap_data in snapshot_dict.items():
            alerts = snap_data.get("Alerts", [])
            if alerts:
                self.logger.warning("Alerts for %s:", ticker)
                for a in alerts:
                    self.logger.warning("  - %s", a)
            else:
                self.logger.info("No snapshot alerts for %s", ticker)

    def _log_additional_quarterly_alerts(self, metrics_map: Dict[str, Dict[str, Any]]) -> None:
        """Log any 'extra_alerts' from multi-quarter analysis."""
        self.logger.info("\n==== Additional Quarterly Alerts ====")
        for ticker, data in metrics_map.items():
            extras = data.get("extra_alerts", [])
            if extras:
                self.logger.warning("Quarterly-based alerts for %s:", ticker)
                for alert in extras:
                    self.logger.warning("  - %s", alert)
            else:
                self.logger.info("No extra quarterly alerts for %s", ticker)

    def _log_multi_year_and_forecast(self, metrics_map: Dict[str, Dict[str, Any]]) -> None:
        """Log yoy growth, CAGR, forecast results for each ticker."""
        self.logger.info("\n==== Multi-Year & Forecast Analysis ====")
        for ticker, data in metrics_map.items():
            multi = data.get("multiyear", {})
            yoy_rev = multi.get("yoy_revenue_growth", {})
            cagr_rev = multi.get("cagr_revenue", 0.0)

            fc_data = data.get("forecast", {})
            annual_fc = fc_data.get("annual_rev_forecast", 0.0)
            qtr_fc = fc_data.get("quarterly_rev_forecast", 0.0)

            if yoy_rev:
                avg_yoy = np.mean(list(yoy_rev.values()))
                yoy_text = f"  Average yoy rev growth: {avg_yoy:.2f}%. "
                if avg_yoy > 20.0:
                    yoy_text += "Strong growth."
                elif avg_yoy < 0.0:
                    yoy_text += "Revenue declining yoy."
            else:
                yoy_text = "  Not enough data for yoy growth."

            cagr_text = f"  CAGR= {cagr_rev:.2f}%. "
            if cagr_rev > 15.0:
                cagr_text += "Multi-year growth is robust."
            elif cagr_rev < 0.0:
                cagr_text += "Overall revenue has contracted"

            fc_text = f"  Forecast(annual)= {annual_fc:,.2f}, Forecast(quarterly)= {qtr_fc:,.2f}"

            self.logger.info("%s =>%s%s%s", ticker, yoy_text, cagr_text, fc_text)

        self.logger.info("==== End of Summary ====")
