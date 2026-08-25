"""Public CLI contract tests."""

from __future__ import annotations

import pytest
import typer
from typer.testing import CliRunner

from zendev.body import app as body_app
from zendev.commit import commit_app, hook_app
from zendev.proposal.cli import app as proposal_app
from zendev.title import app as title_app

runner = CliRunner()


@pytest.mark.parametrize(
    "app",
    [commit_app, hook_app, title_app, body_app, proposal_app],
    ids=["commit", "commit-msg", "title", "body", "proposal"],
)
def test_public_cli_help_is_available(app: typer.Typer) -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "--help" in result.output
