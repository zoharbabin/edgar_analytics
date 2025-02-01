# edgar_analytics/cli.py

import click
from rich.progress import Progress
from .orchestrator import TickerOrchestrator
from .logging_utils import configure_logging

@click.command()
@click.argument("ticker")
@click.argument("peers", nargs=-1)
@click.option(
    "--csv",
    "-c",
    type=click.Path(writable=True, dir_okay=True, exists=False),
    default=None,
    help="Optional path to save the final CSV summary. E.g., 'results.csv'."
)
@click.option(
    "--years",
    "-y",
    type=click.INT,
    default=3,
    show_default=True,
    help="Number of years of 10-K data to retrieve."
)
@click.option(
    "--quarters",
    "-q",
    type=click.INT,
    default=10,
    show_default=True,
    help="Number of quarters of 10-Q data to retrieve."
)
@click.option(
    "--log-level",
    "-l",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    default="INFO",
    help="Set the console logging level. Defaults to INFO."
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Shortcut for --log-level=DEBUG (overrides --log-level)."
)
@click.option(
    "--disable-forecast",
    is_flag=True,
    default=False,
    help="Disable revenue forecasting to speed up analysis."
)
@click.option(
    "--identity",
    type=str,
    default=None,
    help=(
        "Override EDGAR set_identity() with a custom 'Name <email>' string. "
        "Ensures compliance with SEC fair-use requirements."
    )
)
@click.option(
    "--suppress-logs",
    is_flag=True,
    default=False,
    help=(
        "Suppress all console logs except for final summary panels. "
        "Intended for a cleaner user-facing experience if desired."
    )
)
def main(ticker, peers, csv, years, quarters, log_level, debug, disable_forecast, identity, suppress_logs):
    """
    Analyze a TICKER plus optional PEERS. Example usage:
    
        edgar-analytics AAPL
        edgar-analytics AAPL MSFT --csv output.csv
        edgar-analytics AAPL MSFT GOOGL --years 5 --quarters 8

    For additional help on arguments and options:
        edgar-analytics --help
    """
    effective_level = "DEBUG" if debug else log_level
    configure_logging(effective_level, suppress_logs=suppress_logs)

    orchestrator = TickerOrchestrator()
    with Progress() as progress:
        task_id = progress.add_task(
            f"[cyan]Retrieving data for {ticker} + peers...",
            total=1
        )

        orchestrator.analyze_company(
            ticker=ticker,
            peers=list(peers),
            csv_path=csv,
            n_years=years,
            n_quarters=quarters,
            disable_forecast=disable_forecast,
            identity=identity
        )

        progress.update(task_id, advance=1)
        progress.stop()

if __name__ == "__main__":
    main()
