"""Read-only validation for project evolution records."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

from zendev.evolution.document import EvolutionError, validate_document

app = typer.Typer(
    name="zendev-evolution",
    add_completion=False,
    help="Validate a project's initial intent and dated evolution.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
)


@app.callback()
def _evolution() -> None:
    """Check a single EVOLUTION.md file."""


@app.command("check")
def check_command(
    file: Annotated[Path, typer.Option("--file", help="Document path, relative to the current directory.")] = Path(
        "EVOLUTION.md"
    ),
) -> None:
    """Validate the document without changing it."""

    try:
        validate_document(file.read_bytes().decode("utf-8"), path=str(file))
    except EvolutionError as error:
        print(error, file=sys.stderr)
        raise typer.Exit(1) from None
    except (OSError, UnicodeError) as error:
        print(f"{file}:1: {error}", file=sys.stderr)
        raise typer.Exit(2) from None
    print(f"Validated {file}.")


def main() -> None:
    """Run the independently installable evolution command."""

    app(prog_name="zendev-evolution")


if __name__ == "__main__":
    main()
