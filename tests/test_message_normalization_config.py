"""Explicit repository policy for non-Conventional normalization exceptions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from zendev.core.diagnostics import ToolError
from zendev.message import normalize_message
from zendev.message.cli import app
from zendev.message.config import load_message_config

CONFIG = Path(__file__).parent / "fixtures/message/normalization.toml"
ORIGINAL = "[ImgBot] Optimize images"
REPLACEMENT = "⚡️ perf(assets): optimize images"


def test_non_conventional_title_requires_an_explicit_mapping() -> None:
    absent = normalize_message(ORIGINAL)
    assert not absent.ok
    assert absent.text == ORIGINAL
    settings = load_message_config(CONFIG)
    configured = normalize_message(ORIGINAL, replacements=settings.replacements)
    assert configured.ok
    assert configured.text == REPLACEMENT


@pytest.mark.parametrize(
    "text", ["[ImgBot] optimize images", "[ImgBot] Optimize images ", "[ImgBot] Optimize images now"]
)
def test_exceptions_match_the_complete_case_sensitive_subject(text: str) -> None:
    result = normalize_message(text, replacements={ORIGINAL: REPLACEMENT})
    assert not result.ok
    assert result.text == text


def test_exception_has_priority_over_default_conventional_conversion() -> None:
    result = normalize_message(
        "fix: adjust formatting", replacements={"fix: adjust formatting": "🎨 style: adjust formatting"}
    )
    assert result.text == "🎨 style: adjust formatting"


def test_valid_messages_are_never_rewritten_by_exceptions() -> None:
    title = "🐛 fix: handle failure"
    result = normalize_message(title, replacements={title: "🚑 fix: handle failure"})
    assert result.ok
    assert not result.changed
    assert result.text == title


def test_replacements_are_applied_once_and_preserve_the_rest_of_the_commit() -> None:
    text = "# comment\r\n" + ORIGINAL + "\r\n\r\nBody  \r\n\r\nRefs: #12\r\n"
    result = normalize_message(text, commit=True, replacements={ORIGINAL: REPLACEMENT, REPLACEMENT: "📝 docs: other"})
    assert result.text == text.replace(ORIGINAL, REPLACEMENT)
    assert not normalize_message(result.text, commit=True, replacements={ORIGINAL: REPLACEMENT}).changed


@pytest.mark.parametrize("profile", ["conventional", "gitmoji"])
def test_exceptions_only_apply_to_the_zendev_profile(profile: str) -> None:
    result = normalize_message(ORIGINAL, profile=profile, replacements={ORIGINAL: REPLACEMENT})
    assert not result.changed
    assert result.text == ORIGINAL


def test_exception_cannot_hide_a_malformed_commit_body() -> None:
    text = ORIGINAL + "\nMissing the required blank line"
    result = normalize_message(text, replacements={ORIGINAL: REPLACEMENT})
    assert not result.ok
    assert result.text == text


@pytest.mark.parametrize(
    "replacement", ["perf: optimize images", "🐛 feat: wrong pair", "✨ feat: title\n\nInjected body"]
)
def test_pure_api_rejects_invalid_or_multiline_replacements(replacement: str) -> None:
    result = normalize_message(ORIGINAL, replacements={ORIGINAL: replacement})
    assert not result.ok
    assert result.text == ORIGINAL


@pytest.mark.parametrize("embedded", [False, True])
def test_cli_uses_the_same_toml_rules_for_hints_and_fixes(tmp_path: Path, embedded: bool) -> None:
    content = CONFIG.read_text(encoding="utf-8")
    if embedded:
        content = "[tool.zendev]\n" + content.replace("[message.", "[tool.zendev.message.")
    config = tmp_path / ("pyproject.toml" if embedded else "zendev.toml")
    config.write_text(content, encoding="utf-8")
    args = ["check", "--title", "--text", ORIGINAL, "--config", str(config), "--format", "json"]
    runner = CliRunner()
    hint = runner.invoke(app, args)
    assert hint.exit_code == 1
    diagnostic = json.loads(hint.stdout)["diagnostics"][0]
    assert diagnostic["fixable"]
    assert REPLACEMENT in diagnostic["hint"]
    fixed = runner.invoke(app, [*args, "--fix"])
    assert fixed.exit_code == 0
    assert json.loads(fixed.stdout)["summary"]["text"] == REPLACEMENT


@pytest.mark.parametrize(
    "table",
    [
        'normalization = "invalid"',
        "normalization = { unknown = true }",
        "normalization = { replacements = [] }",
        'normalization = { replacements = { "" = "✨ feat: valid" } }',
        'normalization = { replacements = { " " = "✨ feat: valid" } }',
        'normalization = { replacements = { "source" = 42 } }',
        'normalization = { replacements = { "source" = "perf: no emoji" } }',
        'normalization = { replacements = { "source" = "🐛 feat: wrong pair" } }',
        'normalization = { replacements = { "source" = "✨ feat: first\\nsecond" } }',
        'normalization = { replacements = { "first\\nsecond" = "✨ feat: valid" } }',
    ],
)
def test_invalid_rule_configuration_fails_even_when_the_title_does_not_match(tmp_path: Path, table: str) -> None:
    config = tmp_path / "zendev.toml"
    config.write_text("version = 1\n[message]\n" + table + "\n", encoding="utf-8")
    with pytest.raises(ToolError):
        load_message_config(config)
    result = CliRunner().invoke(
        app, ["check", "--title", "--fix", "--text", "✨ feat: already valid", "--config", str(config)]
    )
    assert result.exit_code == 2
