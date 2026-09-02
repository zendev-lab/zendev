"""Generic proposal, graph, draft, and Git-history validation."""

from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, cast

from jsonschema import FormatChecker
from jsonschema.exceptions import SchemaError
from jsonschema.validators import validator_for

from zendev.proposal.indexing import edge_identifiers, normalize_reference
from zendev.proposal.model import (
    Diagnostic,
    ProposalConfig,
    ProposalDocument,
    ProposalToolError,
    RepositoryState,
    ValidationResult,
)
from zendev.proposal.repository import (
    extract_frontmatter,
    h2_headings,
    load_repository,
    parse_frontmatter,
)


def _load_schema(config: ProposalConfig, schema_path: Path):
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ProposalToolError(
            Diagnostic(
                code="proposal.schema.read",
                path=config.relative_path(schema_path),
                message=f"failed to load frontmatter schema: {error}",
            )
        ) from error
    if not isinstance(schema, dict):
        raise ProposalToolError(
            Diagnostic(
                code="proposal.schema.type",
                path=config.relative_path(schema_path),
                message="frontmatter schema must be a JSON object",
            )
        )
    validator_class = validator_for(schema)
    try:
        validator_class.check_schema(schema)
    except SchemaError as error:
        raise ProposalToolError(
            Diagnostic(
                code="proposal.schema.invalid",
                path=config.relative_path(schema_path),
                message=f"invalid frontmatter schema: {error.message}",
            )
        ) from error
    return validator_class(schema, format_checker=FormatChecker())


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
        errors = sorted(
            validator.iter_errors(cast(Any, document.metadata)),
            key=lambda error: tuple(str(item) for item in error.absolute_path),
        )
        for error in errors:
            location = "".join(f"[{item}]" if isinstance(item, int) else f".{item}" for item in error.absolute_path)
            diagnostics.append(
                Diagnostic(
                    code="proposal.frontmatter.schema",
                    path=document.relative_path,
                    message=f"frontmatter{location}: {error.message}",
                )
            )


def _formal_filename_pattern(config: ProposalConfig) -> re.Pattern[str]:
    return re.compile(
        rf"^{re.escape(config.prefix)}-(\d{{{config.number_width}}})-"
        rf"(?:{config.filename_slug_pattern})\.md$"
    )


def _first_nonempty_line(markdown: str) -> str:
    return next((line.strip() for line in markdown.splitlines() if line.strip()), "")


def _validate_formal_shape(config: ProposalConfig, document: ProposalDocument, diagnostics: list[Diagnostic]) -> None:
    match = _formal_filename_pattern(config).fullmatch(document.path.name)
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

    nonempty = [line.strip() for line in document.body.splitlines() if line.strip()]
    if drafts.marker is not None and (len(nonempty) < 2 or nonempty[1] != drafts.marker):
        diagnostics.append(
            Diagnostic(
                code="proposal.draft.marker",
                path=document.relative_path,
                message=f"draft H1 must be followed by `{drafts.marker}`",
            )
        )

    if not drafts.pre_proposal:
        return
    status_pattern = re.compile(rf"(?im)^\s*(?:{re.escape(config.status_field)}\s*:|#+\s+status\b)")
    if status_pattern.search(document.body):
        diagnostics.append(
            Diagnostic(
                code="proposal.draft.declares-status",
                path=document.relative_path,
                message="pre-proposals must not declare a proposal status",
            )
        )
    identifier_pattern = re.compile(rf"\b{re.escape(config.prefix)}-\d{{{config.number_width}}}\b")
    identifiers = sorted(set(identifier_pattern.findall(document.body)))
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


def _template_headings(config: ProposalConfig) -> dict[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}
    for proposal_type, path in config.templates.items():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise ProposalToolError(
                Diagnostic(
                    code="proposal.template.read",
                    path=config.relative_path(path),
                    message=f"failed to read proposal template: {error}",
                )
            ) from error
        headings = h2_headings(text)
        if len(headings) != len(set(headings)):
            raise ProposalToolError(
                Diagnostic(
                    code="proposal.template.duplicate-heading",
                    path=config.relative_path(path),
                    message="proposal template H2 headings must be unique",
                )
            )
        result[proposal_type] = headings
    return result


def _validate_sections(
    config: ProposalConfig,
    document: ProposalDocument,
    templates: dict[str, tuple[str, ...]],
    diagnostics: list[Diagnostic],
) -> None:
    proposal_type = document.metadata.get(config.type_field)
    if not isinstance(proposal_type, str) or proposal_type not in templates:
        return
    found = set(h2_headings(document.body))
    missing = [heading for heading in templates[proposal_type] if heading not in found]
    if missing:
        diagnostics.append(
            Diagnostic(
                code="proposal.sections.missing",
                path=document.relative_path,
                message="missing required sections: " + ", ".join(missing),
            )
        )


def _validate_graph(config: ProposalConfig, state: RepositoryState, diagnostics: list[Diagnostic]) -> None:
    policy = config.graph
    if policy is None:
        return
    by_id = {
        identifier: document
        for document in state.formal_documents
        if (identifier := document.identifier(config)) is not None
    }
    for document in state.formal_documents:
        source = document.identifier(config)
        if source is None:
            continue
        for field in policy.fields:
            raw = document.metadata.get(field)
            if not isinstance(raw, list):
                diagnostics.append(
                    Diagnostic(
                        code="proposal.graph.invalid-field",
                        path=document.relative_path,
                        message=f"`{field}` must be an array of proposal references",
                    )
                )
                continue
            normalized: list[str] = []
            for index, value in enumerate(raw):
                identifier = normalize_reference(config, value)
                if identifier is None:
                    diagnostics.append(
                        Diagnostic(
                            code="proposal.graph.invalid-edge",
                            path=document.relative_path,
                            message=f"`{field}[{index}]` is not a canonical proposal reference",
                        )
                    )
                else:
                    normalized.append(identifier)
            if len(normalized) != len(set(normalized)):
                diagnostics.append(
                    Diagnostic(
                        code="proposal.graph.duplicate-edge",
                        path=document.relative_path,
                        message=f"`{field}` contains duplicate edges",
                    )
                )
            for target in normalized:
                if target == source:
                    diagnostics.append(
                        Diagnostic(
                            code="proposal.graph.self-edge",
                            path=document.relative_path,
                            message=f"`{field}` must not contain a self-edge",
                        )
                    )
                elif target not in by_id:
                    diagnostics.append(
                        Diagnostic(
                            code="proposal.graph.missing-target",
                            path=document.relative_path,
                            message=f"`{field}` references missing {target}",
                        )
                    )

    requires_field = policy.requires_field
    if requires_field is not None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(identifier: str, path: list[str]) -> None:
            if identifier in visiting:
                cycle_start = path.index(identifier)
                cycle = [*path[cycle_start:], identifier]
                diagnostics.append(
                    Diagnostic(
                        code="proposal.graph.requires-cycle",
                        message="requires graph contains a cycle: " + " -> ".join(cycle),
                    )
                )
                return
            if identifier in visited:
                return
            visiting.add(identifier)
            path.append(identifier)
            for target in edge_identifiers(config, by_id[identifier], requires_field):
                if target in by_id:
                    visit(target, path)
            path.pop()
            visiting.remove(identifier)
            visited.add(identifier)

        for identifier in sorted(by_id):
            visit(identifier, [])

        for document in state.formal_documents:
            if document.metadata.get(config.status_field) != policy.accepted_status:
                continue
            pending = list(edge_identifiers(config, document, requires_field))
            seen: set[str] = set()
            while pending:
                target = pending.pop()
                if target in seen or target not in by_id:
                    continue
                seen.add(target)
                target_document = by_id[target]
                if target_document.metadata.get(config.status_field) != policy.accepted_status:
                    diagnostics.append(
                        Diagnostic(
                            code="proposal.graph.accepted-requires-unaccepted",
                            path=document.relative_path,
                            message=f"accepted proposal transitively requires non-accepted {target}",
                        )
                    )
                pending.extend(edge_identifiers(config, target_document, requires_field))

    if policy.amends_field is not None:
        for document in state.formal_documents:
            for target in edge_identifiers(config, document, policy.amends_field):
                if target in by_id and (by_id[target].metadata.get(config.status_field) != policy.accepted_status):
                    diagnostics.append(
                        Diagnostic(
                            code="proposal.graph.amends-unaccepted",
                            path=document.relative_path,
                            message=f"amendment target {target} must remain accepted",
                        )
                    )

    if policy.supersedes_field is None:
        return
    accepted_superseders: dict[str, list[str]] = defaultdict(list)
    for document in state.formal_documents:
        source = document.identifier(config)
        status = document.metadata.get(config.status_field)
        if source is None:
            continue
        for target in edge_identifiers(config, document, policy.supersedes_field):
            if target not in by_id:
                continue
            target_status = by_id[target].metadata.get(config.status_field)
            if status in {policy.accepted_status, policy.superseded_status}:
                if target_status != policy.superseded_status:
                    diagnostics.append(
                        Diagnostic(
                            code="proposal.graph.supersession-incomplete",
                            path=document.relative_path,
                            message=(f"accepted supersession requires {target} to be superseded in the same tree"),
                        )
                    )
            elif target_status != policy.accepted_status:
                diagnostics.append(
                    Diagnostic(
                        code="proposal.graph.supersedes-unaccepted",
                        path=document.relative_path,
                        message=f"proposed supersession target {target} must remain accepted",
                    )
                )
            if status == policy.accepted_status:
                accepted_superseders[target].append(source)

    for identifier, document in by_id.items():
        if document.metadata.get(config.status_field) != policy.superseded_status:
            continue
        superseders = accepted_superseders.get(identifier, [])
        if len(superseders) != 1:
            diagnostics.append(
                Diagnostic(
                    code="proposal.graph.superseded-owner",
                    path=document.relative_path,
                    message=(
                        "superseded proposal must have exactly one accepted forward "
                        f"superseder; found {len(superseders)}"
                    ),
                )
            )


def _git(config: ProposalConfig, *arguments: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *arguments],
            cwd=config.root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        raise ProposalToolError(
            Diagnostic(
                code="proposal.history.git",
                message=f"failed to invoke Git: {error}",
            )
        ) from error


def _metadata_at_ref(config: ProposalConfig, ref: str, relative_path: str) -> dict[str, object]:
    result = _git(config, "show", f"{ref}:{relative_path}")
    if result.returncode != 0:
        raise ProposalToolError(
            Diagnostic(
                code="proposal.history.git",
                path=relative_path,
                message=f"failed to read proposal at the Git base: {result.stderr.strip()}",
            )
        )
    try:
        raw, _ = extract_frontmatter(result.stdout, relative_path)
        return parse_frontmatter(raw, relative_path)
    except ValueError as error:
        raise ProposalToolError(
            Diagnostic(
                code="proposal.history.frontmatter",
                path=relative_path,
                message=f"invalid frontmatter at the Git base: {error}",
            )
        ) from error


def _waived(config: ProposalConfig, path: str, previous: str, current: str) -> bool:
    policy = config.history
    assert policy is not None
    return any(
        waiver.path == path and waiver.from_status == previous and waiver.to_status == current
        for waiver in policy.waivers
    )


def _validate_history(
    config: ProposalConfig,
    state: RepositoryState,
    base_ref: str,
    diagnostics: list[Diagnostic],
) -> None:
    policy = config.history
    if policy is None:
        raise ProposalToolError(
            Diagnostic(
                code="proposal.history.disabled",
                path=config.relative_path(config.config_path),
                message="`--base-ref` requires a `[history]` policy",
            )
        )
    resolved = _git(config, "rev-parse", "--verify", "--end-of-options", f"{base_ref}^{{commit}}")
    if resolved.returncode != 0:
        raise ProposalToolError(
            Diagnostic(
                code="proposal.history.base-ref",
                message=f"Git base ref does not exist: {base_ref}",
                hint="Fetch the base ref or pass an exact locally available ref.",
            )
        )
    base_commit = resolved.stdout.strip()

    documents_relative = config.relative_path(config.documents_dir)
    tree = _git(config, "ls-tree", "-r", "--name-only", base_commit, "--", documents_relative)
    if tree.returncode != 0:
        raise ProposalToolError(
            Diagnostic(
                code="proposal.history.git",
                message=f"failed to read proposal tree at {base_ref}: {tree.stderr.strip()}",
            )
        )
    pattern = _formal_filename_pattern(config)
    old_paths = {line for line in tree.stdout.splitlines() if pattern.fullmatch(Path(line).name) is not None}
    current_by_path = {document.relative_path: document for document in state.formal_documents}
    if policy.protect_records:
        for deleted in sorted(old_paths - set(current_by_path)):
            diagnostics.append(
                Diagnostic(
                    code="proposal.history.deleted",
                    path=deleted,
                    message="formal proposal records must not be deleted",
                )
            )

    previous_by_path = {path: _metadata_at_ref(config, base_commit, path) for path in old_paths}
    old_number_paths: dict[int, str] = {}
    for path, metadata in previous_by_path.items():
        number = metadata.get(config.number_field)
        if isinstance(number, int) and not isinstance(number, bool):
            old_number_paths[number] = path

    for document in state.formal_documents:
        number = document.number(config)
        if number is not None:
            previous_path = old_number_paths.get(number)
            if previous_path is not None and previous_path != document.relative_path:
                diagnostics.append(
                    Diagnostic(
                        code="proposal.history.number-reused",
                        path=document.relative_path,
                        message=(
                            f"{config.format_identifier(number)} was already assigned to {previous_path} at {base_ref}"
                        ),
                    )
                )

        previous = previous_by_path.get(document.relative_path)
        current_status = document.metadata.get(config.status_field)
        if previous is None:
            if number not in policy.bootstrap_numbers and current_status != policy.initial_status:
                diagnostics.append(
                    Diagnostic(
                        code="proposal.history.initial-status",
                        path=document.relative_path,
                        message=(f"new proposals must begin in `{policy.initial_status}`; found `{current_status}`"),
                    )
                )
            continue
        previous_status = previous.get(config.status_field)
        if not isinstance(previous_status, str) or not isinstance(current_status, str):
            continue
        allowed = policy.transitions.get(previous_status, frozenset())
        if current_status not in allowed and not _waived(
            config, document.relative_path, previous_status, current_status
        ):
            diagnostics.append(
                Diagnostic(
                    code="proposal.history.invalid-transition",
                    path=document.relative_path,
                    message=f"invalid status transition `{previous_status}` -> `{current_status}`",
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

    anchor_re = re.compile(rf'<a id="{re.escape(policy.anchor_prefix)}({policy.id_pattern})"></a>')
    owners: dict[str, list[ProposalDocument]] = defaultdict(list)

    for document in state.documents:
        raw = document.metadata.get(policy.field)
        if raw is not None and not isinstance(raw, list):
            diagnostics.append(
                Diagnostic(
                    code="proposal.defines.invalid-field",
                    path=document.relative_path,
                    message=f"`{policy.field}` must be an array of concept IDs",
                )
            )
            continue
        declared = _defined_ids(document, policy.field)
        declared_set = set(declared)
        anchors = anchor_re.findall(document.body)
        for identifier in declared:
            anchor = f'<a id="{policy.anchor_prefix}{identifier}"></a>'
            count = document.body.count(anchor)
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

    state = load_repository(config)
    diagnostics = list(state.diagnostics)
    _validate_schema(config, state, diagnostics)
    _validate_unique_numbers(config, state, diagnostics)
    templates = _template_headings(config)

    for document in state.documents:
        if document.is_draft:
            _validate_frontmatter_draft(config, document, diagnostics)
            if config.drafts is not None and config.drafts.require_summary:
                _validate_summary(config, document, diagnostics)
        else:
            _validate_formal_shape(config, document, diagnostics)
            _validate_summary(config, document, diagnostics)
        _validate_sections(config, document, templates, diagnostics)

    _validate_graph(config, state, diagnostics)
    _validate_defines(config, state, diagnostics)
    if base_ref is not None:
        _validate_history(config, state, base_ref, diagnostics)

    ordered = tuple(sorted(diagnostics, key=Diagnostic.sort_key))
    return ValidationResult(state=state, diagnostics=ordered)
