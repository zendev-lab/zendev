"""Command-line interface for repository-native proposal checks."""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

import typer

from zendev.proposal.config import load_config
from zendev.proposal.indexing import check_index, write_index
from zendev.proposal.model import Diagnostic, ProposalToolError, RepositoryState
from zendev.proposal.validation import validate_repository

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
        summary=None,
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
) -> int:
    try:
        config = load_config(config_path)
        result = validate_repository(config, base_ref=base_ref)
        diagnostics = list(result.diagnostics)
        index_state = "not-checked"
        changed = False
        if not diagnostics:
            if fix:
                changed = write_index(config, result.state)
                index_state = "updated" if changed else "up-to-date"
            else:
                drift = check_index(config, result.state, fix_invocation=fix_invocation)
                if drift is not None:
                    diagnostics.append(drift)
                    index_state = "drifted"
                else:
                    index_state = "up-to-date"
    except ProposalToolError as error:
        return _emit_tool_error(command="check", error=error, json_output=json_output)

    summary = _summary(result.state, index_state=index_state)
    validated = (
        f"Validated {summary['formal_proposals']} formal proposal(s), "
        f"{summary['drafts']} draft(s), and the committed index."
    )
    _emit(
        command="check",
        diagnostics=diagnostics,
        summary=summary,
        json_output=json_output,
        success_message="Updated the proposal index." if changed else validated,
    )
    return 1 if diagnostics else 0


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
        typer.Option("--fix", help="Write the deterministic index when proposals are valid."),
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
    )
    if exit_code:
        raise typer.Exit(code=exit_code)


def main() -> None:
    app(prog_name="zendev-proposal")


if __name__ == "__main__":
    raise SystemExit(main())
