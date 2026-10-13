"""Dedicated proposal policies retain their released layout and behavior."""

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from zendev.cli import app as unified_app
from zendev.core.diagnostics import ToolError
from zendev.core.source import source_session
from zendev.message.config import load_message_config
from zendev.proposal import apply_plan, check_project, load_config, plan_changes
from zendev.proposal.cli import app
from zendev.proposal.indexing import expected_index_text
from zendev.proposal.repository import load_repository

FIXTURES = Path(__file__).parent / "fixtures/proposal"


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "vep"
    shutil.copytree(FIXTURES / "vep", root)
    shutil.copyfile(FIXTURES / "vep-dedicated.toml", root / "proposal.toml")
    return root


def test_released_policy_and_unified_policy_have_identical_behavior(repository: Path) -> None:
    unified = load_config(repository / "zendev.toml")
    dedicated = load_config(repository / "proposal.toml")

    assert replace(unified, config_path=dedicated.config_path) == dedicated
    assert not check_project(dedicated.config_path).diagnostics
    assert expected_index_text(dedicated, load_repository(dedicated)) == dedicated.index_path.read_text()


@pytest.mark.parametrize("embedded", [False, True])
def test_domains_can_use_independent_files(repository: Path, embedded: bool) -> None:
    unified = repository / "zendev.toml"
    unified.unlink()
    if embedded:
        unified = repository / "pyproject.toml"
        message = '[tool.zendev]\nversion = 1\n[tool.zendev.message]\nprofile = "conventional"\n'
    else:
        message = 'version = 1\n[message]\nprofile = "conventional"\n'
    unified.write_text(message)
    nested = repository / "veps"
    (nested / "pyproject.toml").write_text('[project]\nname = "unrelated"\n')

    assert load_config(start=nested).config_path == repository / "proposal.toml"
    selected = load_message_config(start=nested)
    assert selected.profile == "conventional"
    assert selected.source.path == unified


@pytest.mark.parametrize("embedded", [False, True])
@pytest.mark.parametrize("empty", [False, True])
def test_duplicate_proposal_sources_require_explicit_selection(repository: Path, embedded: bool, empty: bool) -> None:
    unified = repository / "zendev.toml"
    content = "version = 1\n[proposal]\n" if empty else unified.read_text()
    if embedded:
        unified.unlink()
        unified = repository / "pyproject.toml"
        content = "[tool.zendev]\n" + content.replace("[proposal", "[tool.zendev.proposal")
    unified.write_text(content)

    with pytest.raises(ToolError) as error:
        load_config(start=repository)
    assert error.value.diagnostic.code == "config.conflict"
    assert "proposal.toml" in error.value.diagnostic.message
    assert unified.name in error.value.diagnostic.message
    assert load_config(repository / "proposal.toml").prefix == "VEP"
    if not empty:
        assert load_config(unified).prefix == "VEP"


def test_nearer_unified_source_does_not_inherit_proposal_policy(repository: Path) -> None:
    nested = repository / "veps"
    (nested / "zendev.toml").write_text('version = 1\n[message]\nprofile = "conventional"\n')

    with pytest.raises(ToolError) as error:
        load_config(start=nested)

    assert error.value.diagnostic.code == "proposal.config.missing"
    assert error.value.diagnostic.path == str(nested / "zendev.toml")


def test_discovery_observations_invalidate_repair_plan(repository: Path) -> None:
    dedicated = repository / "proposal.toml"
    policy_bytes = dedicated.read_bytes()
    dedicated.unlink()
    (repository / "veps-index.json").unlink()
    with source_session():
        config = load_config(start=repository)
        plan = plan_changes(config)
    dedicated.write_bytes(policy_bytes)

    with pytest.raises(ToolError) as error:
        apply_plan(plan)

    assert error.value.diagnostic.code == "proposal.fix.changed"
    assert not config.index_path.exists()


@pytest.mark.parametrize(
    ("dedicated", "output_name", "present"),
    [
        (True, "zendev.toml", True),
        (True, "zendev.toml", False),
        (True, "pyproject.toml", True),
        (True, "pyproject.toml", False),
        (False, "proposal.toml", False),
    ],
)
@pytest.mark.parametrize("explicit", [False, True])
def test_index_cannot_overwrite_or_create_a_configuration_source(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    dedicated: bool,
    output_name: str,
    present: bool,
    explicit: bool,
) -> None:
    if dedicated:
        (repository / "zendev.toml").unlink()
        policy = repository / "proposal.toml"
    else:
        (repository / "proposal.toml").unlink()
        policy = repository / "zendev.toml"
    policy.write_text(policy.read_text().replace('"veps-index.json"', f'"{output_name}"'))
    output = repository / output_name
    if present:
        header = "[tool.zendev]\n" if output_name == "pyproject.toml" else ""
        output.write_text(header + "version = 1\n")
    original_policy = policy.read_bytes()
    original_output = output.read_bytes() if present else None
    monkeypatch.chdir(repository)
    arguments = ["check", "--fix", "--format", "json"]
    if explicit:
        arguments.extend(["--config", str(policy)])

    result = CliRunner().invoke(app, arguments)

    assert result.exit_code == 2, result.output
    assert json.loads(result.stdout)["diagnostics"][0]["code"] == "proposal.config.output-conflict"
    assert policy.read_bytes() == original_policy
    assert (output.read_bytes() if output.exists() else None) == original_output


@pytest.mark.parametrize("explicit", [False, True])
def test_symlinked_dedicated_entry_has_consistent_layout_and_paths(
    repository: Path, monkeypatch: pytest.MonkeyPatch, explicit: bool
) -> None:
    (repository / "zendev.toml").unlink()
    policy = repository / "proposal.toml"
    target = repository / "policy.toml"
    policy.rename(target)
    policy.symlink_to(target.name)
    original = target.read_bytes()
    assert load_config(policy) == load_config(start=repository)
    index = repository / "veps-index.json"
    original_index = index.read_bytes()
    index.unlink()
    monkeypatch.chdir(repository)

    assert not check_project(policy if explicit else None, fix=True).diagnostics

    assert index.read_bytes() == original_index
    assert policy.is_symlink()
    assert target.read_bytes() == original


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("unified", [False, True])
def test_dedicated_policy_works_from_nested_directory(
    repository: Path, monkeypatch: pytest.MonkeyPatch, explicit: bool, unified: bool
) -> None:
    (repository / "zendev.toml").unlink()
    monkeypatch.chdir(repository / "veps")
    arguments = ["proposal", "check"] if unified else ["check"]
    if explicit:
        arguments.extend(["--config", "../proposal.toml"])
    arguments.extend(["--format", "json"])

    result = CliRunner().invoke(unified_app if unified else app, arguments)

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["ok"]


def test_diff_and_fix_preserve_dedicated_policy_bytes(repository: Path) -> None:
    policy = repository / "proposal.toml"
    original_policy = policy.read_bytes()
    index = repository / "veps-index.json"
    original_index = index.read_bytes()
    index.unlink()

    preview = check_project(policy, diff=True)
    assert {d.code for d in preview.diagnostics} == {"proposal.index.drift"}
    assert not index.exists()
    assert policy.read_bytes() == original_policy

    assert not check_project(policy, fix=True).diagnostics
    assert index.read_bytes() == original_index
    assert policy.read_bytes() == original_policy
    assert not check_project(policy, diff=True).patch


def test_dedicated_policy_changes_invalidate_repair_plan(repository: Path) -> None:
    policy = repository / "proposal.toml"
    config = load_config(policy)
    config.index_path.unlink()
    plan = plan_changes(config)
    policy.write_text(policy.read_text() + "\n# Concurrent policy edit\n")

    with pytest.raises(ToolError) as error:
        apply_plan(plan)

    assert error.value.diagnostic.code == "proposal.fix.changed"
    assert not config.index_path.exists()


@pytest.mark.parametrize(
    ("before", "after", "code"),
    [
        ("version = 1", "version = true", "config.version"),
        ("[templates]", "[unknown]", "proposal.config.unknown-key"),
        ('index = "veps-index.json"', "index = 1", "proposal.config.type"),
        ("[index]", '[index]\npath = "second.json"', "proposal.config.unknown-key"),
        ("[graph]", "[proposal.graph]", "proposal.config.unknown-key"),
    ],
)
def test_dedicated_policy_rejects_invalid_or_mixed_layout(repository: Path, before: str, after: str, code: str) -> None:
    policy = repository / "proposal.toml"
    policy.write_text(policy.read_text().replace(before, after))

    result = CliRunner().invoke(app, ["check", "--config", str(policy), "--format", "json"])

    assert result.exit_code == 2
    diagnostic = json.loads(result.stdout)["diagnostics"][0]
    assert diagnostic["code"] == code
    assert diagnostic["path"] == str(policy)
