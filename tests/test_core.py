"""Shared discovery, source lifetimes, and diagnostic format contracts."""

import json
from pathlib import Path

import pytest

from zendev.core.config import load_project_config
from zendev.core.diagnostics import Diagnostic, OutputFormat, ToolError, render_report
from zendev.core.markdown import markdown_session, scan_markdown
from zendev.core.source import exists, read_text, source_session
from zendev.message.config import load_message_config


@pytest.mark.parametrize("embedded", [False, True])
def test_configuration_sources_share_model(tmp_path: Path, embedded: bool) -> None:
    name = "pyproject.toml" if embedded else "zendev.toml"
    text = "[tool.zendev]\nversion = 1\n[tool.zendev.message]\n" if embedded else "version = 1\n[message]\n"
    (tmp_path / name).write_text(text + 'profile = "conventional"\n')
    result = load_message_config(start=tmp_path)
    assert result.profile == "conventional"
    assert result.source.path == tmp_path / name


def test_nested_unrelated_pyproject_does_not_mask_config(tmp_path: Path) -> None:
    (tmp_path / "zendev.toml").write_text('version = 1\n[message]\nprofile = "gitmoji"\n')
    nested = tmp_path / "pkg"
    nested.mkdir()
    (nested / "pyproject.toml").write_text('[project]\nname = "other"\n')
    assert load_project_config(start=nested).root == tmp_path
    (nested / "zendev.toml").write_text("version = 1\n")
    assert load_project_config(start=nested).root == nested


@pytest.mark.parametrize("git_directory", [False, True])
def test_discovery_stops_at_git_root_or_worktree_file(tmp_path: Path, git_directory: bool) -> None:
    (tmp_path / "zendev.toml").write_text("version = 1\n")
    nested = tmp_path / "repo"
    nested.mkdir()
    marker = nested / ".git"
    if git_directory:
        marker.mkdir()
    else:
        marker.write_text("gitdir: /unused\n")
    assert load_project_config(start=nested).path is None


def test_source_conflict_and_explicit_selection(tmp_path: Path) -> None:
    standalone = tmp_path / "zendev.toml"
    standalone.write_text("version = 1\n")
    (tmp_path / "pyproject.toml").write_text("[tool.zendev]\nversion = 1\n")
    with pytest.raises(ToolError) as error:
        load_project_config(start=tmp_path)
    assert error.value.diagnostic.code == "config.conflict"
    assert load_project_config(standalone).path == standalone


@pytest.mark.parametrize(
    ("name", "text", "code"),
    [
        ("proposal.toml", "version = 1\n", "config.migration"),
        ("zendev.toml", "version = 2\n", "config.version"),
        ("zendev.toml", "version = true\n", "config.version"),
        ("pyproject.toml", '[tool.zendev.commit]\nprofile = "zendev"\n', "config.migration"),
        ("zendev.toml", "version = 1\nunknown = 2\n", "config.invalid"),
    ],
)
def test_invalid_or_old_configuration_is_actionable(tmp_path: Path, name: str, text: str, code: str) -> None:
    (tmp_path / name).write_text(text)
    with pytest.raises(ToolError) as error:
        load_project_config(start=tmp_path)
    assert error.value.diagnostic.code == code


def test_cli_override_does_not_hide_invalid_configuration(tmp_path: Path) -> None:
    source = tmp_path / "zendev.toml"
    source.write_text('version = 1\n[message]\nprofile = "invalid"\n')
    with pytest.raises(ToolError):
        load_message_config(source, profile="zendev")


def test_source_session_records_absence_and_avoids_cross_run_cache(tmp_path: Path) -> None:
    source = tmp_path / "input.md"
    with source_session() as snapshot:
        assert not exists(source)
        source.write_text("first")
        assert not exists(source)
        assert snapshot.files[source] is None
    with source_session():
        assert read_text(source) == "first"
        source.write_text("second")
        assert read_text(source) == "first"
        with source_session(fresh=True):
            assert read_text(source) == "second"
        assert read_text(source) == "first"
    assert read_text(source) == "second"


def test_markdown_cache_is_scoped() -> None:
    with markdown_session():
        original = scan_markdown("## Section")
        assert scan_markdown("## Section") is original
    with markdown_session():
        assert scan_markdown("## Section") is not original


def test_renderers_share_diagnostics_and_escape_annotation_data() -> None:
    diagnostic = Diagnostic("example.code", "line one\n::error::line two%", path="a,b:c.md", line=2, hint="fix it")
    payload = json.loads(render_report((diagnostic,), command="check", output_format=OutputFormat.JSON))
    assert payload["schema_version"] == 1
    assert payload["ok"] is False
    assert payload["diagnostics"] == [diagnostic.as_dict()]
    github = render_report((diagnostic,), command="check", output_format=OutputFormat.GITHUB)
    assert github.count("\n") == 0
    assert "a%2Cb%3Ac.md" in github
    assert "%0A" in github and "%25" in github
