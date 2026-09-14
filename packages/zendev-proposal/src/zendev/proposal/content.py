"""Repository-owned body and offline link policies."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import replace
from pathlib import Path
from urllib.parse import unquote, urlsplit

from zendev.proposal._markdown_scan import scan_markdown
from zendev.proposal._slug import GithubSlugger
from zendev.proposal.model import Diagnostic, ProposalConfig, ProposalDocument, RepositoryState


def _body(text: str) -> str:
    from zendev.proposal.repository import extract_frontmatter

    try:
        return extract_frontmatter(text, "Markdown")[1]
    except ValueError:
        return text


def validate_content(
    config: ProposalConfig,
    document: ProposalDocument,
    templates: dict[str, tuple[str, ...]],
    diagnostics: list[Diagnostic],
    bodies: dict[Path, str] | None = None,
) -> None:
    facts = scan_markdown(document.body)
    offset = len(document.raw_frontmatter.splitlines()) + 2

    def error(code: str, message: str, line: int = 1) -> None:
        diagnostics.append(Diagnostic(code=code, path=document.relative_path, line=offset + line, message=message))

    for identifier, count in Counter(anchor.identifier for anchor in facts.anchors).items():
        if count > 1 and (config.defines is None or not identifier.startswith(config.defines.anchor_prefix)):
            error(
                "proposal.anchor.duplicate-id",
                f"HTML ID `{identifier}` occurs {count} times",
                next(a.line for a in facts.anchors if a.identifier == identifier),
            )
    required = templates.get(str(document.metadata.get(config.type_field)), ())
    headings = [h for h in facts.headings if h.level == 2]
    if config.sections.ordered:
        actual = tuple(h.text for h in headings if h.text in required)
        expected = tuple(name for name in required if name in actual)
        if actual != expected:
            error("proposal.sections.order", "required sections must follow template order")
    if config.sections.no_skip_levels:
        previous = 0
        for heading in facts.headings:
            if heading.level > previous + 1:
                error("proposal.sections.level", "heading levels must not be skipped", heading.start + 1)
            previous = heading.level
    lines = document.body.splitlines()
    for heading in headings:
        if config.sections.nonempty and heading.text in required:
            end = next((h.start for h in facts.headings if h.start > heading.start and h.level <= 2), len(lines))
            section = "\n".join(lines[heading.end : end])
            # Comments, empty anchors and subordinate headings do not constitute section content.
            visible = scan_markdown(section)
            if not visible.content:
                error("proposal.sections.empty", f"required section `{heading.text}` has no content", heading.start + 1)
    for line, text in facts.prose:
        if text.strip() in config.sections.placeholders:
            error("proposal.sections.placeholder", f"replace placeholder `{text.strip()}`", line)
    if not config.links.check:
        return
    for line, url in facts.links:
        parsed = urlsplit(url)
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
        if not target.is_relative_to(config.root) or not target.exists():
            error("proposal.link.missing-target", f"local link target does not exist in the repository: `{url}`", line)
            continue
        if not parsed.fragment or not target.is_file() or target.suffix.lower() not in {".md", ".html"}:
            continue
        try:
            target_body = (
                bodies[target] if bodies is not None and target in bodies else _body(target.read_text(encoding="utf-8"))
            )
        except (OSError, UnicodeError) as failure:
            error("proposal.link.read", f"cannot read `{url}`: {failure}", line)
            continue
        target_facts = scan_markdown(target_body)
        identifiers = {anchor.identifier for anchor in target_facts.anchors}
        if config.links.heading_ids == "github":
            slugger = GithubSlugger()
            identifiers.update(slugger.slug(heading.plain) for heading in target_facts.headings)
        if unquote(parsed.fragment) not in identifiers:
            hint = (
                " (configure links.heading_ids for generated heading anchors)"
                if config.links.heading_ids == "explicit"
                else ""
            )
            error("proposal.link.missing-fragment", f"local fragment not found: `{url}`{hint}", line)


def locate_diagnostics(
    config: ProposalConfig, state: RepositoryState, diagnostics: list[Diagnostic]
) -> list[Diagnostic]:
    documents = {doc.relative_path: doc for doc in state.documents}
    result: list[Diagnostic] = []
    for diagnostic in diagnostics:
        document = documents.get(diagnostic.path or "")
        if diagnostic.line is None and document is not None:
            field = re.search(r"frontmatter\.([\w-]+)|`([\w-]+)`", diagnostic.message)
            name = next((group for group in field.groups() if group), "") if field else ""
            line = (
                next(
                    (
                        index + 2
                        for index, raw in enumerate(document.raw_frontmatter.splitlines())
                        if re.match(rf"['\"]?{re.escape(name)}['\"]?\s*:", raw)
                    ),
                    None,
                )
                if name
                else None
            )
            if line is None:
                line = 1 if "frontmatter" in diagnostic.code else len(document.raw_frontmatter.splitlines()) + 3
            diagnostic = replace(diagnostic, line=line)
        result.append(diagnostic)
    return result
