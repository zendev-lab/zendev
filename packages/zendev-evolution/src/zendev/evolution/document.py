"""Parse a small, date-addressed Markdown document without rewriting its source."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

_HEADING = re.compile(r" {0,3}(#{1,6})(?:[ \t]+(.*?)|[ \t]*)$")
_FENCE = re.compile(r" {0,3}(`{3,}|~{3,})(.*)$")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_SECTIONS = ("触发", "变化", "理由")


class EvolutionError(Exception):
    """A user-facing diagnostic with a stable exit category and source location."""

    def __init__(self, message: str, *, path: str, line: int = 1, exit_code: int = 1) -> None:
        super().__init__(message)
        self.path = path
        self.line = line
        self.exit_code = exit_code

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {super().__str__()}"


@dataclass(frozen=True)
class Section:
    """A source slice, including its heading and trailing whitespace."""

    title: str
    line: int
    start: int
    end: int


@dataclass(frozen=True)
class Document:
    """Validated source with an origin and chronologically ordered entries."""

    text: str
    origin: Section
    entries: tuple[Section, ...]

    def source(self, section: Section) -> str:
        return self.text[section.start : section.end]


@dataclass(frozen=True)
class _Heading:
    level: int
    title: str
    start: int
    end: int
    line: int
    raw: str


def _headings(text: str, path: str) -> list[_Heading]:
    headings: list[_Heading] = []
    fence_character = ""
    fence_length = 0
    fence_line = 1
    offset = 0
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        raw = line.rstrip("\r\n")
        end = offset + len(line)
        fence = _FENCE.fullmatch(raw)
        if fence_character:
            if fence and fence[1][0] == fence_character and len(fence[1]) >= fence_length and not fence[2].strip():
                fence_character = ""
        elif fence and not (fence[1][0] == "`" and "`" in fence[2]):
            fence_character, fence_length = fence[1][0], len(fence[1])
            fence_line = number
        else:
            match = _HEADING.fullmatch(raw)
            if match:
                title = re.sub(r"[ \t]+#+[ \t]*$", "", match[2] or "").strip()
                headings.append(_Heading(len(match[1]), title, offset, end, number, raw))
        offset = end
    if fence_character:
        raise EvolutionError("Unclosed fenced code block.", path=path, line=fence_line)
    return headings


def validate_date(value: str, *, path: str, line: int = 1, exit_code: int = 1) -> None:
    """Require a real calendar date written exactly as YYYY-MM-DD."""

    try:
        if not _DATE.fullmatch(value):
            raise ValueError
        date.fromisoformat(value)
    except ValueError:
        raise EvolutionError(
            "Expected a real date in YYYY-MM-DD format.", path=path, line=line, exit_code=exit_code
        ) from None


def parse_document(text: str, *, path: str = "EVOLUTION.md") -> Document:
    """Validate the format and retain exact source slices for reads and writes."""

    def fail(message: str, line: int = 1) -> None:
        raise EvolutionError(message, path=path, line=line)

    headings = _headings(text, path)
    roots = [heading for heading in headings if heading.level == 1]
    if len(roots) != 1 or roots[0].raw != "# 项目演进" or text[: roots[0].start].strip():
        fail("Document must begin with a single '# 项目演进' title.")
    sections = [heading for heading in headings if heading.level == 2]
    origins = [heading for heading in sections if heading.title == "初始意图"]
    if len(origins) != 1:
        fail("Expected exactly one '## 初始意图' section.", origins[-1].line if origins else 1)
    if sections[0] != origins[0]:
        fail("'## 初始意图' must precede all dated entries.", sections[0].line)
    if text[roots[0].end : sections[0].start].strip():
        fail("Put introductory content inside '## 初始意图'.", roots[0].line + 1)
    children_by_section: dict[int, list[_Heading]] = {}
    current_section = -1
    for heading in headings:
        if heading.level == 2:
            current_section = heading.start
            children_by_section[current_section] = []
        elif heading.level == 3 and current_section != -1:
            children_by_section[current_section].append(heading)
    previous = ""
    slices: list[Section] = []
    for index, heading in enumerate(sections):
        end = sections[index + 1].start if index + 1 < len(sections) else len(text)
        if heading.raw != f"## {heading.title}":
            fail("Use an unindented '## 初始意图' or '## YYYY-MM-DD' heading.", heading.line)
        if not text[heading.end : end].strip():
            fail("Section body must not be empty.", heading.line)
        if index:
            validate_date(heading.title, path=path, line=heading.line)
            if heading.title <= previous:
                fail("Dates must be unique and in ascending order.", heading.line)
            previous = heading.title
            children = children_by_section[heading.start]
            if tuple(child.title for child in children) != _SECTIONS:
                fail("Expected '### 触发', '### 变化', '### 理由', once each in that order.", heading.line)
            if text[heading.end : children[0].start].strip():
                fail("Put entry content inside the three required subsections.", heading.line + 1)
            for child_index, child in enumerate(children):
                child_end = children[child_index + 1].start if child_index + 1 < len(children) else end
                if not text[child.end : child_end].strip():
                    fail(f"'{child.title}' body must not be empty.", child.line)
        slices.append(Section(heading.title, heading.line, heading.start, end))
    return Document(text, slices[0], tuple(slices[1:]))
