"""Derived proposal names and template structure shared by checks and repairs."""

from __future__ import annotations

import re
from contextlib import suppress

from zendev.core.diagnostics import ToolError
from zendev.core.source import read_text
from zendev.proposal.model import Diagnostic, ProposalConfig, ProposalDocument
from zendev.proposal.repository import extract_frontmatter, h2_headings


def formal_filename_pattern(config: ProposalConfig) -> re.Pattern[str]:
    return re.compile(
        rf"^{re.escape(config.prefix)}-(\d{{{config.number_width}}})-"
        rf"(?:{config.filename_slug_pattern})\.md$"
    )


def expected_h1(config: ProposalConfig, document: ProposalDocument) -> str | None:
    """Derive a heading only from mechanically valid title and identity metadata."""
    title = document.metadata.get(config.title_field)
    if not isinstance(title, str) or not title.strip() or title != title.strip() or len(title.splitlines()) != 1:
        return None
    if document.is_draft:
        return f"# {title}"
    number = document.number(config)
    if number is None or not 0 <= number < 10**config.number_width:
        return None
    identifier = config.format_identifier(number)
    if config.metadata_title == "plain":
        if re.match(rf"^{re.escape(config.prefix)}-\d+:", title):
            return None
        return f"# {identifier}: {title}"
    if not title.startswith(f"{identifier}:") or not title[len(identifier) + 1 :].strip():
        return None
    return f"# {title}"


def template_headings(config: ProposalConfig) -> dict[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}
    for proposal_type, path in config.templates.items():
        try:
            text = read_text(path)
        except (OSError, UnicodeError) as error:
            raise ToolError(
                Diagnostic(
                    code="proposal.template.read",
                    path=config.relative_path(path),
                    message=f"failed to read proposal template: {error}",
                )
            ) from error
        # Templates may contain only Markdown, without metadata.
        with suppress(ValueError):
            _, text = extract_frontmatter(text, config.relative_path(path))
        headings = h2_headings(text)
        if len(headings) != len(set(headings)):
            raise ToolError(
                Diagnostic(
                    code="proposal.template.duplicate-heading",
                    path=config.relative_path(path),
                    message="proposal template H2 headings must be unique",
                )
            )
        result[proposal_type] = headings
    return result
