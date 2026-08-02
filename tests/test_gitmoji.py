"""Tests for the vendored official gitmoji profile."""

from __future__ import annotations

import pytest

from zendev.gitmoji import load_emoji_conventions, load_gitmojis, parse_gitmoji_commit


def test_catalog_is_complete_and_unique() -> None:
    catalog = load_gitmojis()

    assert len(catalog) == 75
    assert len({item.emoji for item in catalog}) == len(catalog)
    assert len({item.code for item in catalog}) == len(catalog)


def test_emoji_convention_covers_catalog_with_unique_types() -> None:
    conventions = load_emoji_conventions()

    assert len(conventions) == 75
    assert {item.gitmoji for item in conventions} == set(load_gitmojis())
    assert len({item.type for item in conventions}) == len(conventions)
    assert next(item for item in conventions if item.gitmoji.name == "tada").type == "init"


@pytest.mark.parametrize("token_kind", ["emoji", "code"])
def test_every_official_intention_parses(token_kind: str) -> None:
    for gitmoji in load_gitmojis():
        token = getattr(gitmoji, token_kind)
        parsed, issue = parse_gitmoji_commit(f"{token} Improve the project")

        assert issue is None, token
        assert parsed is not None, token
        assert parsed.intention == gitmoji


def test_unicode_without_variation_selector_is_accepted() -> None:
    parsed, issue = parse_gitmoji_commit("⚡ Improve performance")

    assert issue is None
    assert parsed is not None
    assert parsed.intention.code == ":zap:"


@pytest.mark.parametrize(
    ("message", "expected_scope"),
    [
        ("♻️ (components): Transform classes to hooks", "components"),
        (":wheelchair: (account) Improve modal accessibility", "account"),
        ("📈 Add analytics to the dashboard", None),
    ],
)
def test_official_gitmoji_shapes(message: str, expected_scope: str | None) -> None:
    parsed, issue = parse_gitmoji_commit(message)

    assert issue is None
    assert parsed is not None
    assert parsed.scope == expected_scope


def test_gitmoji_message_allows_a_body() -> None:
    parsed, issue = parse_gitmoji_commit("✨ Add export support\n\nSupports CSV and JSON.")

    assert issue is None
    assert parsed is not None
    assert parsed.body == "Supports CSV and JSON."


@pytest.mark.parametrize(
    ("message", "issue_code"),
    [
        ("💡unknown Add comments", "invalid-gitmoji"),
        ("✨", "invalid-gitmoji"),
        ("✨   ", "missing-gitmoji-message"),
        ("✨ () Add comments", "invalid-gitmoji-scope"),
        ("✨ (core)Add comments", "invalid-gitmoji-separator"),
        ("✨ (core):Add comments", "invalid-gitmoji-separator"),
        ("✨ :Add comments", "invalid-gitmoji-separator"),
        ("✨ Add comments\nwithout a blank line", "missing-header-separator"),
    ],
)
def test_invalid_gitmoji_messages(message: str, issue_code: str) -> None:
    parsed, issue = parse_gitmoji_commit(message)

    assert parsed is None
    assert issue is not None
    assert issue.code == issue_code
