"""Offline gitmoji catalog and official-header parsing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from importlib.resources import files

from zendev.conventional import ParseIssue

__all__ = ["Gitmoji", "GitmojiCommit", "GitmojiMatch", "load_gitmojis", "parse_gitmoji_commit"]


@dataclass(frozen=True, slots=True)
class Gitmoji:
    emoji: str
    code: str
    description: str
    name: str
    semver: str | None


@dataclass(frozen=True, slots=True)
class GitmojiMatch:
    gitmoji: Gitmoji
    token: str
    remainder: str


@dataclass(frozen=True, slots=True)
class GitmojiCommit:
    intention: Gitmoji
    token: str
    scope: str | None
    message: str
    body: str | None


@cache
def load_gitmojis() -> tuple[Gitmoji, ...]:
    catalog_path = files("zendev").joinpath("data/gitmojis.json")
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    return tuple(
        Gitmoji(
            emoji=item["emoji"],
            code=item["code"],
            description=item["description"],
            name=item["name"],
            semver=item["semver"],
        )
        for item in payload["gitmojis"]
    )


@cache
def _token_index() -> tuple[tuple[str, Gitmoji], ...]:
    tokens: dict[str, Gitmoji] = {}
    for gitmoji in load_gitmojis():
        tokens[gitmoji.emoji] = gitmoji
        tokens[gitmoji.code] = gitmoji
        without_variation_selector = gitmoji.emoji.replace("\ufe0f", "")
        tokens.setdefault(without_variation_selector, gitmoji)
    return tuple(sorted(tokens.items(), key=lambda item: len(item[0]), reverse=True))


def _match_gitmoji(text: str) -> GitmojiMatch | None:
    for token, gitmoji in _token_index():
        if text.startswith(token) and len(text) > len(token) and text[len(token)].isspace():
            return GitmojiMatch(gitmoji=gitmoji, token=token, remainder=text[len(token) :].lstrip())
    return None


def parse_gitmoji_commit(text: str) -> tuple[GitmojiCommit | None, ParseIssue | None]:
    """Parse the official gitmoji title form and an optional Git body."""

    lines = text.splitlines()
    if not lines or not lines[0]:
        return None, ParseIssue("empty-message", "The commit message is empty.")
    match = _match_gitmoji(lines[0])
    if match is None:
        return None, ParseIssue(
            "invalid-gitmoji",
            "Expected an official gitmoji Unicode token or shortcode.",
        )

    remainder = match.remainder
    scope: str | None = None
    if remainder.startswith("("):
        closing = remainder.find(")")
        if closing <= 1:
            return None, ParseIssue("invalid-gitmoji-scope", "The gitmoji scope must be non-empty.")
        scope = remainder[1:closing]
        remainder = remainder[closing + 1 :]
        if remainder.startswith(":"):
            if len(remainder) == 1 or not remainder[1].isspace():
                return None, ParseIssue(
                    "invalid-gitmoji-separator",
                    "A colon after the gitmoji scope must be followed by a space.",
                )
            remainder = remainder[1:]
        elif not remainder or not remainder[0].isspace():
            return None, ParseIssue(
                "invalid-gitmoji-separator",
                "The gitmoji scope and message must be separated by whitespace or ': '.",
            )
    elif remainder.startswith(":"):
        if len(remainder) == 1 or not remainder[1].isspace():
            return None, ParseIssue(
                "invalid-gitmoji-separator",
                "A gitmoji colon must be followed by a space.",
            )
        remainder = remainder[1:]
    message = remainder.lstrip()
    if not message:
        return None, ParseIssue("missing-gitmoji-message", "The gitmoji message is required.")

    if len(lines) > 1 and lines[1] != "":
        return None, ParseIssue(
            "missing-header-separator",
            "The body must begin one blank line after the gitmoji message.",
            line=2,
        )
    body = "\n".join(lines[2:]).strip() if len(lines) > 2 else ""
    return GitmojiCommit(
        intention=match.gitmoji,
        token=match.token,
        scope=scope,
        message=message,
        body=body or None,
    ), None
