# edgar_analytics/cli.py

import click
from .orchestrator import TickerOrchestrator


@click.command()
@click.argument("ticker")
@click.argument("peers", nargs=-1)
@click.option(
    "--csv",
    "-c",
    type=click.Path(writable=True, dir_okay=True, exists=False),
    default=None,
    help="Optional path to save the CSV summary."
)
def main(ticker, peers, csv):
    """
    CLI command to analyze a TICKER plus optional PEERS.

    Example usage:
        edgar-analytics AAPL MSFT GOOGL AMZN
        edgar-analytics AAPL MSFT GOOGL AMZN --csv outputs/summary.csv
    """
    orchestrator = TickerOrchestrator()
    orchestrator.analyze_company(ticker, list(peers), csv_path=csv)


if __name__ == "__main__":
    main()
