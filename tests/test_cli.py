"""Public CLI contract tests."""

from __future__ import annotations

import pytest
import typer
from typer.testing import CliRunner

from zendev.__main__ import app as module_app
from zendev.body import app as body_app
from zendev.cli import app as zendev_app
from zendev.commit import commit_app, hook_app
from zendev.proposal.cli import app as proposal_app
from zendev.title import app as title_app

runner = CliRunner()


@pytest.mark.parametrize(
    "app",
    [zendev_app, commit_app, hook_app, title_app, body_app, proposal_app],
    ids=["zendev", "commit", "commit-msg", "title", "body", "proposal"],
)
def test_public_cli_help_is_available(app: typer.Typer) -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "--help" in result.output


def test_unified_cli_exposes_installed_workflows() -> None:
    result = runner.invoke(zendev_app, ["--help"])

    assert result.exit_code == 0
    for command in ("commit", "commit-msg", "validate-title", "validate-body", "proposal"):
        assert command in result.output


def test_python_module_exposes_the_unified_application() -> None:
    assert module_app is zendev_app


def test_unified_cli_runs_root_command() -> None:
    result = runner.invoke(zendev_app, ["validate-title", "✨ feat: add unified CLI"])

    assert result.exit_code == 0
    assert "Title format is valid." in result.output


def test_unified_cli_mounts_proposal_commands() -> None:
    result = runner.invoke(zendev_app, ["proposal", "--help"])

    assert result.exit_code == 0
    assert "check" in result.output
    assert "index" in result.output
