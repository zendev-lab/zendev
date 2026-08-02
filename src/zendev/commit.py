"""Commit-message profiles, validation, and zendev's interactive commit tool."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal, TextIO, TypedDict

import questionary

from zendev.conventional import ParseIssue, parse_conventional_commit
from zendev.gitmoji import load_gitmojis, parse_gitmoji_commit

__all__ = [
    "COMMIT_CONVENTION_EXAMPLES",
    "EMOJI_MAP",
    "TYPE_DISPLAY_ORDER",
    "TYPE_SHORT_DESCRIPTIONS",
    "CommitProfile",
    "ValidationResult",
    "ZendevAnswers",
    "ask",
    "commit_msg_hook",
    "format_commit_convention_help_body",
    "hook_main",
    "is_valid_commit_message",
    "main",
    "message",
    "report_invalid_commit_message",
    "resolve_commit_profile",
    "schema_pattern",
    "suggest_commit_message",
    "validate_commit_message",
]


class CommitProfile(StrEnum):
    """Supported commit-message contracts."""

    ZENDEV = "zendev"
    CONVENTIONAL = "conventional"
    GITMOJI = "gitmoji"


@dataclass(frozen=True, slots=True)
class ValidationResult:
    valid: bool
    profile: CommitProfile
    issue: ParseIssue | None = None


EMOJI_MAP: dict[str, str] = {
    "init": "\U0001f389",
    "feat": "\u2728",
    "fix": "\U0001f41b",
    "docs": "\U0001f4dd",
    "refactor": "\u267b\ufe0f",
    "test": "\u2705",
    "ci": "\U0001f477",
    "perf": "\u26a1",
    "chore": "\U0001f527",
    "style": "\U0001f3a8",
    "build": "\U0001f4e6",
}

_DESCRIPTIONS: dict[str, str] = {
    "init": "Project initialization",
    "feat": "A new feature",
    "fix": "A bug fix",
    "docs": "Documentation only changes",
    "refactor": "A code change that neither fixes a bug nor adds a feature",
    "test": "Adding missing or correcting existing tests",
    "ci": "Changes to CI configuration files and scripts",
    "perf": "A code change that improves performance",
    "chore": "Other changes that don't modify src or test files",
    "style": "Changes that do not affect the meaning of the code",
    "build": "Changes that affect the build system or external dependencies",
}

# Short labels for CLI / CI help tables (single source with EMOJI_MAP).
TYPE_SHORT_DESCRIPTIONS: dict[str, str] = {
    "init": "Project initialization",
    "feat": "New feature",
    "fix": "Bug fix",
    "refactor": "Refactoring",
    "perf": "Performance",
    "docs": "Documentation",
    "test": "Tests",
    "build": "Build / dependencies",
    "ci": "CI configuration",
    "chore": "Miscellaneous",
    "style": "Code style",
}

# Stable display order for help output (matches interactive type ordering intent).
TYPE_DISPLAY_ORDER: tuple[str, ...] = (
    "init",
    "feat",
    "fix",
    "refactor",
    "perf",
    "docs",
    "test",
    "build",
    "ci",
    "chore",
    "style",
)

COMMIT_CONVENTION_EXAMPLES: tuple[str, ...] = (
    "✨ feat: add JSON logging mode",
    "🐛 fix(parser): handle null token",
    "📦 build: add pytest-cov dependency",
)

BUMP_PATTERN = r"^((BREAKING[\-\ ]CHANGE|\w+)(\(.+\))?!?):"
BUMP_MAP: OrderedDict[str, str] = OrderedDict(
    (
        (r"^.+!$", "MAJOR"),
        (r"^BREAKING[\-\ ]CHANGE", "MAJOR"),
        (r"^feat", "MINOR"),
        (r"^fix", "PATCH"),
        (r"^refactor", "PATCH"),
        (r"^perf", "PATCH"),
    )
)

SPECIAL_COMMIT_PREFIXES = ("Merge ", "Revert ", "fixup! ", "squash! ", "amend! ", "reword! ")

assert set(TYPE_DISPLAY_ORDER) == set(EMOJI_MAP.keys())
assert set(TYPE_SHORT_DESCRIPTIONS.keys()) == set(EMOJI_MAP.keys())


def _configured_commit_profile(start: Path | None = None) -> CommitProfile | None:
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent
    for directory in (current, *current.parents):
        config_path = directory / "pyproject.toml"
        if not config_path.is_file():
            continue
        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
        value = payload.get("tool", {}).get("zendev", {}).get("commit", {}).get("profile")
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(f"{config_path}: tool.zendev.commit.profile must be a string.")
        try:
            return CommitProfile(value)
        except ValueError as error:
            choices = ", ".join(profile.value for profile in CommitProfile)
            raise ValueError(f"{config_path}: unknown commit profile {value!r}; expected one of {choices}.") from error
    return None


def resolve_commit_profile(
    profile: CommitProfile | str | None = None,
    *,
    start: Path | None = None,
) -> CommitProfile:
    """Resolve an explicit profile or the nearest pyproject setting."""

    if profile is None or profile == "auto":
        return _configured_commit_profile(start) or CommitProfile.ZENDEV
    if isinstance(profile, CommitProfile):
        return profile
    return CommitProfile(profile)


def _parse_scope(text: str) -> str:
    return "-".join(text.strip().split())


def _parse_subject(text: str) -> str:
    subject = text.strip(".").strip()
    if not subject:
        raise ValueError("Subject is required.")
    return subject


class ZendevAnswers(TypedDict):
    prefix: str
    scope: str
    subject: str
    body: str
    footer: str
    is_breaking_change: bool


def message(answers: ZendevAnswers) -> str:
    prefix = answers["prefix"]
    scope = answers["scope"]
    subject = answers["subject"]
    body = answers["body"]
    footer = answers["footer"]
    is_breaking_change = answers["is_breaking_change"]

    emoji = EMOJI_MAP.get(prefix, "")
    formatted_scope = f"({scope})" if scope else ""
    title = f"{emoji} {prefix}{formatted_scope}"

    if is_breaking_change:
        footer = f"BREAKING CHANGE: {footer}"

    formatted_body = f"\n\n{body}" if body else ""
    formatted_footer = f"\n\n{footer}" if footer else ""

    return f"{title}: {subject}{formatted_body}{formatted_footer}"


def schema_pattern(*, require_emoji: bool = True) -> str:
    types = "|".join(EMOJI_MAP.keys())
    if require_emoji:
        emojis = "|".join(re.escape(e) for e in EMOJI_MAP.values())
        emoji_part = r"(" + emojis + r") "
    else:
        emoji_part = r"(\S+ )?"
    return (
        r"(?s)"
        + emoji_part
        + r"("
        + types
        + r")"
        + r"(\(\S+\))?"  # optional scope
        + r"!?"
        + r": "
        + r"([^\n\r]+)"  # subject
        + r"((\n\n.*)|(\s*))?$"
    )


def normalize_commit_message(text: str, *, comment_char: str = "#") -> str:
    lines: list[str] = []
    scissors = f"{comment_char} ------------------------ >8 ------------------------"
    for line in text.splitlines():
        if line.startswith(scissors):
            break
        if comment_char and line.startswith(comment_char):
            continue
        lines.append(line.rstrip())
    return "\n".join(lines).strip()


def _validate_zendev(normalized: str) -> ValidationResult:
    match = re.fullmatch(schema_pattern(), normalized)
    if match is None:
        without_emoji, _ = parse_conventional_commit(normalized)
        issue = (
            ParseIssue("missing-emoji", "An emoji prefix is required.")
            if without_emoji is not None
            else ParseIssue(
                "invalid-zendev-header",
                "Expected <emoji> <type>(<scope>)!: <description>.",
            )
        )
        return ValidationResult(False, CommitProfile.ZENDEV, issue)

    emoji_token = match.group(1).rstrip()
    commit_type = match.group(2)
    if EMOJI_MAP.get(commit_type) != emoji_token:
        return ValidationResult(
            False,
            CommitProfile.ZENDEV,
            ParseIssue(
                "emoji-type-mismatch",
                f"{emoji_token} is not the configured emoji for type {commit_type!r}.",
            ),
        )
    return ValidationResult(True, CommitProfile.ZENDEV)


def validate_commit_message(
    text: str,
    *,
    profile: CommitProfile | str | None = None,
    comment_char: str = "#",
) -> ValidationResult:
    """Validate a complete message against the selected commit profile."""

    selected = resolve_commit_profile(profile)
    normalized = normalize_commit_message(text, comment_char=comment_char)
    if not normalized:
        return ValidationResult(False, selected, ParseIssue("empty-message", "The commit message is empty."))
    if normalized.startswith(SPECIAL_COMMIT_PREFIXES):
        return ValidationResult(True, selected)

    if selected is CommitProfile.ZENDEV:
        return _validate_zendev(normalized)
    if selected is CommitProfile.CONVENTIONAL:
        parsed, issue = parse_conventional_commit(normalized)
    else:
        parsed, issue = parse_gitmoji_commit(normalized)
    return ValidationResult(parsed is not None, selected, issue)


def is_valid_commit_message(
    text: str,
    *,
    profile: CommitProfile | str | None = None,
    comment_char: str = "#",
) -> bool:
    return validate_commit_message(text, profile=profile, comment_char=comment_char).valid


def suggest_commit_message(text: str) -> str | None:
    normalized = normalize_commit_message(text)
    if not normalized or is_valid_commit_message(normalized):
        return None
    if re.fullmatch(schema_pattern(require_emoji=False), normalized) is None:
        return None
    first_token = normalized.split(":", 1)[0]
    commit_type = first_token.split("(", 1)[0].rstrip("!")
    emoji = EMOJI_MAP.get(commit_type)
    if emoji is None:
        return None
    return f"{emoji} {normalized}"


def _format_type_table_lines() -> list[str]:
    lines: list[str] = []
    for name in TYPE_DISPLAY_ORDER:
        emoji = EMOJI_MAP[name]
        desc = TYPE_SHORT_DESCRIPTIONS[name]
        lines.append(f"    {emoji} {name:8} {desc}")
    return lines


def format_commit_convention_help_body(
    *,
    include_special_prefix_note: bool = True,
    profile: CommitProfile | str | None = None,
) -> str:
    selected = resolve_commit_profile(profile)
    if selected is CommitProfile.CONVENTIONAL:
        parts = [
            "",
            "  Expected: <type>(<scope>)!: <description>",
            "            [blank line + optional body]",
            "            [blank line + optional footer(s)]",
            "",
            "  Examples:",
            "    feat: add JSON logging mode",
            "    fix(parser): handle null token",
            "    feat(api)!: replace the response envelope",
            "",
        ]
    elif selected is CommitProfile.GITMOJI:
        parts = [
            "",
            "  Expected: <gitmoji> (<scope>): <message>",
            f"  Catalog:  {len(load_gitmojis())} official Unicode/shortcode intentions from gitmoji.dev",
            "",
            "  Examples:",
            "    ✨ Introduce JSON logging mode",
            "    :bug: (parser): Handle null token",
            "    ♿️ (account): Improve modal accessibility",
            "",
        ]
    else:
        parts = [
            "",
            "  Expected: <emoji> <type>(<scope>): <description>",
            "",
            "  Type table:",
            *_format_type_table_lines(),
            "",
            "  Examples:",
            *(f"    {example}" for example in COMMIT_CONVENTION_EXAMPLES),
            "",
        ]
    if include_special_prefix_note:
        parts.append("  Merge, Revert, fixup!, squash!, amend!, and reword! prefixes are allowed (git-generated).")
        parts.append("")
    return "\n".join(parts).rstrip()


def report_invalid_commit_message(
    normalized: str,
    *,
    context: Literal["hook", "ci"],
    file: TextIO,
    profile: CommitProfile | str | None = None,
    result: ValidationResult | None = None,
) -> None:
    """Print a unified error for invalid messages (commit-msg hook or CI title check)."""
    selected = resolve_commit_profile(profile)
    validation = result or validate_commit_message(normalized, profile=selected)
    suggestion = suggest_commit_message(normalized) if selected is CommitProfile.ZENDEV else None
    if context == "hook":
        print("Invalid commit message.", file=file)
    elif selected is CommitProfile.ZENDEV:
        print("::error::Title does not match zendev emoji commit conventions.", file=file)
    else:
        print(f"::error::Title does not match the {selected.value} commit profile.", file=file)

    if validation.issue is not None:
        print(f"{validation.issue.message} (line {validation.issue.line})", file=file)

    print(format_commit_convention_help_body(profile=selected), file=file)

    if suggestion:
        print(f"Maybe you meant: `{suggestion.splitlines()[0]}`.", file=file)
    elif context == "hook":
        print("Example: `✨ feat: generalize upgrade`.", file=file)

    received_line = normalized.splitlines()[0] if normalized else ""
    print(f"Received: {received_line!r}", file=file)


def commit_msg_hook(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="zendev-commit-msg",
        description="Validate commit messages against a zendev, Conventional Commits, or gitmoji profile.",
    )
    parser.add_argument(
        "--profile",
        choices=("auto", *(profile.value for profile in CommitProfile)),
        default="auto",
        help="Validation profile; auto reads [tool.zendev.commit] and falls back to zendev.",
    )
    parser.add_argument("commit_msg_file", help="Path to the commit message file provided by git/pre-commit.")
    args = parser.parse_args(argv)

    commit_path = Path(args.commit_msg_file)
    try:
        selected = resolve_commit_profile(args.profile, start=commit_path.parent)
    except ValueError as error:
        parser.error(str(error))
    message_text = commit_path.read_text(encoding="utf-8")
    comment_char = _git_comment_char(commit_path.parent)
    normalized = normalize_commit_message(message_text, comment_char=comment_char)
    result = validate_commit_message(normalized, profile=selected, comment_char=comment_char)
    if result.valid:
        return 0

    report_invalid_commit_message(
        normalized,
        context="hook",
        file=sys.stderr,
        profile=selected,
        result=result,
    )
    return 1


def _git_comment_char(cwd: Path) -> str:
    result = subprocess.run(
        ["git", "config", "--get", "core.commentChar"],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    value = result.stdout.strip()
    return value if len(value) == 1 else "#"


def ask() -> ZendevAnswers:
    """Interactively prompt the user for commit details."""
    choices = [
        questionary.Choice(title=f"{emoji} {name}: {_DESCRIPTIONS[name]}", value=name)
        for name, emoji in EMOJI_MAP.items()
    ]

    prefix = questionary.select("Select the type of change you are committing", choices=choices).ask()
    if prefix is None:
        raise KeyboardInterrupt

    scope_raw = questionary.text("Scope (press enter to skip):").ask()
    if scope_raw is None:
        raise KeyboardInterrupt
    scope = _parse_scope(scope_raw)

    subject_raw = questionary.text("Short imperative summary:").ask()
    if subject_raw is None:
        raise KeyboardInterrupt
    subject = _parse_subject(subject_raw)

    body = questionary.text("Body (press enter to skip):").ask()
    if body is None:
        raise KeyboardInterrupt

    is_breaking_change = questionary.confirm("Is this a BREAKING CHANGE?", default=False).ask()
    if is_breaking_change is None:
        raise KeyboardInterrupt

    footer = questionary.text("Footer (press enter to skip):").ask()
    if footer is None:
        raise KeyboardInterrupt

    return ZendevAnswers(
        prefix=prefix,
        scope=scope,
        subject=subject,
        body=body,
        footer=footer,
        is_breaking_change=is_breaking_change,
    )


def main() -> None:
    """Entry point for zendev-commit."""
    try:
        answers = ask()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)

    msg = message(answers)
    result = subprocess.run(["git", "commit", "-m", msg], check=False)
    sys.exit(result.returncode)


def hook_main() -> None:
    """Entry point for the reusable commit-msg hook."""
    sys.exit(commit_msg_hook())
