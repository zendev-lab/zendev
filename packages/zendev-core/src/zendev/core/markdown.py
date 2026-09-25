"""Shared syntax-aware Markdown facts without domain policy."""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace
from html.parser import HTMLParser

from markdown_it import MarkdownIt


@dataclass(frozen=True)
class Heading:
    level: int
    text: str
    start: int
    end: int
    plain: str = ""
    markup: str = ""


@dataclass(frozen=True)
class Anchor:
    identifier: str
    canonical: bool
    line: int = 1


class _Anchors(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self.anchors: list[Anchor] = []
        self.links: list[tuple[int, str]] = []
        self.text: list[str] = []
        self.feed(source)

    def handle_data(self, data: str) -> None:
        self.text.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if value is not None and ((tag == "a" and key == "href") or (tag == "img" and key == "src")):
                self.links.append((self.getpos()[0], value))
            if key != "id" or value is None:
                continue
            line, column = self.getpos()
            offset = sum(len(part) for part in self.source.splitlines(keepends=True)[: line - 1]) + column
            canonical = tag == "a" and self.source[offset:].startswith(f'<a id="{value}"></a>')
            self.anchors.append(Anchor(value, canonical, line))


@dataclass(frozen=True)
class TaskItem:
    text: str
    checked: bool
    line: int
    section: str | None


@dataclass(frozen=True)
class MarkdownFacts:
    headings: tuple[Heading, ...]
    anchors: tuple[Anchor, ...]
    marker_lines: tuple[int, ...]
    links: tuple[tuple[int, str], ...] = ()
    prose: tuple[tuple[int, str], ...] = ()
    content: tuple[str, ...] = ()
    tasks: tuple[TaskItem, ...] = ()
    html_blocks: tuple[tuple[int, str], ...] = ()


_facts: ContextVar[dict[tuple[str, str | None], MarkdownFacts] | None] = ContextVar("markdown_facts", default=None)


@contextmanager
def markdown_session() -> Iterator[None]:
    if _facts.get() is not None:
        yield
        return
    token = _facts.set({})
    try:
        yield
    finally:
        _facts.reset(token)


def scan_markdown(markdown: str, marker: str | None = None) -> MarkdownFacts:
    cache = _facts.get()
    key = (markdown, marker)
    if cache is not None and key in cache:
        return cache[key]
    facts = _scan_markdown(markdown, marker)
    if cache is not None:
        cache[key] = facts
    return facts


def _scan_markdown(markdown: str, marker: str | None = None) -> MarkdownFacts:
    """Read rendered structures, excluding code examples and HTML comments."""
    markdown = markdown.replace("\r\n", "\n").replace("\r", "\n")
    tokens = MarkdownIt("commonmark").parse(markdown)
    lines = markdown.split("\n")
    headings: list[Heading] = []
    anchors: list[Anchor] = []
    markers: list[int] = []
    links: list[tuple[int, str]] = []
    prose: list[tuple[int, str]] = []
    content: list[str] = []
    tasks: list[TaskItem] = []
    html_blocks: list[tuple[int, str]] = []
    section: str | None = None
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.level == 0:
            if token.tag == "h2":
                section = tokens[index + 1].content
            elif token.tag == "h1":
                section = None
        if token.type == "html_block" and token.level == 0 and token.map is not None:
            html_blocks.append((token.map[0] + 1, token.content))
        if token.type == "list_item_open" and token.level == 1 and index + 2 < len(tokens):
            inline = tokens[index + 2]
            if inline.type == "inline" and inline.map is not None:
                visible = "".join(
                    child.content
                    for child in (inline.children or [])
                    if child.type in {"text", "code_inline", "softbreak", "hardbreak", "image"}
                )
                task = re.fullmatch(r"\[([ xX])\]\s+(.+)", visible, re.DOTALL)
                if task and re.match(r"\[([ xX])\]\s+", inline.content):
                    tasks.append(TaskItem(task[2].strip(), task[1].lower() == "x", inline.map[0] + 1, section))
        if token.type in {"fence", "code_block"} and token.content.strip():
            content.append(token.content)
        if token.type == "heading_open" and token.level == 0 and token.map is not None:
            inline = tokens[index + 1]
            plain = "".join(
                child.content for child in (inline.children or []) if child.type in {"text", "code_inline", "image"}
            )
            headings.append(
                Heading(int(token.tag[1:]), inline.content, token.map[0], token.map[1], plain, token.markup)
            )
        if (
            marker is not None
            and token.type in {"paragraph_open", "html_block", "heading_open", "hr"}
            and token.level == (1 if marker.startswith(">") else 0)
            and token.map is not None
            and token.map[1] == token.map[0] + 1
            and lines[token.map[0]].strip() == marker
        ):
            markers.append(token.map[0])
        if token.type == "html_block":
            parsed = _Anchors(token.content)
            content.extend(text for text in parsed.text if text.strip())
            links.extend((line + (token.map[0] if token.map else 0), url) for line, url in parsed.links)
            anchors.extend(
                replace(anchor, line=anchor.line + (token.map[0] if token.map else 0)) for anchor in parsed.anchors
            )
        elif token.children:
            if index == 0 or tokens[index - 1].type != "heading_open":
                content.extend(
                    child.content
                    for child in token.children
                    if child.type in {"text", "code_inline", "image"} and child.content.strip()
                )
            line = token.map[0] + 1 if token.map else 1
            text = "".join(
                child.content for child in token.children if child.type in {"text", "softbreak", "hardbreak"}
            )
            prose.extend((line + offset, part) for offset, part in enumerate(text.splitlines()))
            for child in token.children:
                if child.type in {"link_open", "image"}:
                    url = child.attrGet("href" if child.type == "link_open" else "src")
                    if isinstance(url, str):
                        links.append((line, url))
            # Keep adjacent HTML tokens together so an empty <a></a> stays intact.
            html = ""
            for child in token.children:
                if child.type == "html_inline":
                    html += child.content
                else:
                    parsed = _Anchors(html)
                    anchors.extend(Anchor(a.identifier, a.canonical, line + a.line - 1) for a in parsed.anchors)
                    links.extend((line + offset - 1, url) for offset, url in parsed.links)
                    html = ""
            parsed = _Anchors(html)
            anchors.extend(Anchor(a.identifier, a.canonical, line + a.line - 1) for a in parsed.anchors)
            links.extend((line + offset - 1, url) for offset, url in parsed.links)
    return MarkdownFacts(
        tuple(headings),
        tuple(anchors),
        tuple(markers),
        tuple(links),
        tuple(prose),
        tuple(content),
        tuple(tasks),
        tuple(html_blocks),
    )
