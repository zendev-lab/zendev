"""Conservative, deterministic repairs for messages with an explicit intention."""

from __future__ import annotations

import re
from dataclasses import dataclass

from zendev.core.diagnostics import Diagnostic
from zendev.message.commit import MessageProfile, check_git_message, check_message, normalize_git_message
from zendev.message.conventional import parse_conventional_commit
from zendev.message.policy import load_policy

_DEFAULTS = {
    "feat": "sparkles",
    "fix": "bug",
    "docs": "memo",
    "style": "art",
    "refactor": "recycle",
    "perf": "zap",
    "test": "white-check-mark",
    "build": "package",
    "ci": "construction-worker",
    "chore": "wrench",
    "revert": "rewind",
}
_DEPENDENCY_OPERATIONS = {
    "upgrade": "arrow-up",
    "update": "arrow-up",
    "bump": "arrow-up",
    "downgrade": "arrow-down",
    "pin": "pushpin",
    "add": "heavy-plus-sign",
    "remove": "heavy-minus-sign",
}


@dataclass(frozen=True, slots=True)
class MessageNormalization:
    text: str
    changed: bool = False
    diagnostics: tuple[Diagnostic, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.diagnostics


def _dependency_intention(description: str) -> str | None:
    words = description.lower().split()
    intention = _DEPENDENCY_OPERATIONS.get(words[0])
    if intention is None or len(words) < 2:
        return None
    # A version change may be a downgrade despite an "update" or "bump" prefix.
    if words[0] in {"update", "bump"} and "from" in words:
        return None
    for operation in re.findall(r"(?:\band\b|\bor\b|\bthen\b|[,&/;])\s*(\w+)", description.lower()):
        other = _DEPENDENCY_OPERATIONS.get(operation)
        if other is not None and other != intention:
            return None
    return intention


def _candidate_header(text: str) -> str | None:
    if text.splitlines()[0] == "[ImgBot] Optimize images":
        return "⚡️ perf(assets): optimize images"
    parsed, _ = parse_conventional_commit(text)
    if parsed is None:
        return None
    header = parsed.header
    intention = _dependency_intention(header.description) if header.type == "deps" else _DEFAULTS.get(header.type)
    if intention is None:
        return None
    emoji = load_policy().for_intention(intention).gitmoji.emoji
    return f"{emoji} {text.splitlines()[0]}"


def normalize_message(
    text: str,
    *,
    profile: MessageProfile | str = MessageProfile.ZENDEV,
    commit: bool = False,
    comment_char: str = "#",
) -> MessageNormalization:
    """Repair only the subject; preserve valid messages and all other bytes of text."""
    selected = MessageProfile(profile)
    checked = (
        check_git_message(text, profile=selected, comment_char=comment_char)
        if commit
        else check_message(text, profile=selected)
    )
    if checked.ok or selected is not MessageProfile.ZENDEV:
        return MessageNormalization(text, diagnostics=checked.diagnostics)
    effective = normalize_git_message(text, comment_char=comment_char) if commit else text
    if not effective:
        return MessageNormalization(text, diagnostics=checked.diagnostics)
    header = _candidate_header(effective)
    if header is None:
        return MessageNormalization(text, diagnostics=checked.diagnostics)
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if commit and (not line.strip() or (comment_char and line.startswith(comment_char))):
            continue
        ending = line[len(line.rstrip("\r\n")) :]
        lines[index] = header + ending
        break
    candidate = "".join(lines)
    validated = (
        check_git_message(candidate, profile=selected, comment_char=comment_char)
        if commit
        else check_message(candidate, profile=selected)
    )
    if not validated.ok:
        return MessageNormalization(text, diagnostics=checked.diagnostics)
    return MessageNormalization(candidate, changed=candidate != text)
