"""Proposal identifiers and numeric reference normalization."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from zendev.core.markdown import scan_markdown
from zendev.proposal.model import Diagnostic, ProposalConfig, ProposalDocument, RepositoryState


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


def reference_number(config: ProposalConfig, value: object) -> int | None:
    """Normalize an integer or canonical string edge to its numeric proposal key."""

    identifier = normalize_reference(config, value)
    if identifier is None:
        return None
    return int(identifier.removeprefix(f"{config.prefix}-"))


def edge_numbers(config: ProposalConfig, document: ProposalDocument, field: str) -> tuple[int, ...]:
    raw = document.metadata.get(field)
    if not isinstance(raw, list):
        return ()
    return tuple(number for value in raw if (number := reference_number(config, value)) is not None)


def _body_references(config: ProposalConfig, document: ProposalDocument, by_path: dict[Path, str]) -> dict[str, int]:
    facts = scan_markdown(document.body)
    references: dict[str, int] = {}
    pattern = re.compile(
        rf"(?<![A-Za-z0-9_-]){re.escape(config.prefix)}-[0-9]{{{config.number_width}}}(?![A-Za-z0-9_-])"
    )
    absolute_url = re.compile(r"\b[A-Za-z][A-Za-z0-9+.-]*://[^\s<>]+")
    for span in facts.text_spans:
        if span.link is not None:
            continue
        if span.code:
            if (identifier := normalize_reference(config, span.text.strip())) is not None:
                references.setdefault(identifier, span.line)
        else:
            text = absolute_url.sub(lambda match: " " * len(match[0]), span.text)
            for match in pattern.finditer(text):
                references.setdefault(match[0], span.line + span.text[: match.start()].count("\n"))
    for line, url in facts.links:
        try:
            parsed = urlsplit(url)
        except ValueError:
            continue  # Link validation owns malformed URLs.
        if parsed.scheme or parsed.netloc:
            continue
        raw_path = unquote(parsed.path)
        target = (
            (
                (config.root / raw_path.lstrip("/")) if raw_path.startswith("/") else document.path.parent / raw_path
            ).resolve()
            if raw_path
            else document.path
        )
        if (identifier := by_path.get(target)) is not None:
            references[identifier] = min(line, references.get(identifier, line))
    return references


def validate_references(config: ProposalConfig, state: RepositoryState, diagnostics: list[Diagnostic]) -> None:
    policy = config.graph
    if policy is None or not policy.require_declared_references or policy.requires_field is None:
        return
    by_path = {
        document.path: identifier
        for document in state.formal_documents
        if (identifier := document.identifier(config)) is not None
    }
    identifiers = set(by_path.values())
    for document in state.documents:
        source = document.identifier(config)
        declared = set(edge_identifiers(config, document, policy.requires_field))
        offset = len(document.raw_frontmatter.splitlines()) + 2
        for target, line in _body_references(config, document, by_path).items():
            if target == source:
                continue
            if target not in identifiers:
                code = "proposal.reference.missing-target"
                message = f"body references missing {target}"
            elif target not in declared:
                code = "proposal.reference.undeclared-dependency"
                message = f"body references {target} without a direct declaration in `{policy.requires_field}`"
            else:
                continue
            diagnostics.append(Diagnostic(code=code, path=document.relative_path, line=offset + line, message=message))
