"""Read proposal repositories without mutating their source documents."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode
from yaml.resolver import BaseResolver

from zendev.proposal._markdown_scan import iter_lines_outside_fences
from zendev.proposal.model import (
    Diagnostic,
    ProposalConfig,
    ProposalDocument,
    RepositoryState,
)


class FrontmatterLoader(yaml.SafeLoader):
    """Safe YAML loader that preserves ISO dates as schema-checkable strings."""


type.__setattr__(
    FrontmatterLoader,
    "yaml_implicit_resolvers",
    {
        key: [(tag, resolver) for tag, resolver in resolvers if tag != "tag:yaml.org,2002:timestamp"]
        for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
    },
)


def _construct_unique_mapping(loader: FrontmatterLoader, node: MappingNode, deep: bool = False) -> dict[object, object]:
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as error:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable key",
                key_node.start_mark,
            ) from error
        if duplicate:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


FrontmatterLoader.add_constructor(BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping)


def extract_frontmatter(text: str, path: str) -> tuple[str, str]:
    """Split a Markdown document into YAML frontmatter and body."""

    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise ValueError(f"{path}: missing YAML frontmatter")
    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip("\r\n") == "---":
            return "".join(lines[1:index]), "".join(lines[index + 1 :])
    raise ValueError(f"{path}: unterminated YAML frontmatter")


def parse_frontmatter(raw: str, path: str) -> dict[str, object]:
    """Parse YAML frontmatter with duplicate-key and unsafe-tag protection."""

    try:
        value = yaml.load(raw, Loader=FrontmatterLoader)
    except yaml.YAMLError as error:
        raise ValueError(f"{path}: invalid YAML frontmatter: {error}") from error
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{path}: YAML frontmatter must be a mapping with string keys")
    return value


def _yaml_line(error: ValueError) -> int | None:
    cause = error.__cause__
    if not isinstance(cause, yaml.YAMLError):
        return 1
    mark = getattr(cause, "problem_mark", None)
    return mark.line + 2 if mark is not None else 1


def _read_document(
    config: ProposalConfig, path: Path, *, is_draft: bool
) -> tuple[ProposalDocument | None, Diagnostic | None]:
    relative = config.relative_path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return None, Diagnostic(
            code="proposal.document.read",
            path=relative,
            message=f"failed to read Markdown document: {error}",
        )
    try:
        raw, body = extract_frontmatter(text, relative)
        metadata = parse_frontmatter(raw, relative)
    except ValueError as error:
        return None, Diagnostic(
            code="proposal.frontmatter.invalid",
            path=relative,
            line=_yaml_line(error),
            message=str(error).removeprefix(f"{relative}: "),
        )
    return (
        ProposalDocument(
            path=path,
            relative_path=relative,
            raw_frontmatter=raw,
            metadata=metadata,
            body=body,
            is_draft=is_draft,
        ),
        None,
    )


def _draft_paths(config: ProposalConfig) -> tuple[Path, ...]:
    if config.drafts is None:
        return ()
    return tuple(sorted(path for path in config.drafts.directory.glob("*.md") if path.name != "README.md"))


def load_repository(config: ProposalConfig) -> RepositoryState:
    """Discover and parse formal proposals plus configured draft documents."""

    diagnostics: list[Diagnostic] = []
    formal: list[ProposalDocument] = []
    formal_paths = tuple(sorted(path for path in config.documents_dir.glob("*.md") if path.name != "README.md"))
    if not formal_paths:
        diagnostics.append(
            Diagnostic(
                code="proposal.documents.empty",
                path=config.relative_path(config.documents_dir),
                message=f"no formal {config.prefix} documents were found",
            )
        )
    for path in formal_paths:
        document, diagnostic = _read_document(config, path, is_draft=False)
        if diagnostic is not None:
            diagnostics.append(diagnostic)
        elif document is not None:
            formal.append(document)

    drafts = _draft_paths(config)
    parsed_drafts: list[ProposalDocument] = []
    for path in drafts:
        document, diagnostic = _read_document(config, path, is_draft=True)
        if diagnostic is not None:
            diagnostics.append(diagnostic)
        elif document is not None:
            parsed_drafts.append(document)

    return RepositoryState(
        documents=tuple(formal + parsed_drafts),
        formal_documents=tuple(formal),
        draft_paths=drafts,
        diagnostics=tuple(sorted(diagnostics, key=Diagnostic.sort_key)),
    )


def h2_headings(markdown: str) -> tuple[str, ...]:
    """Return H2 headings outside fenced code blocks, preserving order."""

    headings: list[str] = []
    for line in iter_lines_outside_fences(markdown):
        stripped = line.strip()
        if stripped.startswith("## ") and stripped[3:].strip():
            headings.append(stripped[3:].strip())
    return tuple(headings)


def iter_markdown_lines(paths: tuple[Path, ...]) -> Iterator[tuple[Path, int, str]]:
    for path in sorted(paths):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            yield path, line_number, line
