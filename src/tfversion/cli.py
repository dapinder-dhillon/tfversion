from typing import Optional

import typer

app = typer.Typer(add_completion=False, help="Print the Terraform version from a remote S3 state file.")


@app.command()
def main(
    path: Optional[str] = typer.Argument(default=None),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    pass


def run() -> None:
    app()
