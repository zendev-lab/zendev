"""Thin command-line adapter for proposal application services."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

from zendev.core.diagnostics import Diagnostic, OutputFormat, ToolError, render_report
from zendev.proposal.application import check_project

app = typer.Typer(
    name="zendev-proposal",
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
)


@app.callback()
def _proposal() -> None:
    """Validate repository-native proposals."""


@app.command("check")
def check_command(
    ctx: typer.Context,
    config: Annotated[Path | None, typer.Option("--config", help="Explicit ZenDev configuration source.")] = None,
    base_ref: Annotated[str | None, typer.Option("--base-ref", envvar="PROPOSAL_BASE_REF")] = None,
    fix: Annotated[bool, typer.Option("--fix", help="Apply validated repairs and update the index.")] = False,
    diff: Annotated[bool, typer.Option("--diff", help="Preview repairs without writing.")] = False,
    select: Annotated[str | None, typer.Option("--select", help="Comma-separated repair rule names.")] = None,
    partial: Annotated[
        bool, typer.Option("--partial", help="Allow independently safe repairs with remaining errors.")
    ] = False,
    output_format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.HUMAN,
) -> None:
    """Check proposals, relationships, history, and the committed index."""
    summary = None
    patch = ""
    try:
        result = check_project(
            config,
            base_ref,
            fix=fix,
            diff=diff,
            select=select,
            partial=partial,
            fix_invocation=f"{ctx.command_path.strip()} --fix",
        )
        diagnostics, summary, patch = result.diagnostics, result.summary, result.patch
        exit_code = 1 if diagnostics else 0
    except ToolError as error:
        diagnostics, summary = (error.diagnostic,), error.summary
        exit_code = 2
    except (OSError, UnicodeError) as error:
        diagnostics = (Diagnostic("proposal.io", str(error)),)
        exit_code = 2
    if patch and output_format is not OutputFormat.JSON:
        print(patch, end="")
    print(
        render_report(
            diagnostics,
            command="check",
            output_format=output_format,
            summary=summary,
            success_message=(
                "Updated the proposal index."
                if summary and summary.get("index") == "updated"
                else "Proposal checks passed."
            ),
        ),
        file=sys.stderr if diagnostics and output_format is OutputFormat.HUMAN else sys.stdout,
    )
    if exit_code:
        raise typer.Exit(exit_code)


def main() -> None:
    app(prog_name="zendev-proposal")
