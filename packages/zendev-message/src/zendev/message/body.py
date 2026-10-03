"""PR template policy over shared Markdown source facts."""

from __future__ import annotations

import re
from dataclasses import dataclass

from zendev.core.diagnostics import Diagnostic
from zendev.core.markdown import scan_markdown

_DIRECTIVE = re.compile(r"<!--\s*pr-body:(required|optional)\s*-->")


@dataclass(frozen=True, slots=True)
class BodySection:
    heading: str
    required: bool = True


def parse_template(text: str) -> tuple[BodySection, ...]:
    facts = scan_markdown(text)
    directives = [
        (line, match[1] == "required")
        for line, content in facts.html_blocks
        if (match := _DIRECTIVE.fullmatch(content.strip()))
    ]
    sections = []
    previous = 0
    for heading in facts.headings:
        if heading.level != 2:
            continue
        applicable = [required for line, required in directives if previous < line <= heading.start]
        if len(applicable) > 1:
            raise ValueError("Multiple pr-body directives before an H2 section")
        sections.append(BodySection(heading.text, applicable[0] if applicable else True))
        previous = heading.start + 1
    if any(line > previous for line, _ in directives):
        raise ValueError("A pr-body directive is not followed by an H2 section")
    names = [section.heading for section in sections]
    if not names or len(set(names)) != len(names):
        raise ValueError("PR template must have unique top-level H2 sections")
    return tuple(sections)


def check_body(
    text: str,
    template: str,
    *,
    require_checklist: bool = False,
    checklist_section: str = "Checklist",
    fail_on_empty_checklist: bool = False,
) -> tuple[Diagnostic, ...]:
    sections = parse_template(template)
    facts = scan_markdown(text)
    headings = [heading for heading in facts.headings if heading.level == 2]
    names = [heading.text for heading in headings]
    order = {section.heading: index for index, section in enumerate(sections)}
    diagnostics = []
    for section in sections:
        if section.required and section.heading not in names:
            diagnostics.append(
                Diagnostic("message.body.missing-section", f"Missing required section: {section.heading}")
            )
    seen = set()
    positions = []
    for heading in headings:
        if heading.text in seen or heading.text not in order:
            diagnostics.append(
                Diagnostic(
                    "message.body.section", f"Unexpected or repeated section: {heading.text}", line=heading.start + 1
                )
            )
        else:
            positions.append(order[heading.text])
        seen.add(heading.text)
    if positions != sorted(positions):
        diagnostics.append(Diagnostic("message.body.order", "Sections must follow the repository template order."))
    if require_checklist:
        required = {
            task.text for task in scan_markdown(template).tasks if task.section == checklist_section and task.checked
        }
        actual = {task.text for task in facts.tasks if task.section == checklist_section and task.checked}
        if not required and fail_on_empty_checklist:
            diagnostics.append(
                Diagnostic("message.body.empty-checklist", f"No checked template tasks in {checklist_section!r}.")
            )
        diagnostics.extend(
            Diagnostic("message.body.checklist", f"Missing checked task: {item}") for item in sorted(required - actual)
        )
    return tuple(diagnostics)
