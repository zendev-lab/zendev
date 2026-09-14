"""Command-line interface for repository-native proposal checks."""

from __future__ import annotations

import difflib
import json
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Annotated

import typer

from zendev.proposal.config import load_config
from zendev.proposal.indexing import check_index, expected_index_text
from zendev.proposal.model import Diagnostic, ProposalToolError, RepositoryState
from zendev.proposal.repair import REASONS, RULES, plan_repairs
from zendev.proposal.transaction import commit_files, snapshot_inputs
from zendev.proposal.validation import validate_repository, validate_state

JSON_SCHEMA_VERSION = 1

app = typer.Typer(
    name="zendev-proposal",
    add_completion=False,
    help="Validate repository-native proposals.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
)


@app.callback()
def _proposal() -> None:
    """Validate repository-native proposals."""


def _summary(state: RepositoryState, *, index_state: str) -> dict[str, object]:
    return {
        "formal_proposals": len(state.formal_documents),
        "drafts": state.draft_count,
        "index": index_state,
    }


def _human_diagnostic(diagnostic: Diagnostic) -> str:
    location = diagnostic.path or "proposal"
    if diagnostic.line is not None:
        location += f":{diagnostic.line}"
    rendered = f"{location}: {diagnostic.code}: {diagnostic.message}"
    if diagnostic.hint is not None:
        rendered += f"\n  hint: {diagnostic.hint}"
    return rendered


def _emit(
    *,
    command: str,
    diagnostics: Sequence[Diagnostic],
    summary: dict[str, object] | None,
    json_output: bool,
    success_message: str | None = None,
) -> None:
    if json_output:
        print(
            json.dumps(
                {
                    "schema_version": JSON_SCHEMA_VERSION,
                    "command": command,
                    "ok": not diagnostics,
                    "diagnostics": [diagnostic.as_dict() for diagnostic in diagnostics],
                    "summary": summary,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return
    if diagnostics:
        for diagnostic in diagnostics:
            print(_human_diagnostic(diagnostic), file=sys.stderr)
        return
    if success_message is not None:
        print(success_message)


def _emit_tool_error(*, command: str, error: ProposalToolError, json_output: bool) -> int:
    _emit(
        command=command,
        diagnostics=[error.diagnostic],
        summary=error.summary,
        json_output=json_output,
    )
    return 2


def _check(
    config_path: Path,
    base_ref: str | None,
    *,
    json_output: bool,
    fix: bool,
    fix_invocation: str,
    diff: bool = False,
    select: str | None = None,
    partial: bool = False,
) -> int:
    try:
        config = load_config(config_path)
        selected = tuple(name.strip() for name in select.split(",")) if select is not None else RULES
        if any(name not in RULES for name in selected) or not selected:
            raise ProposalToolError(
                Diagnostic(code="proposal.fix.rule", message="select known repair rules: " + ", ".join(RULES))
            )
        if partial and not (fix or diff):
            raise ProposalToolError(
                Diagnostic(code="proposal.fix.options", message="--partial requires --fix or --diff")
            )
        snapshot = snapshot_inputs(config) if fix or diff else None
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
                    trial = replace(
                        state, documents=docs, formal_documents=tuple(doc for doc in docs if not doc.is_draft)
                    )
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
        fixed_files: list[str] = []
        updates: dict[Path, bytes] = {}
        patch = ""
        if applicable or diff:
            updates = {config.root / edit.path: edit.after for edit in edits}
            if proposed.ok:
                index = expected_index_text(config, candidate).encode("utf-8")
                current = config.index_path.read_bytes() if config.index_path.exists() else None
                if current != index:
                    updates[config.index_path] = index
        for path, after in updates.items():
            before = (snapshot or {}).get(path)
            if before is None:
                before = path.read_bytes() if path.exists() else b""
            patch += "".join(
                difflib.unified_diff(
                    before.decode("utf-8").splitlines(keepends=True),
                    after.decode("utf-8").splitlines(keepends=True),
                    fromfile="a/" + config.relative_path(path),
                    tofile="b/" + config.relative_path(path),
                )
            )
        result = original
        index_state = "not-checked"
        if fix and not diff and applicable:
            assert snapshot is not None
            commit_files(config, updates, snapshot)
            fixed_files = [edit.path for edit in edits]
            result = validate_repository(config, base_ref=base_ref)
            if result.ok:
                index_state = "updated" if config.index_path in updates else "up-to-date"
        diagnostics = list(result.diagnostics)
        if not diagnostics and not (fix and not diff):
            drift = check_index(config, result.state, fix_invocation=fix_invocation)
            if drift:
                diagnostics.append(drift)
                index_state = "drifted"
            else:
                index_state = "up-to-date"
        paths = {edit.path for edit in edits}
        remaining = {(d.code, d.path) for d in proposed.diagnostics}
        diagnostics = [
            replace(
                d, fixable=d.code == "proposal.index.drift" or (d.path in paths and (d.code, d.path) not in remaining)
            )
            for d in diagnostics
        ]
        summary = _summary(result.state, index_state=index_state)
        if fix or diff:
            summary.update(
                fixed_files=fixed_files,
                pending_files=[edit.path for edit in edits if edit.path not in fixed_files],
                repairs=[
                    {"path": edit.path, "rules": list(edit.rules), "reasons": [REASONS[rule] for rule in edit.rules]}
                    for edit in edits
                ],
                candidate_diagnostics=[d.as_dict() for d in proposed.diagnostics],
                diff=patch,
            )
        if not json_output:
            if diff:
                print(patch, end="")
            elif fixed_files:
                print("Repaired proposal sources: " + ", ".join(fixed_files))
            if edits and not applicable:
                print("Candidate repairs were not applied because validation still fails.", file=sys.stderr)
        _emit(
            command="check",
            diagnostics=diagnostics,
            summary=summary,
            json_output=json_output,
            success_message="Updated the proposal index."
            if index_state == "updated"
            else (
                f"Validated {len(result.state.formal_documents)} formal proposal(s), "
                f"{result.state.draft_count} draft(s), and the committed index."
            ),
        )
        return 1 if diagnostics else 0
    except ProposalToolError as error:
        return _emit_tool_error(command="check", error=error, json_output=json_output)
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError) as error:
        return _emit_tool_error(
            command="check",
            error=ProposalToolError(Diagnostic(code="proposal.environment", message=str(error))),
            json_output=json_output,
        )


@app.command("check")
def check_command(
    ctx: typer.Context,
    config: Annotated[
        Path,
        typer.Option("--config", metavar="PATH", help="Proposal TOML policy."),
    ] = Path("proposal.toml"),
    base_ref: Annotated[
        str | None,
        typer.Option(
            "--base-ref",
            envvar="PROPOSAL_BASE_REF",
            help="Exact local Git ref used to validate lifecycle history.",
        ),
    ] = None,
    fix: Annotated[
        bool,
        typer.Option("--fix", help="Repair deterministic source omissions and update the index after validation."),
    ] = False,
    diff: Annotated[bool, typer.Option("--diff", help="Preview repairs without writing, even with --fix.")] = False,
    select: Annotated[str | None, typer.Option("--select", help="Comma-separated repair rule names.")] = None,
    partial: Annotated[
        bool, typer.Option("--partial", help="Apply independent safe repairs while retaining remaining errors.")
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit stable JSON diagnostics."),
    ] = False,
) -> None:
    """Validate proposals, history, graph, and the committed index."""

    invocation = ctx.command_path.strip() or "zendev-proposal check"
    exit_code = _check(
        config,
        base_ref,
        json_output=json_output,
        fix=fix,
        fix_invocation=f"{invocation} --fix",
        diff=diff,
        select=select,
        partial=partial,
    )
    if exit_code:
        raise typer.Exit(code=exit_code)


def main() -> None:
    app(prog_name="zendev-proposal")


if __name__ == "__main__":
    raise SystemExit(main())
