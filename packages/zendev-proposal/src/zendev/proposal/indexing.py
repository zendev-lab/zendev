"""Deterministic proposal-index construction and drift checks."""

from __future__ import annotations

import json

from zendev.core.diagnostics import ToolError
from zendev.core.source import read_text
from zendev.proposal.graph import validate_graph
from zendev.proposal.model import (
    Diagnostic,
    ProposalConfig,
    ProposalDocument,
    RepositoryState,
)
from zendev.proposal.references import edge_numbers, reference_number


def _document_sort_key(config: ProposalConfig, document: ProposalDocument) -> tuple[int, int, str]:
    number = document.number(config)
    if number is not None:
        return (0, number, document.relative_path)
    return (1, 0, document.relative_path)


def build_index(config: ProposalConfig, state: RepositoryState) -> dict[str, object]:
    """Build the configured machine-readable index without writing it."""

    diagnostics = list(state.diagnostics)
    documents = state.formal_documents
    seen: set[int] = set()
    for document in documents:
        number = document.number(config)
        if number is None or reference_number(config, number) is None or number in seen:
            diagnostics.append(
                Diagnostic(
                    code="proposal.index.identity",
                    path=document.relative_path,
                    message="indexed proposals must have unique valid integer numbers",
                )
            )
        else:
            seen.add(number)
    validate_graph(config, state, diagnostics)
    if diagnostics:
        raise ToolError(sorted(diagnostics, key=Diagnostic.sort_key)[0])

    inverse_relations = {
        field.key for field in config.index.fields if field.source == "inverse" and field.key is not None
    }
    numbers = {number: document for document in documents if (number := document.number(config)) is not None}
    inverse: dict[int, dict[str, set[int]]] = {
        number: {relation: set() for relation in inverse_relations} for number in numbers
    }
    for document in documents:
        source = document.number(config)
        if source is None:
            continue
        for relation in inverse_relations:
            for target in edge_numbers(config, document, relation):
                if target in inverse:
                    inverse[target][relation].add(source)

    entries: list[dict[str, object]] = []
    for document in sorted(documents, key=lambda item: _document_sort_key(config, item)):
        number = document.number(config)
        entry: dict[str, object] = {}
        for field in config.index.fields:
            if field.source == "metadata":
                assert field.key is not None
                value: object = document.metadata.get(field.key)
                if config.graph is not None and field.key in config.graph.fields:
                    value = list(edge_numbers(config, document, field.key))
            elif field.source == "path":
                value = document.relative_path
            else:
                assert field.key is not None
                values = set() if number is None else inverse.get(number, {}).get(field.key, set())
                value = sorted(values)
            entry[field.name] = value
        entries.append(entry)

    return {"version": config.index.version, config.index.entries_key: entries}


def expected_index_text(config: ProposalConfig, state: RepositoryState) -> str:
    return json.dumps(build_index(config, state), indent=2, ensure_ascii=False) + "\n"


DEFAULT_FIX_INVOCATION = "zendev proposal check --fix"


def check_index(
    config: ProposalConfig,
    state: RepositoryState,
    *,
    fix_invocation: str = DEFAULT_FIX_INVOCATION,
) -> Diagnostic | None:
    expected = expected_index_text(config, state)
    try:
        current = read_text(config.index_path)
    except FileNotFoundError:
        current = None
    except (OSError, UnicodeError) as error:
        raise ToolError(
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
        hint=f"Run `{fix_invocation}` and commit the result.",
    )
