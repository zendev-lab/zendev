"""Compose the complete Zendev command tree."""

from __future__ import annotations

import typer

from zendev.body import validate_body_command
from zendev.commit import commit_message, create_commit
from zendev.proposal.cli import app as proposal_app
from zendev.title import validate_title

app = typer.Typer(
    name="zendev",
    add_completion=False,
    help="Run Zendev development workflows.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
)

commit_cli = typer.Typer(
    add_completion=False,
    help="Create a git commit.",
    invoke_without_command=True,
    no_args_is_help=False,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
)
review_cli = typer.Typer(
    add_completion=False,
    help="Validate pull-request titles and bodies.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
)


@commit_cli.callback(invoke_without_command=True)
def _commit(ctx: typer.Context) -> None:
    """Create a git commit."""

    if ctx.invoked_subcommand is None:
        create_commit()


commit_cli.command("check")(commit_message)
review_cli.command("title")(validate_title)
review_cli.command("body")(validate_body_command)

app.add_typer(commit_cli, name="commit")
app.add_typer(review_cli, name="review")
app.add_typer(proposal_app, name="proposal")


def main() -> None:
    """Run the unified Zendev CLI."""

    app(prog_name="zendev")


if __name__ == "__main__":
    main()
