"""Shared syntax-aware Markdown facts for proposal validation and repair."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

from markdown_it import MarkdownIt


@dataclass(frozen=True)
class Heading:
    level: int
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class Anchor:
    identifier: str
    canonical: bool


class _Anchors(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self.anchors: list[Anchor] = []
        self.feed(source)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key != "id" or value is None:
                continue
            line, column = self.getpos()
            offset = sum(len(part) for part in self.source.splitlines(keepends=True)[: line - 1]) + column
            canonical = tag == "a" and self.source[offset:].startswith(f'<a id="{value}"></a>')
            self.anchors.append(Anchor(value, canonical))


@dataclass(frozen=True)
class MarkdownFacts:
    headings: tuple[Heading, ...]
    anchors: tuple[Anchor, ...]
    marker_lines: tuple[int, ...]


def scan_markdown(markdown: str, marker: str | None = None) -> MarkdownFacts:
    """Read rendered structures, excluding code examples and HTML comments."""
    tokens = MarkdownIt("commonmark").parse(markdown)
    lines = markdown.splitlines()
    headings: list[Heading] = []
    anchors: list[Anchor] = []
    markers: list[int] = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.level == 0 and token.map is not None:
            headings.append(Heading(int(token.tag[1:]), tokens[index + 1].content, *token.map))
        if (
            marker is not None
            and token.type == "paragraph_open"
            and token.level == (1 if marker.startswith(">") else 0)
            and token.map is not None
            and token.map[1] == token.map[0] + 1
            and lines[token.map[0]].strip() == marker
        ):
            markers.append(token.map[0])
        if token.type == "html_block":
            anchors.extend(_Anchors(token.content).anchors)
        elif token.children:
            # Keep adjacent HTML tokens together so an empty <a></a> stays intact.
            html = ""
            for child in token.children:
                if child.type == "html_inline":
                    html += child.content
                else:
                    anchors.extend(_Anchors(html).anchors)
                    html = ""
            anchors.extend(_Anchors(html).anchors)
    return MarkdownFacts(tuple(headings), tuple(anchors), tuple(markers))
