"""Observable normalization, diagnostic, and commit-msg contracts."""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from zendev.message import check_message, normalize_message
from zendev.message.cli import app

runner = CliRunner()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("feat(api)!: add export", "✨ feat(api)!: add export"),
        ("fix: handle failure", "🐛 fix: handle failure"),
        ("docs: explain setup", "📝 docs: explain setup"),
        ("style: format code", "🎨 style: format code"),
        ("refactor: simplify parser", "♻️ refactor: simplify parser"),
        ("perf: cache lookups", "⚡️ perf: cache lookups"),
        ("test: cover failures", "✅ test: cover failures"),
        ("build: package wheels", "📦️ build: package wheels"),
        ("ci: run checks", "👷 ci: run checks"),
        ("chore: adjust tooling", "🔧 chore: adjust tooling"),
        ("revert: undo export", "⏪️ revert: undo export"),
        ("deps: Upgrade requests", "⬆️ deps: Upgrade requests"),
        ("deps: update dependencies", "⬆️ deps: update dependencies"),
        ("deps: bump requests", "⬆️ deps: bump requests"),
        ("deps: downgrade requests", "⬇️ deps: downgrade requests"),
        ("deps: pin requests", "📌 deps: pin requests"),
        ("deps: add requests", "\u2795 deps: add requests"),
        ("deps: remove requests", "\u2796 deps: remove requests"),
        ("[ImgBot] Optimize images", "⚡️ perf(assets): optimize images"),
    ],
)
def test_unambiguous_messages_normalize_and_are_idempotent(text: str, expected: str) -> None:
    result = normalize_message(text)

    assert result.ok and result.changed
    assert result.text == expected
    assert check_message(result.text).ok
    again = normalize_message(result.text)
    assert again.ok and not again.changed
    assert again.text == expected


@pytest.mark.parametrize(
    "text",
    [
        "deps: change dependencies",
        "deps: update dependencies and downgrade requests",
        "deps: upgrade dependencies, remove requests",
        "deps: upgrade or downgrade requests",
        "deps: update requests from v2 to v1",
        "deps: bump requests from v2 to v1",
        "deps: do not upgrade requests",
        "deps: update",
        "deps-up: upgrade requests",
        "fix: ",
        "fix: handle failure\nmissing blank line",
        "🐛 feat: wrong intention",
        "😀 feat: unknown emoji",
        "✨  feat: invalid spacing",
        "[ImgBot] Optimize images and remove assets",
        "optimize images",
        "ship it",
        "",
    ],
)
def test_ambiguous_or_invalid_messages_keep_the_original(text: str) -> None:
    result = normalize_message(text)

    assert not result.ok and not result.changed
    assert result.text == text


@pytest.mark.parametrize(
    ("text", "profile"),
    [
        ("🚑 fix: urgent repair", "zendev"),
        (":sparkles: feat: add export", "zendev"),
        ("♻ refactor: simplify parser", "zendev"),
        ("custom(api)!: change protocol", "conventional"),
        (":sparkles: Add export", "gitmoji"),
    ],
)
def test_valid_messages_keep_the_authors_choice(text: str, profile: str) -> None:
    result = normalize_message(text, profile=profile)

    assert result.ok and not result.changed
    assert result.text == text


@pytest.mark.parametrize("profile", ["conventional", "gitmoji"])
def test_other_profiles_are_not_reinterpreted(profile: str) -> None:
    result = normalize_message("[ImgBot] Optimize images", profile=profile)

    assert not result.ok and not result.changed


def test_commit_cleanup_locates_subject_without_rewriting_any_other_text() -> None:
    text = (
        "; template\r\n\r\nfeat(api)!: add export\r\n\r\nWhy  \r\n\r\n"
        "BREAKING CHANGE: migrate\r\nRefs: #42\r\n"
        "; ------------------------ >8 ------------------------\r\nfeat: ignored diff\r\n"
    )

    result = normalize_message(text, commit=True, comment_char=";")

    assert result.ok and result.changed
    assert result.text == text.replace("feat(api)!:", "✨ feat(api)!:", 1)


@pytest.mark.parametrize("prefix", ["Merge ", "Revert ", "fixup! ", "squash! ", "amend! ", "reword! "])
def test_special_git_messages_are_only_exempt_in_commit_scope(prefix: str) -> None:
    text = prefix + "original subject\n\n# comment\n"
    assert normalize_message(text, commit=True).ok
    assert not normalize_message(text, commit=True).changed
    assert not normalize_message(text).ok


def test_read_only_check_suggests_without_modifying_the_file(tmp_path: Path) -> None:
    message = tmp_path / "COMMIT_EDITMSG"
    original = b"feat: add export\r\n\r\nBody\r\n"
    message.write_bytes(original)

    result = runner.invoke(app, ["check", "--commit", str(message), "--format", "json"])

    assert result.exit_code == 1
    diagnostic = json.loads(result.stdout)["diagnostics"][0]
    assert diagnostic["fixable"] is True
    assert "✨ feat: add export" in diagnostic["hint"]
    assert "--fix" in diagnostic["hint"]
    assert message.read_bytes() == original


def test_fix_writes_only_the_subject_and_retains_crlf(tmp_path: Path) -> None:
    message = tmp_path / "COMMIT_EDITMSG"
    original = "# template\r\nfix: handle failure\r\n\r\nBody  \r\n\r\nRefs: #42\r\n"
    message.write_bytes(original.encode("utf-8"))

    result = runner.invoke(app, ["check", "--commit", "--fix", str(message), "--format", "json"])

    assert result.exit_code == 0, result.output
    expected = original.replace("fix:", "🐛 fix:", 1)
    assert message.read_bytes() == expected.encode("utf-8")
    assert json.loads(result.stdout)["summary"] == {"changed": True, "text": expected}
    again = runner.invoke(app, ["check", "--commit", "--fix", str(message), "--format", "json"])
    assert again.exit_code == 0
    assert json.loads(again.stdout)["summary"]["changed"] is False


def test_text_fix_exposes_the_candidate_in_the_shared_json_envelope() -> None:
    result = runner.invoke(app, ["check", "--title", "--fix", "--text", "feat: add export", "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 1
    assert payload["summary"] == {"changed": True, "text": "✨ feat: add export"}


def test_github_success_output_does_not_emit_commit_body_as_workflow_commands() -> None:
    result = runner.invoke(
        app,
        ["check", "--commit", "--fix", "--text", "feat: add export\n\n::error::body text", "--format", "github"],
    )

    assert result.exit_code == 0
    assert result.stdout == "Normalized message: ✨ feat: add export\n"


@pytest.mark.parametrize("args", [["--body"], ["--title", "--text", "feat: add\n\nBody"]])
def test_fix_rejects_inapplicable_scopes(args: list[str], tmp_path: Path) -> None:
    message = tmp_path / "message"
    message.write_text("## Summary\n", encoding="utf-8")
    result = runner.invoke(app, ["check", "--fix", *args, *([] if "--text" in args else [str(message)])])

    assert result.exit_code == (2 if "--body" in args else 1)
    assert message.read_text(encoding="utf-8") == "## Summary\n"


def test_ambiguous_fix_fails_without_touching_the_file(tmp_path: Path) -> None:
    message = tmp_path / "COMMIT_EDITMSG"
    original = b"deps: change dependencies\n"
    message.write_bytes(original)

    result = runner.invoke(app, ["check", "--commit", "--fix", str(message)])

    assert result.exit_code == 1
    assert message.read_bytes() == original


def test_write_error_is_an_environment_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    message = tmp_path / "COMMIT_EDITMSG"
    message.write_text("feat: add export\n", encoding="utf-8")

    def deny_write(_path: Path, _data: bytes) -> int:
        raise PermissionError("read-only message file")

    monkeypatch.setattr(Path, "write_bytes", deny_write)
    result = runner.invoke(app, ["check", "--commit", "--fix", str(message), "--format", "json"])

    assert result.exit_code == 2
    assert json.loads(result.stdout)["diagnostics"][0]["code"] == "message.input.write"
    assert message.read_text(encoding="utf-8") == "feat: add export\n"


@pytest.mark.parametrize("fix", [False, True])
def test_real_git_commit_observes_the_hook_result(tmp_path: Path, fix: bool) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    hooks = tmp_path / ".git/hooks"
    hook = hooks / "commit-msg"
    hook.write_text(
        "#!/bin/sh\nexec "
        + shlex.quote(sys.executable)
        + " -m zendev message check --commit "
        + ("--fix " if fix else "")
        + '"$1"\n',
        encoding="utf-8",
    )
    hook.chmod(0o755)
    text = "feat(api)!: add export\n\nKeep the explanation.\n\nBREAKING CHANGE: migrate to v2"
    process = subprocess.run(
        [
            "git",
            "-c",
            f"core.hooksPath={hooks}",
            "-c",
            "user.name=Hook Test",
            "-c",
            "user.email=test@example.com",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--allow-empty",
            "-m",
            text,
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == (0 if fix else 1), process.stderr
    if fix:
        committed = subprocess.check_output(["git", "log", "-1", "--format=%B"], cwd=tmp_path, text=True)
        assert committed.rstrip("\n") == "✨ " + text
    else:
        assert "Suggested message: ✨ feat(api)!: add export" in process.stderr
        assert (tmp_path / ".git/COMMIT_EDITMSG").read_text(encoding="utf-8").rstrip("\n") == text
