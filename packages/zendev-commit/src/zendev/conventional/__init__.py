"""Conventional Commits 1.0.0 parsing primitives."""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "ConventionalCommit",
    "ConventionalFooter",
    "ConventionalHeader",
    "ParseIssue",
    "parse_conventional_commit",
]

_HEADER_PATTERN = re.compile(
    r"^(?P<type>[^\s():]+)"
    r"(?:\((?P<scope>[^()\r\n]+)\))?"
    r"(?P<breaking>!)?"
    r": "
    r"(?P<description>[^\r\n]+)$"
)
_FOOTER_PATTERN = re.compile(
    r"^(?P<token>BREAKING CHANGE|[^\s:#]+)"
    r"(?P<separator>: | #)"
    r"(?P<value>.+)$"
)


@dataclass(frozen=True, slots=True)
class ParseIssue:
    """A stable, user-facing parse failure."""

    code: str
    message: str
    line: int = 1


@dataclass(frozen=True, slots=True)
class ConventionalHeader:
    type: str
    scope: str | None
    description: str
    breaking: bool


@dataclass(frozen=True, slots=True)
class ConventionalFooter:
    token: str
    value: str

    @property
    def is_breaking(self) -> bool:
        return self.token in {"BREAKING CHANGE", "BREAKING-CHANGE"}


@dataclass(frozen=True, slots=True)
class ConventionalCommit:
    header: ConventionalHeader
    body: str | None
    footers: tuple[ConventionalFooter, ...]

    @property
    def is_breaking(self) -> bool:
        return self.header.breaking or any(footer.is_breaking for footer in self.footers)


def _parse_footer_block(lines: list[str]) -> tuple[ConventionalFooter, ...] | None:
    if not lines or not _FOOTER_PATTERN.fullmatch(lines[0]):
        return None

    footers: list[ConventionalFooter] = []
    token: str | None = None
    value_lines: list[str] = []
    for line in lines:
        match = _FOOTER_PATTERN.fullmatch(line)
        if match:
            if token is not None:
                footers.append(ConventionalFooter(token=token, value="\n".join(value_lines)))
            token = match.group("token")
            value_lines = [match.group("value")]
        elif token is not None and line:
            value_lines.append(line)
        else:
            return None

    assert token is not None
    footers.append(ConventionalFooter(token=token, value="\n".join(value_lines)))
    return tuple(footers)


def _split_body_and_footers(lines: list[str]) -> tuple[str | None, tuple[ConventionalFooter, ...]]:
    while lines and not lines[-1]:
        lines.pop()
    if not lines:
        return None, ()

    paragraph_starts = [0]
    for index in range(1, len(lines)):
        if lines[index - 1] == "" and lines[index] != "":
            paragraph_starts.append(index)

    for start in reversed(paragraph_starts):
        footers = _parse_footer_block(lines[start:])
        if footers is None:
            continue
        body_lines = lines[:start]
        while body_lines and not body_lines[-1]:
            body_lines.pop()
        return ("\n".join(body_lines) or None), footers

    return "\n".join(lines), ()


def parse_conventional_commit(text: str) -> tuple[ConventionalCommit | None, ParseIssue | None]:
    """Parse a Conventional Commits 1.0.0 message without imposing project policy."""

    lines = text.splitlines()
    if not lines or not lines[0]:
        return None, ParseIssue("empty-message", "The commit message is empty.")

    match = _HEADER_PATTERN.fullmatch(lines[0])
    if match is None:
        return None, ParseIssue(
            "invalid-conventional-header",
            "Expected <type>(<scope>)!: <description>.",
        )

    header = ConventionalHeader(
        type=match.group("type"),
        scope=match.group("scope"),
        description=match.group("description"),
        breaking=match.group("breaking") is not None,
    )
    if len(lines) == 1:
        return ConventionalCommit(header=header, body=None, footers=()), None
    if lines[1] != "":
        return None, ParseIssue(
            "missing-header-separator",
            "The body or footers must begin one blank line after the description.",
            line=2,
        )

    body, footers = _split_body_and_footers(lines[2:])
    return ConventionalCommit(header=header, body=body, footers=footers), None
