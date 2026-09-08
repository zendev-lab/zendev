"""ZFP authorship policy through the real repository schema and CLI."""

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from zendev.proposal.cli import app


@pytest.mark.parametrize(
    "authors",
    [
        [],
        ["zrr1999", "zrr1999"],
        ["Zhan Rongrui"],
        ["@zrr1999"],
        ["Zrr1999"],
        ["https://github.com/zrr1999"],
        ["person@example.com"],
        [" zrr1999"],
        ["zrr1999\n"],
        ["-author"],
        ["author-"],
        ["author--name"],
        ["author_name"],
        ["作者"],
        ["a" * 40],
    ],
)
def test_zfp_rejects_invalid_authors_without_guessing_or_writing(tmp_path: Path, authors: list[str]) -> None:
    root = Path(__file__).parents[1]
    for directory in ("zfps", "templates", "schemas"):
        shutil.copytree(root / directory, tmp_path / directory)
    for filename in ("proposal.toml", "zfps-index.json"):
        shutil.copyfile(root / filename, tmp_path / filename)
    proposal = tmp_path / "zfps/ZFP-0000-governance.md"
    proposal.write_text(proposal.read_text().replace('authors:\n  - "zrr1999"', "authors: " + json.dumps(authors)))
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    result = CliRunner().invoke(app, ["check", "--config", str(tmp_path / "proposal.toml"), "--fix", "--json"])
    assert result.exit_code == 1, result.output
    payload = json.loads(result.stdout)
    assert any(item["code"] == "proposal.frontmatter.schema" for item in payload["diagnostics"])
    assert {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before


@pytest.mark.parametrize("authors", [["zrr1999"], ["a", "another-author9"], ["a" * 39]])
def test_zfp_author_schema_accepts_canonical_usernames(authors: list[str]) -> None:
    from jsonschema import Draft202012Validator

    schema = json.loads((Path(__file__).parents[1] / "schemas/zfp.schema.json").read_text())
    Draft202012Validator(schema["properties"]["authors"]).validate(authors)
