"""File, Git, and CLI adapters for the message domain."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from zendev.core.diagnostics import Diagnostic, OutputFormat, ToolError, render_report
from zendev.core.markdown import markdown_session
from zendev.message.body import check_body
from zendev.message.commit import MessageProfile, check_git_message, check_message
from zendev.message.config import load_message_config

app = typer.Typer(
    name="zendev-message",
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
)


class MessageScope(StrEnum):
    AUTO = "auto"
    TITLE = "title"
    BODY = "body"
    COMMIT = "commit"


@app.callback()
def _message() -> None:
    """Create and validate development messages."""


def input_is_single_line(text: str) -> bool:
    if text.endswith("\r\n"):
        text = text[:-2]
    elif text.endswith(("\r", "\n")):
        text = text[:-1]
    return "\n" not in text and "\r" not in text


def resolve_message_scope(scope: MessageScope, text: str) -> MessageScope:
    return (
        (MessageScope.TITLE if input_is_single_line(text) else MessageScope.COMMIT)
        if scope is MessageScope.AUTO
        else scope
    )


def _comment_char() -> str:
    process = subprocess.run(
        ["git", "config", "--get", "core.commentChar"], capture_output=True, text=True, check=False
    )
    value = process.stdout.strip()
    return value if len(value) == 1 else "#"


@app.command("check")
def check_command(
    source_file: Annotated[Path | None, typer.Argument(metavar="FILE")] = None,
    text: Annotated[str | None, typer.Option("--text")] = None,
    title: Annotated[bool, typer.Option("--title")] = False,
    body: Annotated[bool, typer.Option("--body")] = False,
    commit: Annotated[
        bool, typer.Option("--commit", help="Use Git message cleanup and special-message rules.")
    ] = False,
    config: Annotated[Path | None, typer.Option("--config")] = None,
    profile: Annotated[MessageProfile | None, typer.Option("--profile")] = None,
    template: Annotated[Path | None, typer.Option("--template")] = None,
    require_checklist: Annotated[bool | None, typer.Option("--require-checklist/--no-require-checklist")] = None,
    checklist_section: Annotated[str | None, typer.Option("--checklist-section")] = None,
    fail_on_empty_checklist: Annotated[
        bool | None, typer.Option("--fail-on-empty-checklist/--allow-empty-checklist")
    ] = None,
    output_format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.HUMAN,
) -> None:
    """Check FILE or --text using the selected message scope."""
    diagnostics: tuple[Diagnostic, ...] = ()
    exit_code = 0
    try:
        if (source_file is None) == (text is None):
            raise ToolError(Diagnostic("message.input", "Provide exactly one of FILE and --text."))
        if sum((title, body, commit)) > 1:
            raise ToolError(Diagnostic("message.scope", "--title, --body, and --commit are mutually exclusive."))
        if body and profile is not None:
            raise ToolError(Diagnostic("message.options", "--profile does not apply to --body."))
        if not body and any(
            value is not None for value in (template, require_checklist, checklist_section, fail_on_empty_checklist)
        ):
            raise ToolError(Diagnostic("message.options", "Template and checklist options require --body."))
        settings = load_message_config(config, profile=profile)
        payload = source_file.read_text(encoding="utf-8") if source_file is not None else text
        assert payload is not None
        scope = (
            MessageScope.TITLE
            if title
            else MessageScope.BODY
            if body
            else MessageScope.COMMIT
            if commit
            else MessageScope.AUTO
        )
        scope = resolve_message_scope(scope, payload)
        with markdown_session():
            if scope is MessageScope.BODY:
                template_path = template if template is not None else settings.template
                try:
                    template_text = template_path.read_text(encoding="utf-8")
                    diagnostics = check_body(
                        payload,
                        template_text,
                        require_checklist=settings.require_checklist
                        if require_checklist is None
                        else require_checklist,
                        checklist_section=checklist_section or settings.checklist_section,
                        fail_on_empty_checklist=settings.fail_on_empty_checklist
                        if fail_on_empty_checklist is None
                        else fail_on_empty_checklist,
                    )
                except (OSError, UnicodeError, ValueError) as error:
                    raise ToolError(Diagnostic("message.template", str(error), path=str(template_path))) from error
            elif scope is MessageScope.TITLE:
                if not input_is_single_line(payload):
                    diagnostics = (Diagnostic("message.title.multiline", "Title scope requires a single-line input."),)
                else:
                    diagnostics = check_message(payload, profile=settings.profile).diagnostics
            else:
                diagnostics = check_git_message(
                    payload, profile=settings.profile, comment_char=_comment_char() if source_file is not None else "#"
                ).diagnostics
        if source_file is not None:
            diagnostics = tuple(replace(item, path=str(source_file)) for item in diagnostics)
        exit_code = 1 if diagnostics else 0
    except ToolError as error:
        diagnostics = (error.diagnostic,)
        exit_code = 2
    except (OSError, UnicodeError) as error:
        diagnostics = (Diagnostic("message.input.read", str(error), path=str(source_file) if source_file else None),)
        exit_code = 2
    report = render_report(diagnostics, command="message check", output_format=output_format)
    print(report, file=sys.stderr if diagnostics and output_format is OutputFormat.HUMAN else sys.stdout)
    if exit_code:
        raise typer.Exit(exit_code)


def main() -> None:
    app(prog_name="zendev-message")
