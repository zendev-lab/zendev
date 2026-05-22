"""Tests for zendev-validate-body CLI."""

from __future__ import annotations

from pathlib import Path

from zendev.body import _extract_h2_headings, validate_body, validate_body_cli

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


def test_extract_h2_headings_normal():
    assert _extract_h2_headings(VALID_BODY) == ["Summary", "Validation", "Notes"]


def test_extract_h2_headings_skips_fences():
    body = "## Summary\n\n```\n## Not a heading\n```\n\n## Validation\n\n## Notes"
    assert _extract_h2_headings(body) == ["Summary", "Validation", "Notes"]


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
