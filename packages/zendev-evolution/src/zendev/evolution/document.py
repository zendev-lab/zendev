"""Validate project evolution records using top-level Markdown structure."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser

from markdown_it import MarkdownIt

_SECTIONS = ("触发", "变化", "理由")


class EvolutionError(ValueError):
    """A document validation error with its source location."""

    def __init__(self, message: str, *, path: str, line: int = 1) -> None:
        super().__init__(f"{path}:{line}: {message}")
        self.message = message
        self.path = path
        self.line = line


@dataclass(frozen=True)
class _Heading:
    level: int
    title: str
    start: int
    end: int


class _HTMLContent(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.has_content = False

    def handle_data(self, data: str) -> None:
        self.has_content |= bool(data.strip())


def _has_content(text: str) -> bool:
    tokens = MarkdownIt("commonmark").parse(text)
    for index, token in enumerate(tokens):
        if token.type in {"fence", "code_block"} and token.content.strip():
            return True
        if token.type == "html_block":
            html = _HTMLContent()
            html.feed(token.content)
            if html.has_content:
                return True
        if (
            token.type == "inline"
            and tokens[index - 1].type != "heading_open"
            and any(
                child.type in {"text", "code_inline", "image"} and child.content.strip()
                for child in token.children or []
            )
        ):
            return True
    return False


def validate_document(text: str, *, path: str = "EVOLUTION.md") -> None:
    """Check initial intent, chronological dates, and nonempty required sections."""

    _validated_sections(text, path=path)


def _validated_sections(text: str, *, path: str) -> list[_Heading]:
    def fail(message: str, line: int = 1) -> None:
        raise EvolutionError(message, path=path, line=line)

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    tokens = MarkdownIt("commonmark").parse(text)
    headings: list[_Heading] = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.level == 0 and token.map is not None:
            level = int(token.tag[1:])
            if level <= 3 and token.markup != "#" * level:
                fail("Use ATX headings for document structure.", token.map[0] + 1)
            headings.append(_Heading(level, tokens[index + 1].content, token.map[0], token.map[1]))

    roots = [heading for heading in headings if heading.level == 1]
    if (
        len(roots) != 1
        or lines[roots[0].start].rstrip("\r\n") != "# 项目演进"
        or "\n".join(lines[: roots[0].start]).strip()
    ):
        fail("Document must begin with a single '# 项目演进' title.")
    sections = [heading for heading in headings if heading.level == 2]
    origins = [heading for heading in sections if heading.title == "初始意图"]
    if len(origins) != 1:
        fail("Expected exactly one '## 初始意图' section.", origins[-1].start + 1 if origins else 1)
    if sections[0] != origins[0]:
        fail("'## 初始意图' must precede all dated entries.", sections[0].start + 1)
    if "\n".join(lines[roots[0].end : sections[0].start]).strip():
        fail("Put introductory content inside '## 初始意图'.", roots[0].end + 1)

    children_by_section: dict[int, list[_Heading]] = {}
    current: list[_Heading] = []
    for heading in headings:
        if heading.level == 2:
            current = children_by_section[heading.start] = []
        elif heading.level == 3:
            current.append(heading)

    previous = ""
    for index, heading in enumerate(sections):
        end = sections[index + 1].start if index + 1 < len(sections) else len(lines)
        if lines[heading.start].rstrip("\r\n") != f"## {heading.title}":
            fail("Use an unindented '## 初始意图' or '## YYYY-MM-DD' heading.", heading.start + 1)
        if not _has_content("\n".join(lines[heading.end : end])):
            fail("Section body must not be empty.", heading.start + 1)
        if index == 0:
            continue
        try:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", heading.title):
                raise ValueError
            date.fromisoformat(heading.title)
        except ValueError:
            fail("Expected a real date in YYYY-MM-DD format.", heading.start + 1)
        if heading.title <= previous:
            fail("Dates must be unique and in ascending order.", heading.start + 1)
        previous = heading.title
        children = children_by_section[heading.start]
        if tuple(child.title for child in children) != _SECTIONS:
            fail("Expected '### 触发', '### 变化', '### 理由', once each in that order.", heading.start + 1)
        if "\n".join(lines[heading.end : children[0].start]).strip():
            fail("Put entry content inside the three required subsections.", heading.end + 1)
        for child_index, child in enumerate(children):
            child_end = children[child_index + 1].start if child_index + 1 < len(children) else end
            if not _has_content("\n".join(lines[child.end : child_end])):
                fail(f"'{child.title}' body must not be empty.", child.start + 1)
    return sections
