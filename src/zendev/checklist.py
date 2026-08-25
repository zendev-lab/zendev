"""Validate PR bodies contain required GitHub-task checklist rows from the template."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from zendev.markdown_scan import iter_lines_outside_fences

_CHECKED_TASK_RE = re.compile(r"^\s*-\s*\[x\]\s+.+$")


def _h2_heading_match(line_stripped: str, section_title: str) -> bool | None:
    """Return True if line is ## <section_title>, False if other H2, None if not an H2 line."""
    m = re.match(r"^##\s+(.+)$", line_stripped)
    if not m:
        return None
    return m.group(1).strip() == section_title


def extract_required_checked_tasks(template_markdown: str, *, section_heading: str) -> list[str]:
    """Return checked checklist rows under ``## <section_heading>`` until the next H2.

    Skips fenced code blocks. Each entry is the raw template line with only trailing
    ``\r``/``\n`` removed so PR bodies can be matched verbatim.
    """
    in_section = False
    required: list[str] = []

    for raw_line in iter_lines_outside_fences(template_markdown):
        stripped = raw_line.strip()

        h2_kind = _h2_heading_match(stripped, section_heading)
        if h2_kind is not None:
            in_section = h2_kind is True
            continue

        if not in_section:
            continue

        line = raw_line.rstrip("\r\n")
        if _CHECKED_TASK_RE.match(line):
            required.append(line)

    return required


def load_required_checked_tasks(template_path: Path, *, section_heading: str) -> list[str]:
    """Load checked checklist rows from ``template_path`` or return an empty list."""
    if not template_path.is_file():
        return []
    return extract_required_checked_tasks(
        template_path.read_text(encoding="utf-8"),
        section_heading=section_heading,
    )


def checklist_items_missing(body: str, required_lines: Sequence[str]) -> list[str]:
    """Return checklist lines that must appear verbatim in ``body`` but do not."""
    if not body:
        return list(required_lines)
    return [item for item in required_lines if item not in body]


def report_missing_checked_tasks(missing: Sequence[str], *, file: TextIO) -> None:
    """Emit a GitHub Actions-friendly error for missing checked template rows."""
    print("::error::PR body is missing required checked checklist items.", file=file)
    for item in missing:
        print(item, file=file)
