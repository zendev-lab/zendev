"""Public CLI contract tests."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pytest
import typer
from typer.testing import CliRunner

from zendev.__main__ import app as module_app
from zendev.cli import app as zendev_app
from zendev.evolution.cli import app as evolution_app
from zendev.message.cli import app as message_app
from zendev.message.interactive import app as commit_app
from zendev.proposal.cli import app as proposal_app

runner = CliRunner()
FIXTURES = Path(__file__).parent / "fixtures" / "proposal"


def _copy_fixture(tmp_path: Path, name: str) -> Path:
    destination = tmp_path / name
    shutil.copytree(FIXTURES / name, destination)
    return destination


@pytest.mark.parametrize(
    "app",
    [zendev_app, commit_app, message_app, proposal_app, evolution_app],
    ids=["zendev", "commit", "message", "proposal", "evolution"],
)
def test_public_cli_help_is_available(app: typer.Typer) -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "--help" in result.output


def test_unified_cli_groups_workflows_by_domain() -> None:
    result = runner.invoke(zendev_app, ["--help"], terminal_width=80)

    assert result.exit_code == 0
    commands = result.output.split("Commands:", 1)[-1]
    listed = re.findall(r"^\s+(\S+)\s", commands, re.MULTILINE)
    assert listed == ["commit", "message", "proposal", "evolution"]
    assert "..." not in commands
    for command in ("check", "commit-msg", "review", "validate-title", "validate-body"):
        assert not re.search(rf"^\s+{command}\b", commands, re.MULTILINE)


def _commands(command: Any, path: str = "zendev") -> list[tuple[str, Any]]:
    found = [(path, command)]
    for name, child in getattr(command, "commands", {}).items():
        found += _commands(child, f"{path} {name}")
    return found


COMMANDS = _commands(typer.main.get_command(zendev_app))


def test_help_covers_the_complete_command_tree() -> None:
    assert [path for path, _ in COMMANDS] == [
        "zendev",
        "zendev commit",
        "zendev message",
        "zendev message check",
        "zendev proposal",
        "zendev proposal check",
        "zendev evolution",
        "zendev evolution init",
        "zendev evolution list",
        "zendev evolution check",
    ]


@pytest.mark.parametrize(("path", "command"), COMMANDS, ids=[path for path, _ in COMMANDS])
def test_every_command_and_parameter_has_help(path: str, command: Any) -> None:
    assert command.help or command.short_help, path
    for parameter in command.params:
        assert getattr(parameter, "help", None), (path, parameter.name)


def test_python_module_exposes_the_unified_application() -> None:
    assert module_app is zendev_app


def test_unified_cli_reports_the_installed_version() -> None:
    result = runner.invoke(zendev_app, ["--version"])

    assert result.exit_code == 0
    assert result.output == f"zendev {version('zendev')}\n"


def test_unified_cli_message_check_validates_a_title() -> None:
    result = runner.invoke(zendev_app, ["message", "check", "--title", "--text", "✨ feat: add unified CLI"])

    assert result.exit_code == 0
    assert "Check passed." in result.output


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
        ["proposal", "check", "--config", str(repository / "zendev.toml"), "--format", "json"],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 1
    assert payload["diagnostics"][0]["hint"] == "Run `zendev proposal check --fix` and commit the result."


@pytest.mark.parametrize("output_format", ["human", "json", "github"])
def test_message_output_is_utf8_independently_of_host_encoding(tmp_path: Path, output_format: str) -> None:
    message = tmp_path / "提交.txt"
    message.write_text("非法 title\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "zendev", "message", "check", message.name, "--format", output_format],
        cwd=tmp_path,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        capture_output=True,
        timeout=15,
        check=False,
    )

    assert result.returncode == 1
    output = (result.stderr if output_format == "human" else result.stdout).decode("utf-8")
    assert "提交.txt" in output
    assert b"Traceback" not in result.stderr


def test_proposal_output_is_utf8_independently_of_host_encoding(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    index = next(repository.glob("*-index.json"))
    index.write_text("{}\n", encoding="utf-8")
    renamed = index.with_name("索引.json")
    config = repository / "zendev.toml"
    config.write_text(config.read_text(encoding="utf-8").replace(index.name, renamed.name), encoding="utf-8")
    index.rename(renamed)

    result = subprocess.run(
        [sys.executable, "-m", "zendev", "proposal", "check", "--diff"],
        cwd=repository,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        capture_output=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 1
    assert "索引.json" in result.stdout.decode("utf-8")
    assert result.stderr.decode("utf-8").startswith("索引.json: proposal.index.drift:")


def test_public_hooks_use_check_ids() -> None:
    manifest = Path(__file__).resolve().parents[1] / ".pre-commit-hooks.yaml"
    text = manifest.read_text(encoding="utf-8")

    assert "id: zendev-message-check" in text
    assert "id: zendev-proposal-check" in text
    assert "id: zendev-evolution-check" in text
    assert "entry: zendev evolution check" in text
    assert "entry: zendev message check" in text
    assert "entry: zendev proposal check" in text
    for removed in ("zendev-commit-msg", "zendev-proposal-index", "zendev-validate-title", "zendev-validate-body"):
        assert removed not in text
