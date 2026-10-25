"""Typed configuration shared by message creation and validation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from zendev.core.config import ConfigSource, config_error, load_project_config
from zendev.message.commit import MessageProfile, check_message


@dataclass(frozen=True, slots=True)
class MessageConfig:
    source: ConfigSource
    profile: MessageProfile
    template: Path
    require_checklist: bool = False
    checklist_section: str = "Checklist"
    fail_on_empty_checklist: bool = False
    replacements: Mapping[str, str] = field(default_factory=dict)


def _replacements(source: ConfigSource, data: dict[str, object]) -> Mapping[str, str]:
    normalization = data.get("normalization", {})
    if not isinstance(normalization, dict) or set(normalization) - {"replacements"}:
        raise config_error(source.path, "message.normalization must contain only a replacements table")
    replacements = normalization.get("replacements", {})
    if not isinstance(replacements, dict):
        raise config_error(source.path, "message.normalization.replacements must be a table")
    for original, replacement in replacements.items():
        if not isinstance(original, str) or not original.strip() or original.splitlines() != [original]:
            raise config_error(source.path, "Replacement keys must be nonempty single-line strings")
        if (
            not isinstance(replacement, str)
            or replacement.splitlines() != [replacement]
            or not check_message(replacement, profile=MessageProfile.ZENDEV).ok
        ):
            raise config_error(source.path, f"Replacement for {original!r} must be a valid single-line zendev title")
    return replacements


def load_message_config(
    path: Path | None = None, *, start: Path | None = None, profile: MessageProfile | str | None = None
) -> MessageConfig:
    source = load_project_config(path, start=start)
    data = source.section("message")
    unknown = set(data) - {"profile", "body", "normalization"}
    if unknown:
        raise config_error(source.path, "Unknown message keys: " + ", ".join(sorted(unknown)))
    raw_profile = data.get("profile", "zendev")
    if not isinstance(raw_profile, str):
        raise config_error(source.path, "message.profile must be a string")
    try:
        configured = MessageProfile(raw_profile)
        selected = MessageProfile(profile) if profile is not None else configured
    except ValueError as error:
        raise config_error(source.path, "message.profile must be zendev, conventional, or gitmoji") from error
    body = data.get("body", {})
    if not isinstance(body, dict) or set(body) - {
        "template",
        "require_checklist",
        "checklist_section",
        "fail_on_empty_checklist",
    }:
        raise config_error(source.path, "message.body contains unknown keys or is not a table")
    template = body.get("template", ".github/pull_request_template.md")
    section = body.get("checklist_section", "Checklist")
    if not isinstance(template, str) or not template or not isinstance(section, str) or not section.strip():
        raise config_error(source.path, "message.body template and checklist_section must be nonempty strings")
    required = body.get("require_checklist", False)
    fail_empty = body.get("fail_on_empty_checklist", False)
    if not isinstance(required, bool) or not isinstance(fail_empty, bool):
        raise config_error(source.path, "Checklist settings must be booleans")
    return MessageConfig(
        source, selected, source.root / template, required, section, fail_empty, _replacements(source, data)
    )
