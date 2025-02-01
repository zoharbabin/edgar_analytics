# edgar_analytics/panel_layout.py

import pandas as pd
import numpy as np
from rich.panel import Panel
from rich.table import Table
from .layout_strategy import LayoutStrategy

class PanelLayoutStrategy(LayoutStrategy):
    """
    Default layout strategy that prints each ticker's data in a Rich Panel,
    with a small sub-table for each row in df_summary.
    """

    def render(self, df_summary: pd.DataFrame) -> None:
        """
        For each row (ticker) in df_summary, produce a vertical panel:
         - A small 2-col sub-table of label->value.
        """
        if df_summary.empty:
            self.console.print("[yellow]No data available.[/yellow]")
            return

        self.console.print("[bold magenta]==== Snapshot (Latest) ====[/bold magenta]")

        for ticker, row in df_summary.iterrows():
            sub_table = Table(box=None, show_header=False, expand=False)
            sub_table.add_column("Metric", style="bold", no_wrap=True)
            sub_table.add_column("Value", style="white", no_wrap=False)

            # Build sub-table rows
            for col in df_summary.columns:
                label = str(col)
                raw_val = row[col]

                # Carefully handle possible array-like values
                val_str = self._safe_format_value(raw_val)
                sub_table.add_row(label, val_str)

            panel = Panel(
                sub_table,
                title=f"[cyan]{ticker}[/cyan]",
                border_style="blue",
                expand=False
            )
            self.console.print(panel)

    def _safe_format_value(self, raw_val) -> str:
        """
        Safely formats the raw_val for display, avoiding the ValueError:
         'The truth value of an empty array is ambiguous'.

        Returns a string for console display.
        """
        # 1) If array-like or Series => handle explicitly
        if isinstance(raw_val, (np.ndarray, pd.Series)):
            if raw_val.size == 0:
                return ""
            else:
                # Convert each element to string, join with comma
                return ", ".join(map(str, raw_val.tolist()))
        # 2) If a list => join with comma
        if isinstance(raw_val, list):
            return ", ".join(map(str, raw_val))
        # 3) If single numeric or scalar => check nullness
        if pd.isnull(raw_val):
            return ""
        # 4) Convert to string
        return str(raw_val)
