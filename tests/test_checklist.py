"""Only actual top-level tasks in the configured section can meet policy."""

import pytest

from zendev.core.markdown import scan_markdown
from zendev.message.body import check_body

TEMPLATE = "## Checklist\n\n- [x] Run tests\n"


@pytest.mark.parametrize(
    "task",
    [
        "- [ ] Run tests",
        "```md\n- [x] Run tests\n```",
        "<!--\n- [x] Run tests\n-->",
        "> - [x] Run tests",
        "- Parent\n  - [x] Run tests",
        "- `[x]` Run tests",
        r"- \[x] Run tests",
        "- <span>[x]</span> Run tests",
        "- **[x]** Run tests",
    ],
)
def test_hidden_or_unchecked_task_cannot_satisfy_template(task: str) -> None:
    assert any(
        d.code == "message.body.checklist"
        for d in check_body("## Checklist\n\n" + task, TEMPLATE, require_checklist=True)
    )


def test_task_text_normalization_and_source_position() -> None:
    body = "## Checklist\r\n\r\n* [X] Run **tests**\r\n"
    assert not check_body(body, TEMPLATE, require_checklist=True)
    assert scan_markdown(body).tasks[0].line == 3


def test_wrong_section_cannot_satisfy_requirement() -> None:
    body = "## Checklist\n\n# Elsewhere\n\n- [x] Run tests\n"
    assert check_body(body, TEMPLATE, require_checklist=True)


def test_empty_template_checklist_policy() -> None:
    assert not check_body("## Checklist\n", "## Checklist\n", require_checklist=True)
    result = check_body("## Checklist\n", "## Checklist\n", require_checklist=True, fail_on_empty_checklist=True)
    assert result[0].code == "message.body.empty-checklist"
