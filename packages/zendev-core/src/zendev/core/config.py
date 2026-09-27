"""Find one project-owned TOML source without merging configuration files."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from zendev.core.diagnostics import Diagnostic, ToolError
from zendev.core.source import exists, read_text


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


def _source(path: Path, data: dict[str, object]) -> ConfigSource:
    if "commit" in data or "templates" in data or (path.name == "proposal.toml"):
        raise config_error(
            path,
            "Legacy configuration: migrate to zendev.toml or [tool.zendev], "
            "using [message] and [proposal] with proposal.index.path.",
            code="config.migration",
        )
    if type(data.get("version")) is not int or data["version"] != 1:
        raise config_error(path, "ZenDev configuration version must be 1", code="config.version")
    unknown = sorted(set(data) - {"version", "message", "proposal"})
    if unknown:
        raise config_error(path, "Unknown ZenDev keys: " + ", ".join(unknown))
    for name in ("message", "proposal"):
        if name in data and not isinstance(data[name], dict):
            raise config_error(path, f"{name} must be a TOML table")
    return ConfigSource(path.parent, path, data)


def load_project_config(path: str | Path | None = None, *, start: Path | None = None) -> ConfigSource:
    if path is not None:
        selected = Path(path).resolve()
        data = _pyproject(selected) if selected.name == "pyproject.toml" else _read(selected)
        if data is None:
            raise config_error(selected, "Explicit pyproject.toml has no [tool.zendev] table")
        return _source(selected, data)
    origin = (start or Path.cwd()).resolve()
    if origin.is_file():
        origin = origin.parent
    for directory in (origin, *origin.parents):
        config = directory / "zendev.toml"
        pyproject = directory / "pyproject.toml"
        embedded = _pyproject(pyproject) if exists(pyproject) else None
        if exists(config) and embedded is not None:
            raise config_error(
                config,
                "Both zendev.toml and [tool.zendev] configure this directory; choose one.",
                code="config.conflict",
            )
        if exists(config):
            return _source(config, _read(config))
        if embedded is not None:
            return _source(pyproject, embedded)
        legacy = directory / "proposal.toml"
        if exists(legacy):
            raise config_error(
                legacy,
                "Migrate proposal.toml into the proposal table of a ZenDev configuration.",
                code="config.migration",
            )
        if (directory / ".git").exists():
            break
    return ConfigSource(origin, None, {})
