"""Human-readable commands for project evolution records."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated

import typer

from zendev.evolution.document import EvolutionError, validate_date
from zendev.evolution.storage import initialize, read_document, write_entry

app = typer.Typer(
    name="zendev-evolution",
    add_completion=False,
    help="Read, write, and validate a project's initial intent and dated evolution.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
)

FileOption = Annotated[Path, typer.Option("--file", help="Document path, relative to the current directory.")]
InputOption = Annotated[Path, typer.Option("--from", help="UTF-8 body file, or - for standard input.")]


@app.callback()
def _evolution() -> None:
    """Manage a single EVOLUTION.md file."""


@contextmanager
def _diagnostics(path: Path) -> Iterator[None]:
    try:
        yield
    except EvolutionError as error:
        print(error, file=sys.stderr)
        raise typer.Exit(error.exit_code) from None
    except (OSError, UnicodeError) as error:
        print(f"{path}:1: {error}", file=sys.stderr)
        raise typer.Exit(2) from None


def _input(path: Path) -> str:
    return sys.stdin.read() if str(path) == "-" else path.read_bytes().decode("utf-8")


@app.command("init")
def init_command(source: InputOption, file: FileOption = Path("EVOLUTION.md")) -> None:
    """Create a document from initial intent prose without overwriting an existing file."""

    with _diagnostics(file):
        initialize(file, _input(source), source="<stdin>" if str(source) == "-" else str(source))
        print(f"Created {file}.")


@app.command("list")
def list_command(file: FileOption = Path("EVOLUTION.md")) -> None:
    """List the origin and dates in chronological order with source line numbers."""

    with _diagnostics(file):
        document = read_document(file)
        for section in (document.origin, *document.entries):
            print(f"{file}:{section.line}: {section.title}")


@app.command("read")
def read_command(
    day: Annotated[str | None, typer.Argument(help="Date in YYYY-MM-DD format.")] = None,
    origin: Annotated[bool, typer.Option("--origin", help="Read only the initial intent.")] = False,
    file: FileOption = Path("EVOLUTION.md"),
) -> None:
    """Read a date, or the initial intent and latest entry when no date is supplied."""

    with _diagnostics(file):
        if day is not None and origin:
            raise EvolutionError("DATE and --origin are mutually exclusive.", path=str(file), exit_code=2)
        if day is not None:
            validate_date(day, path=str(file), exit_code=2)
        document = read_document(file)
        if day is not None:
            section = next((entry for entry in document.entries if entry.title == day), None)
            if section is None:
                raise EvolutionError("Date does not exist.", path=str(file), exit_code=2)
            sys.stdout.write(document.source(section))
        else:
            sys.stdout.write(document.source(document.origin))
            if not origin and document.entries:
                if not document.source(document.origin).endswith(("\n\n", "\r\n\r\n")):
                    sys.stdout.write("\n")
                sys.stdout.write(document.source(document.entries[-1]))


@app.command("write")
def write_command(
    day: Annotated[str, typer.Argument(help="Date in YYYY-MM-DD format.")],
    source: InputOption,
    replace: Annotated[bool, typer.Option("--replace", help="Replace an existing date explicitly.")] = False,
    file: FileOption = Path("EVOLUTION.md"),
) -> None:
    """Write the 触发, 变化, 理由 subsections for one day from a file or standard input."""

    with _diagnostics(file):
        write_entry(file, day, _input(source), replace=replace, source="<stdin>" if str(source) == "-" else str(source))
        print(f"{'Replaced' if replace else 'Added'} {day} in {file}.")


@app.command("check")
def check_command(file: FileOption = Path("EVOLUTION.md")) -> None:
    """Validate initial intent, dates, and required subsections without modifying the file."""

    with _diagnostics(file):
        document = read_document(file)
        print(f"Validated {file}: initial intent and {len(document.entries)} dated entries.")


def main() -> None:
    """Run the independently installable evolution command."""

    app(prog_name="zendev-evolution")


if __name__ == "__main__":
    main()
