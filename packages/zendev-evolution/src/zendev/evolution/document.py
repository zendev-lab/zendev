"""Pure document policy over shared Markdown facts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from zendev.core.diagnostics import Diagnostic
from zendev.core.markdown import Heading, scan_markdown

_SECTIONS = ("触发", "变化", "理由")


@dataclass(frozen=True)
class EvolutionSection:
    title: str
    line: int


@dataclass(frozen=True)
class EvolutionCheck:
    sections: tuple[EvolutionSection, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.diagnostics


def check_document(text: str, *, path: str = "EVOLUTION.md") -> EvolutionCheck:
    """Return validated navigation or the first structural diagnostic, without I/O."""

    def invalid(code: str, message: str, line: int = 1) -> EvolutionCheck:
        return EvolutionCheck(diagnostics=(Diagnostic(code, message, path=path, line=line),))

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    headings = scan_markdown(text).headings
    for heading in headings:
        if heading.level <= 3 and heading.markup != "#" * heading.level:
            return invalid("evolution.heading", "Use ATX headings for document structure.", heading.start + 1)

    roots = [heading for heading in headings if heading.level == 1]
    if (
        len(roots) != 1
        or lines[roots[0].start].rstrip("\r\n") != "# 项目演进"
        or "\n".join(lines[: roots[0].start]).strip()
    ):
        return invalid("evolution.title", "Document must begin with a single '# 项目演进' title.")
    sections = [heading for heading in headings if heading.level == 2]
    origins = [heading for heading in sections if heading.text == "初始意图"]
    if len(origins) != 1:
        return invalid(
            "evolution.origin", "Expected exactly one '## 初始意图' section.", origins[-1].start + 1 if origins else 1
        )
    if sections[0] != origins[0]:
        return invalid("evolution.origin.order", "'## 初始意图' must precede all dated entries.", sections[0].start + 1)
    if "\n".join(lines[roots[0].end : sections[0].start]).strip():
        return invalid("evolution.origin.preamble", "Put introductory content inside '## 初始意图'.", roots[0].end + 1)

    children_by_section: dict[int, list[Heading]] = {}
    current: list[Heading] = []
    for heading in headings:
        if heading.level == 2:
            current = children_by_section[heading.start] = []
        elif heading.level == 3:
            current.append(heading)

    previous = ""
    for index, heading in enumerate(sections):
        end = sections[index + 1].start if index + 1 < len(sections) else len(lines)
        if lines[heading.start].rstrip("\r\n") != f"## {heading.text}":
            return invalid(
                "evolution.heading", "Use an unindented '## 初始意图' or '## YYYY-MM-DD' heading.", heading.start + 1
            )
        if not scan_markdown("\n".join(lines[heading.end : end])).content:
            return invalid("evolution.body.empty", "Section body must not be empty.", heading.start + 1)
        if index == 0:
            continue
        try:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", heading.text):
                raise ValueError
            date.fromisoformat(heading.text)
        except ValueError:
            return invalid("evolution.date", "Expected a real date in YYYY-MM-DD format.", heading.start + 1)
        if heading.text <= previous:
            return invalid("evolution.date.order", "Dates must be unique and in ascending order.", heading.start + 1)
        previous = heading.text
        children = children_by_section[heading.start]
        if tuple(child.text for child in children) != _SECTIONS:
            return invalid(
                "evolution.sections",
                "Expected '### 触发', '### 变化', '### 理由', once each in that order.",
                heading.start + 1,
            )
        if "\n".join(lines[heading.end : children[0].start]).strip():
            return invalid(
                "evolution.sections.preamble",
                "Put entry content inside the three required subsections.",
                heading.end + 1,
            )
        for child_index, child in enumerate(children):
            child_end = children[child_index + 1].start if child_index + 1 < len(children) else end
            if not scan_markdown("\n".join(lines[child.end : child_end])).content:
                return invalid("evolution.body.empty", f"'{child.text}' body must not be empty.", child.start + 1)
    return EvolutionCheck(tuple(EvolutionSection(h.text, h.start + 1) for h in sections))
