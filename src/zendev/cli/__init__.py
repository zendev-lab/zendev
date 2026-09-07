"""Compose the complete Zendev command tree."""

from __future__ import annotations

import typer

from zendev.commit import create_commit
from zendev.message import app as message_app
from zendev.proposal.cli import app as proposal_app

app = typer.Typer(
    name="zendev",
    add_completion=False,
    help="Run Zendev development workflows.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
)

app.command("commit")(create_commit)
app.add_typer(message_app, name="message")
app.add_typer(proposal_app, name="proposal")


def main() -> None:
    """Run the unified Zendev CLI."""

    app(prog_name="zendev")


if __name__ == "__main__":
    main()
