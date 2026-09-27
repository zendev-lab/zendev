"""Message grammar, intention policy, and rendering contracts."""

import pytest

from zendev.message import (
    MessageDraft,
    MessageProfile,
    ZendevCommit,
    check_git_message,
    check_message,
    parse_message,
    render_message,
)
from zendev.message.conventional import ConventionalFooter
from zendev.message.policy import load_policy


@pytest.mark.parametrize("token_kind", ["emoji", "code"])
def test_catalog_pairs_parse_and_validate(token_kind: str) -> None:
    for intention in load_policy().intentions:
        for name in intention.types:
            token = getattr(intention.gitmoji, token_kind)
            suffix = "!" if intention.breaking else ""
            result = check_message(f"{token} {name}{suffix}: change project")
            assert result.ok, result.diagnostics
            assert isinstance(result.parsed, ZendevCommit)
            assert result.parsed.commit.header.type == name
            assert result.parsed.intention == intention.gitmoji


@pytest.mark.parametrize(
    "text",
    [
        "⬆️ deps: upgrade dependencies",
        "⬇️ deps: downgrade dependencies",
        "📌 deps: pin dependency",
        "\u2795 deps: add dependency",
        "\u2796 deps: remove dependency",
        "🎉 chore: begin project",
        "⚡ perf: improve query",
        "📦 build: package artifacts",
        "🧱 ci: configure infrastructure",
        "🧱 build: configure infrastructure",
        "💥 refactor!: replace API",
        "💥 refactor: replace API\n\nBREAKING CHANGE: migrate to v2",
        "✨ feat(scope with spaces): add export",
    ],
)
def test_semantic_examples(text: str) -> None:
    assert check_message(text).ok


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("⬆️ deps-up: upgrade", "message.type"),
        ("🎉 init: start", "message.type"),
        ("🐛 feat: wrong pair", "message.pair"),
        ("🚀 feat: deploy", "message.pair"),
        ("✨ fix: wrong pair", "message.pair"),
        ("💥 refactor: replace API", "message.breaking"),
        ("feat: no emoji", "message.missing-emoji"),
        ("😀 feat: unknown emoji", "message.missing-emoji"),
        ("✨  feat: spacing", "message.separator"),
        ("✨\nfeat: newline", "message.separator"),
    ],
)
def test_policy_errors_are_structured(text: str, code: str) -> None:
    result = check_message(text)
    assert not result.ok
    assert result.diagnostics[0].code == code


def test_syntax_and_policy_are_separate() -> None:
    assert isinstance(parse_message("⬆️ deps-up: upgrade").parsed, ZendevCommit)
    assert not check_message("⬆️ deps-up: upgrade").ok


@pytest.mark.parametrize(
    "text", ["✨ feat: ", "✨ feat:    ", "✨ feat(): missing scope", "✨ feat: add\nmissing blank"]
)
def test_invalid_syntax(text: str) -> None:
    assert not check_message(text).ok


@pytest.mark.parametrize("prefix", ["Merge ", "Revert ", "fixup! ", "squash! ", "amend! ", "reword! "])
def test_git_generated_messages_only_in_commit_context(prefix: str) -> None:
    assert check_git_message(prefix + "original message").ok
    assert not check_message(prefix + "original message").ok


def test_git_cleanup_is_explicit() -> None:
    text = "; template\n✨ feat: add feature\n\nBody\n; ------------------------ >8 ------------------------\nignored"
    result = check_git_message(text, comment_char=";")
    assert result.ok
    assert isinstance(result.parsed, ZendevCommit)
    assert result.parsed.commit.body == "Body"
    assert not check_message(text).ok


@pytest.mark.parametrize(
    ("profile", "draft"),
    [
        (
            MessageProfile.ZENDEV,
            MessageDraft("replace API", "refactor", "boom", "api", "Why", (ConventionalFooter("Refs", "#42"),), True),
        ),
        (
            MessageProfile.CONVENTIONAL,
            MessageDraft(
                "add feature",
                "custom",
                scope="api",
                footers=(ConventionalFooter("BREAKING CHANGE", "migration guide"),),
            ),
        ),
        (MessageProfile.GITMOJI, MessageDraft("Add feature", intention="sparkles", scope="api", body="Why")),
    ],
)
def test_rendered_drafts_round_trip(profile: MessageProfile, draft: MessageDraft) -> None:
    text = render_message(draft, profile=profile)
    assert check_message(text, profile=profile).ok
    assert draft.subject in text
    assert draft.scope in text
    assert draft.body in text


def test_generation_requires_explicit_intention() -> None:
    with pytest.raises(ValueError, match="explicit"):
        render_message(MessageDraft("update dependencies", "deps"))
    assert (
        render_message(MessageDraft("downgrade dependencies", "deps", "arrow-down")) == "⬇️ deps: downgrade dependencies"
    )


@pytest.mark.parametrize(
    "draft",
    [
        MessageDraft("subject\nother", "feat", "sparkles"),
        MessageDraft("", "feat", "sparkles"),
        MessageDraft("subject", "feat", "sparkles", "bad)scope"),
        MessageDraft("subject", "fix", "sparkles"),
    ],
)
def test_render_rejects_invalid_draft(draft: MessageDraft) -> None:
    with pytest.raises(ValueError):
        render_message(draft)


def test_profiles_keep_their_own_grammar() -> None:
    assert check_message("custom(api)!: replace API", profile="conventional").ok
    assert check_message(":sparkles: (api): Add feature", profile="gitmoji").ok
    assert not check_message("✨ feat: add feature", profile="conventional").ok
    assert not check_message("feat: add feature", profile="gitmoji").ok


@pytest.mark.parametrize(
    "footer",
    [ConventionalFooter("BAD TOKEN", "hi"), ConventionalFooter("Refs", ""), ConventionalFooter("Refs", "hi\n\nbody")],
)
def test_render_rejects_footers_that_would_become_body(footer: ConventionalFooter) -> None:
    with pytest.raises(ValueError, match="Footer"):
        render_message(MessageDraft("subject", "feat", "sparkles", footers=(footer,)))
