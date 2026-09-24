"""Template policy validates Markdown structure, not textual lookalikes."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from zendev.message.body import BodySection, check_body, parse_template
from zendev.message.cli import app

TEMPLATE = "## Why\n\nReason.\n\n## Changes\n\nDescription.\n\n<!-- pr-body:optional -->\n## Notes\n"
MINIMAL = "## Why\n\nReason.\n\n## Changes\n\nDescription.\n"


def test_template_marks_optional_sections() -> None:
    assert parse_template(TEMPLATE) == (BodySection("Why"), BodySection("Changes"), BodySection("Notes", False))
    assert not check_body(MINIMAL, TEMPLATE)
    assert not check_body(MINIMAL + "\n## Notes\nMore.\n", TEMPLATE)


@pytest.mark.parametrize(
    "text",
    [
        "## Why\n",
        MINIMAL + "\n## Extra\n",
        MINIMAL + "\n## Why\n",
        "## Changes\n\n## Why\n",
        "## Why\n\n## Notes\n\n## Changes\n",
        "<!--\n## Why\n-->\n## Changes\n",
        "```md\n## Why\n```\n## Changes\n",
        "> ## Why\n\n## Changes\n",
        "- ## Why\n\n## Changes\n",
    ],
)
def test_body_rejects_missing_extra_duplicate_out_of_order_or_hidden_sections(text: str) -> None:
    assert check_body(text, TEMPLATE)


@pytest.mark.parametrize(
    "template",
    [
        "## Why\n\n<!-- pr-body:optional -->\n",
        "## Why\n\n## Why\n",
        "",
        "<!-- pr-body:optional -->\n<!-- pr-body:required -->\n## Why\n",
    ],
)
def test_invalid_template_fails_closed(template: str) -> None:
    with pytest.raises(ValueError):
        parse_template(template)


def test_fenced_directive_does_not_make_section_optional() -> None:
    template = "## Why\n\n```md\n<!-- pr-body:optional -->\n## Hidden\n```\n\n## Changes\n"
    assert parse_template(template) == (BodySection("Why"), BodySection("Changes"))


def test_missing_template_is_tool_error(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["check", "--body", "--text", MINIMAL, "--template", str(tmp_path / "missing.md")])
    assert result.exit_code == 2
    assert "message.template" in result.output


def test_invalid_template_is_tool_error(tmp_path: Path) -> None:
    template = tmp_path / "template.md"
    template.write_text("## Why\n\n<!-- pr-body:optional -->\n")
    result = CliRunner().invoke(app, ["check", "--body", "--text", MINIMAL, "--template", str(template)])
    assert result.exit_code == 2
    assert "message.template" in result.output


def test_body_cli_combines_sections_and_checklist(tmp_path: Path) -> None:
    template = tmp_path / "template.md"
    text = "## Checklist\n\n- [x] Run tests\n- [ ] Optional action\n"
    template.write_text(text)
    result = CliRunner().invoke(
        app, ["check", "--body", "--text", text, "--template", str(template), "--require-checklist"]
    )
    assert result.exit_code == 0
    result = CliRunner().invoke(
        app,
        ["check", "--body", "--text", text.replace("[x]", "[ ]"), "--template", str(template), "--require-checklist"],
    )
    assert result.exit_code == 1
    assert "message.body.checklist" in result.output
