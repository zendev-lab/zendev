"""Proposal identifiers and numeric reference normalization."""

from __future__ import annotations

import re

from zendev.proposal.model import ProposalConfig, ProposalDocument


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
