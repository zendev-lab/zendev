"""Message-check scope and CLI tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from zendev.cli import app as zendev_app
from zendev.message import MessageScope, input_is_single_line, resolve_message_scope

runner = CliRunner()

COMMIT_WITH_BODY = "✨ feat: add foo\n\nExplain why this change is needed.\n"
PR_TEMPLATE = "## Summary\n\nWhy.\n\n## Validation\n\nHow.\n\n## Notes\n\nNone.\n"
PR_BODY = "## Summary\n\nWhy.\n\n## Validation\n\nTests.\n\n## Notes\n\nNone.\n"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("✨ feat: add foo", True),
        ("✨ feat: add foo\n", True),
        ("✨ feat: add foo\r\n", True),
        ("✨ feat: add foo\n\n", False),
        (COMMIT_WITH_BODY, False),
        ("", True),
    ],
)
def test_input_is_single_line(text: str, expected: bool) -> None:
    assert input_is_single_line(text) is expected


@pytest.mark.parametrize(
    ("scope", "text", "expected"),
    [
        (MessageScope.AUTO, "✨ feat: add foo\n", MessageScope.TITLE),
        (MessageScope.AUTO, COMMIT_WITH_BODY, MessageScope.FULL),
        (MessageScope.TITLE, COMMIT_WITH_BODY, MessageScope.TITLE),
        (MessageScope.BODY, "✨ feat: add foo\n", MessageScope.BODY),
        (MessageScope.FULL, "✨ feat: add foo\n", MessageScope.FULL),
    ],
)
def test_resolve_message_scope(scope: MessageScope, text: str, expected: MessageScope) -> None:
    assert resolve_message_scope(scope, text) is expected


def test_auto_single_line_checks_title() -> None:
    result = runner.invoke(zendev_app, ["message", "check", "--text", "✨ feat: add foo"])

    assert result.exit_code == 0
    assert "Title format is valid." in result.output


def test_auto_multiline_uses_commit_body_not_pr_template() -> None:
    result = runner.invoke(zendev_app, ["message", "check", "--text", COMMIT_WITH_BODY])

    assert result.exit_code == 0
    assert "PR body" not in result.output
    assert "Title format is valid." not in result.output


def test_auto_multiline_rejects_invalid_commit_header() -> None:
    result = runner.invoke(zendev_app, ["message", "check", "--text", "ship it\n\nwhy\n"])

    assert result.exit_code == 1
    assert "Invalid commit message." in result.stderr
    assert "PR body" not in result.output


def test_title_scope_rejects_multiline_input() -> None:
    result = runner.invoke(
        zendev_app,
        ["message", "check", "--title", "--text", COMMIT_WITH_BODY],
    )

    assert result.exit_code == 1
    assert "Title scope requires a single-line input." in result.output


def test_body_scope_uses_pr_template(tmp_path: Path) -> None:
    template = tmp_path / "pull_request_template.md"
    template.write_text(PR_TEMPLATE, encoding="utf-8")

    valid = runner.invoke(
        zendev_app,
        ["message", "check", "--body", "--text", PR_BODY, "--template", str(template)],
    )
    commit_body = runner.invoke(
        zendev_app,
        ["message", "check", "--body", "--text", COMMIT_WITH_BODY, "--template", str(template)],
    )

    assert valid.exit_code == 0
    assert "PR body headings are valid." in valid.output
    assert commit_body.exit_code == 1
    assert "PR body headings do not match" in commit_body.output


def test_body_scope_reads_file(tmp_path: Path) -> None:
    template = tmp_path / "pull_request_template.md"
    template.write_text(PR_TEMPLATE, encoding="utf-8")
    body = tmp_path / "pr-body.md"
    body.write_text(PR_BODY, encoding="utf-8")

    result = runner.invoke(
        zendev_app,
        ["message", "check", "--body", str(body), "--template", str(template)],
    )

    assert result.exit_code == 0


def test_commit_editmsg_with_comments_uses_full_commit_semantics(tmp_path: Path) -> None:
    message = tmp_path / "COMMIT_EDITMSG"
    message.write_text("✨ feat: add foo\n\n# Please enter the commit message\n", encoding="utf-8")

    result = runner.invoke(zendev_app, ["message", "check", str(message)])

    assert result.exit_code == 0
    assert "PR body" not in result.output


def test_file_and_text_are_mutually_exclusive(tmp_path: Path) -> None:
    message = tmp_path / "COMMIT_EDITMSG"
    message.write_text("✨ feat: add foo\n", encoding="utf-8")

    result = runner.invoke(
        zendev_app,
        ["message", "check", str(message), "--text", "✨ feat: add foo"],
    )

    assert result.exit_code == 2
    assert "FILE or --text" in result.output


def test_title_and_body_are_mutually_exclusive() -> None:
    result = runner.invoke(
        zendev_app,
        ["message", "check", "--title", "--body", "--text", "✨ feat: add foo"],
    )

    assert result.exit_code == 2
    assert "--title and --body are mutually exclusive" in result.output


def test_missing_input_is_rejected() -> None:
    result = runner.invoke(zendev_app, ["message", "check"])

    assert result.exit_code == 2
    assert "FILE or --text" in result.output


def test_require_checklist_requires_body() -> None:
    result = runner.invoke(
        zendev_app,
        ["message", "check", "--require-checklist", "--text", "✨ feat: add foo"],
    )

    assert result.exit_code == 2
    assert "--require-checklist requires --body" in result.output
