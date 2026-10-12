"""Opt-in dependency policies observe actual proposal references and numeric order."""

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from zendev.core.diagnostics import ToolError
from zendev.proposal.cli import app
from zendev.proposal.config import load_config
from zendev.proposal.validation import validate_repository


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return Path(shutil.copytree(Path(__file__).parent / "fixtures/proposal/vep", tmp_path / "repo"))


def change(repo: Path, path: str, old: str, new: str) -> None:
    target = repo / path
    original = target.read_text()
    assert old in original
    target.write_text(original.replace(old, new))


def enable(repo: Path, settings: str = "require_declared_references = true\nrequires_earlier = true") -> None:
    change(repo, "zendev.toml", "[proposal.graph]", "[proposal.graph]\n" + settings)


def append(repo: Path, body: str, path: str = "veps/VEP-0001-composition.md") -> int:
    target = repo / path
    original = target.read_text()
    target.write_text(original + "\n" + body + "\n")
    return len(original.splitlines()) + 2


def check(repo: Path):
    return validate_repository(load_config(repo / "zendev.toml"))


@pytest.mark.parametrize(
    "reference",
    [
        "依据VEP-0000继续设计。",
        "See **VEP-0000**.",
        "See VEP-**0000**.",
        "See `VEP-0000`.",
        "[Foundation](./VEP-0000-foundation.md)",
        "[Term](/veps/VEP%2D0000-foundation.md#term-foundation)",
        "[Term][base]\n\n[base]: ./VEP-0000-foundation.md#term-foundation",
        '<a href="./VEP-0000-foundation.md#term-foundation">Term</a>',
        "<div>VEP-0000</div>",
    ],
)
def test_references_require_direct_declarations(repo: Path, reference: str) -> None:
    enable(repo)
    line = append(repo, reference)
    assert check(repo).ok

    change(repo, "veps/VEP-0001-composition.md", "requires:\n  - VEP-0000", "requires: []")
    result = check(repo)

    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == "proposal.reference.undeclared-dependency"
    assert diagnostic.path == "veps/VEP-0001-composition.md"
    assert diagnostic.line == line - 1  # Removing the YAML item removes one preceding line.
    assert "VEP-0000" in diagnostic.message


def test_transitive_dependency_does_not_authorize_a_reference(repo: Path) -> None:
    enable(repo)
    source = (repo / "veps/VEP-0001-composition.md").read_text()
    third = repo / "veps/VEP-0002-extension.md"
    third.write_text(source.replace("vep: 1", "vep: 2").replace("VEP-0001", "VEP-0002").replace("VEP-0000", "VEP-0001"))
    append(repo, "VEP-0000 is a prerequisite.", "veps/VEP-0002-extension.md")

    result = check(repo)

    assert [d.code for d in result.diagnostics] == ["proposal.reference.undeclared-dependency"]
    assert result.diagnostics[0].path == "veps/VEP-0002-extension.md"
    change(repo, "veps/VEP-0002-extension.md", "  - VEP-0001", "  - VEP-0001\n  - VEP-0000")
    assert check(repo).ok


def test_self_external_and_code_examples_do_not_require_dependencies(repo: Path) -> None:
    enable(repo)
    change(repo, "veps/VEP-0001-composition.md", "requires:\n  - VEP-0000", "requires: []")
    append(
        repo,
        """Self: VEP-0001, `VEP-0001`, [self](#).

[VEP-0000](https://example.com/VEP-0000)
[`VEP-0000`](//example.com/VEP-0000)
<a href="https://example.com/VEP-0000">VEP-0000</a>
https://example.com/VEP-0000?ref=VEP-0000

<div><a href="https://example.com/VEP-0000">VEP-0000</a></div>

```markdown
VEP-0000 and [term](./VEP-0000-foundation.md)
```

    VEP-0000

`requires: [VEP-0000]` is a code example.

<!-- VEP-0000 -->

<pre>VEP-0000</pre>

Other prefix: FP-0000. Noncanonical: VEP-00000, VEP-00, XVEP-0000, VEP-0000-extra.
""",
    )

    assert check(repo).ok


def test_link_target_controls_dependency_instead_of_label(repo: Path) -> None:
    enable(repo)
    append(repo, "[VEP-9999](./VEP-0000-foundation.md)")
    assert check(repo).ok


def test_first_reference_location_survives_inline_line_breaks(repo: Path) -> None:
    enable(repo)
    change(repo, "veps/VEP-0001-composition.md", "requires:\n  - VEP-0000", "requires: []")
    line = append(repo, "First line.\n[Term](./VEP-0000-foundation.md#term-foundation)\n\nAlso VEP-0000.")
    result = check(repo)
    assert [d.line for d in result.diagnostics] == [line + 1]


def test_unknown_body_identifier_reports_missing_target_at_its_line(repo: Path) -> None:
    enable(repo)
    line = append(repo, "First line.\nSee VEP-9999.")

    result = check(repo)

    assert [d.code for d in result.diagnostics] == ["proposal.reference.missing-target"]
    assert result.diagnostics[0].line == line + 1


def test_reference_check_does_not_depend_on_link_validation(repo: Path) -> None:
    enable(repo)
    with (repo / "zendev.toml").open("a") as policy:
        policy.write("\n[proposal.links]\ncheck = false\n")
    change(repo, "veps/VEP-0001-composition.md", "requires:\n  - VEP-0000", "requires: []")
    append(repo, "[Term](./VEP-0000-foundation.md#term-foundation)")
    assert [d.code for d in check(repo).diagnostics] == ["proposal.reference.undeclared-dependency"]


def test_undeclared_reference_policy_is_disabled_by_default(repo: Path) -> None:
    change(repo, "veps/VEP-0001-composition.md", "requires:\n  - VEP-0000", "requires: []")
    append(repo, "VEP-0000")
    assert check(repo).ok


@pytest.mark.parametrize("edge", ["VEP-0001", 1])
def test_forward_dependency_is_rejected_without_a_cycle(repo: Path, edge: str | int) -> None:
    schema = repo / "schemas/vep.schema.json"
    metadata = json.loads(schema.read_text())
    metadata["properties"]["requires"]["items"]["type"] = ["string", "integer"]
    schema.write_text(json.dumps(metadata))
    change(repo, "veps/VEP-0001-composition.md", "requires:\n  - VEP-0000", "requires: []")
    change(repo, "veps/VEP-0000-foundation.md", "status: Accepted", "status: Draft")
    change(repo, "veps/VEP-0000-foundation.md", "requires: []", f"requires: [{edge}]")
    assert check(repo).ok  # The same acyclic graph remains valid when the option is absent.
    enable(repo, "requires_earlier = true")

    result = check(repo)

    assert [d.code for d in result.diagnostics] == ["proposal.graph.forward-dependency"]
    assert result.diagnostics[0].line == 6
    assert "VEP-0001" in result.diagnostics[0].message


def test_policies_follow_the_configured_relation_name(repo: Path) -> None:
    enable(repo)
    for path in repo.rglob("*"):
        if path.is_file():
            path.write_text(path.read_text().replace('"requires"', '"depends_on"').replace("requires:", "depends_on:"))
    append(repo, "VEP-0000")
    assert check(repo).ok
    change(repo, "veps/VEP-0001-composition.md", "depends_on:\n  - VEP-0000", "depends_on: []")
    diagnostic = check(repo).diagnostics[0]
    assert diagnostic.code == "proposal.reference.undeclared-dependency"
    assert "`depends_on`" in diagnostic.message


def test_unnumbered_draft_checks_declarations_without_inventing_an_order(repo: Path) -> None:
    enable(repo)
    change(repo, "zendev.toml", "pre_proposal = true", "pre_proposal = false")
    schema = repo / "schemas/draft.schema.json"
    metadata = json.loads(schema.read_text())
    metadata["properties"]["requires"] = {"type": "array", "items": {"type": "integer"}}
    metadata["properties"]["status"] = {"const": "Draft"}
    schema.write_text(json.dumps(metadata))
    change(repo, "drafts/temporal-model.md", "defines: []", "defines: []\nstatus: Draft")
    append(repo, "VEP-0001", "drafts/temporal-model.md")
    assert [d.code for d in check(repo).diagnostics] == ["proposal.reference.undeclared-dependency"]
    change(repo, "drafts/temporal-model.md", "defines: []", "defines: []\nrequires: [1]")
    assert check(repo).ok


@pytest.mark.parametrize("option", ["require_declared_references", "requires_earlier"])
@pytest.mark.parametrize("value,missing_role,code", [("true", True, "graph-role"), ('"true"', False, "type")])
def test_dependency_policy_configuration_fails_closed(
    repo: Path, option: str, value: str, missing_role: bool, code: str
) -> None:
    enable(repo, f"{option} = {value}")
    if missing_role:
        change(repo, "zendev.toml", 'requires_field = "requires"\n', "")
    with pytest.raises(ToolError) as error:
        load_config(repo / "zendev.toml")
    assert error.value.diagnostic.code == "proposal.config." + code


@pytest.mark.parametrize("arguments", [[], ["--fix"], ["--fix", "--partial"]])
def test_check_and_fix_leave_undeclared_dependencies_for_the_author(repo: Path, arguments: list[str]) -> None:
    enable(repo)
    change(repo, "veps/VEP-0001-composition.md", "requires:\n  - VEP-0000", "requires: []")
    append(repo, "VEP-0000")
    before = {str(p): p.read_bytes() for p in repo.rglob("*") if p.is_file()}

    result = CliRunner().invoke(app, ["check", "--config", str(repo / "zendev.toml"), "--format", "json", *arguments])

    assert result.exit_code == 1
    assert "proposal.reference.undeclared-dependency" in {d["code"] for d in json.loads(result.stdout)["diagnostics"]}
    assert {str(p): p.read_bytes() for p in repo.rglob("*") if p.is_file()} == before


def test_partial_h1_repair_cannot_introduce_an_undeclared_dependency(repo: Path) -> None:
    enable(repo)
    path = "veps/VEP-0001-composition.md"
    change(repo, path, "requires:\n  - VEP-0000", "requires: []")
    change(repo, path, 'title: "Composition"', 'title: "Uses VEP-0000"')
    before = (repo / path).read_bytes()

    result = CliRunner().invoke(
        app,
        ["check", "--config", str(repo / "zendev.toml"), "--format", "json", "--fix", "--partial", "--select", "h1"],
    )

    assert result.exit_code == 1
    assert (repo / path).read_bytes() == before
    assert "proposal.h1.invalid" in {d["code"] for d in json.loads(result.stdout)["diagnostics"]}
