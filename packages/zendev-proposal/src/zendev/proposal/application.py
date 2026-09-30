"""Proposal application workflow: validate, plan, then explicitly apply."""

from __future__ import annotations

import difflib
from dataclasses import dataclass, replace
from pathlib import Path

from zendev.core.diagnostics import Diagnostic, ToolError
from zendev.core.markdown import markdown_session
from zendev.core.source import current_snapshot, exists, read_bytes, source_session
from zendev.proposal.config import load_config
from zendev.proposal.indexing import check_index, expected_index_text
from zendev.proposal.model import ProposalConfig, ValidationResult
from zendev.proposal.repair import REASONS, RULES, SourceEdit, plan_repairs
from zendev.proposal.transaction import commit_files, snapshot_inputs
from zendev.proposal.validation import validate_repository, validate_state


@dataclass(frozen=True, slots=True)
class ChangePlan:
    config: ProposalConfig
    before: dict[Path, bytes | None]
    original: ValidationResult
    candidate: ValidationResult
    edits: tuple[SourceEdit, ...]
    updates: dict[Path, bytes]
    applicable: bool
    patch: str


@dataclass(frozen=True, slots=True)
class CheckReport:
    diagnostics: tuple[Diagnostic, ...]
    summary: dict[str, object]
    patch: str = ""


def plan_changes(
    config: ProposalConfig,
    *,
    base_ref: str | None = None,
    selected: tuple[str, ...] = RULES,
    partial: bool = False,
    diff: bool = False,
) -> ChangePlan:
    with markdown_session(), source_session():
        if base_ref is not None:
            from zendev.proposal.history import resolve_base_ref

            base_ref = resolve_base_ref(config, base_ref)
        return _plan_changes(config, base_ref=base_ref, selected=selected, partial=partial, diff=diff)


def _plan_changes(
    config: ProposalConfig,
    *,
    base_ref: str | None,
    selected: tuple[str, ...],
    partial: bool,
    diff: bool,
) -> ChangePlan:
    if load_config(config.config_path) != config:
        raise ToolError(
            Diagnostic("proposal.fix.changed", "Configuration changed since loading; reload before planning")
        )
    captured = snapshot_inputs(config)
    session = current_snapshot()
    if session is not None:
        if any(path in captured and captured[path] != data for path, data in session.files.items()):
            raise ToolError(Diagnostic("proposal.fix.changed", "Inputs changed while loading the configuration"))
        session.files.update(captured)
    snapshot: dict[Path, bytes | None] = dict(captured)
    original = validate_repository(config, base_ref=base_ref)
    candidate, edits = plan_repairs(config, original.state, selected=selected)
    proposed = validate_state(config, candidate, base_ref=base_ref) if edits else original
    applicable = proposed.ok
    if partial and not applicable:
        # Only independently safe document edits may bypass unrelated content failures.
        kept = {}
        state = original.state
        initial = {(d.path, d.code, d.message) for d in original.diagnostics}
        sensitive = (
            "proposal.graph.",
            "proposal.number.",
            "proposal.filename.",
            "proposal.history.",
            "proposal.frontmatter.",
            "proposal.defines.duplicate-owner",
        )
        for rule in selected:
            rule_state, rule_edits = plan_repairs(config, state, selected=(rule,), baseline=original.state)
            for edit in rule_edits:
                if not edit.rules:
                    continue
                changed = next(doc for doc in rule_state.documents if doc.relative_path == edit.path)
                docs = tuple(changed if doc.relative_path == edit.path else doc for doc in state.documents)
                trial = replace(state, documents=docs, formal_documents=tuple(doc for doc in docs if not doc.is_draft))
                checked = validate_state(config, trial, base_ref=base_ref)
                if not any(
                    d.code.startswith(sensitive) and (d.path, d.code, d.message) not in initial
                    for d in checked.diagnostics
                ):
                    state = trial
                    previous = kept.get(edit.path)
                    kept[edit.path] = replace(
                        edit, rules=tuple(dict.fromkeys((*(previous.rules if previous else ()), *edit.rules)))
                    )
        candidate = state
        edits = tuple(kept.values())
        proposed = validate_state(config, candidate, base_ref=base_ref)
        applicable = bool(edits) or proposed.ok
    updates: dict[Path, bytes] = {}
    patch = ""
    if applicable or diff:
        updates = {config.root / edit.path: edit.after for edit in edits}
        if proposed.ok:
            index = expected_index_text(config, candidate).encode("utf-8")
            current = read_bytes(config.index_path) if exists(config.index_path) else None
            if current != index:
                updates[config.index_path] = index
    for path, after in updates.items():
        before = (snapshot or {}).get(path)
        if before is None:
            before = read_bytes(path) if exists(path) else b""
        patch += "".join(
            difflib.unified_diff(
                before.decode("utf-8").splitlines(keepends=True),
                after.decode("utf-8").splitlines(keepends=True),
                fromfile="a/" + config.relative_path(path),
                tofile="b/" + config.relative_path(path),
            )
        )
    if session is not None:
        snapshot.update(session.files)
    return ChangePlan(config, snapshot, original, proposed, edits, updates, applicable, patch)


def apply_plan(plan: ChangePlan) -> None:
    if not plan.applicable:
        raise ToolError(
            Diagnostic("proposal.fix.invalid-plan", "Candidate validation prevents this plan from being applied")
        )
    commit_files(plan.config, plan.updates, plan.before)


def check_project(
    config_path: Path | None = None,
    base_ref: str | None = None,
    *,
    fix: bool = False,
    diff: bool = False,
    select: str | None = None,
    partial: bool = False,
    fix_invocation: str = "zendev proposal check --fix",
) -> CheckReport:
    with markdown_session(), source_session():
        return _check_project(
            config_path, base_ref, fix=fix, diff=diff, select=select, partial=partial, fix_invocation=fix_invocation
        )


def _check_project(
    config_path: Path | None,
    base_ref: str | None,
    *,
    fix: bool,
    diff: bool,
    select: str | None,
    partial: bool,
    fix_invocation: str,
) -> CheckReport:
    config = load_config(config_path)
    selected = tuple(name.strip() for name in select.split(",")) if select is not None else RULES
    if not selected or any(name not in RULES for name in selected):
        raise ToolError(Diagnostic("proposal.fix.rule", "Select known repair rules: " + ", ".join(RULES)))
    if partial and not (fix or diff):
        raise ToolError(Diagnostic("proposal.fix.options", "--partial requires --fix or --diff"))
    if base_ref is not None:
        from zendev.proposal.history import resolve_base_ref

        base_ref = resolve_base_ref(config, base_ref)
    plan = plan_changes(config, base_ref=base_ref, selected=selected, partial=partial, diff=diff)
    result = plan.original
    index_state = "not-checked"
    fixed_files: list[str] = []
    if fix and not diff and plan.applicable:
        apply_plan(plan)
        fixed_files = [edit.path for edit in plan.edits]
        with source_session(fresh=True):
            result = validate_repository(config, base_ref=base_ref)
        if result.ok:
            index_state = "updated" if config.index_path in plan.updates else "up-to-date"
    diagnostics = list(result.diagnostics)
    if not diagnostics and not (fix and not diff):
        drift = check_index(config, result.state, fix_invocation=fix_invocation)
        if drift:
            diagnostics.append(drift)
            index_state = "drifted"
        else:
            index_state = "up-to-date"
    paths = {edit.path for edit in plan.edits}
    remaining = {(d.code, d.path) for d in plan.candidate.diagnostics}
    diagnostics = [
        replace(d, fixable=d.code == "proposal.index.drift" or (d.path in paths and (d.code, d.path) not in remaining))
        for d in diagnostics
    ]
    summary: dict[str, object] = {
        "formal_proposals": len(result.state.formal_documents),
        "drafts": result.state.draft_count,
        "index": index_state,
    }
    if fix or diff:
        summary.update(
            fixed_files=fixed_files,
            pending_files=[edit.path for edit in plan.edits if edit.path not in fixed_files],
            repairs=[
                {"path": edit.path, "rules": list(edit.rules), "reasons": [REASONS[rule] for rule in edit.rules]}
                for edit in plan.edits
            ],
            candidate_diagnostics=[d.as_dict() for d in plan.candidate.diagnostics],
            diff=plan.patch,
        )
    return CheckReport(tuple(diagnostics), summary, plan.patch if diff else "")
