"""Conformance tests for the Conventional Commits 1.0.0 parser."""

from __future__ import annotations

import pytest

from zendev.conventional import parse_conventional_commit


@pytest.mark.parametrize(
    "message",
    [
        "feat: allow provided config object to extend other configs\n\nBREAKING CHANGE: `extends` now composes configs",
        "feat!: send an email when a product is shipped",
        "feat(api)!: send an email when a product is shipped",
        "docs: correct spelling of CHANGELOG",
        "feat(lang): add Polish language",
        "REVERT: restore the previous parser",
        "security(auth): rotate signing keys",
    ],
)
def test_official_conventional_shapes_parse(message: str) -> None:
    parsed, issue = parse_conventional_commit(message)

    assert issue is None
    assert parsed is not None


def test_multi_paragraph_body_and_multiple_footers() -> None:
    parsed, issue = parse_conventional_commit(
        "fix: prevent racing of requests\n\n"
        "Introduce a request id and retain only the latest response.\n\n"
        "Remove obsolete timeouts.\n\n"
        "Reviewed-by: Z\n"
        "Refs: #123"
    )

    assert issue is None
    assert parsed is not None
    assert parsed.body == ("Introduce a request id and retain only the latest response.\n\nRemove obsolete timeouts.")
    assert [(footer.token, footer.value) for footer in parsed.footers] == [
        ("Reviewed-by", "Z"),
        ("Refs", "#123"),
    ]


def test_footer_hash_separator_and_multiline_value() -> None:
    parsed, issue = parse_conventional_commit("fix: repair parser\n\nRefs #123\nReviewed-by: Z\n  and Y")

    assert issue is None
    assert parsed is not None
    assert [(footer.token, footer.value) for footer in parsed.footers] == [
        ("Refs", "123"),
        ("Reviewed-by", "Z\n  and Y"),
    ]


@pytest.mark.parametrize("token", ["BREAKING CHANGE", "BREAKING-CHANGE"])
def test_breaking_footer_aliases(token: str) -> None:
    parsed, issue = parse_conventional_commit(f"feat: replace API\n\n{token}: use v2")

    assert issue is None
    assert parsed is not None
    assert parsed.is_breaking


def test_body_requires_blank_line_after_header() -> None:
    parsed, issue = parse_conventional_commit("feat: add export\nbody without a separator")

    assert parsed is None
    assert issue is not None
    assert issue.code == "missing-header-separator"
    assert issue.line == 2


@pytest.mark.parametrize(
    "message",
    [
        "feat add export",
        "feat(scope: add export",
        "feat(scope):",
        "✨ feat: emoji cannot precede a strict conventional header",
    ],
)
def test_invalid_conventional_headers(message: str) -> None:
    parsed, issue = parse_conventional_commit(message)

    assert parsed is None
    assert issue is not None
    assert issue.code == "invalid-conventional-header"
