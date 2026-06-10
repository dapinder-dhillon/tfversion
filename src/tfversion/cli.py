import os
from typing import Optional

import typer

from tfversion.fetcher import S3StateFetcher
from tfversion.formatter import VerboseFormatter
from tfversion.parser import HclParser

app = typer.Typer(add_completion=False, help="Print the Terraform version from a remote S3 state file.")


@app.command()
def main(
    path: Optional[str] = typer.Argument(default=None),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    resolved = path or os.getcwd()
    config = HclParser(resolved).parse()
    version = S3StateFetcher(config).fetch_version()
    if verbose:
        typer.echo(VerboseFormatter(config, version).format())
    else:
        typer.echo(version)


def run() -> None:
    app()
