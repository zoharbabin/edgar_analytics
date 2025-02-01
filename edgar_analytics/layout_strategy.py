# edgar_analytics/layout_strategy.py

import abc
import pandas as pd
from rich.console import Console


class LayoutStrategy(abc.ABC):
    """
    Abstract base class for displaying the final metrics DataFrame.
    Implementations can show it as Rich panels, horizontal tables, 
    or anything else. This keeps the design extensible.
    """

    def __init__(self, console: Console) -> None:
        self.console = console

    @abc.abstractmethod
    def render(self, df_summary: pd.DataFrame) -> None:
        """
        Renders the final DataFrame in the console. 
        Must be implemented by subclasses.
        """
        pass
