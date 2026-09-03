"""CLI entry point for validating PR bodies in CI."""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, TextIO

import typer

from zendev.checklist import (
    checklist_items_missing,
    load_required_checked_tasks,
    report_missing_checked_tasks,
)
from zendev.commit import format_commit_convention_help_body
from zendev.markdown_scan import iter_lines_outside_fences

REQUIRED_SECTIONS: tuple[str, ...] = ("Summary", "Validation", "Notes")
_SECTION_DIRECTIVE_RE = re.compile(r"^<!--\s*pr-body:(required|optional)\s*-->$")

app = typer.Typer(
    add_completion=False,
    help="Validate a PR body against the repository PR template.",
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
)


@dataclass(frozen=True)
class BodySection:
    """One H2 section declared by a PR template."""

    heading: str
    required: bool = True


def _extract_h2_headings(text: str) -> list[str]:
    """Return H2 heading text (without the `## ` prefix), skipping fenced code blocks."""
    headings: list[str] = []
    for line in iter_lines_outside_fences(text):
        stripped = line.strip()
        if re.match(r"^##\s+\S", stripped):
            headings.append(re.sub(r"^##\s+", "", stripped))
    return headings


def _extract_template_sections(text: str) -> list[BodySection]:
    """Parse H2 sections and optional requirement directives from a PR template."""
    sections: list[BodySection] = []
    pending_requirement: bool | None = None

    for line in iter_lines_outside_fences(text):
        stripped = line.strip()
        directive = _SECTION_DIRECTIVE_RE.fullmatch(stripped)
        if directive is not None:
            if pending_requirement is not None:
                raise ValueError("multiple pr-body directives appear before the same H2 section")
            pending_requirement = directive.group(1) == "required"
            continue

        if not re.match(r"^##\s+\S", stripped):
            continue

        heading = re.sub(r"^##\s+", "", stripped)
        sections.append(
            BodySection(
                heading=heading,
                required=True if pending_requirement is None else pending_requirement,
            )
        )
        pending_requirement = None

    if pending_requirement is not None:
        raise ValueError("pr-body directive is not followed by an H2 section")

    headings = [section.heading for section in sections]
    if len(headings) != len(set(headings)):
        raise ValueError("PR template H2 headings must be unique")

    return sections


def _load_template_sections(template_path: Path | None) -> list[BodySection]:
    """Return PR template H2 requirements, or fall back to the legacy required defaults."""
    if template_path is not None and template_path.is_file():
        return _extract_template_sections(template_path.read_text(encoding="utf-8"))
    return [BodySection(heading) for heading in REQUIRED_SECTIONS]


def _coerce_sections(sections: Sequence[BodySection | str]) -> list[BodySection]:
    return [section if isinstance(section, BodySection) else BodySection(section) for section in sections]


def validate_body(body: str, sections: Sequence[BodySection | str]) -> tuple[bool, list[str]]:
    """Validate PR body sections. Returns (is_valid, actual_headings)."""
    expected = _coerce_sections(sections)
    actual = _extract_h2_headings(body)

    expected_headings = [section.heading for section in expected]
    if len(expected_headings) != len(set(expected_headings)):
        return False, actual
    if len(actual) != len(set(actual)):
        return False, actual

    positions = {heading: index for index, heading in enumerate(expected_headings)}
    if any(heading not in positions for heading in actual):
        return False, actual

    actual_positions = [positions[heading] for heading in actual]
    if actual_positions != sorted(actual_positions):
        return False, actual

    actual_set = set(actual)
    if any(section.required and section.heading not in actual_set for section in expected):
        return False, actual

    return True, actual


def report_invalid_body(
    actual: list[str],
    expected: Sequence[BodySection],
    *,
    file: TextIO,
) -> None:
    expected_headings = [section.heading for section in expected]
    required_headings = [section.heading for section in expected if section.required]
    optional_headings = [section.heading for section in expected if not section.required]

    print("::error::PR body headings do not match the repository template.", file=file)
    print(f"\n  Template order:    {expected_headings}", file=file)
    print(f"  Required headings: {required_headings}", file=file)
    print(f"  Optional headings: {optional_headings}", file=file)
    print(f"  Actual headings:   {actual}", file=file)
    print(file=file)
    print("  Undeclared template H2 sections are required by default.", file=file)
    print("  Prefix an optional template section with `<!-- pr-body:optional -->`.", file=file)
    print(file=file)
    print("  Commit convention reference (for the first required section):", file=file)
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


def run_body_check(
    body: str,
    *,
    template: Path = Path(".github/pull_request_template.md"),
    require_checklist: bool = False,
    checklist_section: str = "Checklist",
    fail_on_empty_checklist: bool = False,
) -> None:
    """Validate PR body sections and optional required checklist rows."""

    try:
        sections = _load_template_sections(template)
    except ValueError as exc:
        print(f"::error::Invalid PR template: {exc}")
        raise typer.Exit(code=1) from exc

    print("::group::PR / body check")
    print(f"Template headings: {[section.heading for section in sections]}")
    print(f"Required headings: {[section.heading for section in sections if section.required]}")
    print(f"Optional headings: {[section.heading for section in sections if not section.required]}")
    print("::endgroup::")

    is_valid, actual = validate_body(body, sections)
    if not is_valid:
        report_invalid_body(actual, sections, file=sys.stdout)
        raise typer.Exit(code=1)

    print("PR body headings are valid.")

    if require_checklist and not validate_template_checklist(
        body,
        template_path=template,
        section_heading=checklist_section,
        fail_on_empty=fail_on_empty_checklist,
    ):
        raise typer.Exit(code=1)


@app.command()
def validate_body_command(
    body: Annotated[str, typer.Argument(help="PR body text to validate.")],
    template: Annotated[
        Path,
        typer.Option(
            "--template",
            metavar="PATH",
            help="Path to the PR template file.",
        ),
    ] = Path(".github/pull_request_template.md"),
    require_checklist: Annotated[
        bool,
        typer.Option(
            "--require-checklist",
            help="Require checked rows from the template checklist section in the body.",
        ),
    ] = False,
    checklist_section: Annotated[
        str,
        typer.Option(
            "--checklist-section",
            metavar="TITLE",
            help='H2 title, without "##", containing the checklist rows.',
        ),
    ] = "Checklist",
    fail_on_empty_checklist: Annotated[
        bool,
        typer.Option(
            "--fail-on-empty-checklist",
            help="Fail when checklist validation is requested but the template has no checked rows.",
        ),
    ] = False,
) -> None:
    """Validate PR body sections and optional required checklist rows."""

    run_body_check(
        body,
        template=template,
        require_checklist=require_checklist,
        checklist_section=checklist_section,
        fail_on_empty_checklist=fail_on_empty_checklist,
    )


def main() -> None:
    app(prog_name="zendev-validate-body")
