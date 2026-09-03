"""Tests for repository-native proposal validation and indexing."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from zendev.proposal.cli import app as proposal_app
from zendev.proposal.config import load_config
from zendev.proposal.indexing import check_index, expected_index_text, write_index
from zendev.proposal.model import ProposalToolError
from zendev.proposal.repository import load_repository, parse_frontmatter
from zendev.proposal.validation import validate_repository

FIXTURES = Path(__file__).parent / "fixtures" / "proposal"
runner = CliRunner()


def _copy_fixture(tmp_path: Path, name: str) -> Path:
    destination = tmp_path / name
    shutil.copytree(FIXTURES / name, destination)
    return destination


def _codes(result) -> set[str]:
    return {diagnostic.code for diagnostic in result.diagnostics}


def _git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
    )


def _commit_fixture(repository: Path) -> None:
    assert _git(repository, "init", "-b", "main").returncode == 0
    assert _git(repository, "add", ".").returncode == 0
    result = _git(
        repository,
        "-c",
        "user.name=Proposal Test",
        "-c",
        "user.email=proposal@example.com",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-m",
        "fixture",
    )
    assert result.returncode == 0, result.stderr


def test_vep_fixture_validates_and_builds_inverse_index(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    config = load_config(repository / "proposal.toml")

    result = validate_repository(config)

    assert result.ok
    assert check_index(config, result.state) is None
    payload = json.loads(expected_index_text(config, result.state))
    assert payload["version"] == 2
    assert payload["veps"][0]["vep"] == 0
    assert "id" not in payload["veps"][0]
    assert payload["veps"][0]["defines"] == ["foundation"]
    assert payload["veps"][0]["required_by"] == [1]
    assert payload["veps"][1]["requires"] == [0]


def test_index_field_shorthand_matches_explicit_metadata_table(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    policy = repository / "proposal.toml"
    shorthand = load_config(policy)
    shorthand_text = expected_index_text(shorthand, load_repository(shorthand))
    policy.write_text(
        policy.read_text(encoding="utf-8").replace(
            '  "title",\n',
            '  { name = "title", source = "metadata", key = "title" },\n',
        ),
        encoding="utf-8",
    )

    explicit = load_config(policy)

    assert explicit.index.fields[2].name == "title"
    assert explicit.index.fields[2].source == "metadata"
    assert explicit.index.fields[2].key == "title"
    assert expected_index_text(explicit, load_repository(explicit)) == shorthand_text


def test_index_fields_reject_duplicate_names_across_shorthand_and_tables(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    policy = repository / "proposal.toml"
    policy.write_text(
        policy.read_text(encoding="utf-8").replace(
            '  "title",\n',
            '  "title",\n  { name = "title", source = "metadata", key = "title" },\n',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ProposalToolError) as error:
        load_config(policy)

    assert error.value.diagnostic.code == "proposal.config.duplicate"


def test_identifier_index_source_is_rejected(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    policy = repository / "proposal.toml"
    policy.write_text(
        policy.read_text(encoding="utf-8").replace(
            '{ name = "path", source = "path" }',
            '{ name = "id", source = "identifier" }',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ProposalToolError) as error:
        load_config(policy)

    assert error.value.diagnostic.code == "proposal.config.index-source"


def test_index_version_one_is_rejected(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    policy = repository / "proposal.toml"
    policy.write_text(
        policy.read_text(encoding="utf-8").replace(
            "[index]\nversion = 2\n",
            "[index]\nversion = 1\n",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ProposalToolError) as error:
        load_config(policy)

    assert error.value.diagnostic.code == "proposal.config.index-version"


def test_empty_index_field_shorthand_is_rejected(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    policy = repository / "proposal.toml"
    policy.write_text(
        policy.read_text(encoding="utf-8").replace('  "title",\n', '  "",\n'),
        encoding="utf-8",
    )

    with pytest.raises(ProposalToolError) as error:
        load_config(policy)

    assert error.value.diagnostic.code == "proposal.config.type"


def test_repository_without_drafts_does_not_require_a_draft_directory(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    policy = repository / "proposal.toml"
    policy.write_text(
        policy.read_text(encoding="utf-8").replace(
            """[drafts]
directory = "drafts"
schema = "schemas/draft.schema.json"
marker = "> Pre-VEP design draft. Non-normative."
pre_proposal = true

""",
            "",
        ),
        encoding="utf-8",
    )
    shutil.rmtree(repository / "drafts")

    config = load_config(policy)
    result = validate_repository(config)

    assert result.ok
    assert result.state.draft_count == 0
    assert len(result.state.documents) == 2


def test_sep_frontmatter_draft_is_validated_and_indexed(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "sep")
    config = load_config(repository / "proposal.toml")

    result = validate_repository(config)

    assert result.ok
    assert len(result.state.documents) == 2
    payload = json.loads(expected_index_text(config, result.state))
    assert payload["version"] == 2
    assert payload["documents"][1]["sep"] is None
    assert payload["documents"][0]["authors"] == ["Doe, Jane"]
    assert payload["documents"][0]["requires"] == []
    assert payload["documents"][1]["requires"] == [0]


def test_real_yaml_parser_preserves_quoted_commas_and_rejects_duplicate_keys() -> None:
    assert parse_frontmatter('authors: ["Doe, Jane"]\n', "example.md") == {"authors": ["Doe, Jane"]}
    assert parse_frontmatter("created: 2026-08-25\n", "example.md") == {"created": "2026-08-25"}
    with pytest.raises(ValueError, match="duplicate key"):
        parse_frontmatter("title: One\ntitle: Two\n", "example.md")
    with pytest.raises(ValueError, match="invalid YAML"):
        parse_frontmatter("value: !!python/object:builtins.object {}\n", "example.md")


def test_nested_config_keys_fail_closed(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    policy = repository / "proposal.toml"
    policy.write_text(
        policy.read_text(encoding="utf-8").replace(
            "minimum_sentences = 2\n",
            "minimum_sentences = 2\nminimum_sentence = 2\n",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ProposalToolError) as error:
        load_config(policy)

    assert error.value.diagnostic.code == "proposal.config.unknown-key"


def test_drafts_are_validated_against_their_configured_schema(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    draft = repository / "drafts" / "temporal-model.md"
    draft.write_text(
        draft.read_text(encoding="utf-8").replace("defines: []\n", ""),
        encoding="utf-8",
    )

    result = validate_repository(load_config(repository / "proposal.toml"))

    diagnostic = next(item for item in result.diagnostics if item.code == "proposal.frontmatter.schema")
    assert diagnostic.path == "drafts/temporal-model.md"


def test_missing_metadata_reports_schema_diagnostic_instead_of_crashing(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    proposal = repository / "veps" / "VEP-0001-composition.md"
    proposal.write_text(
        proposal.read_text(encoding="utf-8").replace("status: Draft\n", ""),
        encoding="utf-8",
    )

    result = validate_repository(load_config(repository / "proposal.toml"))

    assert "proposal.frontmatter.schema" in _codes(result)


def test_noncanonical_markdown_filename_cannot_bypass_discovery(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    shutil.copy(
        repository / "veps" / "VEP-0001-composition.md",
        repository / "veps" / "composition.md",
    )

    result = validate_repository(load_config(repository / "proposal.toml"))

    assert "proposal.filename.invalid" in _codes(result)


def test_template_headings_are_the_executable_section_policy(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    proposal = repository / "veps" / "VEP-0001-composition.md"
    proposal.write_text(
        proposal.read_text(encoding="utf-8").replace("## Motivation", "## Why"),
        encoding="utf-8",
    )

    result = validate_repository(load_config(repository / "proposal.toml"))

    diagnostic = next(item for item in result.diagnostics if item.code == "proposal.sections.missing")
    assert "Motivation" in diagnostic.message


def test_pre_proposal_cannot_reserve_a_concrete_identifier(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    draft = repository / "drafts" / "temporal-model.md"
    draft.write_text(
        draft.read_text(encoding="utf-8") + "\nThis might become VEP-0042.\n",
        encoding="utf-8",
    )

    result = validate_repository(load_config(repository / "proposal.toml"))

    assert "proposal.draft.concrete-id" in _codes(result)


def test_proposal_draft_uses_the_configured_summary_policy(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "sep")
    draft = repository / "drafts" / "script-mode.md"
    draft.write_text(
        draft.read_text(encoding="utf-8").replace(
            "Explore script mode. Keep the record provisional.",
            "Explore script mode.",
        ),
        encoding="utf-8",
    )

    result = validate_repository(load_config(repository / "proposal.toml"))

    diagnostic = next(item for item in result.diagnostics if item.code == "proposal.summary.sentence-count")
    assert diagnostic.path == "drafts/script-mode.md"


def test_graph_rejects_missing_targets(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    proposal = repository / "veps" / "VEP-0001-composition.md"
    proposal.write_text(
        proposal.read_text(encoding="utf-8").replace("VEP-0000", "VEP-9999"),
        encoding="utf-8",
    )

    result = validate_repository(load_config(repository / "proposal.toml"))

    assert "proposal.graph.missing-target" in _codes(result)


def test_graph_rejects_noncanonical_edges_even_when_schema_is_permissive(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    proposal = repository / "veps" / "VEP-0001-composition.md"
    proposal.write_text(
        proposal.read_text(encoding="utf-8").replace("VEP-0000", "VEP-0"),
        encoding="utf-8",
    )

    result = validate_repository(load_config(repository / "proposal.toml"))

    assert "proposal.graph.invalid-edge" in _codes(result)


def test_graph_rejects_requires_cycles(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    proposal = repository / "veps" / "VEP-0000-foundation.md"
    proposal.write_text(
        proposal.read_text(encoding="utf-8").replace("requires: []", "requires: [VEP-0001]"),
        encoding="utf-8",
    )

    result = validate_repository(load_config(repository / "proposal.toml"))

    assert "proposal.graph.requires-cycle" in _codes(result)


def test_index_drift_is_read_only_until_write_is_explicit(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    config = load_config(repository / "proposal.toml")
    state = load_repository(config)
    config.index_path.write_text("{}\n", encoding="utf-8")

    diagnostic = check_index(config, state)
    assert diagnostic is not None
    assert diagnostic.code == "proposal.index.drift"
    assert config.index_path.read_text(encoding="utf-8") == "{}\n"
    assert write_index(config, state)
    assert check_index(config, state) is None
    assert not write_index(config, state)


def test_check_cli_emits_stable_json(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")

    result = runner.invoke(proposal_app, ["check", "--config", str(repository / "proposal.toml"), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload == {
        "command": "check",
        "diagnostics": [],
        "ok": True,
        "schema_version": 1,
        "summary": {
            "drafts": 1,
            "formal_proposals": 2,
            "index": "up-to-date",
        },
    }


def test_check_cli_distinguishes_validation_and_tool_errors(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    draft = repository / "drafts" / "temporal-model.md"
    draft.write_text(draft.read_text(encoding="utf-8") + "\nVEP-0042\n", encoding="utf-8")

    validation = runner.invoke(
        proposal_app,
        ["check", "--config", str(repository / "proposal.toml"), "--json"],
    )
    tool = runner.invoke(
        proposal_app,
        ["check", "--config", str(repository / "missing.toml"), "--json"],
    )
    validation_payload = json.loads(validation.stdout)
    tool_payload = json.loads(tool.stdout)

    assert validation.exit_code == 1
    assert validation_payload["diagnostics"][0]["code"] == "proposal.draft.concrete-id"
    assert tool.exit_code == 2
    assert tool_payload["diagnostics"][0]["code"] == "proposal.config.missing"


def test_index_cli_writes_only_with_explicit_write(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    index = repository / "veps-index.json"
    index.write_text("{}\n", encoding="utf-8")

    checked = runner.invoke(
        proposal_app,
        ["index", "--config", str(repository / "proposal.toml"), "--check"],
    )

    assert checked.exit_code == 1
    assert index.read_text(encoding="utf-8") == "{}\n"
    written = runner.invoke(
        proposal_app,
        ["index", "--config", str(repository / "proposal.toml"), "--write"],
    )
    assert written.exit_code == 0
    entry = json.loads(index.read_text(encoding="utf-8"))["veps"][0]
    assert entry["vep"] == 0
    assert "id" not in entry


@pytest.mark.parametrize("operation", [[], ["--check", "--write"]])
def test_index_cli_requires_exactly_one_operation(operation: list[str]) -> None:
    result = runner.invoke(proposal_app, ["index", *operation])

    assert result.exit_code == 2
    assert "exactly one of --check or --write is required" in result.output


def test_history_rejects_invalid_transition(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    _commit_fixture(repository)
    proposal = repository / "veps" / "VEP-0000-foundation.md"
    proposal.write_text(
        proposal.read_text(encoding="utf-8").replace("status: Accepted", "status: Draft"),
        encoding="utf-8",
    )

    result = validate_repository(load_config(repository / "proposal.toml"), base_ref="HEAD")

    assert "proposal.history.invalid-transition" in _codes(result)


def test_history_allows_an_exact_documented_waiver(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    _commit_fixture(repository)
    proposal = repository / "veps" / "VEP-0000-foundation.md"
    proposal.write_text(
        proposal.read_text(encoding="utf-8").replace("status: Accepted", "status: Draft"),
        encoding="utf-8",
    )
    policy = repository / "proposal.toml"
    policy.write_text(
        policy.read_text(encoding="utf-8")
        + """

[[history.waivers]]
path = "veps/VEP-0000-foundation.md"
from_status = "Accepted"
to_status = "Draft"
reason = "Fixture-only bootstrap correction."
""",
        encoding="utf-8",
    )

    result = validate_repository(load_config(policy), base_ref="HEAD")

    assert "proposal.history.invalid-transition" not in _codes(result)


def test_history_rejects_deleted_formal_records(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    _commit_fixture(repository)
    (repository / "veps" / "VEP-0001-composition.md").unlink()

    result = validate_repository(load_config(repository / "proposal.toml"), base_ref="HEAD")

    assert "proposal.history.deleted" in _codes(result)


def test_history_fails_closed_on_invalid_base_frontmatter(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    proposal = repository / "veps" / "VEP-0000-foundation.md"
    proposal.write_text(
        proposal.read_text(encoding="utf-8").replace(
            "status: Accepted\n",
            "status: Accepted\nstatus: Draft\n",
        ),
        encoding="utf-8",
    )
    _commit_fixture(repository)
    proposal.write_text(
        proposal.read_text(encoding="utf-8").replace("status: Accepted\nstatus: Draft\n", "status: Accepted\n"),
        encoding="utf-8",
    )

    with pytest.raises(ProposalToolError) as error:
        validate_repository(load_config(repository / "proposal.toml"), base_ref="HEAD")

    assert error.value.diagnostic.code == "proposal.history.frontmatter"


def test_missing_base_ref_is_a_tool_error(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    _commit_fixture(repository)

    with pytest.raises(ProposalToolError) as error:
        validate_repository(load_config(repository / "proposal.toml"), base_ref="missing")

    assert error.value.diagnostic.code == "proposal.history.base-ref"


def test_defines_requires_a_matching_anchor(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    draft = repository / "drafts" / "temporal-model.md"
    draft.write_text(
        draft.read_text(encoding="utf-8").replace("defines: []\n", "defines:\n  - tempo\n"),
        encoding="utf-8",
    )

    result = validate_repository(load_config(repository / "proposal.toml"))

    assert "proposal.defines.missing-anchor" in _codes(result)


def test_defines_rejects_an_undeclared_anchor(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    draft = repository / "drafts" / "temporal-model.md"
    draft.write_text(
        draft.read_text(encoding="utf-8") + '\n<a id="term-tempo"></a>\n',
        encoding="utf-8",
    )

    result = validate_repository(load_config(repository / "proposal.toml"))

    assert "proposal.defines.undeclared-anchor" in _codes(result)


def test_defines_rejects_duplicate_current_owners(tmp_path: Path) -> None:
    repository = _copy_fixture(tmp_path, "vep")
    first = repository / "drafts" / "temporal-model.md"
    second = repository / "drafts" / "other-model.md"
    first.write_text(
        first.read_text(encoding="utf-8").replace("defines: []\n", "defines:\n  - tempo\n")
        + '\n<a id="term-tempo"></a>\n',
        encoding="utf-8",
    )
    second.write_text(
        '---\ntitle: "Other model"\ndefines:\n  - tempo\n---\n\n# Other model\n\n'
        '> Pre-VEP design draft. Non-normative.\n\n<a id="term-tempo"></a>\n',
        encoding="utf-8",
    )

    result = validate_repository(load_config(repository / "proposal.toml"))

    assert "proposal.defines.duplicate-owner" in _codes(result)
