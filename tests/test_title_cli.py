"""Tests for the zendev-validate-title CLI."""

from __future__ import annotations

from typer.testing import CliRunner

from zendev.message.cli import app

runner = CliRunner()


def test_validate_title_cli_accepts_valid_title() -> None:
    result = runner.invoke(app, ["check", "--title", "--text", "✨ feat: add portable action"])

    assert result.exit_code == 0
    assert "Check passed." in result.output


def test_validate_title_cli_rejects_invalid_title() -> None:
    result = runner.invoke(app, ["check", "--title", "--text", "feat: missing emoji"])

    assert result.exit_code == 1
    assert "message.missing-emoji" in result.output


def test_validate_title_cli_supports_conventional_profile() -> None:
    result = runner.invoke(app, ["check", "--title", "--profile", "conventional", "--text", "feat(api): add export"])

    assert result.exit_code == 0
    assert "Check passed." in result.output


def test_validate_title_cli_supports_gitmoji_profile() -> None:
    result = runner.invoke(app, ["check", "--title", "--profile", "gitmoji", "--text", ":sparkles: Add export"])

    assert result.exit_code == 0
    assert "Check passed." in result.output
