"""Commit-message profiles, validation, and zendev's interactive commit tool."""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from collections import OrderedDict
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal, TextIO, TypedDict

import questionary
import typer

from zendev.conventional import ParseIssue, parse_conventional_commit
from zendev.gitmoji import load_emoji_conventions, load_gitmojis, match_gitmoji, parse_gitmoji_commit

__all__ = [
    "COMMIT_CONVENTION_EXAMPLES",
    "EMOJI_MAP",
    "TYPE_DISPLAY_ORDER",
    "TYPE_SHORT_DESCRIPTIONS",
    "CommitProfile",
    "CommitProfileSelection",
    "ValidationResult",
    "ZendevAnswers",
    "ask",
    "commit_app",
    "format_commit_convention_help_body",
    "hook_app",
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


class CommitProfileSelection(StrEnum):
    """CLI values include automatic repository configuration discovery."""

    AUTO = "auto"
    ZENDEV = "zendev"
    CONVENTIONAL = "conventional"
    GITMOJI = "gitmoji"


commit_app = typer.Typer(
    add_completion=False,
    help="Create a commit using zendev's interactive message convention.",
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
)
hook_app = typer.Typer(
    add_completion=False,
    help="Validate a commit message against a configured profile.",
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
)


@dataclass(frozen=True, slots=True)
class ValidationResult:
    valid: bool
    profile: CommitProfile
    issue: ParseIssue | None = None


_CONVENTIONS = load_emoji_conventions()
_CONVENTION_BY_GITMOJI_NAME = {convention.gitmoji.name: convention for convention in _CONVENTIONS}

EMOJI_MAP: dict[str, str] = {convention.type: convention.gitmoji.emoji for convention in _CONVENTIONS}
_DESCRIPTIONS: dict[str, str] = {convention.type: convention.gitmoji.description for convention in _CONVENTIONS}

# Short labels for CLI / CI help tables come directly from the vendored catalog.
TYPE_SHORT_DESCRIPTIONS: dict[str, str] = dict(_DESCRIPTIONS)

_LEGACY_DISPLAY_ORDER: tuple[str, ...] = (
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
TYPE_DISPLAY_ORDER: tuple[str, ...] = _LEGACY_DISPLAY_ORDER + tuple(
    convention.type for convention in _CONVENTIONS if convention.type not in _LEGACY_DISPLAY_ORDER
)

COMMIT_CONVENTION_EXAMPLES: tuple[str, ...] = (
    "🎉 init: begin a project",
    "✨ feat: add JSON logging mode",
    "🐛 fix(parser): handle null token",
    "🚀 deploy: publish the package",
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
        try:
            payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as error:
            raise ValueError(f"{config_path}: failed to load commit profile ({error}).") from error

        tool = payload.get("tool", {})
        if not isinstance(tool, dict):
            raise ValueError(f"{config_path}: tool must be a TOML table.")
        zendev = tool.get("zendev", {})
        if not isinstance(zendev, dict):
            raise ValueError(f"{config_path}: tool.zendev must be a TOML table.")
        commit = zendev.get("commit", {})
        if not isinstance(commit, dict):
            raise ValueError(f"{config_path}: tool.zendev.commit must be a TOML table.")
        value = commit.get("profile")
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
    types = "|".join(re.escape(name) for name in EMOJI_MAP)
    if require_emoji:
        pairs: list[str] = []
        for convention in _CONVENTIONS:
            gitmoji = convention.gitmoji
            tokens = {gitmoji.emoji, gitmoji.emoji.replace("\ufe0f", ""), gitmoji.code}
            token_pattern = "|".join(re.escape(token) for token in sorted(tokens, key=len, reverse=True))
            pairs.append(r"(?:" + token_pattern + r") " + re.escape(convention.type))
        header = r"(?:" + "|".join(pairs) + r")"
    else:
        header = r"(?:\S+ )?(?:" + types + r")"
    return (
        r"(?s)"
        + header
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
    match = match_gitmoji(normalized)
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

    separator_end = len(match.token) + 1
    if normalized[len(match.token)] != " " or separator_end >= len(normalized) or normalized[separator_end].isspace():
        return ValidationResult(
            False,
            CommitProfile.ZENDEV,
            ParseIssue(
                "invalid-zendev-separator",
                "The emoji or shortcode must be followed by exactly one space.",
            ),
        )

    parsed, issue = parse_conventional_commit(match.remainder)
    if parsed is None:
        return ValidationResult(
            False,
            CommitProfile.ZENDEV,
            issue
            or ParseIssue(
                "invalid-zendev-header",
                "Expected <emoji-or-shortcode> <type>(<scope>)!: <description>.",
            ),
        )

    expected_type = _CONVENTION_BY_GITMOJI_NAME[match.gitmoji.name].type
    if parsed.header.type != expected_type:
        return ValidationResult(
            False,
            CommitProfile.ZENDEV,
            ParseIssue(
                "emoji-type-mismatch",
                f"{match.token} must be paired with type {expected_type!r}, not {parsed.header.type!r}.",
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
    parsed, _ = parse_conventional_commit(normalized)
    if parsed is None:
        return None
    emoji = EMOJI_MAP.get(parsed.header.type)
    if emoji is None:
        return None
    return f"{emoji} {normalized}"


def _format_type_table_lines() -> list[str]:
    lines: list[str] = []
    type_width = max(map(len, TYPE_DISPLAY_ORDER))
    for name in TYPE_DISPLAY_ORDER:
        emoji = EMOJI_MAP[name]
        desc = TYPE_SHORT_DESCRIPTIONS[name]
        lines.append(f"    {emoji} {name:{type_width}} {desc}")
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
            "  Expected: <emoji-or-shortcode> <type>(<scope>)!: <description>",
            f"  Catalog:  {len(_CONVENTIONS)} strict emoji-to-type pairs covering every Gitmoji intention",
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


def run_commit_message_check(
    text: str,
    *,
    profile: CommitProfile | str | None = None,
    start: Path | None = None,
    comment_char: str | None = None,
    context: Literal["hook", "ci"] = "hook",
    output: TextIO | None = None,
) -> None:
    """Validate a complete commit message and exit on failure."""

    try:
        selected = resolve_commit_profile(profile, start=start)
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="--profile") from error

    if comment_char is None:
        comment_char = _git_comment_char(start) if start is not None else "#"
    normalized = normalize_commit_message(text, comment_char=comment_char)
    result = validate_commit_message(normalized, profile=selected, comment_char=comment_char)
    if result.valid:
        return

    report_invalid_commit_message(
        normalized,
        context=context,
        file=sys.stderr if output is None else output,
        profile=selected,
        result=result,
    )
    raise typer.Exit(code=1)


@hook_app.command()
def commit_message(
    commit_msg_file: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to the commit message file provided by Git or the hook runner.",
        ),
    ],
    profile: Annotated[
        CommitProfileSelection,
        typer.Option(
            "--profile",
            help="Validation profile; auto reads [tool.zendev.commit] and falls back to zendev.",
        ),
    ] = CommitProfileSelection.AUTO,
) -> None:
    """Validate the message file supplied by Git or a hook runner."""

    run_commit_message_check(
        commit_msg_file.read_text(encoding="utf-8"),
        profile=profile.value,
        start=commit_msg_file.parent,
        context="hook",
        output=sys.stderr,
    )


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
        for name in TYPE_DISPLAY_ORDER
        for emoji in (EMOJI_MAP[name],)
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


@commit_app.command()
def create_commit() -> None:
    """Prompt for a commit message and invoke Git."""

    try:
        answers = ask()
    except KeyboardInterrupt:
        print("\nAborted.")
        raise typer.Exit(code=1) from None

    msg = message(answers)
    result = subprocess.run(["git", "commit", "-m", msg], check=False)
    raise typer.Exit(code=result.returncode)


def main() -> None:
    """Run the interactive commit CLI."""

    commit_app(prog_name="zendev-commit")


def hook_main() -> None:
    """Run the reusable commit-msg hook CLI."""

    hook_app(prog_name="zendev-commit-msg")
