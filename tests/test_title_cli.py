"""Tests for the zendev-validate-title CLI."""

from __future__ import annotations

from typer.testing import CliRunner

from zendev.title import app

runner = CliRunner()


def test_validate_title_cli_accepts_valid_title() -> None:
    result = runner.invoke(app, ["✨ feat: add portable action"])

    assert result.exit_code == 0
    assert "Title format is valid." in result.output


def test_validate_title_cli_rejects_invalid_title() -> None:
    result = runner.invoke(app, ["feat: missing emoji"])

    assert result.exit_code == 1
    assert "::error::Title does not match zendev emoji commit conventions." in result.output


def test_validate_title_cli_supports_conventional_profile() -> None:
    result = runner.invoke(app, ["--profile", "conventional", "feat(api): add export"])

    assert result.exit_code == 0
    assert "Title format is valid." in result.output


def test_validate_title_cli_supports_gitmoji_profile() -> None:
    result = runner.invoke(app, ["--profile", "gitmoji", ":sparkles: Add export"])

    assert result.exit_code == 0
    assert "Title format is valid." in result.output
