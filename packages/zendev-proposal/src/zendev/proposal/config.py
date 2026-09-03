"""Load and fail-closed validate ``proposal.toml``."""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from pathlib import Path

from zendev.proposal.model import (
    DefinesPolicy,
    Diagnostic,
    DraftPolicy,
    GraphPolicy,
    HistoryPolicy,
    HistoryWaiver,
    IndexField,
    IndexPolicy,
    IndexSource,
    MetadataTitleMode,
    ProposalConfig,
    ProposalToolError,
    SummaryPolicy,
)

_TOP_LEVEL_KEYS = {
    "version",
    "proposal",
    "drafts",
    "templates",
    "summary",
    "graph",
    "history",
    "defines",
    "index",
}
_PROPOSAL_KEYS = {
    "prefix",
    "number_field",
    "title_field",
    "type_field",
    "status_field",
    "documents_dir",
    "schema",
    "index",
    "number_width",
    "metadata_title",
    "filename_slug_pattern",
}
_DRAFT_KEYS = {"directory", "schema", "marker", "require_summary", "pre_proposal"}
_SUMMARY_KEYS = {"prefix", "minimum_sentences", "maximum_sentences"}
_GRAPH_KEYS = {
    "fields",
    "requires_field",
    "amends_field",
    "supersedes_field",
    "accepted_status",
    "superseded_status",
}
_HISTORY_KEYS = {"initial_status", "protect_records", "bootstrap_numbers", "transitions", "waivers"}
_HISTORY_WAIVER_KEYS = {"path", "from_status", "to_status", "reason"}
_INDEX_KEYS = {"version", "entries_key", "include_drafts", "fields"}
_INDEX_FIELD_KEYS = {"name", "source", "key"}
_DEFINES_KEYS = {"field", "anchor_prefix", "id_pattern"}


def _index_source(value: str) -> IndexSource:
    match value:
        case "metadata":
            return "metadata"
        case "path":
            return "path"
        case "inverse":
            return "inverse"
        case _:  # guarded by config validation
            raise AssertionError(f"unsupported index source: {value}")


def _metadata_title_mode(value: str) -> MetadataTitleMode:
    return "prefixed" if value == "prefixed" else "plain"


def _error(config_path: Path, code: str, message: str, *, hint: str | None = None) -> ProposalToolError:
    return ProposalToolError(Diagnostic(code=code, path=config_path.as_posix(), message=message, hint=hint))


def _reject_unknown(
    table: Mapping[str, object],
    allowed: set[str],
    *,
    config_path: Path,
    field: str,
) -> None:
    unknown = sorted(set(table) - allowed)
    if unknown:
        raise _error(
            config_path,
            "proposal.config.unknown-key",
            f"unknown `{field}` keys: " + ", ".join(unknown),
        )


def _mapping(
    value: object,
    *,
    config_path: Path,
    field: str,
    required: bool = True,
) -> Mapping[str, object]:
    if value is None and not required:
        return {}
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise _error(config_path, "proposal.config.type", f"`{field}` must be a TOML table")
    return value


def _string(
    table: Mapping[str, object],
    key: str,
    *,
    config_path: Path,
    field: str,
    default: str | None = None,
) -> str:
    value = table.get(key, default)
    if not isinstance(value, str) or not value:
        raise _error(
            config_path,
            "proposal.config.type",
            f"`{field}.{key}` must be a non-empty string",
        )
    return value


def _optional_string(table: Mapping[str, object], key: str, *, config_path: Path, field: str) -> str | None:
    value = table.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise _error(
            config_path,
            "proposal.config.type",
            f"`{field}.{key}` must be a non-empty string when present",
        )
    return value


def _integer(
    table: Mapping[str, object],
    key: str,
    *,
    config_path: Path,
    field: str,
    default: int | None = None,
) -> int:
    value = table.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise _error(
            config_path,
            "proposal.config.type",
            f"`{field}.{key}` must be an integer",
        )
    return value


def _boolean(
    table: Mapping[str, object],
    key: str,
    *,
    config_path: Path,
    field: str,
    default: bool,
) -> bool:
    value = table.get(key, default)
    if not isinstance(value, bool):
        raise _error(
            config_path,
            "proposal.config.type",
            f"`{field}.{key}` must be a boolean",
        )
    return value


def _string_list(value: object, *, config_path: Path, field: str, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise _error(
            config_path,
            "proposal.config.type",
            f"`{field}` must be an array of non-empty strings",
        )
    if not allow_empty and not value:
        raise _error(config_path, "proposal.config.empty", f"`{field}` must not be empty")
    return tuple(value)


def _repo_path(root: Path, raw: str, *, config_path: Path, field: str) -> Path:
    relative = Path(raw)
    if relative.is_absolute():
        raise _error(
            config_path,
            "proposal.config.path",
            f"`{field}` must be relative to the proposal repository",
        )
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root):
        raise _error(
            config_path,
            "proposal.config.path",
            f"`{field}` must stay inside the proposal repository",
        )
    return resolved


def _load_drafts(
    raw: object,
    *,
    root: Path,
    formal_schema: Path,
    config_path: Path,
) -> DraftPolicy | None:
    if raw is None:
        return None
    table = _mapping(raw, config_path=config_path, field="drafts")
    _reject_unknown(table, _DRAFT_KEYS, config_path=config_path, field="drafts")
    directory = _repo_path(
        root,
        _string(table, "directory", config_path=config_path, field="drafts"),
        config_path=config_path,
        field="drafts.directory",
    )
    raw_schema = _optional_string(table, "schema", config_path=config_path, field="drafts")
    schema_path = (
        formal_schema
        if raw_schema is None
        else _repo_path(root, raw_schema, config_path=config_path, field="drafts.schema")
    )
    if not directory.is_dir():
        raise _error(config_path, "proposal.config.missing-path", "`drafts.directory` is not a directory")
    if not schema_path.is_file():
        raise _error(config_path, "proposal.config.missing-path", "`drafts.schema` is not a file")
    return DraftPolicy(
        directory=directory,
        schema_path=schema_path,
        marker=_optional_string(table, "marker", config_path=config_path, field="drafts"),
        require_summary=_boolean(
            table,
            "require_summary",
            config_path=config_path,
            field="drafts",
            default=False,
        ),
        pre_proposal=_boolean(
            table,
            "pre_proposal",
            config_path=config_path,
            field="drafts",
            default=False,
        ),
    )


def _load_summary(raw: object, config_path: Path) -> SummaryPolicy | None:
    if raw is None:
        return None
    table = _mapping(raw, config_path=config_path, field="summary")
    _reject_unknown(table, _SUMMARY_KEYS, config_path=config_path, field="summary")
    minimum = _integer(table, "minimum_sentences", config_path=config_path, field="summary", default=2)
    maximum = _integer(table, "maximum_sentences", config_path=config_path, field="summary", default=4)
    if minimum < 1 or maximum < minimum:
        raise _error(
            config_path,
            "proposal.config.range",
            "`summary` sentence bounds must satisfy 1 <= minimum <= maximum",
        )
    return SummaryPolicy(
        prefix=_string(table, "prefix", config_path=config_path, field="summary"),
        minimum_sentences=minimum,
        maximum_sentences=maximum,
    )


def _load_graph(raw: object, config_path: Path) -> GraphPolicy | None:
    if raw is None:
        return None
    table = _mapping(raw, config_path=config_path, field="graph")
    _reject_unknown(table, _GRAPH_KEYS, config_path=config_path, field="graph")
    fields = _string_list(table.get("fields"), config_path=config_path, field="graph.fields", allow_empty=False)
    if len(fields) != len(set(fields)):
        raise _error(config_path, "proposal.config.duplicate", "`graph.fields` must be unique")

    roles = {
        name: _optional_string(table, name, config_path=config_path, field="graph")
        for name in ("requires_field", "amends_field", "supersedes_field")
    }
    for name, value in roles.items():
        if value is not None and value not in fields:
            raise _error(
                config_path,
                "proposal.config.graph-role",
                f"`graph.{name}` must name an entry in `graph.fields`",
            )

    return GraphPolicy(
        fields=fields,
        requires_field=roles["requires_field"],
        amends_field=roles["amends_field"],
        supersedes_field=roles["supersedes_field"],
        accepted_status=_string(
            table,
            "accepted_status",
            config_path=config_path,
            field="graph",
            default="Accepted",
        ),
        superseded_status=_string(
            table,
            "superseded_status",
            config_path=config_path,
            field="graph",
            default="Superseded",
        ),
    )


def _load_history(raw: object, config_path: Path) -> HistoryPolicy | None:
    if raw is None:
        return None
    table = _mapping(raw, config_path=config_path, field="history")
    _reject_unknown(table, _HISTORY_KEYS, config_path=config_path, field="history")
    raw_bootstrap = table.get("bootstrap_numbers", [])
    if not isinstance(raw_bootstrap, list) or not all(
        isinstance(item, int) and not isinstance(item, bool) and item >= 0 for item in raw_bootstrap
    ):
        raise _error(
            config_path,
            "proposal.config.type",
            "`history.bootstrap_numbers` must be an array of non-negative integers",
        )

    raw_transitions = _mapping(table.get("transitions"), config_path=config_path, field="history.transitions")
    transitions: dict[str, frozenset[str]] = {}
    for status, targets in raw_transitions.items():
        if not status:
            raise _error(
                config_path,
                "proposal.config.type",
                "`history.transitions` status names must not be empty",
            )
        transitions[status] = frozenset(
            _string_list(
                targets,
                config_path=config_path,
                field=f"history.transitions.{status}",
                allow_empty=False,
            )
        )

    raw_waivers = table.get("waivers", [])
    if not isinstance(raw_waivers, list):
        raise _error(config_path, "proposal.config.type", "`history.waivers` must be an array of tables")
    waivers: list[HistoryWaiver] = []
    for index, raw_waiver in enumerate(raw_waivers):
        waiver = _mapping(
            raw_waiver,
            config_path=config_path,
            field=f"history.waivers[{index}]",
        )
        _reject_unknown(
            waiver,
            _HISTORY_WAIVER_KEYS,
            config_path=config_path,
            field=f"history.waivers[{index}]",
        )
        waivers.append(
            HistoryWaiver(
                path=_string(
                    waiver,
                    "path",
                    config_path=config_path,
                    field=f"history.waivers[{index}]",
                ),
                from_status=_string(
                    waiver,
                    "from_status",
                    config_path=config_path,
                    field=f"history.waivers[{index}]",
                ),
                to_status=_string(
                    waiver,
                    "to_status",
                    config_path=config_path,
                    field=f"history.waivers[{index}]",
                ),
                reason=_string(
                    waiver,
                    "reason",
                    config_path=config_path,
                    field=f"history.waivers[{index}]",
                ),
            )
        )

    return HistoryPolicy(
        initial_status=_string(table, "initial_status", config_path=config_path, field="history"),
        protect_records=_boolean(
            table,
            "protect_records",
            config_path=config_path,
            field="history",
            default=True,
        ),
        bootstrap_numbers=frozenset(raw_bootstrap),
        transitions=transitions,
        waivers=tuple(waivers),
    )


def _load_index(raw: object, config_path: Path) -> IndexPolicy:
    table = _mapping(raw, config_path=config_path, field="index")
    _reject_unknown(table, _INDEX_KEYS, config_path=config_path, field="index")
    raw_fields = table.get("fields")
    if not isinstance(raw_fields, list) or not raw_fields:
        raise _error(
            config_path,
            "proposal.config.type",
            "`index.fields` must be a non-empty array of strings or tables",
        )

    fields: list[IndexField] = []
    for index, raw_field in enumerate(raw_fields):
        if isinstance(raw_field, str):
            if not raw_field:
                raise _error(
                    config_path,
                    "proposal.config.type",
                    f"`index.fields[{index}]` must be a non-empty string or table",
                )
            fields.append(IndexField(name=raw_field, source="metadata", key=raw_field))
            continue

        field = _mapping(raw_field, config_path=config_path, field=f"index.fields[{index}]")
        _reject_unknown(
            field,
            _INDEX_FIELD_KEYS,
            config_path=config_path,
            field=f"index.fields[{index}]",
        )
        source = _string(
            field,
            "source",
            config_path=config_path,
            field=f"index.fields[{index}]",
        )
        if source not in {"metadata", "path", "inverse"}:
            raise _error(
                config_path,
                "proposal.config.index-source",
                f"`index.fields[{index}].source` has unsupported value `{source}`",
            )
        key = _optional_string(field, "key", config_path=config_path, field=f"index.fields[{index}]")
        if source in {"metadata", "inverse"} and key is None:
            raise _error(
                config_path,
                "proposal.config.index-key",
                f"`index.fields[{index}].key` is required for source `{source}`",
            )
        if source == "path" and key is not None:
            raise _error(
                config_path,
                "proposal.config.index-key",
                f"`index.fields[{index}].key` is not allowed for source `{source}`",
            )
        fields.append(
            IndexField(
                name=_string(
                    field,
                    "name",
                    config_path=config_path,
                    field=f"index.fields[{index}]",
                ),
                source=_index_source(source),
                key=key,
            )
        )

    names = [field.name for field in fields]
    if len(names) != len(set(names)):
        raise _error(config_path, "proposal.config.duplicate", "`index.fields` names must be unique")

    version = _integer(table, "version", config_path=config_path, field="index", default=2)
    if version != 2:
        raise _error(
            config_path,
            "proposal.config.index-version",
            "`index.version` must be 2",
        )
    return IndexPolicy(
        version=version,
        entries_key=_string(table, "entries_key", config_path=config_path, field="index"),
        include_drafts=_boolean(
            table,
            "include_drafts",
            config_path=config_path,
            field="index",
            default=False,
        ),
        fields=tuple(fields),
    )


def _load_defines(raw: object, config_path: Path) -> DefinesPolicy | None:
    if raw is None:
        return None
    table = _mapping(raw, config_path=config_path, field="defines")
    _reject_unknown(table, _DEFINES_KEYS, config_path=config_path, field="defines")
    id_pattern = _string(
        table,
        "id_pattern",
        config_path=config_path,
        field="defines",
        default=r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*",
    )
    try:
        re.compile(id_pattern)
    except re.error as error:
        raise _error(
            config_path,
            "proposal.config.regex",
            f"invalid `defines.id_pattern`: {error}",
        ) from error
    return DefinesPolicy(
        field=_string(table, "field", config_path=config_path, field="defines", default="defines"),
        anchor_prefix=_string(
            table,
            "anchor_prefix",
            config_path=config_path,
            field="defines",
            default="term-",
        ),
        id_pattern=id_pattern,
    )


def load_config(path: str | Path = "proposal.toml") -> ProposalConfig:
    """Load a proposal repository's single executable policy file."""

    config_path = Path(path).resolve()
    try:
        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise _error(
            config_path,
            "proposal.config.missing",
            "proposal configuration does not exist",
            hint="Pass `--config PATH` or add proposal.toml at the repository root.",
        ) from error
    except OSError as error:
        raise _error(config_path, "proposal.config.read", f"failed to read proposal configuration: {error}") from error
    except tomllib.TOMLDecodeError as error:
        raise _error(config_path, "proposal.config.toml", f"invalid TOML: {error}") from error

    unknown_top = sorted(set(payload) - _TOP_LEVEL_KEYS)
    if unknown_top:
        raise _error(
            config_path,
            "proposal.config.unknown-key",
            "unknown top-level keys: " + ", ".join(unknown_top),
        )
    if payload.get("version") != 1:
        raise _error(config_path, "proposal.config.version", "`version` must be 1")

    root = config_path.parent.resolve()
    proposal = _mapping(payload.get("proposal"), config_path=config_path, field="proposal")
    unknown_proposal = sorted(set(proposal) - _PROPOSAL_KEYS)
    if unknown_proposal:
        raise _error(
            config_path,
            "proposal.config.unknown-key",
            "unknown `proposal` keys: " + ", ".join(unknown_proposal),
        )

    prefix = _string(proposal, "prefix", config_path=config_path, field="proposal")
    if re.fullmatch(r"[A-Z][A-Z0-9]*", prefix) is None:
        raise _error(
            config_path,
            "proposal.config.prefix",
            "`proposal.prefix` must contain uppercase ASCII letters and digits",
        )
    number_width = _integer(proposal, "number_width", config_path=config_path, field="proposal", default=4)
    if not 1 <= number_width <= 12:
        raise _error(config_path, "proposal.config.range", "`proposal.number_width` must be between 1 and 12")

    metadata_title = _string(
        proposal,
        "metadata_title",
        config_path=config_path,
        field="proposal",
        default="plain",
    )
    if metadata_title not in {"plain", "prefixed"}:
        raise _error(
            config_path,
            "proposal.config.title-mode",
            "`proposal.metadata_title` must be `plain` or `prefixed`",
        )

    slug_pattern = _string(
        proposal,
        "filename_slug_pattern",
        config_path=config_path,
        field="proposal",
        default=r"[a-z0-9]+(?:-[a-z0-9]+)*",
    )
    try:
        re.compile(slug_pattern)
    except re.error as error:
        raise _error(
            config_path,
            "proposal.config.regex",
            f"invalid `proposal.filename_slug_pattern`: {error}",
        ) from error

    documents_dir = _repo_path(
        root,
        _string(proposal, "documents_dir", config_path=config_path, field="proposal"),
        config_path=config_path,
        field="proposal.documents_dir",
    )
    schema_path = _repo_path(
        root,
        _string(proposal, "schema", config_path=config_path, field="proposal"),
        config_path=config_path,
        field="proposal.schema",
    )
    index_path = _repo_path(
        root,
        _string(proposal, "index", config_path=config_path, field="proposal"),
        config_path=config_path,
        field="proposal.index",
    )
    if not documents_dir.is_dir():
        raise _error(
            config_path,
            "proposal.config.missing-path",
            "`proposal.documents_dir` is not a directory",
        )
    if not schema_path.is_file():
        raise _error(config_path, "proposal.config.missing-path", "`proposal.schema` is not a file")
    drafts = _load_drafts(
        payload.get("drafts"),
        root=root,
        formal_schema=schema_path,
        config_path=config_path,
    )

    raw_templates = _mapping(
        payload.get("templates"),
        config_path=config_path,
        field="templates",
        required=False,
    )
    templates: dict[str, Path] = {}
    for proposal_type, raw_path in raw_templates.items():
        if not isinstance(raw_path, str) or not raw_path:
            raise _error(
                config_path,
                "proposal.config.type",
                f"`templates.{proposal_type}` must be a non-empty path string",
            )
        template = _repo_path(
            root,
            raw_path,
            config_path=config_path,
            field=f"templates.{proposal_type}",
        )
        if not template.is_file():
            raise _error(
                config_path,
                "proposal.config.missing-path",
                f"`templates.{proposal_type}` is not a file",
            )
        templates[proposal_type] = template

    summary = _load_summary(payload.get("summary"), config_path)
    graph = _load_graph(payload.get("graph"), config_path)
    history = _load_history(payload.get("history"), config_path)
    defines = _load_defines(payload.get("defines"), config_path)
    index = _load_index(payload.get("index"), config_path)

    return ProposalConfig(
        root=root,
        config_path=config_path,
        prefix=prefix,
        number_field=_string(proposal, "number_field", config_path=config_path, field="proposal"),
        title_field=_string(
            proposal,
            "title_field",
            config_path=config_path,
            field="proposal",
            default="title",
        ),
        type_field=_string(
            proposal,
            "type_field",
            config_path=config_path,
            field="proposal",
            default="type",
        ),
        status_field=_string(
            proposal,
            "status_field",
            config_path=config_path,
            field="proposal",
            default="status",
        ),
        documents_dir=documents_dir,
        drafts=drafts,
        schema_path=schema_path,
        index_path=index_path,
        number_width=number_width,
        metadata_title=_metadata_title_mode(metadata_title),
        filename_slug_pattern=slug_pattern,
        templates=templates,
        summary=summary,
        graph=graph,
        history=history,
        defines=defines,
        index=index,
    )
