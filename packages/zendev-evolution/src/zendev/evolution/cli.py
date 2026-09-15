"""Initialize, list, and validate project evolution records."""

from __future__ import annotations

import sys
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated

import typer

from zendev.evolution.document import EvolutionError, _validated_sections, validate_document

app = typer.Typer(
    name="zendev-evolution",
    add_completion=False,
    help="Initialize, list, and validate a project's initial intent and dated evolution.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
)

FileOption = Annotated[Path, typer.Option("--file", help="Document path, relative to the current directory.")]


@app.callback()
def _evolution() -> None:
    """Work with a single EVOLUTION.md file."""


@contextmanager
def _diagnostics(path: str | Path) -> Generator[None, None, None]:
    try:
        yield
    except EvolutionError as error:
        print(error, file=sys.stderr)
        raise typer.Exit(1) from None
    except (OSError, UnicodeError) as error:
        print(f"{path}:1: {error}", file=sys.stderr)
        raise typer.Exit(2) from None


@app.command("init")
def init_command(
    source: Annotated[Path, typer.Option("--from", help="UTF-8 initial intent body, or - for standard input.")],
    file: FileOption = Path("EVOLUTION.md"),
) -> None:
    """Create a document from initial intent without overwriting an existing path."""

    source_name = "<stdin>" if str(source) == "-" else str(source)
    prefix = "# 项目演进\n\n## 初始意图\n\n"
    with _diagnostics(source_name):
        content = sys.stdin.buffer.read() if str(source) == "-" else source.read_bytes()
        text = prefix + content.decode("utf-8").rstrip() + "\n"
        try:
            sections = _validated_sections(text, path=source_name)
        except EvolutionError as error:
            raise EvolutionError(
                error.message, path=source_name, line=max(1, error.line - prefix.count("\n"))
            ) from None
        if len(sections) != 1:
            raise EvolutionError(
                "Initial intent must not contain dated entries.",
                path=source_name,
                line=sections[1].start + 1 - prefix.count("\n"),
            )
    with _diagnostics(file):
        with file.open("xb") as output:
            output.write(text.encode("utf-8"))
        print(f"Created {file}.")


@app.command("list")
def list_command(file: FileOption = Path("EVOLUTION.md")) -> None:
    """List the initial intent and dates with source line numbers."""

    with _diagnostics(file):
        sections = _validated_sections(file.read_bytes().decode("utf-8"), path=str(file))
        for section in sections:
            print(f"{file}:{section.start + 1}: {section.title}")


@app.command("check")
def check_command(file: FileOption = Path("EVOLUTION.md")) -> None:
    """Validate the document without changing it."""

    with _diagnostics(file):
        validate_document(file.read_bytes().decode("utf-8"), path=str(file))
        print(f"Validated {file}.")


def main() -> None:
    """Run the independently installable evolution command."""

    app(prog_name="zendev-evolution")


if __name__ == "__main__":
    main()
