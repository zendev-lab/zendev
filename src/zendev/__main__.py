"""Unified command-line entry point for Zendev."""

from __future__ import annotations

import typer

from zendev.body import validate_body_command
from zendev.commit import commit_message, create_commit
from zendev.title import validate_title

app = typer.Typer(
    add_completion=False,
    help="Run Zendev development workflows.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
)

app.command("commit")(create_commit)
app.command("commit-msg")(commit_message)
app.command("validate-title")(validate_title)
app.command("validate-body")(validate_body_command)

try:
    from zendev.proposal.cli import app as proposal_app
except ModuleNotFoundError as error:
    if error.name != "zendev.proposal":
        raise
else:
    app.add_typer(proposal_app, name="proposal")


def main() -> None:
    """Run the unified Zendev CLI."""

    app(prog_name="zendev")


if __name__ == "__main__":
    main()
