"""File I/O and command-line adapters for project evolution."""

from __future__ import annotations

import sys
from dataclasses import asdict, replace
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from zendev.core.diagnostics import Diagnostic, OutputFormat, render_report
from zendev.evolution import EvolutionCheck, check_document

app = typer.Typer(
    name="zendev-evolution",
    add_completion=False,
    help="Initialize, list, and validate a project's initial intent and dated evolution.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
)

FileOption = Annotated[Path, typer.Option("--file", help="Document path, relative to the current directory.")]
FormatOption = Annotated[OutputFormat, typer.Option("--format")]


@app.callback()
def _evolution() -> None:
    """Work with a single EVOLUTION.md file."""


def _finish(
    result: EvolutionCheck,
    command: str,
    file: str | Path,
    output_format: OutputFormat,
    *,
    exit_code: int | None = None,
) -> NoReturn:
    success = (
        "\n".join(f"{file}:{section.line}: {section.title}" for section in result.sections)
        if command == "list"
        else f"{'Created' if command == 'init' else 'Validated'} {file}."
    )
    print(
        render_report(
            result.diagnostics,
            command=f"evolution {command}",
            output_format=output_format,
            summary={"path": str(file), "sections": [asdict(section) for section in result.sections]},
            success_message=success,
        ),
        file=sys.stderr if not result.ok and output_format is OutputFormat.HUMAN else sys.stdout,
    )
    raise typer.Exit(exit_code if exit_code is not None else (0 if result.ok else 1))


def _read(source: Path, command: str, output_format: OutputFormat, *, stdin: bool = False) -> str:
    path = "<stdin>" if stdin else str(source)
    try:
        content = sys.stdin.buffer.read() if stdin else source.read_bytes()
        return content.decode("utf-8")
    except (OSError, UnicodeError) as error:
        diagnostic = Diagnostic("evolution.input.read", str(error), path=path, line=1)
        _finish(EvolutionCheck(diagnostics=(diagnostic,)), command, path, output_format, exit_code=2)


@app.command("init")
def init_command(
    source: Annotated[Path, typer.Option("--from", help="UTF-8 initial intent body, or - for standard input.")],
    file: FileOption = Path("EVOLUTION.md"),
    output_format: FormatOption = OutputFormat.HUMAN,
) -> None:
    """Create a document from initial intent without overwriting an existing path."""
    source_name = "<stdin>" if str(source) == "-" else str(source)
    prefix = "# 项目演进\n\n## 初始意图\n\n"
    content = _read(source, "init", output_format, stdin=str(source) == "-")
    text = prefix + content.rstrip() + "\n"
    result = check_document(text, path=source_name)
    diagnostics = tuple(replace(d, line=max(1, (d.line or 1) - prefix.count("\n"))) for d in result.diagnostics)
    if result.ok and len(result.sections) != 1:
        diagnostics = (
            Diagnostic(
                "evolution.init.entries",
                "Initial intent must not contain dated entries.",
                path=source_name,
                line=result.sections[1].line - prefix.count("\n"),
            ),
        )
    if diagnostics:
        _finish(EvolutionCheck(diagnostics=diagnostics), "init", source_name, output_format)
    try:
        with file.open("xb") as output:
            output.write(text.encode("utf-8"))
    except (OSError, UnicodeError) as error:
        diagnostic = Diagnostic("evolution.output.create", str(error), path=str(file), line=1)
        _finish(EvolutionCheck(diagnostics=(diagnostic,)), "init", file, output_format, exit_code=2)
    _finish(result, "init", file, output_format)


@app.command("list")
def list_command(file: FileOption = Path("EVOLUTION.md"), output_format: FormatOption = OutputFormat.HUMAN) -> None:
    """List the initial intent and dates with source line numbers."""
    result = check_document(_read(file, "list", output_format), path=str(file))
    _finish(result, "list", file, output_format)


@app.command("check")
def check_command(file: FileOption = Path("EVOLUTION.md"), output_format: FormatOption = OutputFormat.HUMAN) -> None:
    """Validate the document without changing it."""
    result = check_document(_read(file, "check", output_format), path=str(file))
    _finish(result, "check", file, output_format)


def main() -> None:
    app(prog_name="zendev-evolution")


if __name__ == "__main__":
    main()
