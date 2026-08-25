"""Tests for zendev.commit — emoji commit convention."""

from __future__ import annotations

import io
import re
from pathlib import Path

from typer.testing import CliRunner

from zendev.commit import (
    EMOJI_MAP,
    CommitProfile,
    ZendevAnswers,
    format_commit_convention_help_body,
    hook_app,
    is_valid_commit_message,
    message,
    report_invalid_commit_message,
    resolve_commit_profile,
    schema_pattern,
    suggest_commit_message,
    validate_commit_message,
)
from zendev.gitmoji import load_emoji_conventions

runner = CliRunner()


def _answers(
    prefix: str = "feat",
    scope: str = "",
    subject: str = "test",
    body: str = "",
    footer: str = "",
    is_breaking_change: bool = False,
) -> ZendevAnswers:
    return ZendevAnswers(
        prefix=prefix,
        scope=scope,
        subject=subject,
        body=body,
        footer=footer,
        is_breaking_change=is_breaking_change,
    )


class TestEmojiMap:
    """Tests for emoji mapping."""

    def test_all_gitmoji_intentions_have_unique_types_and_emojis(self) -> None:
        assert len(EMOJI_MAP) == 75
        assert len(set(EMOJI_MAP.values())) == 75

    def test_original_canonical_pairs_are_preserved(self) -> None:
        expected_pairs = {
            "init": "🎉",
            "feat": "✨",
            "fix": "🐛",
            "docs": "📝",
            "refactor": "♻️",
            "test": "✅",
            "ci": "👷",
            "perf": "⚡️",
            "chore": "🔧",
            "style": "🎨",
            "build": "📦️",
        }
        for type_name, emoji in expected_pairs.items():
            assert EMOJI_MAP[type_name] == emoji

    def test_emoji_values_are_nonempty(self) -> None:
        for type_name, emoji in EMOJI_MAP.items():
            assert len(emoji) > 0, f"{type_name} has empty emoji"


class TestMessage:
    """Tests for the message() function."""

    def test_message_format(self) -> None:
        msg = message(_answers(prefix="feat", subject="add dark mode"))
        assert msg == "\u2728 feat: add dark mode"

    def test_message_with_scope(self) -> None:
        msg = message(_answers(prefix="fix", scope="parser", subject="null pointer"))
        assert msg == "\U0001f41b fix(parser): null pointer"

    def test_message_with_body(self) -> None:
        msg = message(_answers(prefix="feat", subject="add export", body="supports CSV and JSON"))
        assert "\u2728 feat: add export" in msg
        assert "supports CSV and JSON" in msg

    def test_message_breaking_change(self) -> None:
        msg = message(_answers(subject="new API", footer="migration guide", is_breaking_change=True))
        assert "BREAKING CHANGE" in msg

    def test_message_supports_every_emoji_convention(self) -> None:
        for commit_type, emoji in EMOJI_MAP.items():
            assert message(_answers(prefix=commit_type)) == f"{emoji} {commit_type}: test"


class TestSchemaPattern:
    """Tests for the schema_pattern() function."""

    def test_schema_pattern_matches_valid(self) -> None:
        pattern = re.compile(schema_pattern())
        valid_messages = [
            "\u2728 feat: add feature",
            "\U0001f41b fix: resolve bug",
            "\U0001f4dd docs: update readme",
            "\u267b\ufe0f refactor(core): extract helper",
            "\U0001f389 init: begin project",
            ":tada: init: begin project",
            "\u26a1 perf: optimize query",
            "\U0001f527 chore: update deps",
            "🚀 deploy: publish package",
            ":rocket: deploy: publish package",
        ]
        for msg in valid_messages:
            assert pattern.match(msg), f"Pattern should match: {msg}"

    def test_schema_pattern_rejects_invalid(self) -> None:
        pattern = re.compile(schema_pattern())
        invalid_messages = [
            "random message",
            "feat add feature",
            "feat:",
        ]
        for msg in invalid_messages:
            assert not pattern.match(msg), f"Pattern should reject: {msg}"


class TestCommitMessageValidation:
    """Tests for reusable commit-msg validation."""

    def test_commit_message_without_emoji_is_rejected(self) -> None:
        assert not is_valid_commit_message("feat(parser): add streaming mode")

    def test_valid_commit_message_with_comments(self) -> None:
        commit_message = "✨ feat: add export\n\nbody line\n# Please enter the commit message"
        assert is_valid_commit_message(commit_message)

    def test_special_commit_messages_are_allowed(self) -> None:
        special_messages = [
            'Merge branch "main" into feature/test',
            'Revert "✨ feat: add export"',
            "fixup! ✨ feat: add export",
            "squash! 🐛 fix: repair parser",
        ]
        for commit_message in special_messages:
            assert is_valid_commit_message(commit_message), f"Expected special message to pass: {commit_message}"

    def test_invalid_commit_message_rejected(self) -> None:
        assert not is_valid_commit_message("ship it")

    def test_type_only_commit_message_rejected(self) -> None:
        assert not is_valid_commit_message("feat: add export")

    def test_suggest_commit_message_adds_missing_emoji(self) -> None:
        assert suggest_commit_message("feat(parser): add export") == "✨ feat(parser): add export"

    def test_suggest_commit_message_ignores_unstructured_text(self) -> None:
        assert suggest_commit_message("ship it") is None

    def test_conventional_profile_accepts_full_message_without_emoji(self) -> None:
        message = "feat(api)!: replace the response envelope\n\nBREAKING CHANGE: use v2"

        result = validate_commit_message(message, profile="conventional")

        assert result.valid
        assert result.profile is CommitProfile.CONVENTIONAL

    def test_gitmoji_profile_accepts_shortcode(self) -> None:
        result = validate_commit_message(":sparkles: (api): Add export support", profile="gitmoji")

        assert result.valid
        assert result.profile is CommitProfile.GITMOJI

    def test_profiles_do_not_claim_cross_spec_compatibility(self) -> None:
        assert not is_valid_commit_message("✨ feat: add export", profile="conventional")
        assert not is_valid_commit_message("feat: add export", profile="gitmoji")

    def test_autosquash_variants_are_allowed(self) -> None:
        assert is_valid_commit_message("amend! ✨ feat: add export")
        assert is_valid_commit_message("reword! ✨ feat: add export")

    def test_scissors_and_custom_comment_character_are_removed(self) -> None:
        message = "feat: add export\n\nBody\n; ------------------------ >8 ------------------------\n; ignored template"

        assert is_valid_commit_message(message, profile="conventional", comment_char=";")

    def test_profile_resolves_from_pyproject(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[tool.zendev.commit]\nprofile = "gitmoji"\n',
            encoding="utf-8",
        )

        assert resolve_commit_profile(start=tmp_path) is CommitProfile.GITMOJI


class TestEmojiEnforcement:
    """Tests that emoji prefix is strictly validated — guards against regression."""

    def test_all_canonical_emoji_type_pairs_accepted(self) -> None:
        """Every type must pass when paired with its canonical emoji."""
        for commit_type, emoji in EMOJI_MAP.items():
            msg = f"{emoji} {commit_type}: test subject"
            assert is_valid_commit_message(msg), f"Canonical pair should pass: {msg}"

    def test_every_canonical_shortcode_type_pair_is_accepted(self) -> None:
        for convention in load_emoji_conventions():
            msg = f"{convention.gitmoji.code} {convention.type}: test subject"
            assert is_valid_commit_message(msg), f"Canonical shortcode pair should pass: {msg}"

    def test_begin_project_example_is_canonical(self) -> None:
        assert is_valid_commit_message("🎉 init: begin a project")

    def test_variation_selector_aliases_are_accepted(self) -> None:
        assert is_valid_commit_message("⚡ perf: optimize query")
        assert is_valid_commit_message("📦 build: package artifacts")

    def test_token_requires_exactly_one_space_before_type(self) -> None:
        assert not is_valid_commit_message("🎉  init: begin a project")
        assert not is_valid_commit_message("🎉\ninit: begin a project")
        assert not is_valid_commit_message(":tada:  init: begin a project")

    def test_non_emoji_prefix_rejected(self) -> None:
        """An arbitrary non-emoji token before the type must be rejected."""
        assert not is_valid_commit_message("X feat: add feature")
        assert not is_valid_commit_message("abc fix: resolve bug")
        assert not is_valid_commit_message("123 docs: update readme")

    def test_wrong_emoji_for_type_rejected(self) -> None:
        """The emoji must match the type — swapped pairs are invalid."""
        assert not is_valid_commit_message("🐛 feat: wrong emoji")  # 🐛 is fix, not feat
        assert not is_valid_commit_message("✨ fix: wrong emoji")  # ✨ is feat, not fix
        assert not is_valid_commit_message("🎉 docs: wrong emoji")  # 🎉 is init, not docs

    def test_schema_pattern_rejects_unknown_emoji(self) -> None:
        """An emoji not in EMOJI_MAP must not match the strict pattern."""
        pattern = re.compile(schema_pattern())
        assert not pattern.match("😀 feat: unknown emoji")
        assert not pattern.match("🫠 fix: unknown emoji")

    def test_schema_pattern_rejects_known_but_wrong_pair(self) -> None:
        pattern = re.compile(schema_pattern())
        assert not pattern.match("🚀 feat: wrong pair")
        assert not pattern.match(":rocket: feat: wrong pair")

    def test_schema_pattern_relaxed_mode_still_accepts_missing_emoji(self) -> None:
        """require_emoji=False allows omitting the prefix entirely."""
        pattern = re.compile(schema_pattern(require_emoji=False))
        assert pattern.match("feat: add feature")
        assert pattern.match("fix(core): resolve bug")

    def test_suggest_adds_correct_emoji_for_each_type(self) -> None:
        """suggest_commit_message should propose the canonical emoji for every type."""
        for commit_type, emoji in EMOJI_MAP.items():
            bare = f"{commit_type}: test subject"
            suggestion = suggest_commit_message(bare)
            assert suggestion is not None, f"Should suggest for: {bare}"
            assert suggestion.startswith(f"{emoji} {commit_type}:"), (
                f"Suggestion should start with canonical emoji: got {suggestion!r}"
            )

    def test_hook_rejects_wrong_emoji(self, tmp_path: Path) -> None:
        """commit-msg hook must reject a message with wrong emoji pairing."""
        commit_file = tmp_path / "COMMIT_EDITMSG"
        commit_file.write_text("🐛 feat: wrong emoji for feat type", encoding="utf-8")
        result = runner.invoke(hook_app, [str(commit_file)])

        assert result.exit_code == 1


class TestSharedCommitHelp:
    """Shared helpers for hook and CI."""

    def test_format_commit_convention_help_body_covers_all_types(self) -> None:
        body = format_commit_convention_help_body()
        assert "Type table:" in body
        assert "Merge, Revert, fixup!" in body
        for name, emoji in EMOJI_MAP.items():
            assert emoji in body
            assert name in body

    def test_report_invalid_commit_message_ci_includes_error_annotation(self) -> None:
        buf = io.StringIO()
        report_invalid_commit_message("ship it", context="ci", file=buf)
        out = buf.getvalue()
        assert "::error::" in out
        assert "Received: 'ship it'" in out


class TestCommitMsgHook:
    """Tests for commit-msg hook CLI behavior."""

    def test_commit_msg_hook_accepts_valid_message(self, tmp_path: Path) -> None:
        commit_file = tmp_path / "COMMIT_EDITMSG"
        commit_file.write_text("✨ feat: add export", encoding="utf-8")

        result = runner.invoke(hook_app, [str(commit_file)])

        assert result.exit_code == 0

    def test_commit_msg_hook_rejects_invalid_message(self, tmp_path: Path) -> None:
        commit_file = tmp_path / "COMMIT_EDITMSG"
        commit_file.write_text("ship it", encoding="utf-8")

        result = runner.invoke(hook_app, [str(commit_file)])

        assert result.exit_code == 1
        assert "Invalid commit message." in result.stderr
        assert "Type table:" in result.stderr

    def test_commit_msg_hook_rejects_missing_emoji(self, tmp_path: Path) -> None:
        commit_file = tmp_path / "COMMIT_EDITMSG"
        commit_file.write_text("feat: add export", encoding="utf-8")

        result = runner.invoke(hook_app, [str(commit_file)])

        assert result.exit_code == 1
        assert "An emoji prefix is required." in result.stderr
        assert "Maybe you meant: `✨ feat: add export`." in result.stderr

    def test_commit_msg_hook_uses_explicit_conventional_profile(self, tmp_path: Path) -> None:
        commit_file = tmp_path / "COMMIT_EDITMSG"
        commit_file.write_text("feat: add export", encoding="utf-8")

        result = runner.invoke(hook_app, ["--profile", "conventional", str(commit_file)])

        assert result.exit_code == 0

    def test_commit_msg_hook_loads_profile_from_pyproject(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[tool.zendev.commit]\nprofile = "gitmoji"\n',
            encoding="utf-8",
        )
        commit_file = tmp_path / "COMMIT_EDITMSG"
        commit_file.write_text(":sparkles: Add export", encoding="utf-8")

        result = runner.invoke(hook_app, [str(commit_file)])

        assert result.exit_code == 0

    def test_commit_msg_hook_reports_invalid_repository_config(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[tool.zendev.commit\n", encoding="utf-8")
        commit_file = tmp_path / "COMMIT_EDITMSG"
        commit_file.write_text("✨ feat: add export", encoding="utf-8")

        result = runner.invoke(hook_app, [str(commit_file)])

        assert result.exit_code == 2
        assert "failed to load commit profile" in result.output
