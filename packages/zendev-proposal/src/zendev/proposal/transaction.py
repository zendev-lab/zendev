"""Optimistic input snapshots and rollback-capable local file replacement."""

from __future__ import annotations

import os
import stat
import tempfile
from contextlib import suppress
from pathlib import Path

from zendev.proposal.model import Diagnostic, ProposalConfig, ProposalToolError


def snapshot_inputs(config: ProposalConfig) -> dict[Path, bytes]:
    paths = {config.config_path, config.schema_path, *config.templates.values()}
    directories = [config.documents_dir]
    schemas = {config.schema_path.parent}
    if config.drafts:
        directories.append(config.drafts.directory)
        paths.add(config.drafts.schema_path)
        schemas.add(config.drafts.schema_path.parent)
    for directory in directories:
        paths.update(path for path in directory.rglob("*") if path.is_file() and not path.name.startswith(".zendev-"))
    for directory in schemas:
        paths.update(
            path
            for path in directory.rglob("*.json")
            if not any(part.startswith(".") for part in path.relative_to(directory).parts)
        )
    # Include linked files used by the offline fragment validator.
    from urllib.parse import unquote, urlsplit

    from zendev.proposal._markdown_scan import scan_markdown

    for path in tuple(paths):
        if path.suffix.lower() != ".md":
            continue
        for _, url in scan_markdown(path.read_text(encoding="utf-8")).links:
            parsed = urlsplit(url)
            if not parsed.scheme and not parsed.netloc and parsed.path:
                relative = unquote(parsed.path)
                target = (
                    config.root / relative.lstrip("/") if relative.startswith("/") else path.parent / relative
                ).resolve()
                if target != config.index_path and target.is_relative_to(config.root) and target.is_file():
                    paths.add(target)
    if config.index_path in paths or any(config.index_path.is_relative_to(directory) for directory in directories):
        raise ProposalToolError(
            Diagnostic(
                code="proposal.config.output-conflict",
                path=config.relative_path(config.index_path),
                message="index aliases a proposal input",
            )
        )
    if config.index_path.exists():
        if not config.index_path.is_file() or any(config.index_path.samefile(path) for path in paths):
            raise ProposalToolError(
                Diagnostic(
                    code="proposal.config.output-conflict", message="index must be a distinct regular output file"
                )
            )
        paths.add(config.index_path)
    try:
        return {path: path.read_bytes() for path in sorted(paths)}
    except (OSError, UnicodeError) as error:
        raise ProposalToolError(
            Diagnostic(code="proposal.fix.read", message=f"cannot snapshot repair inputs: {error}")
        ) from error


def commit_files(config: ProposalConfig, updates: dict[Path, bytes], before: dict[Path, bytes]) -> None:
    """Prepare every replacement and backup before changing any destination."""
    prepared: dict[Path, Path] = {}
    backups: dict[Path, Path] = {}
    applied: list[Path] = []
    recovery: set[Path] = set()

    def temporary(path: Path, content: bytes) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".zendev-", suffix=".tmp", dir=path.parent)
        result = Path(name)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            if path.exists():
                result.chmod(stat.S_IMODE(path.stat().st_mode))
            return result
        except OSError:
            result.unlink(missing_ok=True)
            raise

    try:
        if snapshot_inputs(config) != before:
            raise ProposalToolError(
                Diagnostic(
                    code="proposal.fix.changed", message="repair inputs changed after validation; no files written"
                )
            )
        for path, content in updates.items():
            if path.is_symlink() or not path.resolve().is_relative_to(config.root):
                raise ProposalToolError(
                    Diagnostic(
                        code="proposal.fix.path",
                        path=config.relative_path(path),
                        message="repair target is not a regular repository-local file",
                    )
                )
            prepared[path] = temporary(path, content)
            if path in before:
                backups[path] = temporary(path, before[path])
        if snapshot_inputs(config) != before:
            raise ProposalToolError(
                Diagnostic(
                    code="proposal.fix.changed",
                    message="repair inputs changed while preparing writes; no files written",
                )
            )
        for path, temp in prepared.items():
            os.replace(temp, path)
            applied.append(path)
    except OSError as error:
        remaining: list[str] = []
        for path in reversed(applied):
            try:
                if path in backups:
                    os.replace(backups[path], path)
                else:
                    path.unlink()
            except OSError:
                remaining.append(config.relative_path(path))
                if path in backups:
                    recovery.add(backups[path])
        summary: dict[str, object] = {
            "written_files": sorted(remaining),
            "recovery_files": [str(path) for path in sorted(recovery)],
            "rolled_back_files": [
                config.relative_path(path) for path in applied if config.relative_path(path) not in remaining
            ],
        }
        raise ProposalToolError(
            Diagnostic(code="proposal.fix.write", message=f"repair write failed: {error}"), summary=summary
        ) from error
    finally:
        for temp in (*prepared.values(), *backups.values()):
            if temp not in recovery:
                with suppress(OSError):
                    temp.unlink(missing_ok=True)
