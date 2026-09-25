"""Domain-independent diagnostics and deterministic output rendering."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    message: str
    path: str | None = None
    line: int | None = None
    hint: str | None = None
    fixable: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "line": self.line,
            "hint": self.hint,
            "fixable": self.fixable,
        }

    def sort_key(self) -> tuple[str, int, str, str]:
        return (self.path or "", self.line or 0, self.code, self.message)


class ToolError(Exception):
    """Configuration or environment failure; distinct from invalid content."""

    def __init__(self, diagnostic: Diagnostic, *, summary: dict[str, object] | None = None) -> None:
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic
        self.summary = summary


class OutputFormat(StrEnum):
    HUMAN = "human"
    JSON = "json"
    GITHUB = "github"


def render_report(
    diagnostics: Sequence[Diagnostic],
    *,
    command: str,
    output_format: OutputFormat,
    summary: dict[str, object] | None = None,
    success_message: str = "Check passed.",
) -> str:
    if output_format is OutputFormat.JSON:
        return json.dumps(
            {
                "schema_version": 1,
                "command": command,
                "ok": not diagnostics,
                "diagnostics": [d.as_dict() for d in diagnostics],
                "summary": summary,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    if not diagnostics:
        return success_message
    lines = []
    for diagnostic in diagnostics:
        location = diagnostic.path or command
        if diagnostic.line is not None:
            location += f":{diagnostic.line}"
        message = f"{diagnostic.code}: {diagnostic.message}"
        if diagnostic.hint:
            message += f"\n  hint: {diagnostic.hint}"
        if output_format is OutputFormat.GITHUB:
            escaped = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            properties = []
            if diagnostic.path:
                path = diagnostic.path.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
                properties.append("file=" + path.replace(":", "%3A").replace(",", "%2C"))
            if diagnostic.line is not None:
                properties.append(f"line={diagnostic.line}")
            lines.append("::error" + (" " + ",".join(properties) if properties else "") + "::" + escaped)
        else:
            lines.append(f"{location}: {message}")
    return "\n".join(lines)
