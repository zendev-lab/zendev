"""Observable document and read-only CLI contracts for project evolution."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from zendev.evolution import EvolutionError, validate_document

ORIGIN = "# 项目演进\n\n## 初始意图\n\n最初为开发者简化工作流。\n"
BODY = "### 触发\n出现新的需求。\n\n### 变化\n走向独立产品。\n\n### 理由\n需要拥有生命周期。\n"
TEMPLATE = Path(__file__).parents[1] / "templates" / "evolution.md"
FENCE = "```"


def entry(day: str, body: str = BODY) -> str:
    return f"## {day}\n\n{body}"


def cli(directory: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "zendev", "evolution", *args],
        cwd=directory,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        check=False,
    )


@pytest.mark.parametrize(
    ("text", "message", "line"),
    [
        ("", "single '# 项目演进'", 1),
        ("# 项目演进\n", "exactly one", 1),
        (ORIGIN + "\n## 初始意图\n重复\n", "exactly one", 7),
        ("# 项目演进\n\n" + entry("2026-09-08") + "\n## 初始意图\n起点\n", "must precede", 3),
        ("# 项目演进\n\n## 初始意图\n \n", "must not be empty", 3),
        ("# 项目演进\n\n## 初始意图\n<!-- TODO -->\n", "must not be empty", 3),
        ("# 项目演进\n\n## 初始意图\n<div><!-- TODO --></div>\n", "must not be empty", 3),
        ("# 项目演进\n\n## 初始意图\n### 待补充\n", "must not be empty", 3),
        (ORIGIN + "\n" + entry("2026-02-30"), "real date", 7),
        (ORIGIN + "\n" + entry("2026-9-08"), "real date", 7),
        (ORIGIN + "\n## 其他\n正文\n", "real date", 7),
        (ORIGIN + "\n" + entry("2026-09-08", BODY.replace("### 变化", "### 触发")), "once each", 7),
        (ORIGIN + "\n" + entry("2026-09-08", BODY.replace("走向独立产品。", "<!-- TODO -->")), "must not be empty", 12),
        (ORIGIN + "\n" + entry("2026-09-08", BODY.replace("### 理由", "### 其他")), "once each", 7),
        (ORIGIN + "\n" + entry("2026-09-08", "正文\n" + BODY), "inside the three", 8),
        (ORIGIN + "\n" + entry("2026-09-08", "<!--\n" + BODY + "-->\n"), "must not be empty", 7),
        (ORIGIN + "\n" + entry("2026-09-08", "### 触发\n原因\n"), "once each", 7),
        (ORIGIN.replace("# 项目演进", "项目演进\n======"), "ATX", 1),
    ],
)
def test_invalid_documents_report_source(text: str, message: str, line: int) -> None:
    with pytest.raises(EvolutionError, match=message) as caught:
        validate_document(text, path="history.md")
    assert caught.value.line == line
    assert caught.value.path == "history.md"


@pytest.mark.parametrize("second", ["2026-09-07", "2026-09-08"])
def test_dates_are_unique_and_ascending(second: str) -> None:
    with pytest.raises(EvolutionError, match="unique and in ascending"):
        validate_document(ORIGIN + "\n" + entry("2026-09-08") + "\n" + entry(second))


@pytest.mark.parametrize(
    "example",
    [
        "<!--\n" + entry("2026-09-09") + "-->\n",
        f"{FENCE}markdown\n## fake\n### 理由\n{FENCE}\n",
        "~~~~markdown\n# 项目演进\n~~~\n## fake\n~~~~\n",
        f"- {FENCE}markdown\n  ## fake\n  {FENCE}\n",
        f"> {FENCE}markdown\n> ## fake\n> {FENCE}\n",
        "    ## fake\n    ### 理由\n",
        "> ## fake\n> quoted text\n",
    ],
)
def test_examples_do_not_become_structural_headings(example: str) -> None:
    # The hidden 09-09 entry would put the following real 09-08 entry out of order.
    validate_document(ORIGIN + "\n" + example + "\n" + entry("2026-09-08"))


def test_prose_can_contain_subsections_lists_and_code() -> None:
    validate_document(
        ORIGIN + "\n### 假设\n- 宿主提供执行环境。\n\n" + entry("2026-09-08", BODY + "\n#### 依据\n正文\n")
    )
    validate_document(f"# 项目演进\n\n## 初始意图\n\n{FENCE}text\nOriginal intent.\n{FENCE}\n")


def test_html_prose_counts_as_section_content() -> None:
    origin = "# 项目演进\n\n## 初始意图\n\n<p>最初为开发者简化工作流。</p>\n"
    validate_document(origin + "\n" + entry("2026-09-08", BODY.replace("走向独立产品。", "<p>真正的变化。</p>")))


@pytest.mark.parametrize("separator", ["\n", "\r\n", "\r"])
def test_source_lines_match_markdown_newlines(separator: str) -> None:
    text = ORIGIN.replace("最初为开发者简化工作流。", "第一行\u2028第二行") + "\n"
    validate_document((text + entry("2026-09-08")).replace("\n", separator))
    with pytest.raises(EvolutionError) as caught:
        validate_document((text + entry("2026-02-30")).replace("\n", separator))
    assert caught.value.line == 7


@pytest.mark.parametrize("text", [ORIGIN, TEMPLATE.read_text(encoding="utf-8")])
def test_cli_checks_real_documents_without_writing(tmp_path: Path, text: str) -> None:
    path = tmp_path / "EVOLUTION.md"
    original = text.replace("\n", "\r\n").encode("utf-8")
    path.write_bytes(original)
    result = cli(tmp_path, "check")
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Validated EVOLUTION.md.\n"
    assert path.read_bytes() == original
    assert [p.name for p in tmp_path.iterdir()] == ["EVOLUTION.md"]


def test_cli_paths_diagnostics_and_exit_codes(tmp_path: Path) -> None:
    path = tmp_path / "history.md"
    path.write_text(ORIGIN, encoding="utf-8")
    assert cli(tmp_path, "check", "--file", "history.md").returncode == 0
    assert cli(tmp_path, "check").returncode == 2
    child = tmp_path / "child"
    child.mkdir()
    assert cli(child, "check", "--file", "history.md").returncode == 2
    assert cli(tmp_path, "check", "--file", "child").returncode == 2
    bad = (ORIGIN + "\n" + entry("2026-02-30")).encode("utf-8")
    path.write_bytes(bad)
    result = cli(tmp_path, "check", "--file", "history.md")
    assert result.returncode == 1
    assert "history.md:7:" in result.stderr
    assert path.read_bytes() == bad
    path.write_bytes(b"\xff")
    result = cli(tmp_path, "check", "--file", "history.md")
    assert result.returncode == 2
    assert "history.md:1:" in result.stderr
    assert "Traceback" not in result.stderr
    assert path.read_bytes() == b"\xff"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["child", "history.md"]


@pytest.mark.parametrize("command", ["init", "list", "read", "write"])
def test_cli_has_no_document_management_commands(tmp_path: Path, command: str) -> None:
    result = cli(tmp_path, command)
    assert result.returncode == 2
    assert "No such command" in result.stderr
    assert not list(tmp_path.iterdir())
