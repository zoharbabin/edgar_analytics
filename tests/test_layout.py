"""tests/test_layout.py — tests for layout_strategy and panel_layout modules."""

import numpy as np
import pandas as pd
from io import StringIO
from rich.console import Console

from edgar_analytics.layout_strategy import LayoutStrategy
from edgar_analytics.panel_layout import PanelLayoutStrategy


class TestLayoutStrategy:
    def test_cannot_instantiate_abstract(self):
        import pytest
        with pytest.raises(TypeError):
            LayoutStrategy(Console())

    def test_subclass_can_implement_render(self):
        class DummyLayout(LayoutStrategy):
            def render(self, df_summary):
                pass

        layout = DummyLayout(Console())
        layout.render(pd.DataFrame())


class TestPanelLayoutStrategy:
    def test_render_empty_df(self, capsys):
        console = Console(file=StringIO())
        layout = PanelLayoutStrategy(console)
        layout.render(pd.DataFrame())

    def test_render_single_row(self):
        console = Console(file=StringIO())
        layout = PanelLayoutStrategy(console)
        df = pd.DataFrame({"Revenue": [1000.0], "Net Income": [100.0]}, index=["AAPL"])
        layout.render(df)

    def test_safe_format_value_nan(self):
        console = Console(file=StringIO())
        layout = PanelLayoutStrategy(console)
        assert layout._safe_format_value(np.nan) == ""
        assert layout._safe_format_value(None) == ""

    def test_safe_format_value_array(self):
        console = Console(file=StringIO())
        layout = PanelLayoutStrategy(console)
        result = layout._safe_format_value(np.array([1, 2, 3]))
        assert result == "1, 2, 3"

    def test_safe_format_value_empty_array(self):
        console = Console(file=StringIO())
        layout = PanelLayoutStrategy(console)
        result = layout._safe_format_value(np.array([]))
        assert result == ""

    def test_safe_format_value_list(self):
        console = Console(file=StringIO())
        layout = PanelLayoutStrategy(console)
        result = layout._safe_format_value(["a", "b"])
        assert result == "a, b"

    def test_safe_format_value_scalar(self):
        console = Console(file=StringIO())
        layout = PanelLayoutStrategy(console)
        assert layout._safe_format_value(42.5) == "42.5"
