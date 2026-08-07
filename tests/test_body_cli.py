"""Tests for zendev-validate-body CLI."""

from __future__ import annotations

from pathlib import Path

from zendev.body import (
    BodySection,
    _extract_h2_headings,
    _extract_template_sections,
    validate_body,
    validate_body_cli,
)

VALID_BODY = """\
## Summary

Some description here.

## Validation

- ran tests

## Notes

None.
"""

WRONG_BODY = """\
## Summary

Some description.

## Checklist

- [ ] Done
"""

EMPTY_BODY = ""

REQUIRED = ["Summary", "Validation", "Notes"]

CHECKLIST_TEMPLATE = """\
## Summary

Describe the change.

## Checklist

- [x] First item here.
- [x] Second item here.

## Notes

Reviewer notes.
"""

CHECKLIST_BODY = """\
## Summary

Some description here.

## Checklist

- [x] First item here.
- [x] Second item here.

## Notes

None.
"""

OPTIONAL_TEMPLATE = """\
## Why

Explain the problem.

## What changed

Describe the change.

<!-- pr-body:optional -->
## Notes

Compatibility or risk notes.

<!-- pr-body:optional -->
## Next

Immediate follow-up work.
"""


def test_extract_h2_headings_normal():
    assert _extract_h2_headings(VALID_BODY) == ["Summary", "Validation", "Notes"]


def test_extract_h2_headings_skips_fences():
    body = "## Summary\n\n```\n## Not a heading\n```\n\n## Validation\n\n## Notes"
    assert _extract_h2_headings(body) == ["Summary", "Validation", "Notes"]


def test_extract_template_sections_defaults_unmarked_h2_to_required():
    assert _extract_template_sections(OPTIONAL_TEMPLATE) == [
        BodySection("Why", required=True),
        BodySection("What changed", required=True),
        BodySection("Notes", required=False),
        BodySection("Next", required=False),
    ]


def test_extract_template_sections_supports_explicit_required_and_ignores_fenced_directives():
    template = """\
<!-- pr-body:required -->
## Why

```md
<!-- pr-body:optional -->
## Hidden
```

<!-- pr-body:optional -->
## Notes
"""
    assert _extract_template_sections(template) == [
        BodySection("Why", required=True),
        BodySection("Notes", required=False),
    ]


def test_extract_template_sections_rejects_ambiguous_or_dangling_directives():
    ambiguous = "<!-- pr-body:optional -->\n<!-- pr-body:required -->\n## Why\n"
    dangling = "## Why\n\n<!-- pr-body:optional -->\n"
    duplicate = "## Why\n\n## Why\n"

    for template in (ambiguous, dangling, duplicate):
        try:
            _extract_template_sections(template)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid template must fail closed")


def test_validate_body_valid():
    ok, actual = validate_body(VALID_BODY, REQUIRED)
    assert ok
    assert actual == REQUIRED


def test_validate_body_wrong_sections():
    ok, actual = validate_body(WRONG_BODY, REQUIRED)
    assert not ok
    assert actual == ["Summary", "Checklist"]


def test_validate_body_empty():
    ok, actual = validate_body(EMPTY_BODY, REQUIRED)
    assert not ok
    assert actual == []


def test_validate_body_allows_optional_sections_to_be_omitted_or_present_in_order():
    sections = _extract_template_sections(OPTIONAL_TEMPLATE)
    minimal = "## Why\n\nReason.\n\n## What changed\n\nChange.\n"
    with_next = minimal + "\n## Next\n\nFollow-up.\n"
    with_all = minimal + "\n## Notes\n\nNone.\n\n## Next\n\nFollow-up.\n"

    assert validate_body(minimal, sections)[0]
    assert validate_body(with_next, sections)[0]
    assert validate_body(with_all, sections)[0]


def test_validate_body_rejects_missing_required_extra_duplicate_or_out_of_order_sections():
    sections = _extract_template_sections(OPTIONAL_TEMPLATE)
    invalid_bodies = [
        "## Why\n\nReason.\n",
        "## Why\n\nReason.\n\n## What changed\n\nChange.\n\n## Validation\n\nTests.\n",
        "## Why\n\nReason.\n\n## Why\n\nAgain.\n\n## What changed\n\nChange.\n",
        "## What changed\n\nChange.\n\n## Why\n\nReason.\n",
        "## Why\n\nReason.\n\n## Notes\n\nNone.\n\n## What changed\n\nChange.\n",
    ]

    for body in invalid_bodies:
        assert not validate_body(body, sections)[0]


def test_validate_body_cli_supports_optional_template_sections(tmp_path: Path) -> None:
    template = tmp_path / "pull_request_template.md"
    template.write_text(OPTIONAL_TEMPLATE, encoding="utf-8")
    body = "## Why\n\nReason.\n\n## What changed\n\nChange.\n"

    assert validate_body_cli([body, "--template", str(template)]) == 0


def test_validate_body_cli_rejects_invalid_template_directive(tmp_path: Path) -> None:
    template = tmp_path / "pull_request_template.md"
    template.write_text("## Summary\n\n<!-- pr-body:optional -->\n", encoding="utf-8")

    assert validate_body_cli(["## Summary\n", "--template", str(template)]) == 1


def test_validate_body_cli_success_with_required_checklist(tmp_path: Path) -> None:
    template = tmp_path / "pull_request_template.md"
    template.write_text(CHECKLIST_TEMPLATE, encoding="utf-8")

    assert validate_body_cli([CHECKLIST_BODY, "--template", str(template), "--require-checklist"]) == 0


def test_validate_body_cli_reports_missing_required_checklist_item(tmp_path: Path) -> None:
    template = tmp_path / "pull_request_template.md"
    template.write_text(CHECKLIST_TEMPLATE, encoding="utf-8")
    body = CHECKLIST_BODY.replace("- [x] Second item here.\n", "")

    assert validate_body_cli([body, "--template", str(template), "--require-checklist"]) == 1


def test_validate_body_cli_fail_on_empty_required_checklist(tmp_path: Path) -> None:
    template = tmp_path / "pull_request_template.md"
    template.write_text(VALID_BODY, encoding="utf-8")

    assert (
        validate_body_cli(
            [
                VALID_BODY,
                "--template",
                str(template),
                "--require-checklist",
                "--fail-on-empty-checklist",
            ]
        )
        == 1
    )

    assert validate_body_cli([VALID_BODY, "--template", str(template), "--require-checklist"]) == 0
