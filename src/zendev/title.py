"""CLI entry point for validating PR titles in CI."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from zendev.commit import (
    CommitProfile,
    normalize_commit_message,
    report_invalid_commit_message,
    resolve_commit_profile,
    validate_commit_message,
)


def validate_title_cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="zendev-validate-title",
        description="Validate a PR title against a configured commit profile.",
    )
    parser.add_argument(
        "--profile",
        choices=("auto", *(profile.value for profile in CommitProfile)),
        default="auto",
        help="Validation profile; auto reads [tool.zendev.commit] and falls back to zendev.",
    )
    parser.add_argument("text", help="PR title text to validate.")
    args = parser.parse_args(argv)

    try:
        selected = resolve_commit_profile(args.profile)
    except ValueError as error:
        parser.error(str(error))

    normalized = normalize_commit_message(args.text)
    print("::group::PR / title check")
    print(f"Text: {normalized!r}")
    print("::endgroup::")

    result = validate_commit_message(normalized, profile=selected)
    if result.valid:
        print("Title format is valid.")
        return 0

    report_invalid_commit_message(
        normalized,
        context="ci",
        file=sys.stdout,
        profile=selected,
        result=result,
    )
    return 1


def main() -> None:
    sys.exit(validate_title_cli())
