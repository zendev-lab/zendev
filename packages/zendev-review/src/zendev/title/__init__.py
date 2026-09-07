"""CLI entry point for validating PR titles in CI."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

from zendev.commit import (
    CommitProfile,
    CommitProfileSelection,
    normalize_commit_message,
    report_invalid_commit_message,
    resolve_commit_profile,
    validate_commit_message,
)

app = typer.Typer(
    add_completion=False,
    help="Validate a PR title against a configured commit profile.",
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
)


def run_title_check(
    text: str,
    *,
    profile: CommitProfile | str | None = None,
    start: Path | None = None,
) -> None:
    """Validate one title using the selected commit profile."""

    try:
        selected = resolve_commit_profile(profile, start=start)
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="--profile") from error

    normalized = normalize_commit_message(text)
    print("::group::PR / title check")
    print(f"Text: {normalized!r}")
    print("::endgroup::")

    result = validate_commit_message(normalized, profile=selected)
    if result.valid:
        print("Title format is valid.")
        return

    report_invalid_commit_message(
        normalized,
        context="ci",
        file=sys.stdout,
        profile=selected,
        result=result,
    )
    raise typer.Exit(code=1)


@app.command()
def validate_title(
    text: Annotated[str, typer.Argument(help="PR title text to validate.")],
    profile: Annotated[
        CommitProfileSelection,
        typer.Option(
            "--profile",
            help="Validation profile; auto reads [tool.zendev.commit] and falls back to zendev.",
        ),
    ] = CommitProfileSelection.AUTO,
) -> None:
    """Validate one PR title using the selected commit profile."""

    run_title_check(text, profile=profile.value)


def main() -> None:
    app(prog_name="zendev-validate-title")
