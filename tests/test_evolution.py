"""Observable format, CLI and safe-write contracts for project evolution."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from zendev.evolution import EvolutionError, initialize, parse_document, read_document, write_entry

ORIGIN = "# 项目演进\n\n## 初始意图\n\n最初为开发者简化工作流。\n"
BODY = "### 触发\n出现新的需求。\n\n### 变化\n走向独立产品。\n\n### 理由\n需要拥有生命周期。\n"


def entry(day: str, body: str = BODY) -> str:
    return f"## {day}\n\n{body}"


def cli(directory: Path, *args: str, body: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "zendev", "evolution", *args],
        cwd=directory,
        input=body,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        check=False,
    )


def test_origin_only_and_source_lines() -> None:
    document = parse_document(ORIGIN)
    assert document.origin.line == 3
    assert document.source(document.origin) == ORIGIN.split("\n\n", 1)[1]
    assert not document.entries
    document = parse_document(ORIGIN + "\n" + entry("2026-09-08"))
    assert document.entries[0].line == 7
    assert document.source(document.entries[0]) == entry("2026-09-08")


@pytest.mark.parametrize(
    ("text", "message", "line"),
    [
        ("", "single '# 项目演进'", 1),
        ("# 项目演进\n", "exactly one", 1),
        (ORIGIN + "\n## 初始意图\n重复\n", "exactly one", 7),
        ("# 项目演进\n\n" + entry("2026-09-08") + "\n## 初始意图\n起点\n", "must precede", 3),
        ("# 项目演进\n\n## 初始意图\n \n", "must not be empty", 3),
        (ORIGIN + "\n" + entry("2026-02-30"), "real date", 7),
        (ORIGIN + "\n" + entry("2026-9-08"), "real date", 7),
        (ORIGIN + "\n## 其他\n正文\n", "real date", 7),
        (ORIGIN + "\n" + entry("2026-09-08", BODY.replace("### 变化", "### 触发")), "once each", 7),
        (ORIGIN + "\n" + entry("2026-09-08", BODY.replace("走向独立产品。", " ")), "must not be empty", 12),
        (ORIGIN + "\n" + entry("2026-09-08", BODY.replace("### 理由", "### 其他")), "once each", 7),
        (ORIGIN + "\n" + entry("2026-09-08", "正文\n" + BODY), "inside the three", 8),
        (ORIGIN + "\n~~~markdown\n## 初始意图\n", "Unclosed", 7),
    ],
)
def test_invalid_documents_report_source(text: str, message: str, line: int) -> None:
    with pytest.raises(EvolutionError, match=message) as caught:
        parse_document(text, path="history.md")
    assert caught.value.line == line
    assert caught.value.path == "history.md"
    assert caught.value.exit_code == 1


@pytest.mark.parametrize("second", ["2026-09-07", "2026-09-08"])
def test_dates_are_unique_and_ascending(second: str) -> None:
    with pytest.raises(EvolutionError, match="unique and in ascending"):
        parse_document(ORIGIN + "\n" + entry("2026-09-08") + "\n" + entry(second))


@pytest.mark.parametrize("fence", ["```", "~~~~", "````"])
def test_fences_hide_fake_titles_and_shorter_closers(fence: str) -> None:
    literal = f"{fence}markdown\n# 项目演进\n## 初始意图\n## 2020-01-01\n### 理由\n"
    if len(fence) > 3:
        literal += fence[:3] + "\n## still code\n"
    literal += fence + "\n"
    document = parse_document(ORIGIN + "\n" + literal + "\n" + entry("2026-09-08", BODY + "\n" + literal))
    assert len(document.entries) == 1
    assert literal in document.source(document.origin)
    assert literal in document.source(document.entries[0])


def test_origin_accepts_free_subsections_and_entry_accepts_lower_headings() -> None:
    document = parse_document(
        ORIGIN + "\n### 最初假设\n可以依赖宿主。\n\n" + entry("2026-09-08", BODY + "\n#### 依据\n- 普通链接\n")
    )
    assert "最初假设" in document.source(document.origin)
    assert "#### 依据" in document.source(document.entries[0])


def test_cli_full_workflow(tmp_path: Path) -> None:
    result = cli(tmp_path, "init", "--from", "-", body="最初为开发者简化工作流。")
    assert result.returncode == 0, result.stderr
    path = tmp_path / "EVOLUTION.md"
    assert path.read_text() == ORIGIN
    assert cli(tmp_path, "check").returncode == 0
    assert cli(tmp_path, "read").stdout == ORIGIN.split("\n\n", 1)[1]
    assert cli(tmp_path, "list").stdout == "EVOLUTION.md:3: 初始意图\n"
    before = path.read_bytes()
    assert cli(tmp_path, "init", "--from", "-", body="different").returncode == 2
    assert path.read_bytes() == before

    body_file = tmp_path / "body.md"
    body_file.write_text(BODY, encoding="utf-8")
    assert cli(tmp_path, "write", "2026-09-09", "--from", str(body_file)).returncode == 0
    assert cli(tmp_path, "write", "2026-09-08", "--from", "-", body=BODY).returncode == 0
    document = read_document(path)
    assert [part.title for part in document.entries] == ["2026-09-08", "2026-09-09"]
    assert cli(tmp_path, "read", "--origin").stdout == document.source(document.origin)
    assert cli(tmp_path, "read", "2026-09-08").stdout == document.source(document.entries[0])
    assert cli(tmp_path, "read").stdout == (document.source(document.origin) + document.source(document.entries[-1]))
    assert cli(tmp_path, "list").stdout.splitlines() == [
        f"EVOLUTION.md:{part.line}: {part.title}" for part in (document.origin, *document.entries)
    ]

    before = path.read_bytes()
    assert cli(tmp_path, "write", "2026-09-08", "--from", "-", body=BODY).returncode == 2
    assert cli(tmp_path, "write", "2026-09-07", "--replace", "--from", "-", body=BODY).returncode == 2
    assert path.read_bytes() == before
    replacement = BODY.replace("新的需求", "更多实际需求")
    assert cli(tmp_path, "write", "2026-09-08", "--replace", "--from", "-", body=replacement).returncode == 0
    after = read_document(path)
    assert after.source(after.origin) == document.source(document.origin)
    assert after.source(after.entries[1]) == document.source(document.entries[1])
    assert "更多实际需求" in after.source(after.entries[0])


@pytest.mark.parametrize(
    "arguments",
    [
        ("read", "2026-09-10"),
        ("read", "2026-09-08", "--origin"),
        ("read", "2026-02-30"),
        ("write", "2026-9-8", "--from", "-"),
        ("write", "2026-09-08", "--from", "missing.md"),
    ],
)
def test_cli_usage_errors_do_not_write(tmp_path: Path, arguments: tuple[str, ...]) -> None:
    path = tmp_path / "EVOLUTION.md"
    path.write_text(ORIGIN, encoding="utf-8")
    result = cli(tmp_path, *arguments, body=BODY)
    assert result.returncode == 2
    assert result.stderr
    assert "Traceback" not in result.stderr
    assert path.read_text() == ORIGIN


def test_paths_missing_files_and_validation_exit_codes(tmp_path: Path) -> None:
    source = tmp_path / "origin.txt"
    source.write_text("初始目标", encoding="utf-8")
    assert cli(tmp_path, "init", "--file", "history.md", "--from", str(source)).returncode == 0
    assert cli(tmp_path, "read", "--file", "history.md").stdout == "## 初始意图\n\n初始目标\n"
    assert cli(tmp_path, "check").returncode == 2
    assert cli(tmp_path, "write", "2026-09-08", "--from", "-", body=BODY).returncode == 2
    assert not (tmp_path / "EVOLUTION.md").exists()
    child = tmp_path / "child"
    child.mkdir()
    assert cli(child, "check", "--file", "history.md").returncode == 2
    bad = tmp_path / "bad.md"
    bad.write_text(ORIGIN + "\n## 2026-02-30\ncontent\n", encoding="utf-8")
    result = cli(tmp_path, "check", "--file", "bad.md")
    assert result.returncode == 1
    assert "bad.md:7:" in result.stderr
    assert cli(tmp_path, "read", "--file", "bad.md").returncode == 1
    bad.write_bytes(b"\xff")
    assert cli(tmp_path, "check", "--file", "bad.md").returncode == 2


@pytest.mark.parametrize("body", ["", "### 触发\nonly one", BODY + "\n" + entry("2026-09-09")])
def test_invalid_input_keeps_file_intact(tmp_path: Path, body: str) -> None:
    path = tmp_path / "EVOLUTION.md"
    path.write_text(ORIGIN, encoding="utf-8")
    result = cli(tmp_path, "write", "2026-09-08", "--from", "-", body=body)
    assert result.returncode == 1
    assert path.read_text() == ORIGIN
    assert sorted(file.name for file in tmp_path.iterdir()) == ["EVOLUTION.md"]


def test_invalid_origin_or_existing_document_never_writes(tmp_path: Path) -> None:
    path = tmp_path / "EVOLUTION.md"
    for body in (" ", "Origin\n\n" + entry("2026-09-08")):
        with pytest.raises(EvolutionError):
            initialize(path, body)
        assert not path.exists()
    path.write_text("broken\n", encoding="utf-8")
    with pytest.raises(EvolutionError):
        write_entry(path, "2026-09-08", BODY)
    assert path.read_text() == "broken\n"


def test_replace_preserves_unrelated_bytes_line_endings_and_mode(tmp_path: Path) -> None:
    path = tmp_path / "EVOLUTION.md"
    prefix = (ORIGIN + "\n").replace("\n", "\r\n")
    suffix = entry("2026-09-09").replace("\n", "\r\n")
    path.write_bytes((prefix + entry("2026-09-08") + "\n" + suffix).encode())
    path.chmod(0o640)
    write_entry(path, "2026-09-08", BODY.replace("独立产品", "新的方向"), replace=True)
    assert path.read_bytes().startswith(prefix.encode())
    assert path.read_bytes().endswith(suffix.encode())
    if os.name != "nt":
        assert path.stat().st_mode & 0o777 == 0o640


def test_replace_and_insert_preserve_adjacent_sections_without_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "EVOLUTION.md"
    original = ORIGIN + entry("2026-09-08") + entry("2026-09-10")
    path.write_text(original, encoding="utf-8")
    before = read_document(path)
    write_entry(path, "2026-09-08", BODY.replace("新的需求", "实际需求"), replace=True)
    after = read_document(path)
    assert after.source(after.origin) == before.source(before.origin)
    assert after.source(after.entries[-1]) == before.source(before.entries[-1])
    write_entry(path, "2026-09-09", BODY)
    inserted = read_document(path)
    assert inserted.source(inserted.entries[0]) == after.source(after.entries[0])
    assert inserted.source(inserted.entries[-1]) == after.source(after.entries[-1])


def test_input_diagnostics_use_input_line_numbers(tmp_path: Path) -> None:
    (tmp_path / "EVOLUTION.md").write_text(ORIGIN, encoding="utf-8")
    body = tmp_path / "body.md"
    body.write_text("### 触发\nA\n### 变化\n\n### 理由\nC\n", encoding="utf-8")
    result = cli(tmp_path, "write", "2026-09-08", "--from", "body.md")
    assert result.returncode == 1
    assert "body.md:3:" in result.stderr


def test_failed_atomic_replace_keeps_original_and_cleans_temporary_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "EVOLUTION.md"
    path.write_text(ORIGIN, encoding="utf-8")

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError("simulated filesystem failure")

    monkeypatch.setattr("zendev.evolution.storage.os.replace", fail_replace)
    with pytest.raises(OSError, match="simulated filesystem failure"):
        write_entry(path, "2026-09-08", BODY)
    assert path.read_text() == ORIGIN
    assert sorted(file.name for file in tmp_path.iterdir()) == ["EVOLUTION.md"]


def test_symlinks_are_not_replaced(tmp_path: Path) -> None:
    target = tmp_path / "actual.md"
    target.write_text(ORIGIN, encoding="utf-8")
    path = tmp_path / "EVOLUTION.md"
    path.symlink_to(target)
    assert cli(tmp_path, "write", "2026-09-08", "--from", "-", body=BODY).returncode == 2
    assert path.is_symlink()
    assert target.read_text() == ORIGIN


# Pause an actual writer after flushing its temporary file, while its lock is held.
# This lets a competing CLI or external editor run at a deterministic save boundary.
_PAUSED_WRITER = """
import os, sys
from pathlib import Path
from zendev.evolution import write_entry
original_fsync = os.fsync
def pause(fd):
    original_fsync(fd)
    print("ready", flush=True)
    sys.stdin.readline()
os.fsync = pause
try:
    write_entry(Path(sys.argv[1]), "2026-09-08", sys.argv[2])
except Exception as error:
    print(error, file=sys.stderr)
    sys.exit(2)
"""


@pytest.mark.parametrize("external_editor", [False, True])
def test_concurrent_writers_and_external_edits_do_not_lose_content(tmp_path: Path, external_editor: bool) -> None:
    path = tmp_path / "EVOLUTION.md"
    path.write_text(ORIGIN, encoding="utf-8")
    with subprocess.Popen(
        [sys.executable, "-c", _PAUSED_WRITER, str(path), BODY],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    ) as writer:
        assert writer.stdout is not None
        assert writer.stdout.readline().strip() == "ready"
        if external_editor:
            edited = ORIGIN.replace("简化工作流", "保留编辑器里的新内容")
            path.write_text(edited, encoding="utf-8")
        else:
            result = cli(tmp_path, "write", "2026-09-09", "--from", "-", body=BODY)
            assert result.returncode == 2
            assert "Writer lock exists" in result.stderr
            assert path.read_text() == ORIGIN
        _, stderr = writer.communicate("\n", timeout=15)
        if external_editor:
            assert writer.returncode == 2
            assert "File changed" in stderr
            assert path.read_text() == edited
        else:
            assert writer.returncode == 0, stderr
            assert [part.title for part in read_document(path).entries] == ["2026-09-08"]
    assert sorted(file.name for file in tmp_path.iterdir()) == ["EVOLUTION.md"]
