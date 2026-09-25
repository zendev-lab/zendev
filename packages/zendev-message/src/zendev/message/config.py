"""Typed configuration shared by message creation and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from zendev.core.config import ConfigSource, config_error, load_project_config
from zendev.message.commit import MessageProfile


@dataclass(frozen=True, slots=True)
class MessageConfig:
    source: ConfigSource
    profile: MessageProfile
    template: Path
    require_checklist: bool = False
    checklist_section: str = "Checklist"
    fail_on_empty_checklist: bool = False


def load_message_config(
    path: Path | None = None, *, start: Path | None = None, profile: MessageProfile | str | None = None
) -> MessageConfig:
    source = load_project_config(path, start=start)
    data = source.section("message")
    unknown = set(data) - {"profile", "body"}
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
    return MessageConfig(source, selected, source.root / template, required, section, fail_empty)
