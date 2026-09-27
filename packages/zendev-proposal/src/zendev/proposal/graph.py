"""Proposal relationship integrity, independent of index projection."""

from __future__ import annotations

from collections import defaultdict

from zendev.proposal.model import Diagnostic, ProposalConfig, RepositoryState
from zendev.proposal.references import edge_identifiers, normalize_reference


def validate_graph(config: ProposalConfig, state: RepositoryState, diagnostics: list[Diagnostic]) -> None:
    policy = config.graph
    if policy is None:
        return
    by_id = {
        identifier: document
        for document in state.formal_documents
        if (identifier := document.identifier(config)) is not None
    }
    for document in state.documents:
        source = document.identifier(config)
        for field in policy.fields:
            if document.is_draft and field not in document.metadata:
                continue
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

    acyclic = tuple(
        dict.fromkeys(
            (
                *policy.acyclic_fields,
                *([policy.requires_field] if policy.requires_field else []),
                *([policy.supersedes_field] if policy.supersedes_field else []),
            )
        )
    )
    for relation in acyclic:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(
            identifier: str,
            path: list[str],
            visiting: set[str] = visiting,
            visited: set[str] = visited,
            relation: str = relation,
        ) -> None:
            if identifier in visiting:
                cycle_start = path.index(identifier)
                cycle = [*path[cycle_start:], identifier]
                diagnostics.append(
                    Diagnostic(
                        code=f"proposal.graph.{relation}-cycle",
                        message=f"{relation} graph contains a cycle: " + " -> ".join(cycle),
                    )
                )
                return
            if identifier in visited:
                return
            visiting.add(identifier)
            path.append(identifier)
            for target in edge_identifiers(config, by_id[identifier], relation):
                if target in by_id:
                    visit(target, path)
            path.pop()
            visiting.remove(identifier)
            visited.add(identifier)

        for identifier in sorted(by_id):
            visit(identifier, [])

    requires_field = policy.requires_field
    if requires_field is not None:
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
    superseders_by_target: dict[str, list[str]] = defaultdict(list)
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
            if status in {policy.accepted_status, policy.superseded_status}:
                superseders_by_target[target].append(source)

    for identifier, document in by_id.items():
        if document.metadata.get(config.status_field) != policy.superseded_status:
            continue
        pending = list(superseders_by_target.get(identifier, []))
        visited: set[str] = set()
        current: set[str] = set()
        while pending:
            target = pending.pop()
            if target in visited:
                continue
            visited.add(target)
            if by_id[target].metadata.get(config.status_field) == policy.accepted_status:
                current.add(target)
            else:
                pending.extend(superseders_by_target.get(target, []))
        if len(current) != 1:
            diagnostics.append(
                Diagnostic(
                    code="proposal.graph.superseded-owner",
                    path=document.relative_path,
                    message=(
                        f"superseded proposal must reach exactly one accepted current superseder; found {len(current)}"
                    ),
                )
            )
