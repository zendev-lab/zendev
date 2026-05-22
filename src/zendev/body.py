"""CLI entry point for validating PR bodies in CI."""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from zendev.checklist import (
    checklist_items_missing,
    load_required_checked_tasks,
    report_missing_checked_tasks,
)
from zendev.commit import format_commit_convention_help_body
from zendev.markdown_scan import iter_lines_outside_fences

REQUIRED_SECTIONS: tuple[str, ...] = ("Summary", "Validation", "Notes")


def _extract_h2_headings(text: str) -> list[str]:
    """Return H2 heading text (without the `## ` prefix), skipping fenced code blocks."""
    headings: list[str] = []
    for line in iter_lines_outside_fences(text):
        stripped = line.strip()
        if re.match(r"^##\s+\S", stripped):
            headings.append(re.sub(r"^##\s+", "", stripped))
    return headings


def _load_template_headings(template_path: Path | None) -> list[str]:
    """Return required H2 headings from the PR template file, or fall back to defaults."""
    if template_path is not None and template_path.is_file():
        return _extract_h2_headings(template_path.read_text(encoding="utf-8"))
    return list(REQUIRED_SECTIONS)


def validate_body(body: str, required_headings: list[str]) -> tuple[bool, list[str]]:
    """Validate PR body sections. Returns (is_valid, actual_headings)."""
    actual = _extract_h2_headings(body)
    return actual == required_headings, actual


def report_invalid_body(
    actual: list[str],
    expected: list[str],
    *,
    file: TextIO,
) -> None:
    print("::error::PR body headings do not match the repository template.", file=file)
    print(f"\n  Expected headings: {expected}", file=file)
    print(f"  Actual headings:   {actual}", file=file)
    print(file=file)
    print("  Each PR body should contain exactly these H2 sections:", file=file)
    for section in expected:
        print(f"    ## {section}", file=file)
    print(file=file)
    print("  Commit convention reference (for the Summary section):", file=file)
    print(format_commit_convention_help_body(include_special_prefix_note=False), file=file)


def validate_template_checklist(
    body: str,
    *,
    template_path: Path,
    section_heading: str,
    fail_on_empty: bool,
) -> bool:
    """Validate checked checklist rows copied from the PR template."""
    required = load_required_checked_tasks(template_path, section_heading=section_heading)

    print("::group::PR / checklist")
    print(f"Template: {template_path}")
    print(f"Section:  ## {section_heading}")
    print(f"Required `- [x]` rows: {len(required)}")
    print("::endgroup::")

    if not required:
        msg = "No `- [x]` checklist rows found under that heading; " + (
            "configured to fail." if fail_on_empty else "nothing to validate."
        )
        print(msg)
        return not fail_on_empty

    missing = checklist_items_missing(body, required)
    if missing:
        report_missing_checked_tasks(missing, file=sys.stdout)
        return False

    print("PR checklist items look good.")
    return True


def validate_body_cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="zendev-validate-body",
        description="Validate a PR body against the repository PR template.",
    )
    parser.add_argument("body", help="PR body text to validate.")
    parser.add_argument(
        "--template",
        metavar="PATH",
        default=".github/pull_request_template.md",
        help="Path to the PR template file (default: .github/pull_request_template.md).",
    )
    parser.add_argument(
        "--require-checklist",
        action="store_true",
        help="Also require every checked checklist row from the template checklist section to appear in the body.",
    )
    parser.add_argument(
        "--checklist-section",
        metavar="TITLE",
        default="Checklist",
        help='H2 title (without "##") naming the checklist section (default: Checklist).',
    )
    parser.add_argument(
        "--fail-on-empty-checklist",
        action="store_true",
        help=("When --require-checklist is set, exit 1 if the template defines no `- [x]` rows in that section."),
    )
    args = parser.parse_args(argv)

    template_path = Path(args.template)
    required = _load_template_headings(template_path)

    print("::group::PR / body check")
    print(f"Required headings: {required}")
    print("::endgroup::")

    is_valid, actual = validate_body(args.body, required)
    if not is_valid:
        report_invalid_body(actual, required, file=sys.stdout)
        return 1

    print("PR body headings are valid.")

    if args.require_checklist and not validate_template_checklist(
        args.body,
        template_path=template_path,
        section_heading=args.checklist_section,
        fail_on_empty=args.fail_on_empty_checklist,
    ):
        return 1

    return 0


def main() -> None:
    sys.exit(validate_body_cli())
