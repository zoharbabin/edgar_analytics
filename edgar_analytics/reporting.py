# edgar_analytics/reporting.py

from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd
from rich.console import Console

from .data_utils import custom_float_format
from .logging_utils import get_logger
from .layout_strategy import LayoutStrategy

logger = get_logger(__name__)

class ReportingEngine:
    """
    The ReportingEngine aggregates 'metrics_map' results into a final summary,
    applies a LayoutStrategy for console rendering, logs alerts,
    and optionally saves the summary to CSV.
    """

    def __init__(self, layout_strategy: Optional[LayoutStrategy] = None) -> None:
        self.logger = logger
        self.console = Console()

        if layout_strategy is None:
            from .panel_layout import PanelLayoutStrategy
            layout_strategy = PanelLayoutStrategy(self.console)

        self.layout_strategy = layout_strategy

    def summarize_metrics_table(
        self,
        metrics_map: Dict[str, Dict[str, Any]],
        main_ticker: str,
        csv_path: Optional[str] = None
    ) -> None:
        """
        Builds a DataFrame from 'metrics_map', then uses the layout_strategy
        to display in the console, shows alerts, multi-year forecasts, etc.
        Finally, optionally saves a CSV summary.

        Args:
            metrics_map: Nested dict, typically created by TickerOrchestrator.
            main_ticker: The primary ticker being analyzed (displayed first).
            csv_path: If given, writes the final summary DataFrame to CSV.
        """
        snapshot_dict = self._build_snapshot_dict(metrics_map)

        if not snapshot_dict:
            self.console.print("[yellow]No snapshot data to summarize.[/yellow]")
            self.logger.info("No snapshot data to summarize.")
            return

        df_summary = pd.DataFrame(snapshot_dict).T
        df_summary = self._prepare_dataframe_for_presentation(df_summary, main_ticker)

        # Render in the console
        self.layout_strategy.render(df_summary)

        # Display & log snapshot alerts
        self._show_alerts(snapshot_dict)

        # Additional quarterly-based alerts
        self._show_quarterly_alerts(metrics_map)

        # Multi-year data + forecast
        self._show_multi_year_and_forecast(metrics_map)

        # Save CSV if requested
        self._save_csv_if_requested(df_summary, csv_path)

    def _build_snapshot_dict(self, metrics_map: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        snapshot_dict = {}
        for ticker, data in metrics_map.items():
            annual = data.get("annual_snapshot", {})
            qtr = data.get("quarterly_snapshot", {})

            snap = {}
            if annual.get("metrics"):
                snap.update(annual["metrics"])
                snap["_FormType"] = annual["filing_info"].get("form_type", "Unknown")
                snap["_FilingDate"] = annual["filing_info"].get("filed_date", "")
            elif qtr.get("metrics"):
                snap.update(qtr["metrics"])
                snap["_FormType"] = qtr["filing_info"].get("form_type", "Unknown")
                snap["_FilingDate"] = qtr["filing_info"].get("filed_date", "")

            if snap:
                snapshot_dict[ticker] = snap

        return snapshot_dict

    def _prepare_dataframe_for_presentation(
        self,
        df_summary: pd.DataFrame,
        main_ticker: str
    ) -> pd.DataFrame:
        if df_summary.empty:
            return df_summary

        # Reorder columns
        ordered_cols = [
            "_FormType", "_FilingDate", "Revenue", "Net Income", "Gross Margin %",
            "Net Margin %", "Operating Expenses", "Debt-to-Equity", "Equity Ratio %",
            "ROE %", "ROA %", "Free Cash Flow", "EBITDA (approx)", "Alerts",
            "Intangible Ratio %", "Goodwill Ratio %", "Tangible Equity",
            "Net Debt", "Net Debt/EBITDA", "Lease Liabilities Ratio %"
        ]
        existing_cols = [c for c in ordered_cols if c in df_summary.columns]
        df_summary = df_summary[existing_cols]

        # Move main ticker to top
        all_tickers = df_summary.index.tolist()
        if main_ticker in all_tickers:
            new_order = [main_ticker] + [t for t in all_tickers if t != main_ticker]
            df_summary = df_summary.loc[new_order]

        # Force numeric if possible
        for col in df_summary.columns:
            df_summary[col] = pd.to_numeric(df_summary[col], errors="ignore")

        # Format numeric columns
        numeric_cols = df_summary.select_dtypes(include=["number"]).columns
        for col in numeric_cols:
            df_summary[col] = df_summary[col].apply(custom_float_format)

        return df_summary

    def _show_alerts(self, snapshot_dict: Dict[str, Dict[str, Any]]) -> None:
        self.console.print("\n[bold magenta]==== Snapshot Alerts ====[/bold magenta]")
        for ticker, snap_data in snapshot_dict.items():
            alerts = snap_data.get("Alerts", [])
            if alerts:
                alert_header = f"Alerts for {ticker}:"
                self.console.print(f"[yellow]{alert_header}[/yellow]")
                self.logger.warning(alert_header)

                for a in alerts:
                    self.console.print(f"   [red]- {a}[/red]")
            else:
                self.console.print(f"No snapshot alerts for [bold]{ticker}[/bold].")

    def _show_quarterly_alerts(self, metrics_map: Dict[str, Dict[str, Any]]) -> None:
        self.console.print("\n[bold magenta]==== Additional Quarterly Alerts ====[/bold magenta]")
        for ticker, data in metrics_map.items():
            extras = data.get("extra_alerts", [])
            if extras:
                header = f"Quarterly-based alerts for {ticker}:"
                self.console.print(f"[yellow]{header}[/yellow]")
                self.logger.warning(header)
                for alert in extras:
                    self.console.print(f"   [red]- {alert}[/red]")
            else:
                self.console.print(f"No extra quarterly alerts for [bold]{ticker}[/bold].")

    def _show_multi_year_and_forecast(self, metrics_map: Dict[str, Dict[str, Any]]) -> None:
        self.console.print("\n[bold magenta]==== Multi-Year & Forecast Analysis ====[/bold magenta]")
        for ticker, data in metrics_map.items():
            multi = data.get("multiyear", {})
            yoy_rev = multi.get("yoy_revenue_growth", {})
            cagr_rev = multi.get("cagr_revenue", 0.0)
            fc_data = data.get("forecast", {})
            annual_fc = fc_data.get("annual_rev_forecast", 0.0)
            qtr_fc = fc_data.get("quarterly_rev_forecast", 0.0)

            # yoy
            if yoy_rev:
                avg_yoy = sum(yoy_rev.values()) / len(yoy_rev)
                yoy_msg = f"  Average yoy rev growth: {avg_yoy:.2f}%."
                if avg_yoy > 20.0:
                    yoy_msg += " [green]Strong growth[/green]."
                elif avg_yoy < 0.0:
                    yoy_msg += " [red]Revenue declining yoy[/red]."
            else:
                yoy_msg = "  Not enough data for yoy growth."

            # cagr
            cagr_msg = f"  CAGR= {cagr_rev:.2f}%. "
            if cagr_rev < 0.0:
                cagr_msg += "[red]Overall revenue has contracted[/red]."
                self.logger.info("Overall revenue has contracted")

            fc_text = f"  Forecast(annual)= {annual_fc:,.2f}, Forecast(quarterly)= {qtr_fc:,.2f}"

            line_out = f"[bold]{ticker}[/bold] => {yoy_msg}{cagr_msg}{fc_text}"
            self.console.print(line_out)

        self.console.print("[bold magenta]==== End of Summary ====[/bold magenta]\n")

    def _save_csv_if_requested(
        self,
        df_summary: pd.DataFrame,
        csv_path: Optional[str]
    ) -> None:
        if not csv_path or df_summary.empty:
            return
        try:
            path_obj = Path(csv_path).resolve()
            if str(path_obj) == "/" or ".." in path_obj.parts:
                self.logger.error("CSV path invalid or insecure: %s", csv_path)
                return
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            df_summary.to_csv(path_obj, index=True)
            self.console.print(f"[green]Snapshot summary saved to {csv_path}[/green]")
            self.logger.info("Snapshot summary saved to %s", csv_path)
        except Exception as exc:
            self.logger.exception("Failed to save CSV %s: %s", csv_path, exc)
