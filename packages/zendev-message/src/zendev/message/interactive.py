"""Interactive message creation and Git execution adapters."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Annotated

import questionary
import typer

from zendev.core.diagnostics import ToolError
from zendev.message.commit import MessageDraft, MessageProfile, render_message
from zendev.message.config import load_message_config
from zendev.message.conventional import ConventionalFooter
from zendev.message.gitmoji import load_gitmojis
from zendev.message.policy import load_policy

app = typer.Typer(add_completion=False, pretty_exceptions_enable=False, rich_markup_mode=None)


def _answer(value: str | bool | None):
    if value is None:
        raise KeyboardInterrupt
    return value


def ask(profile: MessageProfile) -> MessageDraft:
    name = ""
    intention = None
    if profile is MessageProfile.ZENDEV:
        name = str(_answer(questionary.select("Change type", choices=list(load_policy().types)).ask()))
    elif profile is MessageProfile.CONVENTIONAL:
        name = str(_answer(questionary.text("Change type").ask()))
    if profile is not MessageProfile.CONVENTIONAL:
        choices = (
            [item.gitmoji for item in load_policy().for_type(name)]
            if profile is MessageProfile.ZENDEV
            else load_gitmojis()
        )
        intention = str(
            _answer(
                questionary.select(
                    "Change intention",
                    choices=[
                        questionary.Choice(f"{item.emoji} {item.description}", value=item.name) for item in choices
                    ],
                ).ask()
            )
        )
    scope = str(_answer(questionary.text("Scope (optional)").ask())).strip()
    subject = str(_answer(questionary.text("Short summary").ask())).strip()
    body = str(_answer(questionary.text("Body (optional)").ask()))
    breaking = False
    footers = []
    if profile is not MessageProfile.GITMOJI:
        breaking = bool(_answer(questionary.confirm("Breaking change?", default=False).ask()))
        while _answer(questionary.confirm("Add footer?", default=False).ask()):
            token = str(_answer(questionary.text("Footer token (e.g. Refs or BREAKING CHANGE)").ask()))
            value = str(_answer(questionary.text("Footer value").ask()))
            footers.append(ConventionalFooter(token, value))
    return MessageDraft(subject, name, intention, scope, body, tuple(footers), breaking)


@app.command()
def create_commit(
    config: Annotated[Path | None, typer.Option("--config")] = None,
    profile: Annotated[MessageProfile | None, typer.Option("--profile")] = None,
) -> None:
    """Create a message using the active profile and invoke Git."""
    try:
        settings = load_message_config(config, profile=profile)
        text = render_message(ask(settings.profile), profile=settings.profile)
    except KeyboardInterrupt:
        typer.echo("Aborted.", err=True)
        raise typer.Exit(1) from None
    except (ToolError, ValueError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(2) from error
    raise typer.Exit(subprocess.run(["git", "commit", "-m", text], check=False).returncode)


def main() -> None:
    app(prog_name="zendev-commit")
