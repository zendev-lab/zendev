"""Deterministic proposal-index construction and drift checks."""

from __future__ import annotations

import json
import re

from zendev.proposal.model import (
    Diagnostic,
    ProposalConfig,
    ProposalDocument,
    ProposalToolError,
    RepositoryState,
)


def normalize_reference(config: ProposalConfig, value: object) -> str | None:
    """Normalize integer or canonical string edges to a display identifier."""

    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 10**config.number_width:
        return config.format_identifier(value)
    if not isinstance(value, str):
        return None
    pattern = rf"^{re.escape(config.prefix)}-(\d{{{config.number_width}}})$"
    return value if re.fullmatch(pattern, value) is not None else None


def edge_identifiers(config: ProposalConfig, document: ProposalDocument, field: str) -> tuple[str, ...]:
    raw = document.metadata.get(field)
    if not isinstance(raw, list):
        return ()
    return tuple(identifier for value in raw if (identifier := normalize_reference(config, value)) is not None)


def _identifier_sort_key(config: ProposalConfig, identifier: str) -> tuple[int, int, str]:
    prefix = f"{config.prefix}-"
    suffix = identifier.removeprefix(prefix)
    if identifier.startswith(prefix) and suffix.isdigit():
        return (0, int(suffix), identifier)
    return (1, 0, identifier)


def _document_sort_key(config: ProposalConfig, document: ProposalDocument) -> tuple[int, int, str]:
    number = document.number(config)
    if number is not None:
        return (0, number, document.relative_path)
    return (1, 0, document.relative_path)


def build_index(config: ProposalConfig, state: RepositoryState) -> dict[str, object]:
    """Build the configured machine-readable index without writing it."""

    documents = state.documents if config.index.include_drafts else state.formal_documents
    inverse_relations = {
        field.key for field in config.index.fields if field.source == "inverse" and field.key is not None
    }
    identifiers = {
        identifier: document for document in documents if (identifier := document.identifier(config)) is not None
    }
    inverse: dict[str, dict[str, set[str]]] = {
        identifier: {relation: set() for relation in inverse_relations} for identifier in identifiers
    }
    for document in documents:
        source = document.identifier(config)
        if source is None:
            continue
        for relation in inverse_relations:
            for target in edge_identifiers(config, document, relation):
                if target in inverse:
                    inverse[target][relation].add(source)

    entries: list[dict[str, object]] = []
    for document in sorted(documents, key=lambda item: _document_sort_key(config, item)):
        identifier = document.identifier(config)
        entry: dict[str, object] = {}
        for field in config.index.fields:
            if field.source == "metadata":
                assert field.key is not None
                value: object = document.metadata.get(field.key)
            elif field.source == "identifier":
                value = identifier
            elif field.source == "path":
                value = document.relative_path
            else:
                assert field.key is not None
                values = set() if identifier is None else inverse.get(identifier, {}).get(field.key, set())
                value = sorted(values, key=lambda item: _identifier_sort_key(config, item))
            entry[field.name] = value
        entries.append(entry)

    return {"version": config.index.version, config.index.entries_key: entries}


def expected_index_text(config: ProposalConfig, state: RepositoryState) -> str:
    return json.dumps(build_index(config, state), indent=2, ensure_ascii=False) + "\n"


def check_index(config: ProposalConfig, state: RepositoryState) -> Diagnostic | None:
    expected = expected_index_text(config, state)
    try:
        current = config.index_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        current = None
    except (OSError, UnicodeError) as error:
        raise ProposalToolError(
            Diagnostic(
                code="proposal.index.read",
                path=config.relative_path(config.index_path),
                message=f"failed to read proposal index: {error}",
            )
        ) from error
    if current == expected:
        return None
    return Diagnostic(
        code="proposal.index.drift",
        path=config.relative_path(config.index_path),
        message="committed proposal index is missing or out of date",
        hint="Run `zendev-proposal index --write` and commit the result.",
    )


def write_index(config: ProposalConfig, state: RepositoryState) -> bool:
    """Write the expected index and return whether the file changed."""

    expected = expected_index_text(config, state)
    try:
        current = config.index_path.read_text(encoding="utf-8") if config.index_path.exists() else None
        if current == expected:
            return False
        config.index_path.parent.mkdir(parents=True, exist_ok=True)
        config.index_path.write_text(expected, encoding="utf-8", newline="\n")
    except (OSError, UnicodeError) as error:
        raise ProposalToolError(
            Diagnostic(
                code="proposal.index.write",
                path=config.relative_path(config.index_path),
                message=f"failed to write proposal index: {error}",
            )
        ) from error
    return True
