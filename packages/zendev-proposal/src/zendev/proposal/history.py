"""Git baseline loading and proposal lifecycle comparisons."""

from __future__ import annotations

import subprocess
from pathlib import Path

from zendev.core.diagnostics import ToolError
from zendev.proposal.model import Diagnostic, ProposalConfig, RepositoryState
from zendev.proposal.repository import extract_frontmatter, parse_frontmatter
from zendev.proposal.shape import formal_filename_pattern


def _git(config: ProposalConfig, *arguments: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *arguments],
            cwd=config.root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        raise ToolError(
            Diagnostic(
                code="proposal.history.git",
                message=f"failed to invoke Git: {error}",
            )
        ) from error


def _metadata_at_ref(config: ProposalConfig, ref: str, relative_path: str) -> dict[str, object]:
    prefix = _git(config, "rev-parse", "--show-prefix").stdout.strip()
    result = _git(config, "show", f"{ref}:{prefix}{relative_path}")
    if result.returncode != 0:
        raise ToolError(
            Diagnostic(
                code="proposal.history.git",
                path=relative_path,
                message=f"failed to read proposal at the Git base: {result.stderr.strip()}",
            )
        )
    try:
        raw, _ = extract_frontmatter(result.stdout, relative_path)
        return parse_frontmatter(raw, relative_path)
    except ValueError as error:
        raise ToolError(
            Diagnostic(
                code="proposal.history.frontmatter",
                path=relative_path,
                message=f"invalid frontmatter at the Git base: {error}",
            )
        ) from error


def _waived(config: ProposalConfig, path: str, previous: str, current: str) -> bool:
    policy = config.history
    assert policy is not None
    return any(
        waiver.path == path and waiver.from_status == previous and waiver.to_status == current
        for waiver in policy.waivers
    )


def validate_history(
    config: ProposalConfig,
    state: RepositoryState,
    base_ref: str,
    diagnostics: list[Diagnostic],
) -> None:
    policy = config.history
    if policy is None:
        raise ToolError(
            Diagnostic(
                code="proposal.history.disabled",
                path=config.relative_path(config.config_path),
                message="`--base-ref` requires a `[history]` policy",
            )
        )
    resolved = _git(config, "rev-parse", "--verify", "--end-of-options", f"{base_ref}^{{commit}}")
    if resolved.returncode != 0:
        raise ToolError(
            Diagnostic(
                code="proposal.history.base-ref",
                message=f"Git base ref does not exist: {base_ref}",
                hint="Fetch the base ref or pass an exact locally available ref.",
            )
        )
    base_commit = resolved.stdout.strip()

    documents_relative = config.relative_path(config.documents_dir)
    tree = _git(config, "ls-tree", "-r", "--name-only", base_commit, "--", documents_relative)
    if tree.returncode != 0:
        raise ToolError(
            Diagnostic(
                code="proposal.history.git",
                message=f"failed to read proposal tree at {base_ref}: {tree.stderr.strip()}",
            )
        )
    pattern = formal_filename_pattern(config)
    old_paths = {line for line in tree.stdout.splitlines() if pattern.fullmatch(Path(line).name) is not None}
    current_by_path = {document.relative_path: document for document in state.formal_documents}
    if policy.protect_records:
        for deleted in sorted(old_paths - set(current_by_path)):
            diagnostics.append(
                Diagnostic(
                    code="proposal.history.deleted",
                    path=deleted,
                    message="formal proposal records must not be deleted",
                )
            )

    previous_by_path = {path: _metadata_at_ref(config, base_commit, path) for path in old_paths}
    old_number_paths: dict[int, str] = {}
    for path, metadata in previous_by_path.items():
        number = metadata.get(config.number_field)
        if isinstance(number, int) and not isinstance(number, bool):
            old_number_paths[number] = path

    for waiver in policy.waivers:
        previous = previous_by_path.get(waiver.path, {})
        current = current_by_path.get(waiver.path)
        if (
            previous.get(config.status_field) != waiver.from_status
            or current is None
            or current.metadata.get(config.status_field) != waiver.to_status
        ):
            diagnostics.append(
                Diagnostic(
                    code="proposal.history.unused-waiver",
                    path=waiver.path,
                    message="waiver does not match the requested base transition",
                )
            )

    for document in state.formal_documents:
        number = document.number(config)
        if number is not None:
            previous_path = old_number_paths.get(number)
            if previous_path is not None and previous_path != document.relative_path:
                diagnostics.append(
                    Diagnostic(
                        code="proposal.history.number-reused",
                        path=document.relative_path,
                        message=(
                            f"{config.format_identifier(number)} was already assigned to {previous_path} at {base_ref}"
                        ),
                    )
                )

        previous = previous_by_path.get(document.relative_path)
        current_status = document.metadata.get(config.status_field)
        if previous is None:
            if number not in policy.bootstrap_numbers and current_status != policy.initial_status:
                diagnostics.append(
                    Diagnostic(
                        code="proposal.history.initial-status",
                        path=document.relative_path,
                        message=(f"new proposals must begin in `{policy.initial_status}`; found `{current_status}`"),
                    )
                )
            continue
        previous_status = previous.get(config.status_field)
        if not isinstance(previous_status, str) or not isinstance(current_status, str):
            continue
        allowed = policy.transitions.get(previous_status, frozenset())
        if current_status not in allowed and not _waived(
            config, document.relative_path, previous_status, current_status
        ):
            diagnostics.append(
                Diagnostic(
                    code="proposal.history.invalid-transition",
                    path=document.relative_path,
                    message=f"invalid status transition `{previous_status}` -> `{current_status}`",
                )
            )


def resolve_base_ref(config: ProposalConfig, ref: str) -> str:
    result = _git(config, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}")
    if result.returncode:
        raise ToolError(
            Diagnostic("proposal.history.git", "Cannot resolve the requested Git baseline: " + result.stderr.strip())
        )
    return result.stdout.strip()
