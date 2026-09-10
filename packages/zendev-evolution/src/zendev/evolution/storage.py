"""Locked, optimistic, atomic writes to a single evolution file."""

from __future__ import annotations

import os
import stat
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from zendev.evolution.document import Document, EvolutionError, parse_document, validate_date


@dataclass(frozen=True)
class _Snapshot:
    content: bytes
    identity: tuple[int, int, int, int, int]
    mode: int


def _snapshot(path: Path) -> _Snapshot | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode):
        raise EvolutionError("Expected a regular file, not a symlink or directory.", path=str(path), exit_code=2)
    content = path.read_bytes()
    return _Snapshot(
        content,
        (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns),
        stat.S_IMODE(info.st_mode),
    )


def _decode(content: bytes, path: Path) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        raise EvolutionError("Expected UTF-8 text.", path=str(path), exit_code=2) from None


def read_document(path: Path) -> Document:
    """Read and validate a document, preserving its line endings."""

    snapshot = _snapshot(path)
    if snapshot is None:
        raise EvolutionError("File does not exist; run evolution init first.", path=str(path), exit_code=2)
    return parse_document(_decode(snapshot.content, path), path=str(path))


@contextmanager
def _locked(path: Path) -> Iterator[None]:
    lock_path = path.with_name(f".{path.name}.lock")
    try:
        descriptor = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise EvolutionError(
            f"Writer lock exists: {lock_path}. Retry after the writer finishes; "
            "remove a stale lock only after confirming no writer is running.",
            path=str(path),
            exit_code=2,
        ) from None
    try:
        with os.fdopen(descriptor, "w") as lock:
            lock.write(f"{os.getpid()}\n")
        yield
    finally:
        lock_path.unlink()


def _save(path: Path, original: _Snapshot | None, text: str) -> None:
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(text.encode("utf-8"))
            output.flush()
            os.fsync(output.fileno())
        if original is not None:
            temporary.chmod(original.mode)
        if _snapshot(path) != original:
            raise EvolutionError(
                "File changed while preparing the write; retry from fresh content.", path=str(path), exit_code=2
            )
        if original is None:
            # Linking a complete file creates it atomically without replacing a racing creator.
            os.link(temporary, path)
        else:
            os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _validate_input(prefix: str, body: str, source: str) -> Document:
    try:
        return parse_document(prefix + body.rstrip() + "\n", path=source)
    except EvolutionError as error:
        error.line = max(1, error.line - prefix.count("\n"))
        raise


def initialize(path: Path, body: str, *, source: str = "<input>") -> None:
    """Create the origin once. Existing paths are never overwritten."""

    document = _validate_input("# 项目演进\n\n## 初始意图\n\n", body, source)
    text = document.text
    if document.entries:
        raise EvolutionError("Origin input must not contain dated entries.", path=source)
    with _locked(path):
        if _snapshot(path) is not None:
            raise EvolutionError("File already exists; init never overwrites it.", path=str(path), exit_code=2)
        _save(path, None, text)


def write_entry(path: Path, day: str, body: str, *, replace: bool = False, source: str = "<input>") -> None:
    """Insert or explicitly replace one date, leaving all other source intact."""

    validate_date(day, path=str(path), exit_code=2)
    entry = f"## {day}\n\n{body.rstrip()}\n"
    candidate = _validate_input(f"# 项目演进\n\n## 初始意图\n\nOrigin\n\n## {day}\n\n", body, source)
    if len(candidate.entries) != 1:
        raise EvolutionError("Input must contain only the three subsections for one day.", path=source)
    with _locked(path):
        original = _snapshot(path)
        if original is None:
            raise EvolutionError("File does not exist; run evolution init first.", path=str(path), exit_code=2)
        document = parse_document(_decode(original.content, path), path=str(path))
        existing = next((section for section in document.entries if section.title == day), None)
        if replace and existing is None:
            raise EvolutionError("Cannot replace a date that does not exist.", path=str(path), exit_code=2)
        if existing and not replace:
            raise EvolutionError("Date already exists; use --replace to change it.", path=str(path), exit_code=2)
        if existing:
            start, end = existing.start, existing.end
        else:
            following = next((section for section in document.entries if section.title > day), None)
            start = end = following.start if following else len(document.text)
        prefix, suffix = document.text[:start], document.text[end:]
        separator = (
            ""
            if start < len(document.text) or not prefix or prefix.endswith("\n\n") or prefix.endswith("\r\n\r\n")
            else ("\n" if prefix.endswith("\n") else "\n\n")
        )
        text = prefix + separator + entry + ("\n" if suffix else "") + suffix
        parse_document(text, path=str(path))
        _save(path, original, text)
