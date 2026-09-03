"""Validate commit and pull-request messages."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated, assert_never

import typer

from zendev.body import run_body_check
from zendev.commit import CommitProfile, CommitProfileSelection, run_commit_message_check
from zendev.title import run_title_check

app = typer.Typer(
    name="zendev-message",
    add_completion=False,
    help="Validate commit and pull-request messages.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
)


class MessageScope(StrEnum):
    """Requested or resolved message-check scope."""

    AUTO = "auto"
    TITLE = "title"
    BODY = "body"
    FULL = "full"


@app.callback()
def _message() -> None:
    """Validate commit and pull-request messages."""


def input_is_single_line(text: str) -> bool:
    """Return True when text is one line, ignoring a single trailing newline."""

    if text.endswith("\r\n"):
        content = text[:-2]
    elif text.endswith(("\n", "\r")):
        content = text[:-1]
    else:
        content = text
    return "\n" not in content and "\r" not in content


def resolve_message_scope(scope: MessageScope, text: str) -> MessageScope:
    """Resolve AUTO from input shape. Newlines never select a body schema."""

    if scope is MessageScope.AUTO:
        return MessageScope.TITLE if input_is_single_line(text) else MessageScope.FULL
    return scope


def run_message_check(
    text: str,
    *,
    scope: MessageScope,
    profile: CommitProfile | str | None = None,
    start: Path | None = None,
    comment_char: str | None = None,
    template: Path = Path(".github/pull_request_template.md"),
    require_checklist: bool = False,
    checklist_section: str = "Checklist",
    fail_on_empty_checklist: bool = False,
) -> None:
    """Dispatch a resolved message check and exit on failure."""

    resolved = resolve_message_scope(scope, text)
    if resolved is MessageScope.TITLE and not input_is_single_line(text):
        print("Title scope requires a single-line input.")
        raise typer.Exit(code=1)

    match resolved:
        case MessageScope.TITLE:
            run_title_check(text, profile=profile, start=start)
        case MessageScope.BODY:
            run_body_check(
                text,
                template=template,
                require_checklist=require_checklist,
                checklist_section=checklist_section,
                fail_on_empty_checklist=fail_on_empty_checklist,
            )
        case MessageScope.FULL:
            run_commit_message_check(
                text,
                profile=profile,
                start=start,
                comment_char=comment_char,
                context="hook",
            )
        case MessageScope.AUTO:
            raise RuntimeError("AUTO must be resolved before dispatch")
        case _:
            assert_never(resolved)


def _requested_scope(*, title: bool, body: bool) -> MessageScope:
    if title and body:
        raise typer.BadParameter("--title and --body are mutually exclusive.")
    if title:
        return MessageScope.TITLE
    if body:
        return MessageScope.BODY
    return MessageScope.AUTO


def _read_input(*, source_file: Path | None, text: str | None) -> tuple[str, Path | None]:
    if source_file is not None and text is not None:
        raise typer.BadParameter("Provide FILE or --text, not both.")
    if source_file is None and text is None:
        raise typer.BadParameter("Provide FILE or --text.")
    if text is not None:
        return text, None
    assert source_file is not None
    if not source_file.is_file():
        raise typer.BadParameter(f"{source_file} is not a readable file.", param_hint="FILE")
    return source_file.read_text(encoding="utf-8"), source_file.parent


@app.command("check")
def check_command(
    source_file: Annotated[
        Path | None,
        typer.Argument(metavar="FILE", help="Message file. Mutually exclusive with --text."),
    ] = None,
    text: Annotated[
        str | None,
        typer.Option("--text", metavar="TEXT", help="Message text. Mutually exclusive with FILE."),
    ] = None,
    title: Annotated[
        bool,
        typer.Option("--title", help="Check only the title. The input must be a single line."),
    ] = False,
    body: Annotated[
        bool,
        typer.Option("--body", help="Check only the pull-request body against the template schema."),
    ] = False,
    profile: Annotated[
        CommitProfileSelection,
        typer.Option(
            "--profile",
            help="Commit profile for title and complete-message checks.",
        ),
    ] = CommitProfileSelection.AUTO,
    template: Annotated[
        Path,
        typer.Option("--template", metavar="PATH", help="PR template used with --body."),
    ] = Path(".github/pull_request_template.md"),
    require_checklist: Annotated[
        bool,
        typer.Option(
            "--require-checklist",
            help="With --body, require checked rows from the template checklist section.",
        ),
    ] = False,
    checklist_section: Annotated[
        str,
        typer.Option(
            "--checklist-section",
            metavar="TITLE",
            help='H2 title, without "##", containing the checklist rows.',
        ),
    ] = "Checklist",
    fail_on_empty_checklist: Annotated[
        bool,
        typer.Option(
            "--fail-on-empty-checklist",
            help="Fail when checklist validation is requested but the template has no checked rows.",
        ),
    ] = False,
) -> None:
    """Validate message text from FILE or --text."""

    if require_checklist and not body:
        raise typer.BadParameter("--require-checklist requires --body.")
    if body and profile is not CommitProfileSelection.AUTO:
        raise typer.BadParameter("--profile applies to title and complete messages, not --body.")

    payload, start = _read_input(source_file=source_file, text=text)
    run_message_check(
        payload,
        scope=_requested_scope(title=title, body=body),
        profile=profile.value,
        start=start,
        comment_char="#" if start is None else None,
        template=template,
        require_checklist=require_checklist,
        checklist_section=checklist_section,
        fail_on_empty_checklist=fail_on_empty_checklist,
    )
