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
from zendev.cli import app as zendev_app
from zendev.commit import commit_app
from zendev.message import app as message_app
from zendev.proposal.cli import app as proposal_app

runner = CliRunner()
FIXTURES = Path(__file__).parent / "fixtures" / "proposal"


def _copy_fixture(tmp_path: Path, name: str) -> Path:
    destination = tmp_path / name
    shutil.copytree(FIXTURES / name, destination)
    return destination


@pytest.mark.parametrize(
    "app",
    [zendev_app, commit_app, message_app, proposal_app],
    ids=["zendev", "commit", "message", "proposal"],
)
def test_public_cli_help_is_available(app: typer.Typer) -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "--help" in result.output


def test_unified_cli_groups_workflows_by_domain() -> None:
    result = runner.invoke(zendev_app, ["--help"])

    assert result.exit_code == 0
    commands = result.output.split("Commands:", 1)[-1]
    for command in ("commit", "message", "proposal"):
        assert re.search(rf"^\s+{command}\b", commands, re.MULTILINE)
    for command in ("check", "commit-msg", "review", "validate-title", "validate-body"):
        assert command not in result.output


def test_python_module_exposes_the_unified_application() -> None:
    assert module_app is zendev_app


def test_unified_cli_message_check_validates_a_title() -> None:
    result = runner.invoke(zendev_app, ["message", "check", "--title", "--text", "✨ feat: add unified CLI"])

    assert result.exit_code == 0
    assert "Title format is valid." in result.output


def test_unified_cli_message_check_validates_a_message_file(tmp_path: Path) -> None:
    message = tmp_path / "COMMIT_EDITMSG"
    message.write_text("✨ feat: add grouped CLI\n", encoding="utf-8")

    result = runner.invoke(zendev_app, ["message", "check", str(message)])

    assert result.exit_code == 0


def test_unified_cli_message_and_proposal_expose_check() -> None:
    message_help = runner.invoke(zendev_app, ["message", "--help"])
    message_check_help = runner.invoke(zendev_app, ["message", "check", "--help"])
    proposal_help = runner.invoke(zendev_app, ["proposal", "--help"])

    assert message_help.exit_code == 0
    assert re.search(r"^\s+check\b", message_help.output.split("Commands:", 1)[-1], re.MULTILINE)
    assert message_check_help.exit_code == 0
    for option in ("--text", "--title", "--body"):
        assert option in message_check_help.output
    assert proposal_help.exit_code == 0
    commands = proposal_help.output.split("Commands:", 1)[-1]
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


def test_public_hooks_use_check_ids() -> None:
    manifest = Path(__file__).resolve().parents[1] / ".pre-commit-hooks.yaml"
    text = manifest.read_text(encoding="utf-8")

    assert "id: zendev-message-check" in text
    assert "id: zendev-proposal-check" in text
    assert "entry: zendev message check" in text
    assert "entry: zendev proposal check" in text
    for removed in ("zendev-commit-msg", "zendev-proposal-index", "zendev-validate-title", "zendev-validate-body"):
        assert removed not in text
