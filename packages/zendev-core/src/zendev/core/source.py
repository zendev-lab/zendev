"""Read each input once during one application invocation."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class SourceSnapshot:
    files: dict[Path, bytes | None] = field(default_factory=dict)

    def read(self, path: Path) -> bytes:
        path = path.resolve()
        if path not in self.files:
            try:
                self.files[path] = path.read_bytes()
            except FileNotFoundError:
                self.files[path] = None
        data = self.files[path]
        if data is None:
            raise FileNotFoundError(path)
        return data


_current: ContextVar[SourceSnapshot | None] = ContextVar("source_snapshot", default=None)


def current_snapshot() -> SourceSnapshot | None:
    return _current.get()


@contextmanager
def source_session(*, fresh: bool = False) -> Iterator[SourceSnapshot]:
    existing = _current.get()
    if existing is not None and not fresh:
        yield existing
        return
    snapshot = SourceSnapshot()
    token = _current.set(snapshot)
    try:
        yield snapshot
    finally:
        _current.reset(token)


def read_bytes(path: Path) -> bytes:
    snapshot = _current.get()
    return snapshot.read(path) if snapshot is not None else path.read_bytes()


def read_text(path: Path) -> str:
    return read_bytes(path).decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")


def exists(path: Path) -> bool:
    if path.is_dir():
        return True
    try:
        read_bytes(path)
        return True
    except FileNotFoundError:
        return False
