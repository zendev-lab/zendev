"""Offline gitmoji catalog and official-header parsing."""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from functools import cache
from importlib.resources import files

from zendev.conventional import ParseIssue

__all__ = [
    "EmojiConvention",
    "Gitmoji",
    "GitmojiCommit",
    "GitmojiMatch",
    "load_emoji_conventions",
    "load_gitmojis",
    "match_gitmoji",
    "parse_gitmoji_commit",
]


@dataclass(frozen=True, slots=True)
class Gitmoji:
    emoji: str
    code: str
    description: str
    name: str
    semver: str | None


@dataclass(frozen=True, slots=True)
class EmojiConvention:
    """A Gitmoji intention paired with its canonical zendev commit type."""

    type: str
    gitmoji: Gitmoji


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
def load_emoji_conventions() -> tuple[EmojiConvention, ...]:
    """Load and validate the complete, strict emoji-to-type convention."""

    mapping_path = files("zendev").joinpath("data/emoji-conventions.toml")
    payload = tomllib.loads(mapping_path.read_text(encoding="utf-8"))
    types = payload.get("types")
    if not isinstance(types, dict):
        raise ValueError("emoji-conventions.toml must contain a string-to-string [types] table.")
    type_mapping = {name: value for name, value in types.items() if isinstance(name, str) and isinstance(value, str)}
    if len(type_mapping) != len(types):
        raise ValueError("emoji-conventions.toml must contain a string-to-string [types] table.")

    catalog = load_gitmojis()
    catalog_names = {item.name for item in catalog}
    mapped_names = set(type_mapping)
    if mapped_names != catalog_names:
        missing = ", ".join(sorted(catalog_names - mapped_names)) or "none"
        extra = ", ".join(sorted(mapped_names - catalog_names)) or "none"
        raise ValueError(
            f"Emoji convention must cover the Gitmoji catalog exactly (missing: {missing}; extra: {extra})."
        )

    type_names = tuple(type_mapping[item.name] for item in catalog)
    if any(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", type_name) is None for type_name in type_names):
        raise ValueError("Emoji convention types must be lowercase words separated by single hyphens.")
    if len(set(type_names)) != len(type_names):
        raise ValueError("Emoji convention types must be unique.")

    return tuple(EmojiConvention(type=type_mapping[item.name], gitmoji=item) for item in catalog)


@cache
def _token_index() -> tuple[tuple[str, Gitmoji], ...]:
    tokens: dict[str, Gitmoji] = {}
    for gitmoji in load_gitmojis():
        tokens[gitmoji.emoji] = gitmoji
        tokens[gitmoji.code] = gitmoji
        without_variation_selector = gitmoji.emoji.replace("\ufe0f", "")
        tokens.setdefault(without_variation_selector, gitmoji)
    return tuple(sorted(tokens.items(), key=lambda item: len(item[0]), reverse=True))


def match_gitmoji(text: str) -> GitmojiMatch | None:
    for token, gitmoji in _token_index():
        if text.startswith(token) and len(text) > len(token) and text[len(token)].isspace():
            return GitmojiMatch(gitmoji=gitmoji, token=token, remainder=text[len(token) :].lstrip())
    return None


def parse_gitmoji_commit(text: str) -> tuple[GitmojiCommit | None, ParseIssue | None]:
    """Parse the official gitmoji title form and an optional Git body."""

    lines = text.splitlines()
    if not lines or not lines[0]:
        return None, ParseIssue("empty-message", "The commit message is empty.")
    match = match_gitmoji(lines[0])
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
