"""Select one project-owned TOML source for a domain without merging files."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from zendev.core.diagnostics import Diagnostic, ToolError
from zendev.core.source import exists, read_text

CONFIG_FILENAMES = ("zendev.toml", "pyproject.toml", "proposal.toml")


@dataclass(frozen=True, slots=True)
class ConfigSource:
    root: Path
    path: Path | None
    data: dict[str, object]

    def section(self, name: str) -> dict[str, object]:
        value = self.data.get(name, {})
        if not isinstance(value, dict):
            raise config_error(self.path, f"{name} must be a TOML table")
        return value


def config_error(path: Path | None, message: str, *, code: str = "config.invalid") -> ToolError:
    return ToolError(Diagnostic(code, message, path=str(path) if path else None))


def _read(path: Path) -> dict[str, object]:
    try:
        return tomllib.loads(read_text(path))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise config_error(path, f"Cannot read configuration: {error}", code="config.read") from error


def _pyproject(path: Path) -> dict[str, object] | None:
    payload = _read(path)
    tool = payload.get("tool", {})
    if not isinstance(tool, dict):
        raise config_error(path, "tool must be a table")
    value = tool.get("zendev")
    if value is not None and not isinstance(value, dict):
        raise config_error(path, "tool.zendev must be a table")
    return value


def _source(path: Path, data: dict[str, object], *, dedicated: bool = False) -> ConfigSource:
    if not dedicated and ("commit" in data or "templates" in data):
        raise config_error(
            path,
            "Legacy configuration: migrate to zendev.toml or [tool.zendev], "
            "using [message] and [proposal] with proposal.index.path.",
            code="config.migration",
        )
    if type(data.get("version")) is not int or data["version"] != 1:
        raise config_error(path, "ZenDev configuration version must be 1", code="config.version")
    if dedicated:
        return ConfigSource(path.parent, path, data)
    unknown = sorted(set(data) - {"version", "message", "proposal"})
    if unknown:
        raise config_error(path, "Unknown ZenDev keys: " + ", ".join(unknown))
    for name in ("message", "proposal"):
        if name in data and not isinstance(data[name], dict):
            raise config_error(path, f"{name} must be a TOML table")
    return ConfigSource(path.parent, path, data)


def load_project_config(
    path: str | Path | None = None,
    *,
    start: Path | None = None,
    domain: Literal["message", "proposal"] | None = None,
) -> ConfigSource:
    if path is not None:
        entry = Path(path)
        selected = entry.parent.resolve() / entry.name
        dedicated = selected.name == "proposal.toml"
        if dedicated and domain != "proposal":
            raise config_error(selected, "proposal.toml configures only the proposal domain", code="config.domain")
        data = _pyproject(selected) if selected.name == "pyproject.toml" else _read(selected)
        if data is None:
            raise config_error(selected, "Explicit pyproject.toml has no [tool.zendev] table")
        return _source(selected, data, dedicated=dedicated)
    origin = (start or Path.cwd()).resolve()
    if origin.is_file():
        origin = origin.parent
    for directory in (origin, *origin.parents):
        config, pyproject, dedicated = (directory / name for name in CONFIG_FILENAMES)
        embedded = _pyproject(pyproject) if exists(pyproject) else None
        if exists(config) and embedded is not None:
            raise config_error(
                config,
                "Both zendev.toml and [tool.zendev] configure this directory; choose one.",
                code="config.conflict",
            )
        source = None
        if exists(config):
            source = _source(config, _read(config))
        elif embedded is not None:
            source = _source(pyproject, embedded)
        if domain == "proposal" and exists(dedicated):
            if source is not None and "proposal" in source.data:
                raise config_error(
                    dedicated,
                    f"Both proposal.toml and {source.path} configure proposals; choose one.",
                    code="config.conflict",
                )
            return _source(dedicated, _read(dedicated), dedicated=True)
        if source is not None:
            return source
        if (directory / ".git").exists():
            break
    return ConfigSource(origin, None, {})
