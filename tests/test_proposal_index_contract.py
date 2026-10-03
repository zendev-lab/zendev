"""Failure and projection contracts for the numeric proposal index."""

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from zendev.core.diagnostics import ToolError
from zendev.proposal import build_index, expected_index_text, load_config
from zendev.proposal.cli import app
from zendev.proposal.repository import load_repository


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "vep"
    shutil.copytree(Path(__file__).parent / "fixtures/proposal/vep", root)
    return root


@pytest.mark.parametrize("edge", ["VEP-00O1", "VEP-9999", "drafts/temporal-model.md", "https://example.com/VEP-0000"])
def test_invalid_edges_fail_all_index_entrypoints_without_writing(repository: Path, edge: str) -> None:
    proposal = repository / "veps/VEP-0001-composition.md"
    proposal.write_text(proposal.read_text().replace("VEP-0000", edge))
    config = load_config(repository / "zendev.toml")
    state = load_repository(config)
    before = config.index_path.read_bytes()
    for generate in (build_index, expected_index_text):
        with pytest.raises(ToolError) as error:
            generate(config, state)
        assert error.value.diagnostic.code in {"proposal.graph.invalid-edge", "proposal.graph.missing-target"}
        assert config.index_path.read_bytes() == before
    result = CliRunner().invoke(app, ["check", "--config", str(config.config_path), "--fix", "--format", "json"])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["summary"]["index"] == "not-checked"
    assert config.index_path.read_bytes() == before


@pytest.mark.parametrize(
    "replacement",
    [
        "",
        '  { name = "number", source = "metadata", key = "vep" },\n',
        '  "vep",\n  { name = "number", source = "metadata", key = "vep" },\n',
        '  { name = "vep", source = "path" },\n',
    ],
)
def test_identity_projection_is_required(repository: Path, replacement: str) -> None:
    policy = repository / "zendev.toml"
    policy.write_text(policy.read_text().replace('  "vep",\n', replacement))
    with pytest.raises(ToolError) as error:
        load_config(policy)
    assert error.value.diagnostic.code == "proposal.config.index-identity"


def test_removed_draft_switch_is_rejected(repository: Path) -> None:
    policy = repository / "zendev.toml"
    policy.write_text(policy.read_text().replace("[proposal.index]", "[proposal.index]\ninclude_drafts = false"))
    with pytest.raises(ToolError) as error:
        load_config(policy)
    assert error.value.diagnostic.code == "proposal.config.unknown-key"


def test_projection_uses_source_keys_and_preserves_ordinary_id(repository: Path) -> None:
    policy = repository / "zendev.toml"
    policy.write_text(
        policy.read_text().replace(
            '  "requires",',
            '  { name = "dependencies", source = "metadata", key = "requires" },\n'
            '  { name = "requires", source = "metadata", key = "authors" },\n'
            '  "id",',
        )
    )
    config = load_config(policy)
    state = load_repository(config)
    for document in state.documents:
        document.metadata["id"] = "ordinary metadata"
        document.metadata["authors"] = ["Doe, Jane"]
    entries = build_index(config, state)["veps"]
    assert isinstance(entries, list)
    assert len(entries) == 2
    assert entries[1]["vep"] == 1
    assert entries[1]["status"] == "Draft"
    assert entries[1]["dependencies"] == [0]
    assert entries[1]["requires"] == state.formal_documents[1].metadata["authors"]
    assert entries[1]["id"] == "ordinary metadata"
