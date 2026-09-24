"""Public planning verifies all observed inputs before its only write boundary."""

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from zendev.core.diagnostics import ToolError
from zendev.proposal import apply_plan, check_project, load_config, plan_changes
from zendev.proposal.cli import app


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "sep"
    shutil.copytree(Path(__file__).parent / "fixtures/proposal/sep", root)
    return root


def test_plan_rejects_stale_configuration_object(repository: Path) -> None:
    path = repository / "zendev.toml"
    config = load_config(path)
    path.write_text(path.read_text().replace('prefix = "SEP"', 'prefix = "OTHER"'))
    with pytest.raises(ToolError) as error:
        plan_changes(config)
    assert error.value.diagnostic.code == "proposal.fix.changed"


def test_new_index_cannot_be_overwritten_after_planning(repository: Path) -> None:
    config = load_config(repository / "zendev.toml")
    config.index_path.unlink()
    plan = plan_changes(config)
    assert plan.applicable
    assert plan.before[config.index_path] is None
    config.index_path.write_text("concurrent content\n")
    with pytest.raises(ToolError) as error:
        apply_plan(plan)
    assert error.value.diagnostic.code == "proposal.fix.changed"
    assert config.index_path.read_text() == "concurrent content\n"


def test_schema_references_outside_schema_directory_join_snapshot(repository: Path) -> None:
    schema = repository / "schemas/sep.schema.json"
    shared = repository / "shared.json"
    shared.write_bytes(schema.read_bytes())
    schema.write_text('{"$ref": "../shared.json"}')
    config = load_config(repository / "zendev.toml")
    config.index_path.unlink()
    plan = plan_changes(config)
    assert plan.applicable
    assert shared in plan.before
    shared.write_text("{}")
    with pytest.raises(ToolError) as error:
        apply_plan(plan)
    assert error.value.diagnostic.code == "proposal.fix.changed"
    assert not config.index_path.exists()


def test_runs_do_not_reuse_previous_source_bytes(repository: Path) -> None:
    path = repository / "zendev.toml"
    assert not check_project(path).diagnostics
    document = repository / "seps/SEP-0000-process.md"
    document.write_text(document.read_text().replace("# SEP-0000:", "# SEP-9999:"))
    assert check_project(path).diagnostics


def test_malformed_html_link_keeps_structured_output(repository: Path) -> None:
    document = repository / "seps/SEP-0000-process.md"
    document.write_text(document.read_text() + '\n<a href="http://[bad">broken</a>\n')
    result = CliRunner().invoke(app, ["check", "--config", str(repository / "zendev.toml"), "--format", "json"])
    assert result.exit_code == 1
    diagnostics = json.loads(result.stdout)["diagnostics"]
    diagnostic = next(d for d in diagnostics if d["code"] == "proposal.link.invalid")
    assert diagnostic["path"] == "seps/SEP-0000-process.md" and diagnostic["line"] > 1
