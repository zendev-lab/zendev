"""Generic proposal, graph, draft, and Git-history validation."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, cast

from referencing.exceptions import Unresolvable

from zendev.core.diagnostics import ToolError
from zendev.core.markdown import markdown_session, scan_markdown
from zendev.core.source import source_session
from zendev.proposal.content import locate_diagnostics, validate_content
from zendev.proposal.graph import validate_graph
from zendev.proposal.history import validate_history
from zendev.proposal.model import (
    Diagnostic,
    ProposalConfig,
    ProposalDocument,
    RepositoryState,
    ValidationResult,
)
from zendev.proposal.references import edge_identifiers
from zendev.proposal.repository import (
    h2_headings,
    load_repository,
)
from zendev.proposal.schema import load_schema, schema_properties
from zendev.proposal.shape import formal_filename_pattern, template_headings


def _load_schema(config: ProposalConfig, schema_path: Path):
    return load_schema(config, schema_path)[0]


def _validate_schema(
    config: ProposalConfig,
    state: RepositoryState,
    diagnostics: list[Diagnostic],
) -> None:
    formal_validator = _load_schema(config, config.schema_path)
    drafts = config.drafts
    draft_validator = (
        formal_validator
        if drafts is None or drafts.schema_path == config.schema_path
        else _load_schema(config, drafts.schema_path)
    )
    for document in state.documents:
        validator = draft_validator if document.is_draft else formal_validator
        try:
            errors = sorted(
                validator.iter_errors(cast(Any, document.metadata)),
                key=lambda error: tuple(str(item) for item in error.absolute_path),
            )
        except (Unresolvable, RecursionError) as error:
            raise ToolError(
                Diagnostic(
                    code="proposal.schema.reference",
                    path=document.relative_path,
                    message=f"cannot resolve local schema: {error}",
                )
            ) from error
        for error in errors:
            location = "".join(f"[{item}]" if isinstance(item, int) else f".{item}" for item in error.absolute_path)
            diagnostics.append(
                Diagnostic(
                    code="proposal.frontmatter.schema",
                    path=document.relative_path,
                    message=f"frontmatter{location}: {error.message}",
                    line=document.field_lines.get(str(next(iter(error.absolute_path), "")), 1),
                )
            )


def _first_nonempty_line(markdown: str) -> str:
    return next((line.strip() for line in markdown.splitlines() if line.strip()), "")


def _validate_title(config: ProposalConfig, document: ProposalDocument, diagnostics: list[Diagnostic]) -> None:
    title = document.metadata.get(config.title_field)
    if not isinstance(title, str) or not title.strip() or title != title.strip() or len(title.splitlines()) != 1:
        diagnostics.append(
            Diagnostic(
                code="proposal.title.invalid",
                path=document.relative_path,
                message=f"`{config.title_field}` must be non-empty single-line text without surrounding whitespace",
            )
        )
    elif not document.is_draft and config.metadata_title == "prefixed":
        identifier = document.identifier(config)
        if identifier is not None and title.startswith(f"{identifier}:") and not title[len(identifier) + 1 :].strip():
            diagnostics.append(
                Diagnostic(
                    code="proposal.title.invalid",
                    path=document.relative_path,
                    message="metadata title must contain text after the proposal identifier",
                )
            )
    h1s = [heading for heading in scan_markdown(document.body).headings if heading.level == 1]
    if not h1s:
        diagnostics.append(
            Diagnostic(
                code="proposal.h1.missing",
                path=document.relative_path,
                message="proposal body requires an actual Markdown H1",
            )
        )
    if len(h1s) > 1:
        diagnostics.append(
            Diagnostic(
                code="proposal.h1.duplicate",
                path=document.relative_path,
                message=f"proposal body must contain exactly one H1; found {len(h1s)}",
            )
        )


def _validate_formal_shape(config: ProposalConfig, document: ProposalDocument, diagnostics: list[Diagnostic]) -> None:
    match = formal_filename_pattern(config).fullmatch(document.path.name)
    if match is None:
        diagnostics.append(
            Diagnostic(
                code="proposal.filename.invalid",
                path=document.relative_path,
                message=(f"filename must match `{config.prefix}-{'N' * config.number_width}-short-title.md`"),
            )
        )

    number = document.number(config)
    if number is None:
        diagnostics.append(
            Diagnostic(
                code="proposal.number.invalid",
                path=document.relative_path,
                message=f"`{config.number_field}` must be an integer",
            )
        )
        return
    identifier = config.format_identifier(number)
    if match is not None and int(match.group(1)) != number:
        diagnostics.append(
            Diagnostic(
                code="proposal.filename.number-mismatch",
                path=document.relative_path,
                message=(
                    f"filename identifies {config.format_identifier(int(match.group(1)))} "
                    f"but frontmatter identifies {identifier}"
                ),
            )
        )

    title = document.metadata.get(config.title_field)
    if not isinstance(title, str):
        diagnostics.append(
            Diagnostic(
                code="proposal.title.invalid",
                path=document.relative_path,
                message=f"`{config.title_field}` must be a string",
            )
        )
        return
    if config.metadata_title == "plain":
        if re.match(rf"^{re.escape(config.prefix)}-\d{{{config.number_width}}}:", title):
            diagnostics.append(
                Diagnostic(
                    code="proposal.title.contains-id",
                    path=document.relative_path,
                    message="metadata title must not contain the proposal identifier",
                )
            )
        expected_h1 = f"# {identifier}: {title}"
    else:
        expected_prefix = f"{identifier}:"
        if not title.startswith(expected_prefix):
            diagnostics.append(
                Diagnostic(
                    code="proposal.title.missing-id",
                    path=document.relative_path,
                    message=f"metadata title must start with `{expected_prefix}`",
                )
            )
        expected_h1 = f"# {title}"

    actual_h1 = _first_nonempty_line(document.body)
    if actual_h1 != expected_h1:
        diagnostics.append(
            Diagnostic(
                code="proposal.h1.invalid",
                path=document.relative_path,
                message=f"first body heading must be exactly `{expected_h1}`",
            )
        )


def _validate_frontmatter_draft(
    config: ProposalConfig, document: ProposalDocument, diagnostics: list[Diagnostic]
) -> None:
    drafts = config.drafts
    if drafts is None:
        raise AssertionError("draft documents require configured draft policy")
    if document.metadata.get(config.number_field) is not None:
        diagnostics.append(
            Diagnostic(
                code="proposal.draft.numbered",
                path=document.relative_path,
                message=f"drafts must not assign `{config.number_field}`",
            )
        )
    status = document.metadata.get(config.status_field)
    if drafts.pre_proposal and status is not None:
        diagnostics.append(
            Diagnostic(
                code="proposal.draft.status",
                path=document.relative_path,
                message=f"pre-proposals must not assign `{config.status_field}`",
            )
        )
    elif not drafts.pre_proposal and status != "Draft":
        diagnostics.append(
            Diagnostic(
                code="proposal.draft.status",
                path=document.relative_path,
                message=f"proposal drafts must use `{config.status_field}: Draft`",
            )
        )

    if re.match(rf"(?i)^{re.escape(config.prefix)}-\d{{{config.number_width}}}", document.path.name):
        diagnostics.append(
            Diagnostic(
                code="proposal.draft.filename-id",
                path=document.relative_path,
                message="draft filenames must not use a proposal number",
            )
        )

    title = document.metadata.get(config.title_field)
    expected_h1 = f"# {title}" if isinstance(title, str) else None
    actual_h1 = _first_nonempty_line(document.body)
    if expected_h1 is not None and actual_h1 != expected_h1:
        diagnostics.append(
            Diagnostic(
                code="proposal.draft.h1",
                path=document.relative_path,
                message=f"draft H1 must be exactly `{expected_h1}`",
            )
        )

    nonempty = [index for index, line in enumerate(document.body.splitlines()) if line.strip()]
    markers = scan_markdown(document.body, drafts.marker).marker_lines
    if drafts.marker is not None and (len(nonempty) < 2 or markers != (nonempty[1],)):
        diagnostics.append(
            Diagnostic(
                code="proposal.draft.marker",
                path=document.relative_path,
                message=f"draft H1 must be followed by exactly one standalone `{drafts.marker}` marker",
            )
        )

    if not drafts.pre_proposal:
        return
    status_pattern = re.compile(rf"(?im)^\s*(?:{re.escape(config.status_field)}\s*:|#+\s+status\b)")
    prose = "\n".join(text for _, text in scan_markdown(document.body).prose)
    if status_pattern.search(prose):
        diagnostics.append(
            Diagnostic(
                code="proposal.draft.declares-status",
                path=document.relative_path,
                message="pre-proposals must not declare a proposal status",
            )
        )
    identifier_pattern = re.compile(rf"\b{re.escape(config.prefix)}-\d{{{config.number_width}}}\b")
    identifiers = sorted(set(identifier_pattern.findall(prose)))
    if identifiers:
        diagnostics.append(
            Diagnostic(
                code="proposal.draft.concrete-id",
                path=document.relative_path,
                message="pre-proposals must not use concrete proposal IDs: " + ", ".join(identifiers),
            )
        )


def _validate_unique_numbers(config: ProposalConfig, state: RepositoryState, diagnostics: list[Diagnostic]) -> None:
    seen: dict[int, str] = {}
    for document in state.formal_documents:
        number = document.number(config)
        if number is None:
            continue
        other = seen.get(number)
        if other is not None:
            diagnostics.append(
                Diagnostic(
                    code="proposal.number.duplicate",
                    path=document.relative_path,
                    message=f"duplicate {config.format_identifier(number)} already used by {other}",
                )
            )
        else:
            seen[number] = document.relative_path


def _validate_summary(config: ProposalConfig, document: ProposalDocument, diagnostics: list[Diagnostic]) -> None:
    policy = config.summary
    if policy is None:
        return
    lines = document.body.splitlines()
    index = 0
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines) or not lines[index].startswith("# "):
        diagnostics.append(
            Diagnostic(
                code="proposal.summary.missing-h1",
                path=document.relative_path,
                message="proposal body must begin with an H1 heading",
            )
        )
        return
    index += 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    if (
        document.is_draft
        and config.drafts is not None
        and config.drafts.marker is not None
        and index < len(lines)
        and lines[index].strip() == config.drafts.marker
    ):
        index += 1
        while index < len(lines) and not lines[index].strip():
            index += 1
    if index >= len(lines) or not lines[index].startswith(">"):
        diagnostics.append(
            Diagnostic(
                code="proposal.summary.placement",
                path=document.relative_path,
                message="Executive Summary must be a blockquote immediately below the H1",
            )
        )
        return
    blockquote: list[str] = []
    while index < len(lines) and lines[index].startswith(">"):
        blockquote.append(lines[index].removeprefix(">").strip())
        index += 1
    summary = " ".join(blockquote)
    if not summary.startswith(policy.prefix):
        diagnostics.append(
            Diagnostic(
                code="proposal.summary.prefix",
                path=document.relative_path,
                message=f"Executive Summary must start with `{policy.prefix}`",
            )
        )
        return
    body = summary.removeprefix(policy.prefix).strip()
    if not body.endswith((".", "!", "?")):
        diagnostics.append(
            Diagnostic(
                code="proposal.summary.punctuation",
                path=document.relative_path,
                message="Executive Summary must end with sentence punctuation",
            )
        )
        return
    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", body) if sentence.strip()]
    if not policy.minimum_sentences <= len(sentences) <= policy.maximum_sentences:
        diagnostics.append(
            Diagnostic(
                code="proposal.summary.sentence-count",
                path=document.relative_path,
                message=(
                    "Executive Summary must contain "
                    f"{policy.minimum_sentences}-{policy.maximum_sentences} sentences; "
                    f"found {len(sentences)}"
                ),
            )
        )


def _validate_sections(
    config: ProposalConfig,
    document: ProposalDocument,
    templates: dict[str, tuple[str, ...]],
    diagnostics: list[Diagnostic],
) -> None:
    proposal_type = document.metadata.get(config.type_field)
    if not isinstance(proposal_type, str) or proposal_type not in templates:
        return
    headings = h2_headings(document.body)
    found = set(headings)
    repeated = [heading for heading in templates[proposal_type] if headings.count(heading) > 1]
    if repeated:
        diagnostics.append(
            Diagnostic(
                code="proposal.sections.duplicate",
                path=document.relative_path,
                message="duplicate required sections: " + ", ".join(repeated),
            )
        )
    missing = [heading for heading in templates[proposal_type] if heading not in found]
    if missing:
        diagnostics.append(
            Diagnostic(
                code="proposal.sections.missing",
                path=document.relative_path,
                message="missing required sections: " + ", ".join(missing),
            )
        )


def _defined_ids(document: ProposalDocument, field: str) -> list[str]:
    values = document.metadata.get(field)
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, str)]


def _superseded_closure(
    config: ProposalConfig,
    start: str,
    documents_by_id: dict[str, ProposalDocument],
) -> set[str]:
    policy = config.graph
    if policy is None or policy.supersedes_field is None:
        return set()
    seen: set[str] = set()
    pending = [start]
    while pending:
        identifier = pending.pop()
        document = documents_by_id.get(identifier)
        if document is None:
            continue
        for target in edge_identifiers(config, document, policy.supersedes_field):
            if target not in seen:
                seen.add(target)
                pending.append(target)
    return seen


def _validate_defines(
    config: ProposalConfig,
    state: RepositoryState,
    diagnostics: list[Diagnostic],
) -> None:
    policy = config.defines
    if policy is None:
        return

    id_re = re.compile(policy.id_pattern)
    owners: dict[str, list[ProposalDocument]] = defaultdict(list)

    for document in state.documents:
        raw = document.metadata.get(policy.field)
        if policy.field in document.metadata and not isinstance(raw, list):
            diagnostics.append(
                Diagnostic(
                    code="proposal.defines.invalid-field",
                    path=document.relative_path,
                    message=f"`{policy.field}` must be an array of concept IDs",
                )
            )
            continue
        values = raw if isinstance(raw, list) else []
        declared = _defined_ids(document, policy.field)
        invalid = [value for value in values if not isinstance(value, str) or id_re.fullmatch(value) is None]
        if invalid:
            diagnostics.append(
                Diagnostic(
                    code="proposal.defines.invalid-id",
                    path=document.relative_path,
                    message=f"`{policy.field}` entries must be strings matching `{policy.id_pattern}`: {invalid!r}",
                )
            )
        declared_set = set(declared)
        if len(declared) != len(declared_set):
            diagnostics.append(
                Diagnostic(
                    code="proposal.defines.duplicate-id",
                    path=document.relative_path,
                    message=f"`{policy.field}` must not contain duplicate concept IDs",
                )
            )
        anchors: list[str] = []
        for anchor_fact in scan_markdown(document.body).anchors:
            if not anchor_fact.identifier.startswith(policy.anchor_prefix):
                continue
            concept = anchor_fact.identifier.removeprefix(policy.anchor_prefix)
            if id_re.fullmatch(concept) is None or not anchor_fact.canonical:
                diagnostics.append(
                    Diagnostic(
                        code="proposal.defines.invalid-anchor",
                        path=document.relative_path,
                        message=(
                            f"definition anchor `{anchor_fact.identifier}` "
                            "must use a valid ID and canonical empty <a> tag"
                        ),
                    )
                )
            anchors.append(concept)
        counts = Counter(anchors)
        for concept, count in counts.items():
            if count > 1:
                diagnostics.append(
                    Diagnostic(
                        code="proposal.defines.duplicate-anchor",
                        path=document.relative_path,
                        message=f"definition anchor `{policy.anchor_prefix}{concept}` occurs {count} times",
                    )
                )
        for identifier in sorted(declared_set):
            anchor = f'<a id="{policy.anchor_prefix}{identifier}"></a>'
            count = counts[identifier]
            if count != 1:
                diagnostics.append(
                    Diagnostic(
                        code="proposal.defines.missing-anchor",
                        path=document.relative_path,
                        message=(
                            f"`{policy.field}` entry `{identifier}` requires exactly one "
                            f"`{anchor}` anchor; found {count}"
                        ),
                    )
                )
            owners[identifier].append(document)
        for identifier in sorted(set(anchors) - declared_set):
            diagnostics.append(
                Diagnostic(
                    code="proposal.defines.undeclared-anchor",
                    path=document.relative_path,
                    message=(
                        f"definition anchor `{policy.anchor_prefix}{identifier}` must be declared in `{policy.field}`"
                    ),
                )
            )

    documents_by_id = {
        identifier: document
        for document in state.formal_documents
        if (identifier := document.identifier(config)) is not None
    }
    superseded_status = config.graph.superseded_status if config.graph is not None else "Superseded"
    for identifier, defining_documents in sorted(owners.items()):
        if len(defining_documents) == 1:
            continue
        current = [
            document
            for document in defining_documents
            if document.metadata.get(config.status_field) != superseded_status
        ]
        if len(current) == 1 and (current_id := current[0].identifier(config)) is not None:
            superseded = _superseded_closure(config, current_id, documents_by_id)
            previous = [document for document in defining_documents if document is not current[0]]
            if all(
                document.metadata.get(config.status_field) == superseded_status
                and (previous_id := document.identifier(config)) is not None
                and previous_id in superseded
                for document in previous
            ):
                continue
        locations = ", ".join(document.relative_path for document in defining_documents)
        diagnostics.append(
            Diagnostic(
                code="proposal.defines.duplicate-owner",
                path=current[0].relative_path if len(current) == 1 else defining_documents[0].relative_path,
                message=f"`{identifier}` is defined by {locations}",
            )
        )


def validate_repository(config: ProposalConfig, *, base_ref: str | None = None) -> ValidationResult:
    """Validate repository mechanics while leaving project terminology local."""

    with markdown_session(), source_session():
        return validate_state(config, load_repository(config), base_ref=base_ref)


def validate_state(config: ProposalConfig, state: RepositoryState, *, base_ref: str | None = None) -> ValidationResult:
    """Validate a parsed snapshot, including a proposed repair before any writes."""
    diagnostics = list(state.diagnostics)
    _validate_schema(config, state, diagnostics)
    properties = schema_properties(config, config.schema_path)
    present = {key for document in state.formal_documents for key in document.metadata}
    for field in config.index.fields:
        if field.source == "metadata" and field.key not in properties and field.key not in present:
            diagnostics.append(
                Diagnostic(
                    code="proposal.index.unknown-field",
                    path=config.relative_path(config.config_path),
                    message=(
                        f"index metadata field `{field.key}` is neither declared in the schema nor present in proposals"
                    ),
                )
            )
    for name, mapping in config.fix.aliases.items():
        enum = properties.get(name, {}).get("enum")
        if name not in properties or (enum is not None and any(value not in enum for value in mapping.values())):
            raise ToolError(
                Diagnostic(
                    code="proposal.config.alias",
                    path=config.relative_path(config.config_path),
                    message=f"aliases for `{name}` must target declared schema values",
                )
            )
    status_enum = properties.get(config.status_field, {}).get("enum")
    if (
        config.history
        and status_enum is not None
        and any(name not in status_enum for name in config.history.transitions)
    ):
        raise ToolError(
            Diagnostic(
                code="proposal.config.history",
                path=config.relative_path(config.config_path),
                message="history statuses must belong to the schema enum",
            )
        )
    _validate_unique_numbers(config, state, diagnostics)
    templates = template_headings(config)

    for document in state.documents:
        _validate_title(config, document, diagnostics)
        if document.is_draft:
            _validate_frontmatter_draft(config, document, diagnostics)
            if config.drafts is not None and config.drafts.require_summary:
                _validate_summary(config, document, diagnostics)
        else:
            _validate_formal_shape(config, document, diagnostics)
            _validate_summary(config, document, diagnostics)
        _validate_sections(config, document, templates, diagnostics)
        validate_content(config, document, templates, diagnostics, {doc.path: doc.body for doc in state.documents})

    validate_graph(config, state, diagnostics)
    _validate_defines(config, state, diagnostics)
    if base_ref is not None:
        validate_history(config, state, base_ref, diagnostics)

    diagnostics = locate_diagnostics(config, state, diagnostics)
    ordered = tuple(sorted(diagnostics, key=Diagnostic.sort_key))
    return ValidationResult(state=state, diagnostics=ordered)
