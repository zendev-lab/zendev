"""Plan conservative source repairs and validate them before writing."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, replace
from difflib import SequenceMatcher

import yaml
from yaml.nodes import MappingNode, SequenceNode
from yaml.tokens import AliasToken, AnchorToken

from zendev.proposal._markdown_scan import scan_markdown
from zendev.proposal.model import Diagnostic, ProposalConfig, ProposalToolError, RepositoryState
from zendev.proposal.repository import FrontmatterLoader, parse_frontmatter
from zendev.proposal.validation import expected_h1


@dataclass(frozen=True)
class SourceEdit:
    path: str
    before: bytes
    after: bytes


def _append_defines(raw: str, field: str, additions: list[str]) -> str:
    """Append IDs without reserializing unrelated YAML or removing comments."""
    if not additions:
        return raw
    # Aliases can make a local edit change other metadata implicitly.
    if any(isinstance(token, (AliasToken, AnchorToken)) for token in yaml.scan(raw)):
        return raw
    node = yaml.compose(raw, Loader=FrontmatterLoader)
    if not isinstance(node, MappingNode) or node.flow_style:
        return raw
    encoded = ", ".join(json.dumps(value, ensure_ascii=False) for value in additions)
    for key, value in node.value:
        if key.value != field:
            continue
        if not isinstance(value, SequenceNode):
            return raw
        if value.flow_style:
            offset = value.end_mark.index - 1
            prefix = re.sub(r"#[^\n]*", "", raw[value.start_mark.index : offset]).rstrip()
            separator = ", " if value.value and not prefix.endswith(",") else " "
            return raw[:offset] + separator + encoded + raw[offset:]
        if not value.value:
            return raw
        last = value.value[-1]
        lines = raw.splitlines(keepends=True)
        offset = sum(len(line) for line in lines[: last.end_mark.line + 1])
        indent = " " * value.start_mark.column
        insertion = "".join(f"{indent}- {json.dumps(item, ensure_ascii=False)}\n" for item in additions)
        return raw[:offset] + insertion + raw[offset:]
    return f"{json.dumps(field)}: [{encoded}]\n" + raw


def _repair_body(config: ProposalConfig, document_body: str, h1: str | None, *, is_draft: bool) -> str:
    lines = document_body.splitlines(keepends=True)
    first = next((index for index, line in enumerate(lines) if line.strip()), len(lines))
    headings = [heading for heading in scan_markdown(document_body).headings if heading.level == 1]
    if h1 is not None:
        if not headings:
            lines[first:first] = [h1 + "\n", "\n"]
        elif len(headings) == 1 and headings[0].start == first:
            heading = headings[0]
            if "".join(lines[heading.start : heading.end]).rstrip("\r\n") != h1:
                lines[heading.start : heading.end] = [h1 + "\n"]
    body = "".join(lines)
    marker = config.drafts.marker if is_draft and config.drafts is not None else None
    if marker is None or h1 is None:
        return body
    nonempty = [index for index, line in enumerate(lines) if line.strip()]
    if not nonempty or lines[nonempty[0]].strip() != h1:
        return body
    markers = scan_markdown(body, marker).marker_lines
    if len(markers) > 1:
        return body
    if len(markers) == 1:
        if len(nonempty) > 1 and markers[0] == nonempty[1]:
            return body
        del lines[markers[0]]
    elif len(nonempty) > 1 and lines[nonempty[1]].lstrip().startswith(">"):
        # A configured summary is known prose; another declaration needs review.
        summary = config.summary
        if summary is None or not lines[nonempty[1]].startswith(f"> {summary.prefix}"):
            return body
    lines[nonempty[0] + 1 : nonempty[0] + 1] = ["\n", marker + "\n", "\n"]
    return "".join(lines)


def plan_repairs(config: ProposalConfig, state: RepositoryState) -> tuple[RepositoryState, tuple[SourceEdit, ...]]:
    """Return a candidate snapshot and byte-preserving edits; do not write files."""
    documents = []
    edits: list[SourceEdit] = []
    for document in state.documents:
        body = _repair_body(config, document.body, expected_h1(config, document), is_draft=document.is_draft)
        raw = document.raw_frontmatter
        policy = config.defines
        if policy is not None:
            facts = scan_markdown(body)
            counts = Counter(anchor.identifier for anchor in facts.anchors)
            declared = document.metadata.get(policy.field, [])
            if isinstance(declared, list) and all(
                isinstance(item, str) and re.fullmatch(policy.id_pattern, item) is not None for item in declared
            ):
                additions: list[str] = []
                for anchor in facts.anchors:
                    concept = anchor.identifier.removeprefix(policy.anchor_prefix)
                    if (
                        anchor.canonical
                        and anchor.identifier.startswith(policy.anchor_prefix)
                        and counts[anchor.identifier] == 1
                        and re.fullmatch(policy.id_pattern, concept) is not None
                        and concept not in declared
                    ):
                        additions.append(concept)
                proposed_raw = _append_defines(raw, policy.field, additions)
                try:
                    parsed = parse_frontmatter(proposed_raw, document.relative_path)
                except ValueError:
                    pass  # Unsupported YAML layout: retain the source and its diagnostic.
                else:
                    expected_metadata = {**document.metadata, policy.field: [*declared, *additions]}
                    if parsed == expected_metadata:
                        raw = proposed_raw
                lines = body.splitlines(keepends=True)
                insertions: dict[int, str] = {}
                for concept in declared:
                    anchor_id = f"{policy.anchor_prefix}{concept}"
                    matches = [heading for heading in facts.headings if heading.level >= 2 and heading.text == concept]
                    if counts[anchor_id] == 0 and len(matches) == 1:
                        insertions[matches[0].start] = f'<a id="{anchor_id}"></a>\n\n'
                for line, insertion in sorted(insertions.items(), reverse=True):
                    lines.insert(line, insertion)
                body = "".join(lines)
        candidate = replace(
            document, raw_frontmatter=raw, body=body, metadata=parse_frontmatter(raw, document.relative_path)
        )
        documents.append(candidate)
        if raw == document.raw_frontmatter and body == document.body:
            continue
        try:
            before = document.path.read_bytes()
            original = before.decode("utf-8")
        except (OSError, UnicodeError) as error:
            raise ProposalToolError(
                Diagnostic(
                    code="proposal.document.read",
                    path=document.relative_path,
                    message=str(error),
                )
            ) from error
        normalized = original.replace("\r\n", "\n").replace("\r", "\n")
        expected = "---\n" + document.raw_frontmatter + "---\n" + document.body
        if normalized != expected:
            raise ProposalToolError(
                Diagnostic(
                    code="proposal.fix.changed",
                    path=document.relative_path,
                    message="document changed during repair planning or has an unsupported delimiter ending",
                )
            )
        newline = "\r\n" if "\r\n" in original else "\r" if "\r" in original else "\n"
        updated = "---\n" + raw + "---\n" + body
        old_lines = normalized.splitlines(keepends=True)
        new_lines = updated.splitlines(keepends=True)
        original_lines = original.splitlines(keepends=True)
        output: list[str] = []
        for tag, start, end, new_start, new_end in SequenceMatcher(
            None, old_lines, new_lines, autojunk=False
        ).get_opcodes():
            if tag == "equal":
                output.extend(original_lines[start:end])
            else:
                output.extend(line.replace("\n", newline) for line in new_lines[new_start:new_end])
        after = "".join(output).encode("utf-8")
        edits.append(SourceEdit(document.relative_path, before, after))
    return replace(
        state, documents=tuple(documents), formal_documents=tuple(doc for doc in documents if not doc.is_draft)
    ), tuple(edits)


def write_repairs(config: ProposalConfig, edits: tuple[SourceEdit, ...]) -> None:
    """Check source snapshots before applying an already validated repair plan."""
    try:
        for edit in edits:
            path = config.root / edit.path
            if path.is_symlink() or path.read_bytes() != edit.before:
                raise ProposalToolError(
                    Diagnostic(
                        code="proposal.fix.changed",
                        path=edit.path,
                        message="document changed since validation or is a symbolic link; repairs were not applied",
                    )
                )
        for edit in edits:
            (config.root / edit.path).write_bytes(edit.after)
    except OSError as error:
        raise ProposalToolError(
            Diagnostic(
                code="proposal.fix.write",
                message=f"failed to apply proposal repairs: {error}",
            )
        ) from error
