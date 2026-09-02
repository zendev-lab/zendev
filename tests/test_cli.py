"""Public CLI contract tests."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

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
FIXTURES = Path(__file__).parent / "fixtures" / "proposal"


def _copy_fixture(tmp_path: Path, name: str) -> Path:
    destination = tmp_path / name
    shutil.copytree(FIXTURES / name, destination)
    return destination


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


def test_unified_cli_groups_workflows_by_domain() -> None:
    result = runner.invoke(zendev_app, ["--help"])

    assert result.exit_code == 0
    for command in ("commit", "review", "proposal"):
        assert command in result.output
    for command in ("commit-msg", "validate-title", "validate-body"):
        assert command not in result.output


def test_python_module_exposes_the_unified_application() -> None:
    assert module_app is zendev_app


def test_unified_cli_runs_review_title() -> None:
    result = runner.invoke(zendev_app, ["review", "title", "✨ feat: add unified CLI"])

    assert result.exit_code == 0
    assert "Title format is valid." in result.output


def test_unified_cli_commit_check_validates_a_message_file(tmp_path: Path) -> None:
    message = tmp_path / "COMMIT_EDITMSG"
    message.write_text("✨ feat: add grouped CLI\n", encoding="utf-8")

    result = runner.invoke(zendev_app, ["commit", "check", str(message)])

    assert result.exit_code == 0


def test_unified_cli_mounts_proposal_check_without_index() -> None:
    result = runner.invoke(zendev_app, ["proposal", "--help"])

    assert result.exit_code == 0
    assert "check" in result.output
    commands = result.output.split("Commands:", 1)[-1]
    assert re.search(r"^\s+check\b", commands, re.MULTILINE)
    assert not re.search(r"^\s+index\b", commands, re.MULTILINE)


def test_unified_cli_drift_hint_uses_zendev_proposal_check(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    (repository / "veps-index.json").write_text("{}\n", encoding="utf-8")

    result = runner.invoke(
        zendev_app,
        ["proposal", "check", "--config", str(repository / "proposal.toml"), "--json"],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 1
    assert payload["diagnostics"][0]["hint"] == "Run `zendev proposal check --fix` and commit the result."
