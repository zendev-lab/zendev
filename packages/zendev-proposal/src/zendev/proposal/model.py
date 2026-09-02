"""Typed proposal-tool contracts shared by validation, indexing, and the CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

IndexSource = Literal["metadata", "identifier", "path", "inverse"]
MetadataTitleMode = Literal["plain", "prefixed"]


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """One stable, machine-readable proposal diagnostic."""

    code: str
    message: str
    path: str | None = None
    line: int | None = None
    hint: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "path": self.path,
            "line": self.line,
            "message": self.message,
            "hint": self.hint,
        }

    def sort_key(self) -> tuple[str, int, str, str]:
        return (self.path or "", self.line or 0, self.code, self.message)


class ProposalToolError(Exception):
    """A configuration or environment error, distinct from invalid proposals."""

    def __init__(self, diagnostic: Diagnostic) -> None:
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


@dataclass(frozen=True, slots=True)
class SummaryPolicy:
    prefix: str
    minimum_sentences: int = 2
    maximum_sentences: int = 4


@dataclass(frozen=True, slots=True)
class DraftPolicy:
    directory: Path
    schema_path: Path
    marker: str | None
    require_summary: bool
    pre_proposal: bool


@dataclass(frozen=True, slots=True)
class GraphPolicy:
    fields: tuple[str, ...]
    requires_field: str | None = None
    amends_field: str | None = None
    supersedes_field: str | None = None
    accepted_status: str = "Accepted"
    superseded_status: str = "Superseded"


@dataclass(frozen=True, slots=True)
class HistoryWaiver:
    path: str
    from_status: str
    to_status: str
    reason: str


@dataclass(frozen=True, slots=True)
class HistoryPolicy:
    initial_status: str
    protect_records: bool
    bootstrap_numbers: frozenset[int]
    transitions: dict[str, frozenset[str]]
    waivers: tuple[HistoryWaiver, ...] = ()


@dataclass(frozen=True, slots=True)
class IndexField:
    name: str
    source: IndexSource
    key: str | None = None


@dataclass(frozen=True, slots=True)
class IndexPolicy:
    version: int
    entries_key: str
    include_drafts: bool
    fields: tuple[IndexField, ...]


@dataclass(frozen=True, slots=True)
class DefinesPolicy:
    field: str
    anchor_prefix: str
    id_pattern: str


@dataclass(frozen=True, slots=True)
class ProposalConfig:
    root: Path
    config_path: Path
    prefix: str
    number_field: str
    title_field: str
    type_field: str
    status_field: str
    documents_dir: Path
    drafts: DraftPolicy | None
    schema_path: Path
    index_path: Path
    number_width: int
    metadata_title: MetadataTitleMode
    filename_slug_pattern: str
    templates: dict[str, Path]
    summary: SummaryPolicy | None
    graph: GraphPolicy | None
    history: HistoryPolicy | None
    defines: DefinesPolicy | None
    index: IndexPolicy

    def format_identifier(self, number: int) -> str:
        return f"{self.prefix}-{number:0{self.number_width}d}"

    def relative_path(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return path.as_posix()


@dataclass(frozen=True, slots=True)
class ProposalDocument:
    path: Path
    relative_path: str
    raw_frontmatter: str
    metadata: dict[str, object]
    body: str
    is_draft: bool = False

    def number(self, config: ProposalConfig) -> int | None:
        value = self.metadata.get(config.number_field)
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    def identifier(self, config: ProposalConfig) -> str | None:
        number = self.number(config)
        return config.format_identifier(number) if number is not None else None


@dataclass(frozen=True, slots=True)
class RepositoryState:
    documents: tuple[ProposalDocument, ...]
    formal_documents: tuple[ProposalDocument, ...]
    draft_paths: tuple[Path, ...]
    diagnostics: tuple[Diagnostic, ...] = field(default_factory=tuple)

    @property
    def draft_count(self) -> int:
        return len(self.draft_paths)


@dataclass(frozen=True, slots=True)
class ValidationResult:
    state: RepositoryState
    diagnostics: tuple[Diagnostic, ...]

    @property
    def ok(self) -> bool:
        return not self.diagnostics
