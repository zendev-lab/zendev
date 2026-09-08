"""Observable contracts for semantic checks and conservative source repairs."""

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from zendev.proposal.cli import app
from zendev.proposal.config import load_config
from zendev.proposal.validation import validate_repository

runner = CliRunner()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    return Path(shutil.copytree(Path(__file__).parent / "fixtures/proposal/vep", tmp_path / "repo"))


def draft(repository: Path) -> Path:
    return repository / "drafts/temporal-model.md"


def check(repository: Path, *, fix: bool = False):
    args = ["check", "--config", str(repository / "proposal.toml"), "--json"]
    if fix:
        args.append("--fix")
    result = runner.invoke(app, args)
    assert result.exception is None or isinstance(result.exception, SystemExit), result.exception
    return result.exit_code, json.loads(result.stdout)


def snapshot(repository: Path) -> dict[str, bytes]:
    return {str(path.relative_to(repository)): path.read_bytes() for path in repository.rglob("*") if path.is_file()}


@pytest.mark.parametrize("title", ['"   "', '""', '" leading"', '"line\\nline"'])
def test_titles_must_be_nonempty_single_line(repository: Path, title: str) -> None:
    path = draft(repository)
    path.write_text(path.read_text().replace('"Temporal model"', title))
    assert "proposal.title.invalid" in {
        d.code for d in validate_repository(load_config(repository / "proposal.toml")).diagnostics
    }


@pytest.mark.parametrize(
    "wrapper", ["```html\n{}\n```", "~~~~\n{}\n~~~~", "````\n```\n{}\n````", "    {}", "`{}`", "<!--\n{}\n-->"]
)
def test_example_anchors_are_not_definitions(repository: Path, wrapper: str) -> None:
    path = draft(repository)
    path.write_text(path.read_text() + "\n" + wrapper.format('<a id="term-example"></a>') + "\n")
    before = snapshot(repository)
    assert check(repository, fix=True)[0] == 0
    assert snapshot(repository) == before


def test_example_anchor_cannot_satisfy_a_declaration(repository: Path) -> None:
    path = draft(repository)
    path.write_text(path.read_text().replace("defines: []", "defines: [example]") + '\n`<a id="term-example"></a>`\n')
    before = snapshot(repository)
    code, payload = check(repository, fix=True)
    assert code == 1
    assert "proposal.defines.missing-anchor" in {d["code"] for d in payload["diagnostics"]}
    assert snapshot(repository) == before


@pytest.mark.parametrize(
    ("value", "code"), [("[42]", "invalid-id"), ("[Invalid]", "invalid-id"), ("[tempo, tempo]", "duplicate-id")]
)
def test_defines_policy_validates_ids_even_with_permissive_schema(repository: Path, value: str, code: str) -> None:
    schema = repository / "schemas/draft.schema.json"
    schema.write_text("{}")
    path = draft(repository)
    path.write_text(path.read_text().replace("defines: []", f"defines: {value}") + '\n<a id="term-tempo"></a>\n')
    result = validate_repository(load_config(repository / "proposal.toml"))
    assert f"proposal.defines.{code}" in {d.code for d in result.diagnostics}


@pytest.mark.parametrize("anchor", ['<a id="term-Bad"></a>', "<a id='term-tempo'></a>", '<div id="term-tempo"></div>'])
def test_invalid_definition_anchor_is_reported(repository: Path, anchor: str) -> None:
    path = draft(repository)
    path.write_text(path.read_text() + "\n" + anchor + "\n")
    before = snapshot(repository)
    code, payload = check(repository, fix=True)
    assert code == 1
    assert "proposal.defines.invalid-anchor" in {d["code"] for d in payload["diagnostics"]}
    assert snapshot(repository) == before


def test_duplicate_undeclared_anchors_cannot_be_fixed(repository: Path) -> None:
    path = draft(repository)
    path.write_text(path.read_text() + '\n<a id="term-tempo"></a>\n\n<a id="term-tempo"></a>\n')
    before = snapshot(repository)
    code, payload = check(repository, fix=True)
    assert code == 1
    assert "proposal.defines.duplicate-anchor" in {d["code"] for d in payload["diagnostics"]}
    assert snapshot(repository) == before


@pytest.mark.parametrize("missing", [True, False])
def test_marker_is_inserted_or_moved_and_fix_is_idempotent(repository: Path, missing: bool) -> None:
    path = draft(repository)
    marker = "> Pre-VEP design draft. Non-normative."
    text = path.read_text().replace(marker + "\n", "")
    if not missing:
        text += "\n" + marker + "\n"
    path.write_text(text)
    before = snapshot(repository)
    assert check(repository)[0] == 1
    assert snapshot(repository) == before
    code, payload = check(repository, fix=True)
    assert code == 0
    assert payload["summary"]["fixed_files"] == ["drafts/temporal-model.md"]
    body = path.read_text().split("---", 2)[2]
    assert [line for line in body.splitlines() if line.strip()][:2] == ["# Temporal model", marker]
    assert check(repository)[0] == 0
    after = snapshot(repository)
    assert check(repository, fix=True)[1]["summary"]["fixed_files"] == []
    assert snapshot(repository) == after


def test_duplicate_marker_is_reported_without_deleting_prose(repository: Path) -> None:
    path = draft(repository)
    path.write_text(path.read_text() + "\n> Pre-VEP design draft. Non-normative.\n")
    before = snapshot(repository)
    code, payload = check(repository, fix=True)
    assert code == 1
    assert "proposal.draft.marker" in {d["code"] for d in payload["diagnostics"]}
    assert snapshot(repository) == before


def test_marker_in_code_does_not_prevent_insertion(repository: Path) -> None:
    path = draft(repository)
    marker = "> Pre-VEP design draft. Non-normative."
    path.write_text(path.read_text().replace(marker, "") + f"\n```markdown\n{marker}\n```\n")
    assert check(repository, fix=True)[0] == 0
    assert path.read_text().count(marker) == 2


@pytest.mark.parametrize("initial", ["# Wrong heading", ""])
def test_h1_is_derived_from_metadata(repository: Path, initial: str) -> None:
    path = draft(repository)
    path.write_text(path.read_text().replace("# Temporal model", initial))
    assert check(repository, fix=True)[0] == 0
    assert "# Temporal model" in path.read_text()


def test_extra_h1_is_not_deleted(repository: Path) -> None:
    path = draft(repository)
    path.write_text(path.read_text() + "\n# Another title\n")
    before = snapshot(repository)
    code, payload = check(repository, fix=True)
    assert code == 1
    assert "proposal.h1.duplicate" in {d["code"] for d in payload["diagnostics"]}
    assert snapshot(repository) == before


@pytest.mark.parametrize(
    "declaration",
    [
        "",
        "defines: [] # retain comment\n",
        "defines:\n  - existing # retain comment\n",
        "defines: [existing] # retain comment\n",
    ],
)
def test_defines_append_preserves_yaml_and_crlf(repository: Path, declaration: str) -> None:
    path = draft(repository)
    text = path.read_text().replace("defines: []\n", declaration)
    if "existing" in declaration:
        text += '\n<a id="term-existing"></a>\n'
    text += '\n<a id="term-tempo"></a>\n'
    path.write_bytes(text.replace("\n", "\r\n").encode())
    assert check(repository, fix=True)[0] == 0
    after = path.read_bytes()
    assert after.count(b"\n") == after.count(b"\r\n")
    assert b"# retain comment" in after if declaration else True
    assert '"tempo"' in path.read_text()
    assert check(repository)[0] == 0
    before = snapshot(repository)
    assert check(repository, fix=True)[0] == 0
    assert snapshot(repository) == before


def test_missing_anchor_is_inserted_at_unique_exact_heading(repository: Path) -> None:
    path = draft(repository)
    path.write_text(path.read_text().replace("defines: []", "defines: [tempo]") + "\n## tempo\n\nDefinition.\n")
    assert check(repository, fix=True)[0] == 0
    assert '<a id="term-tempo"></a>\n\n## tempo' in path.read_text()


@pytest.mark.parametrize("headings", ["## Tempo", "## tempo\n\n## tempo"])
def test_ambiguous_or_inexact_definition_location_is_not_guessed(repository: Path, headings: str) -> None:
    path = draft(repository)
    path.write_text(path.read_text().replace("defines: []", "defines: [tempo]") + "\n" + headings + "\n")
    before = snapshot(repository)
    assert check(repository, fix=True)[0] == 1
    assert snapshot(repository) == before


def test_unresolved_error_prevents_all_candidate_writes(repository: Path) -> None:
    path = draft(repository)
    path.write_text(
        path.read_text().replace("> Pre-VEP design draft. Non-normative.", "") + '\n<a id="term-foundation"></a>\n'
    )
    before = snapshot(repository)
    code, payload = check(repository, fix=True)
    assert code == 1
    assert "proposal.defines.duplicate-owner" in {d["code"] for d in payload["diagnostics"]}
    assert payload["summary"]["fixed_files"] == []
    assert snapshot(repository) == before


def test_required_sections_cannot_be_repeated(repository: Path) -> None:
    path = repository / "veps/VEP-0000-foundation.md"
    path.write_text(path.read_text() + "\n## Summary\n")
    assert "proposal.sections.duplicate" in {
        d.code for d in validate_repository(load_config(repository / "proposal.toml")).diagnostics
    }


@pytest.mark.parametrize("value", ["[existing,]", "[existing, # comment\n]"])
def test_flow_sequence_trailing_comma_is_preserved(repository: Path, value: str) -> None:
    path = draft(repository)
    path.write_text(
        path.read_text().replace("defines: []", f"defines: {value}")
        + '\n<a id="term-existing"></a>\n<a id="term-tempo"></a>\n'
    )
    assert check(repository, fix=True)[0] == 0
    assert check(repository)[0] == 0


def test_draft_marker_and_required_summary_can_coexist(repository: Path) -> None:
    policy = repository / "proposal.toml"
    policy.write_text(policy.read_text().replace("pre_proposal = true", "pre_proposal = true\nrequire_summary = true"))
    path = draft(repository)
    path.write_text(
        path.read_text().replace(
            "> Pre-VEP design draft. Non-normative.", "> **Executive Summary:** Explore time. Keep a durable record."
        )
    )
    assert check(repository, fix=True)[0] == 0
    assert check(repository)[0] == 0


def test_yaml_alias_is_not_implicitly_modified(repository: Path) -> None:
    path = draft(repository)
    path.write_text(path.read_text().replace("defines: []", "defines: &concepts []") + '\n<a id="term-tempo"></a>\n')
    before = snapshot(repository)
    assert check(repository, fix=True)[0] == 1
    assert snapshot(repository) == before


def test_missing_base_ref_prevents_source_repairs(repository: Path) -> None:
    path = draft(repository)
    path.write_text(path.read_text().replace("> Pre-VEP design draft. Non-normative.", ""))
    before = snapshot(repository)
    result = runner.invoke(
        app, ["check", "--config", str(repository / "proposal.toml"), "--fix", "--json", "--base-ref", "does-not-exist"]
    )
    assert result.exit_code == 2
    assert json.loads(result.stdout)["ok"] is False
    assert snapshot(repository) == before


def test_example_headings_do_not_satisfy_required_sections(repository: Path) -> None:
    path = repository / "veps/VEP-0000-foundation.md"
    path.write_text(path.read_text().replace("## Summary", "~~~\n## Summary\n~~~"))
    assert "proposal.sections.missing" in {
        d.code for d in validate_repository(load_config(repository / "proposal.toml")).diagnostics
    }


def test_plain_text_marker_policy_remains_supported(repository: Path) -> None:
    policy = repository / "proposal.toml"
    policy.write_text(policy.read_text().replace("> Pre-VEP", "Pre-VEP"))
    path = draft(repository)
    path.write_text(path.read_text().replace("> Pre-VEP", "Pre-VEP"))
    assert check(repository)[0] == 0


def test_unrelated_mixed_line_endings_are_preserved(repository: Path) -> None:
    path = draft(repository)
    before = path.read_bytes().replace(b"> Pre-VEP design draft. Non-normative.\n", b"")
    before = before.replace(b'title: "Temporal model"\n', b'title: "Temporal model"\r\n')
    path.write_bytes(before)
    assert check(repository, fix=True)[0] == 0
    assert b'title: "Temporal model"\r\n' in path.read_bytes()
    assert b"defines: []\n" in path.read_bytes()


def test_custom_definition_pattern_with_capture_groups(repository: Path) -> None:
    policy = repository / "proposal.toml"
    policy.write_text(
        policy.read_text().replace(
            'anchor_prefix = "term-"', 'anchor_prefix = "concept-"\nid_pattern = "([a-z]+)(-[a-z]+)*"'
        )
    )
    for path in (repository / "veps").glob("*.md"):
        path.write_text(path.read_text().replace("term-", "concept-"))
    path = draft(repository)
    path.write_text(path.read_text() + '\n<a id="concept-new-name"></a>\n')
    assert check(repository, fix=True)[0] == 0
    assert '"new-name"' in path.read_text()


def test_template_frontmatter_is_not_a_setext_section(repository: Path) -> None:
    template = repository / "templates/technical.md"
    template.write_text("---\ntitle: example\ntype: Technical\n---\n\n" + template.read_text())
    assert check(repository)[0] == 0
