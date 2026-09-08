"""End-to-end regressions for the complete proposal audit."""

import json
import os
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from zendev.proposal.cli import app
from zendev.proposal.config import load_config
from zendev.proposal.model import GraphPolicy, ProposalToolError
from zendev.proposal.transaction import commit_files, snapshot_inputs
from zendev.proposal.validation import validate_repository, validate_state


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return Path(shutil.copytree(Path(__file__).parent / "fixtures/proposal/vep", tmp_path / "repo"))


def change(repo: Path, path: str, old: str, new: str) -> None:
    target = repo / path
    target.write_text(target.read_text().replace(old, new))


def invoke(repo: Path, *args: str):
    result = CliRunner().invoke(app, ["check", "--config", str(repo / "proposal.toml"), "--json", *args])
    assert result.stdout, repr(result.exception)
    return result.exit_code, json.loads(result.stdout)


def codes(payload):
    return {d["code"] for d in payload["diagnostics"]}


def snapshot(repo: Path):
    return {str(p.relative_to(repo)): p.read_bytes() for p in repo.rglob("*") if p.is_file()}


@pytest.mark.parametrize(
    "output", ["schemas/vep.schema.json", "proposal.toml", "templates/technical.md", "veps/new.json", "schemas"]
)
def test_output_cannot_overwrite_inputs(repo: Path, output: str) -> None:
    change(repo, "proposal.toml", 'index = "veps-index.json"', f'index = "{output}"')
    before = snapshot(repo)
    code, payload = invoke(repo, "--fix")
    assert code == 2 and "proposal.config.output-conflict" in codes(payload)
    assert snapshot(repo) == before


def test_output_hardlink_is_rejected(repo: Path) -> None:
    index = repo / "veps-index.json"
    index.unlink()
    os.link(repo / "schemas/vep.schema.json", index)
    before = snapshot(repo)
    assert invoke(repo, "--fix")[0] == 2
    assert snapshot(repo) == before


@pytest.mark.parametrize("mutation", ["boolean", "utf8", "reference", "format", "yaml", "roles", "states", "marker"])
def test_errors_always_emit_structured_diagnostics(repo: Path, mutation: str) -> None:
    match mutation:
        case "boolean":
            change(repo, "proposal.toml", "version = 1", "version = true")
        case "utf8":
            (repo / "proposal.toml").write_bytes(b"\xff")
        case "reference":
            (repo / "schemas/draft.schema.json").write_text('{"$ref":"#/$defs/nope"}')
        case "format":
            (repo / "schemas/draft.schema.json").write_text('{"format":"dtae"}')
        case "yaml":
            change(repo, "drafts/temporal-model.md", "defines: []", "defines: !!set {a: null}")
        case "roles":
            change(repo, "proposal.toml", 'number_field = "vep"', 'number_field = "title"')
        case "states":
            change(repo, "proposal.toml", 'Draft = ["Draft", "Review", "Withdrawn"]', 'Draft = ["Drfat"]')
        case "marker":
            change(repo, "proposal.toml", 'marker = "> Pre-VEP design draft. Non-normative."', 'marker = "   "')
    code, payload = invoke(repo)
    assert code in {1, 2} and payload["ok"] is False and payload["diagnostics"]


def test_local_schema_references_work_offline(repo: Path) -> None:
    schema = repo / "schemas/draft.schema.json"
    shutil.copy(schema, repo / "schemas/shared.json")
    schema.write_text('{"$ref":"shared.json"}')
    assert invoke(repo)[0] == 0


@pytest.mark.parametrize("path", ["veps/BAD.MD", "veps/nested/bad.md"])
def test_unsupported_markdown_layout_is_not_silently_ignored(repo: Path, path: str) -> None:
    target = repo / path
    target.parent.mkdir(exist_ok=True)
    target.write_text("bad")
    assert "proposal.document.layout" in codes(invoke(repo)[1])


def test_indented_h1_is_not_a_heading(repo: Path) -> None:
    change(repo, "drafts/temporal-model.md", "# Temporal model", "    # Temporal model")
    assert "proposal.h1.missing" in codes(invoke(repo)[1])


def test_html_comment_marker_is_supported(repo: Path) -> None:
    for path in ["proposal.toml", "drafts/temporal-model.md"]:
        change(repo, path, "> Pre-VEP design draft. Non-normative.", "<!-- draft -->")
    assert invoke(repo)[0] == 0
    change(repo, "drafts/temporal-model.md", "<!-- draft -->", "")
    assert invoke(repo, "--fix")[0] == 0


def test_examples_are_not_status_or_identity_declarations(repo: Path) -> None:
    path = repo / "drafts/temporal-model.md"
    path.write_text(
        path.read_text() + "\n```yaml\nstatus: Draft\nVEP-0042\n```\n\n`VEP-0042`\n<!-- status: Draft -->\n"
    )
    assert invoke(repo)[0] == 0


def test_draft_relationship_targets_are_checked(repo: Path) -> None:
    schema = repo / "schemas/draft.schema.json"
    value = json.loads(schema.read_text())
    value["additionalProperties"] = True
    schema.write_text(json.dumps(value))
    change(repo, "drafts/temporal-model.md", "defines: []", "defines: []\nrequires: [9999]")
    assert "proposal.graph.missing-target" in codes(invoke(repo)[1])


def test_generic_relation_can_be_acyclic_without_status_role(repo: Path) -> None:
    config = load_config(repo / "proposal.toml")
    state = validate_repository(config).state
    a, b = state.formal_documents
    docs = (replace(a, metadata={**a.metadata, "requires": ["VEP-0001"]}), b)
    config = replace(config, graph=GraphPolicy(fields=("requires",), acyclic_fields=("requires",)))
    result = validate_state(config, replace(state, formal_documents=docs, documents=docs))
    assert "proposal.graph.requires-cycle" in {d.code for d in result.diagnostics}


def test_supersession_chain_reaches_current_owner(repo: Path) -> None:
    config = load_config(repo / "proposal.toml")
    state = validate_repository(config).state
    a, b = state.formal_documents
    (repo / "schemas/vep.schema.json").write_text("{}")
    docs = (
        replace(a, metadata={**a.metadata, "status": "Superseded", "supersedes": []}),
        replace(b, metadata={**b.metadata, "status": "Superseded", "supersedes": [0], "requires": []}),
        replace(
            b,
            path=repo / "veps/VEP-0002-current.md",
            relative_path="veps/VEP-0002-current.md",
            body=b.body.replace("# VEP-0001:", "# VEP-0002:"),
            metadata={**b.metadata, "vep": 2, "status": "Accepted", "supersedes": [1], "requires": []},
        ),
    )
    config = replace(config, graph=GraphPolicy(fields=("supersedes",), supersedes_field="supersedes"), defines=None)
    result = validate_state(config, replace(state, formal_documents=docs, documents=docs))
    assert not [d for d in result.diagnostics if d.code.startswith("proposal.graph")]


def test_history_resolves_config_subdirectory(repo: Path) -> None:
    root = repo.parent
    for args in [
        ("init",),
        ("add", "."),
        (
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-m",
            "fixture",
        ),
    ]:
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    assert invoke(repo, "--base-ref", "HEAD")[0] == 0


def test_unknown_index_key_does_not_turn_into_null(repo: Path) -> None:
    change(repo, "proposal.toml", '  "title",', '  "titlle",')
    before = snapshot(repo)
    code, payload = invoke(repo, "--fix")
    assert code == 1 and "proposal.index.unknown-field" in codes(payload)
    assert snapshot(repo) == before


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ("[bad](missing.md)", "proposal.link.missing-target"),
        ("[bad](#missing)", "proposal.link.missing-fragment"),
        ('<a id="same"></a>\n\n<a id="same"></a>', "proposal.anchor.duplicate-id"),
    ],
)
def test_local_links_and_ids(repo: Path, body: str, code: str) -> None:
    path = repo / "drafts/temporal-model.md"
    path.write_text(path.read_text() + "\n" + body + "\n")
    assert code in codes(invoke(repo)[1])


def test_github_heading_fragments_are_explicitly_selected(repo: Path) -> None:
    path = repo / "drafts/temporal-model.md"
    path.write_text(path.read_text() + "\n## 中文 `name`\n\n## 中文 `name`\n\n[ok](#中文-name-1)\n")
    assert "proposal.link.missing-fragment" in codes(invoke(repo)[1])
    policy = repo / "proposal.toml"
    policy.write_text(policy.read_text() + '\n[links]\nheading_ids = "github"\n')
    assert invoke(repo)[0] == 0


@pytest.mark.parametrize(
    ("setting", "mutation", "code"),
    [
        ("nonempty = true", "empty", "empty"),
        ("ordered = true", "order", "order"),
        ("no_skip_levels = true", "level", "level"),
        ('placeholders = ["TBD"]', "placeholder", "placeholder"),
    ],
)
def test_section_rules_are_repository_owned(repo: Path, setting: str, mutation: str, code: str) -> None:
    policy = repo / "proposal.toml"
    policy.write_text(policy.read_text() + "\n[sections]\n" + setting + "\n")
    path = repo / "veps/VEP-0000-foundation.md"
    text = path.read_text()
    if mutation == "empty":
        text = text.replace("Define the base proposal model.", "")
    if mutation == "order":
        text = (
            text.replace("## Summary", "## Temporary")
            .replace("## Motivation", "## Summary")
            .replace("## Temporary", "## Motivation")
        )
    if mutation == "level":
        text += "\n#### Jump\n"
    if mutation == "placeholder":
        text += "\nTBD\n"
    path.write_text(text)
    assert f"proposal.sections.{code}" in codes(invoke(repo)[1])


@pytest.mark.parametrize("omission", ["number", "title", "defines"])
def test_missing_metadata_is_repaired_from_evidence(repo: Path, omission: str) -> None:
    path = "drafts/temporal-model.md" if omission == "defines" else "veps/VEP-0000-foundation.md"
    line = {"number": "vep: 0\n", "title": 'title: "Foundation"\n', "defines": "defines: []\n"}[omission]
    change(repo, path, line, "")
    assert invoke(repo, "--fix")[0] == 0
    assert invoke(repo)[0] == 0


def test_title_format_and_duplicate_relations_are_repaired(repo: Path) -> None:
    change(repo, "veps/VEP-0000-foundation.md", 'title: "Foundation"', 'title: " VEP-0000: Foundation "')
    change(repo, "veps/VEP-0001-composition.md", "  - VEP-0000", "  - VEP-0000\n  - VEP-0000")
    assert invoke(repo, "--fix")[0] == 0


def test_aliases_and_reference_style_are_explicit(repo: Path) -> None:
    policy = repo / "proposal.toml"
    policy.write_text(
        policy.read_text() + '\n[fix]\nreference_style="number"\n[fix.aliases.status]\naccepted="Accepted"\n'
    )
    change(repo, "schemas/vep.schema.json", '{"type": "string", "pattern": "^VEP-[0-9]{4}$"}', '{"type": "integer"}')
    change(repo, "veps/VEP-0000-foundation.md", "status: Accepted", "status: accepted")
    assert invoke(repo, "--fix")[0] == 0


def test_diff_select_and_partial_do_not_claim_false_completion(repo: Path) -> None:
    change(repo, "drafts/temporal-model.md", "> Pre-VEP design draft. Non-normative.", "")
    path = repo / "drafts/temporal-model.md"
    path.write_text(path.read_text() + '\n<a id="term-missing"></a>\n')
    before = snapshot(repo)
    code, payload = invoke(repo, "--diff", "--select", "marker")
    assert code == 1 and "+> Pre-VEP" in payload["summary"]["diff"]
    assert snapshot(repo) == before
    code, payload = invoke(repo, "--fix", "--partial", "--select", "marker")
    assert code == 1 and payload["summary"]["fixed_files"] == ["drafts/temporal-model.md"]
    assert "proposal.defines.undeclared-anchor" in codes(payload)
    assert "proposal.draft.marker" not in codes(payload)
    assert (repo / "veps-index.json").read_bytes() == before["veps-index.json"]


def test_section_skeleton_does_not_invent_content(repo: Path) -> None:
    policy = repo / "proposal.toml"
    policy.write_text(policy.read_text() + "\n[sections]\nnonempty=true\n")
    change(repo, "veps/VEP-0000-foundation.md", "## Motivation\n\nGive later proposals a stable dependency.", "")
    code, payload = invoke(repo, "--fix", "--partial", "--select", "sections")
    assert code == 1 and "proposal.sections.empty" in codes(payload)
    assert "## Motivation" in (repo / "veps/VEP-0000-foundation.md").read_text()


def test_transaction_rolls_back_replace_failure(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = load_config(repo / "proposal.toml")
    before = snapshot_inputs(config)
    original = os.replace
    paths = [repo / "drafts/temporal-model.md", repo / "veps-index.json"]
    failed = False

    def fail_once(source, dest):
        nonlocal failed
        if Path(dest) == paths[1] and not failed:
            failed = True
            raise OSError("injected index replacement failure")
        original(source, dest)

    monkeypatch.setattr(os, "replace", fail_once)
    with pytest.raises(ProposalToolError) as error:
        commit_files(config, dict.fromkeys(paths, b"changed"), before)
    assert error.value.summary is not None
    assert error.value.summary["written_files"] == []
    assert snapshot_inputs(config) == before
    assert not list(repo.rglob(".zendev-*"))


def test_preparation_failure_does_not_write_sources(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import zendev.proposal.transaction as transaction

    config = load_config(repo / "proposal.toml")
    before = snapshot_inputs(config)
    mkstemp = transaction.tempfile.mkstemp

    def fail_index(*args, **kwargs):
        if kwargs["dir"] == repo:
            raise OSError("injected preparation failure")
        return mkstemp(*args, **kwargs)

    monkeypatch.setattr(transaction.tempfile, "mkstemp", fail_index)
    with pytest.raises(ProposalToolError):
        commit_files(
            config, {repo / "drafts/temporal-model.md": b"changed", repo / "veps-index.json": b"index"}, before
        )
    assert snapshot_inputs(config) == before


def test_unedited_input_changes_invalidate_the_plan(repo: Path) -> None:
    config = load_config(repo / "proposal.toml")
    before = snapshot_inputs(config)
    other = repo / "templates/technical.md"
    other.write_text(other.read_text() + "\n## New policy\n")
    with pytest.raises(ProposalToolError) as error:
        commit_files(config, {repo / "drafts/temporal-model.md": b"changed"}, before)
    assert error.value.diagnostic.code == "proposal.fix.changed"
    assert (repo / "drafts/temporal-model.md").read_bytes() == before[repo / "drafts/temporal-model.md"]


def test_partial_rules_separate_marker_from_conflicting_definition(repo: Path) -> None:
    change(repo, "drafts/temporal-model.md", "> Pre-VEP design draft. Non-normative.", "")
    path = repo / "drafts/temporal-model.md"
    path.write_text(path.read_text() + '\n<a id="term-foundation"></a>\n')
    code, payload = invoke(repo, "--fix", "--partial")
    assert code == 1 and "> Pre-VEP" in path.read_text()
    assert "defines: []" in path.read_text()
    assert "proposal.defines.undeclared-anchor" in codes(payload)


def test_fragment_validation_uses_repaired_snapshot(repo: Path) -> None:
    change(repo, "drafts/temporal-model.md", "defines: []", "defines: [tempo]")
    path = repo / "drafts/temporal-model.md"
    path.write_text(path.read_text() + "\n## tempo\n\n[definition](#term-tempo)\n")
    assert invoke(repo, "--fix")[0] == 0


def test_empty_code_block_does_not_fill_a_required_section(repo: Path) -> None:
    policy = repo / "proposal.toml"
    policy.write_text(policy.read_text() + "\n[sections]\nnonempty=true\n")
    change(repo, "veps/VEP-0000-foundation.md", "Define the base proposal model.", "```\n```")
    assert "proposal.sections.empty" in codes(invoke(repo)[1])


def test_schema_example_data_is_not_interpreted_as_schema(repo: Path) -> None:
    path = repo / "schemas/draft.schema.json"
    value = json.loads(path.read_text())
    value["examples"] = [{"format": "not-a-schema-format"}]
    path.write_text(json.dumps(value))
    assert invoke(repo)[0] == 0


def test_failed_rollback_keeps_recovery_copy_and_reports_changed_file(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = load_config(repo / "proposal.toml")
    before = snapshot_inputs(config)
    document = repo / "drafts/temporal-model.md"
    index = repo / "veps-index.json"
    original = os.replace
    applied = False

    def fail_write_and_rollback(source, dest):
        nonlocal applied
        if Path(dest) == index or applied:
            raise OSError("injected write and rollback failure")
        original(source, dest)
        applied = True

    monkeypatch.setattr(os, "replace", fail_write_and_rollback)
    with pytest.raises(ProposalToolError) as error:
        commit_files(config, {document: b"changed", index: b"index"}, before)
    receipt = error.value.summary
    assert receipt is not None
    assert receipt["written_files"] == ["drafts/temporal-model.md"]
    assert receipt["rolled_back_files"] == []
    recovery_files = receipt["recovery_files"]
    assert isinstance(recovery_files, list) and len(recovery_files) == 1
    assert Path(recovery_files[0]).read_bytes() == before[document]
    assert document.read_bytes() == b"changed"
    assert index.read_bytes() == before[index]
