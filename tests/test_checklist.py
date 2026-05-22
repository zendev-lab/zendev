"""Tests for PR checklist extraction helpers."""

from __future__ import annotations

from zendev.checklist import (
    checklist_items_missing,
    extract_required_checked_tasks,
)

_TEMPLATE = """\
## Proposal summary

x

## Checklist

- [x] First item here.
- [ ] Unchecked skip.
- [x] Second item here.

## Notes for reviewers

done
"""

_TEMPLATE_FENCE = """\
## Checklist

```text
- [x] inside a fence
```

- [x] Real item one.
"""


def test_extract_required_checked_tasks_filters_unchecked_and_heading() -> None:
    assert extract_required_checked_tasks(_TEMPLATE, section_heading="Checklist") == [
        "- [x] First item here.",
        "- [x] Second item here.",
    ]


def test_extract_skips_fenced_checklist_lookalikes() -> None:
    assert extract_required_checked_tasks(_TEMPLATE_FENCE, section_heading="Checklist") == [
        "- [x] Real item one.",
    ]


def test_checklist_items_missing() -> None:
    body = "## Checklist\n\n- [x] First item here.\n\nMissing second.\n"
    required = ["- [x] First item here.", "- [x] Second item here."]
    missing = checklist_items_missing(body, required)
    assert missing == ["- [x] Second item here."]


def test_checklist_items_missing_empty_body() -> None:
    required = ["- [x] First item here.", "- [x] Second item here."]
    assert checklist_items_missing("", required) == required
