"""Conformance tests for the Conventional Commits 1.0.0 parser."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from zendev.message.conventional import parse_conventional_commit

words = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789更新修复", min_size=1, max_size=40
)


@given(kind=words, scope=st.one_of(st.none(), words), description=words, breaking=st.booleans())
def test_header_fields_survive_parsing(kind: str, scope: str | None, description: str, breaking: bool) -> None:
    subject = kind + (f"({scope})" if scope is not None else "") + ("!" if breaking else "") + f": {description}"
    parsed, issue = parse_conventional_commit(subject)

    assert issue is None
    assert parsed is not None
    assert (parsed.header.type, parsed.header.scope, parsed.header.description) == (kind, scope, description)
    assert parsed.header.breaking is breaking
    assert parsed.is_breaking is breaking
    assert parsed.body is None
    assert parsed.footers == ()


@given(body=words, values=st.lists(words, min_size=1, max_size=8), ending=st.sampled_from(["\n", "\r\n"]))
def test_body_and_ordered_footers_survive_parsing(body: str, values: list[str], ending: str) -> None:
    lines = ["fix: preserve text", "", body, "", *[f"Refs: {value}" for value in values], "", ""]
    parsed, issue = parse_conventional_commit(ending.join(lines))

    assert issue is None
    assert parsed is not None
    assert parsed.body == body
    assert [(footer.token, footer.value) for footer in parsed.footers] == [("Refs", value) for value in values]
    assert not parsed.is_breaking


@pytest.mark.parametrize("text", ["", "\n", "\r\n"])
def test_empty_messages_report_empty_message(text: str) -> None:
    parsed, issue = parse_conventional_commit(text)
    assert parsed is None
    assert issue is not None
    assert issue.code == "empty-message"
    assert issue.message


@pytest.mark.parametrize("text", ["feat:   ", "feat: \t"])
def test_whitespace_is_not_a_description(text: str) -> None:
    parsed, issue = parse_conventional_commit(text)
    assert parsed is None
    assert issue is not None
    assert issue.code == "invalid-conventional-header"
    assert issue.message


@pytest.mark.parametrize(
    "body", ["Body without a footer", "First paragraph.\n\nSecond paragraph.", "Refs: #1\n\nMore body."]
)
def test_body_without_a_final_footer_block_is_preserved(body: str) -> None:
    parsed, issue = parse_conventional_commit(f"fix: retain body\n\n{body}\n\n")
    assert issue is None
    assert parsed is not None
    assert parsed.body == body
    assert parsed.footers == ()


def test_multiline_footer_preceding_another_footer() -> None:
    parsed, issue = parse_conventional_commit("fix: retain footers\n\nReviewed-by: Z\n  and Y\nRefs: #42")
    assert issue is None
    assert parsed is not None
    assert [(footer.token, footer.value) for footer in parsed.footers] == [
        ("Reviewed-by", "Z\n  and Y"),
        ("Refs", "#42"),
    ]


def test_extra_separator_before_footers_does_not_create_a_body() -> None:
    parsed, issue = parse_conventional_commit("fix: retain footers\n\n\nRefs: #42")
    assert issue is None
    assert parsed is not None
    assert parsed.body is None
    assert [(footer.token, footer.value) for footer in parsed.footers] == [("Refs", "#42")]


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
    assert issue.message
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
