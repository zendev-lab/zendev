"""Plan conservative source repairs and validate them before writing."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, replace
from difflib import SequenceMatcher
from typing import Any, cast

import yaml
from yaml.nodes import MappingNode, SequenceNode
from yaml.tokens import AliasToken, AnchorToken

from zendev.proposal._markdown_scan import scan_markdown
from zendev.proposal.indexing import normalize_reference, reference_number
from zendev.proposal.model import Diagnostic, ProposalConfig, ProposalToolError, RepositoryState
from zendev.proposal.repository import FrontmatterLoader, parse_frontmatter
from zendev.proposal.schema import load_schema
from zendev.proposal.validation import _formal_filename_pattern, _template_headings, expected_h1


@dataclass(frozen=True)
class SourceEdit:
    path: str
    before: bytes
    after: bytes
    rules: tuple[str, ...] = ()


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


RULES = ("number", "title", "h1", "marker", "defines", "deduplicate", "references", "aliases", "sections")
REASONS = {
    "number": "unique canonical filename",
    "title": "matching H1 or title-mode policy",
    "h1": "valid title and identity metadata",
    "marker": "configured standalone marker",
    "defines": "canonical anchors, exact headings or required empty field",
    "deduplicate": "equivalent declaration or relationship entries",
    "references": "configured reference representation",
    "aliases": "configured value mapping",
    "sections": "required template headings (no generated prose)",
}


def _set_metadata(raw: str, key: str, value: object) -> str:
    if any(isinstance(token, (AliasToken, AnchorToken)) for token in yaml.scan(raw)):
        return raw
    node = yaml.compose(raw, Loader=FrontmatterLoader)
    if not isinstance(node, MappingNode) or node.flow_style:
        return raw
    encoded = json.dumps(value, ensure_ascii=False)
    expected = {**parse_frontmatter(raw, "metadata"), key: value}
    for field, old in node.value:
        if field.value != key:
            continue
        start, end = old.start_mark.index, old.end_mark.index
        if "#" in raw[start:end]:
            return raw
        replacement = encoded + ("\n" if raw[start:end].endswith("\n") else "")
        candidate = raw[:start] + replacement + raw[end:]
        break
    else:
        candidate = f"{json.dumps(key)}: {encoded}\n" + raw
    try:
        if parse_frontmatter(candidate, "metadata") == expected:
            return candidate
    except ValueError:
        pass
    return raw


def plan_repairs(
    config: ProposalConfig,
    state: RepositoryState,
    *,
    selected: tuple[str, ...] = RULES,
    baseline: RepositoryState | None = None,
) -> tuple[RepositoryState, tuple[SourceEdit, ...]]:
    """Return a candidate snapshot and byte-preserving edits; do not write files."""
    documents = []
    edits: list[SourceEdit] = []
    templates = _template_headings(config) if "sections" in selected else {}
    numbers = Counter(document.number(config) for document in state.formal_documents)
    filenames = Counter(
        int(match.group(1))
        for doc in state.formal_documents
        if (match := _formal_filename_pattern(config).fullmatch(doc.path.name))
    )
    for document in state.documents:
        original_document = next(doc for doc in (baseline or state).documents if doc.path == document.path)
        applied: list[str] = []
        raw = document.raw_frontmatter
        metadata = dict(document.metadata)

        def put(
            key: str, value: object, rule: str, path: str = document.relative_path, applied: list[str] = applied
        ) -> None:
            nonlocal raw, metadata
            changed = _set_metadata(raw, key, value)
            if changed != raw:
                raw = changed
                metadata = parse_frontmatter(raw, path)
                applied.append(rule)

        if "number" in selected and not document.is_draft and config.number_field not in metadata:
            match = _formal_filename_pattern(config).fullmatch(document.path.name)
            if match and filenames[int(match.group(1))] == 1 and numbers[int(match.group(1))] == 0:
                put(config.number_field, int(match.group(1)), "number")
        if "title" in selected:
            title = metadata.get(config.title_field)
            number = metadata.get(config.number_field)
            identifier = config.format_identifier(number) if type(number) is int else None
            if title is None and config.title_field not in metadata:
                headings = [h for h in scan_markdown(document.body).headings if h.level == 1]
                first = next((i for i, line in enumerate(document.body.splitlines()) if line.strip()), -1)
                if len(headings) == 1 and headings[0].start == first:
                    candidate_title = headings[0].text
                    if document.is_draft:
                        put(config.title_field, candidate_title, "title")
                    elif identifier and candidate_title.startswith(f"{identifier}:"):
                        put(
                            config.title_field,
                            candidate_title.removeprefix(f"{identifier}:").strip()
                            if config.metadata_title == "plain"
                            else candidate_title,
                            "title",
                        )
            elif isinstance(title, str) and len(title.splitlines()) == 1:
                cleaned = title.strip()
                if identifier and not document.is_draft:
                    if config.metadata_title == "plain":
                        cleaned = cleaned.removeprefix(f"{identifier}:").strip()
                    elif not re.match(rf"^{re.escape(config.prefix)}-\d+:", cleaned):
                        cleaned = f"{identifier}: {cleaned}"
                if cleaned and cleaned != title:
                    put(config.title_field, cleaned, "title")
        fields = (*config.graph.fields,) if config.graph else ()
        if config.defines:
            fields = (*fields, config.defines.field)
        for field in fields:
            values = metadata.get(field)
            if not isinstance(values, list):
                continue
            if "deduplicate" in selected:
                unique: list[object] = []
                seen: list[object] = []
                for value in values:
                    key = normalize_reference(config, value) if config.graph and field in config.graph.fields else value
                    if key is None:
                        key = value
                    if key not in seen:
                        seen.append(key)
                        unique.append(value)
                if unique != values:
                    put(field, unique, "deduplicate")
            values = metadata.get(field)
            if "references" in selected and config.graph and field in config.graph.fields and isinstance(values, list):
                normalized = [
                    reference_number(config, value)
                    if config.fix.reference_style == "number"
                    else normalize_reference(config, value)
                    for value in values
                ]
                if (
                    config.fix.reference_style != "preserve"
                    and all(value is not None for value in normalized)
                    and normalized != values
                ):
                    put(field, normalized, "references")
        if "aliases" in selected:
            for field, mapping in config.fix.aliases.items():
                value = metadata.get(field)
                if isinstance(value, str) and value in mapping:
                    put(field, mapping[value], "aliases")
        document = replace(document, metadata=metadata, raw_frontmatter=raw)
        body_config = (
            config
            if "marker" in selected
            else replace(config, drafts=replace(config.drafts, marker=None) if config.drafts else None)
        )
        body = _repair_body(
            body_config,
            document.body,
            expected_h1(config, document) if "h1" in selected else None,
            is_draft=document.is_draft,
        )
        if (
            "marker" in selected
            and "h1" not in selected
            and expected_h1(config, document)
            == next((line.strip() for line in document.body.splitlines() if line.strip()), None)
        ):
            body = _repair_body(config, document.body, expected_h1(config, document), is_draft=document.is_draft)
        h1_only = _repair_body(
            replace(config, drafts=replace(config.drafts, marker=None) if config.drafts else None),
            document.body,
            expected_h1(config, document) if "h1" in selected else None,
            is_draft=document.is_draft,
        )
        if h1_only != document.body:
            applied.append("h1")
        if body != h1_only:
            applied.append("marker")

        policy = config.defines
        if policy is not None and "defines" in selected:
            before_defines = (raw, body)
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
                if policy.field not in metadata and not additions and not facts.anchors:
                    validator = load_schema(
                        config, config.drafts.schema_path if document.is_draft and config.drafts else config.schema_path
                    )[0]
                    if any(
                        error.validator == "required"
                        and not error.path
                        and isinstance(error.validator_value, list)
                        and policy.field in error.validator_value
                        for error in validator.iter_errors(cast(Any, metadata))
                    ):
                        proposed_raw = _set_metadata(raw, policy.field, [])
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
            if (raw, body) != before_defines:
                applied.append("defines")
        if "sections" in selected:
            required = templates.get(str(metadata.get(config.type_field)), ())
            found = {h.text for h in scan_markdown(body).headings if h.level == 2}
            for heading in required:
                if heading not in found:
                    following = set(required[required.index(heading) + 1 :])
                    next_heading = next(
                        (item for item in scan_markdown(body).headings if item.level == 2 and item.text in following),
                        None,
                    )
                    if next_heading:
                        lines = body.splitlines(keepends=True)
                        lines.insert(next_heading.start, f"## {heading}\n\n")
                        body = "".join(lines)
                    else:
                        body = body.rstrip() + f"\n\n## {heading}\n"
                    applied.append("sections")
        candidate = replace(
            document, raw_frontmatter=raw, body=body, metadata=parse_frontmatter(raw, document.relative_path)
        )
        documents.append(candidate)
        if raw == original_document.raw_frontmatter and body == original_document.body:
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
        expected = "---\n" + original_document.raw_frontmatter + "---\n" + original_document.body
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
        edits.append(SourceEdit(document.relative_path, before, after, tuple(dict.fromkeys(applied))))
    return replace(
        state, documents=tuple(documents), formal_documents=tuple(doc for doc in documents if not doc.is_draft)
    ), tuple(edits)


def write_repairs(config: ProposalConfig, edits: tuple[SourceEdit, ...]) -> None:
    """Apply source-only plans through the shared snapshot and rollback boundary."""
    from zendev.proposal.transaction import commit_files, snapshot_inputs

    before = snapshot_inputs(config)
    if any(before.get(config.root / edit.path) != edit.before for edit in edits):
        raise ProposalToolError(Diagnostic(code="proposal.fix.changed", message="source changed since planning"))
    commit_files(config, {config.root / edit.path: edit.after for edit in edits}, before)
