"""Observable document, initialization, and navigation contracts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from zendev.evolution import EvolutionSection, check_document

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
    result = check_document(text, path="history.md")
    assert not result.ok
    assert result.sections == ()
    (diagnostic,) = result.diagnostics
    assert message in diagnostic.message
    assert diagnostic.code.startswith("evolution.")
    assert diagnostic.line == line
    assert diagnostic.path == "history.md"


@pytest.mark.parametrize("second", ["2026-09-07", "2026-09-08"])
def test_dates_are_unique_and_ascending(second: str) -> None:
    result = check_document(ORIGIN + "\n" + entry("2026-09-08") + "\n" + entry(second))
    assert not result.ok
    assert result.diagnostics[0].code == "evolution.date.order"


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
    assert check_document(ORIGIN + "\n" + example + "\n" + entry("2026-09-08")).ok


def test_prose_can_contain_subsections_lists_and_code() -> None:
    assert check_document(
        ORIGIN + "\n### 假设\n- 宿主提供执行环境。\n\n" + entry("2026-09-08", BODY + "\n#### 依据\n正文\n")
    ).ok
    assert check_document(f"# 项目演进\n\n## 初始意图\n\n{FENCE}text\nOriginal intent.\n{FENCE}\n").ok


def test_html_prose_counts_as_section_content() -> None:
    origin = "# 项目演进\n\n## 初始意图\n\n<p>最初为开发者简化工作流。</p>\n"
    assert check_document(origin + "\n" + entry("2026-09-08", BODY.replace("走向独立产品。", "<p>真正的变化。</p>"))).ok


@pytest.mark.parametrize("separator", ["\n", "\r\n", "\r"])
def test_source_lines_match_markdown_newlines(separator: str) -> None:
    text = ORIGIN.replace("最初为开发者简化工作流。", "第一行\u2028第二行") + "\n"
    assert check_document((text + entry("2026-09-08")).replace("\n", separator)).ok
    result = check_document((text + entry("2026-02-30")).replace("\n", separator))
    assert not result.ok
    assert result.diagnostics[0].line == 7


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


@pytest.mark.parametrize("command", ["read", "write"])
def test_cli_has_no_document_management_commands(tmp_path: Path, command: str) -> None:
    result = cli(tmp_path, command)
    assert result.returncode == 2
    assert "No such command" in result.stderr
    assert not list(tmp_path.iterdir())


def test_init_and_list_workflow(tmp_path: Path) -> None:
    source = tmp_path / "origin.md"
    source.write_text("最初为开发者简化工作流。", encoding="utf-8")
    result = cli(tmp_path, "init", "--from", "origin.md")
    assert result.returncode == 0, result.stderr
    path = tmp_path / "EVOLUTION.md"
    assert path.read_text(encoding="utf-8") == ORIGIN
    assert cli(tmp_path, "list").stdout == "EVOLUTION.md:3: 初始意图\n"
    assert cli(tmp_path, "check").returncode == 0
    assert cli(tmp_path, "init", "--from", "origin.md").returncode == 2
    assert path.read_text(encoding="utf-8") == ORIGIN

    assert cli(tmp_path, "init", "--from", "origin.md", "--file", "history.md").returncode == 0
    custom = tmp_path / "history.md"
    document = ORIGIN + "\n" + entry("2026-09-08") + "\n" + entry("2026-09-09")
    original = document.replace("\n", "\r\n").encode("utf-8")
    custom.write_bytes(original)
    result = cli(tmp_path, "list", "--file", "history.md")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "history.md:3: 初始意图",
        "history.md:7: 2026-09-08",
        "history.md:18: 2026-09-09",
    ]
    assert custom.read_bytes() == original
    assert sorted(p.name for p in tmp_path.iterdir()) == ["EVOLUTION.md", "history.md", "origin.md"]


@pytest.mark.parametrize(
    ("body", "exit_code"),
    [(b"", 1), (b"<!-- TODO -->", 1), (("Origin\n\n" + entry("2026-09-08")).encode(), 1), (b"\xff", 2)],
)
def test_init_invalid_input_creates_no_document(tmp_path: Path, body: bytes, exit_code: int) -> None:
    source = tmp_path / "origin.md"
    source.write_bytes(body)
    result = cli(tmp_path, "init", "--from", "origin.md")
    assert result.returncode == exit_code
    assert "origin.md:" in result.stderr
    assert "Traceback" not in result.stderr
    assert [p.name for p in tmp_path.iterdir()] == ["origin.md"]


@pytest.mark.parametrize("kind", ["directory", "symlink", "broken_symlink"])
def test_init_refuses_existing_nonfiles(tmp_path: Path, kind: str) -> None:
    source = tmp_path / "origin.md"
    source.write_text("Origin.", encoding="utf-8")
    target = tmp_path / "EVOLUTION.md"
    if kind == "directory":
        target.mkdir()
    else:
        target.symlink_to(source if kind == "symlink" else tmp_path / "absent.md")
    assert cli(tmp_path, "init", "--from", "origin.md").returncode == 2
    assert target.is_dir() if kind == "directory" else target.is_symlink()
    assert source.read_text() == "Origin."
    assert not (tmp_path / "absent.md").exists()


def test_init_stdin_decodes_utf8_independently_of_host_encoding(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "zendev", "evolution", "init", "--from", "-"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        input="中文".encode(),
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "EVOLUTION.md").read_text(encoding="utf-8") == "# 项目演进\n\n## 初始意图\n\n中文\n"


def test_concurrent_initializers_do_not_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "origin.md"
    source.write_text("Origin.", encoding="utf-8")
    command = [sys.executable, "-m", "zendev", "evolution", "init", "--from", "origin.md"]
    with (
        subprocess.Popen(command, cwd=tmp_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as first,
        subprocess.Popen(command, cwd=tmp_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as second,
    ):
        first.communicate(timeout=15)
        second.communicate(timeout=15)
    assert sorted([first.returncode, second.returncode]) == [0, 2]
    assert (tmp_path / "EVOLUTION.md").read_text(encoding="utf-8") == "# 项目演进\n\n## 初始意图\n\nOrigin.\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["EVOLUTION.md", "origin.md"]


def test_list_ignores_examples_and_emits_no_partial_invalid_directory(tmp_path: Path) -> None:
    path = tmp_path / "EVOLUTION.md"
    assert cli(tmp_path, "list").returncode == 2
    path.write_text(ORIGIN + "\n<!--\n" + entry("2026-09-08") + "-->\n", encoding="utf-8")
    result = cli(tmp_path, "list")
    assert result.returncode == 0, result.stderr
    assert result.stdout == "EVOLUTION.md:3: 初始意图\n"
    invalid = ORIGIN + "\n" + entry("2026-02-30")
    path.write_text(invalid, encoding="utf-8")
    result = cli(tmp_path, "list")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "EVOLUTION.md:7:" in result.stderr
    assert path.read_text(encoding="utf-8") == invalid


def test_public_result_contains_only_validated_sections() -> None:
    text = ORIGIN + "\n" + entry("2026-09-08")
    result = check_document(text)
    assert result.ok
    assert result.sections == (EvolutionSection("初始意图", 3), EvolutionSection("2026-09-08", 7))
    assert result.diagnostics == ()
    assert check_document(text + "\n" + entry("2026-02-30")).sections == ()


@pytest.mark.parametrize("command", ["check", "list"])
def test_json_navigation_and_content_errors(tmp_path: Path, command: str) -> None:
    path = tmp_path / "EVOLUTION.md"
    path.write_text(ORIGIN + "\n" + entry("2026-09-08"), encoding="utf-8")
    result = cli(tmp_path, command, "--format", "json")
    payload = json.loads(result.stdout)
    assert result.returncode == 0 and result.stderr == ""
    assert payload["schema_version"] == 1
    assert payload["command"] == f"evolution {command}"
    assert payload["ok"] and payload["diagnostics"] == []
    assert payload["summary"] == {
        "path": "EVOLUTION.md",
        "sections": [{"title": "初始意图", "line": 3}, {"title": "2026-09-08", "line": 7}],
    }
    path.write_text(ORIGIN + "\n" + entry("2026-02-30"), encoding="utf-8")
    result = cli(tmp_path, command, "--format", "json")
    payload = json.loads(result.stdout)
    assert result.returncode == 1 and result.stderr == ""
    assert not payload["ok"] and payload["summary"]["sections"] == []
    assert payload["diagnostics"][0]["code"] == "evolution.date"
    assert payload["diagnostics"][0]["line"] == 7


@pytest.mark.parametrize("content", [None, b"\xff"])
def test_json_input_failure_is_an_environment_error(tmp_path: Path, content: bytes | None) -> None:
    if content is not None:
        (tmp_path / "EVOLUTION.md").write_bytes(content)
    result = cli(tmp_path, "check", "--format", "json")
    payload = json.loads(result.stdout)
    assert result.returncode == 2 and result.stderr == ""
    assert not payload["ok"] and payload["summary"]["sections"] == []
    assert payload["diagnostics"][0]["code"] == "evolution.input.read"
    assert payload["diagnostics"][0]["path"] == "EVOLUTION.md"


def test_init_json_locations_distinguish_source_and_output(tmp_path: Path) -> None:
    source = tmp_path / "origin.md"
    source.write_text("Original intent.\n\n" + entry("2026-09-08"), encoding="utf-8")
    args = ("init", "--from", "origin.md", "--file", "history.md", "--format", "json")
    result = cli(tmp_path, *args)
    payload = json.loads(result.stdout)
    assert result.returncode == 1 and not (tmp_path / "history.md").exists()
    assert payload["diagnostics"][0]["code"] == "evolution.init.entries"
    assert payload["diagnostics"][0]["path"] == "origin.md"
    assert payload["diagnostics"][0]["line"] == 3
    assert payload["summary"]["sections"] == []
    source.write_text("## 2026-02-30\nBad date.\n", encoding="utf-8")
    payload = json.loads(cli(tmp_path, *args).stdout)
    assert payload["diagnostics"][0]["path"] == "origin.md"
    assert payload["diagnostics"][0]["line"] == 1
    source.write_text("Original intent.\n", encoding="utf-8")
    result = cli(tmp_path, *args)
    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload["summary"] == {"path": "history.md", "sections": [{"title": "初始意图", "line": 3}]}
    result = cli(tmp_path, *args)
    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload["diagnostics"][0]["code"] == "evolution.output.create"
    assert payload["diagnostics"][0]["path"] == "history.md"
    assert payload["summary"]["sections"] == []


def test_github_diagnostics_escape_paths(tmp_path: Path) -> None:
    name = "a,b%.md"
    (tmp_path / name).write_text(ORIGIN + "\n" + entry("2026-02-30"), encoding="utf-8")
    result = cli(tmp_path, "check", "--file", name, "--format", "github")
    assert result.returncode == 1 and result.stderr == ""
    assert result.stdout.startswith("::error file=a%2Cb%25.md,line=7::evolution.date:")


@pytest.mark.parametrize(
    ("command", "output_format"),
    [("init", "json"), ("list", "human"), ("check", "json"), ("check", "github")],
)
def test_output_is_utf8_independently_of_host_encoding(tmp_path: Path, command: str, output_format: str) -> None:
    source = tmp_path / "origin.md"
    source.write_text("Original intent.", encoding="utf-8")
    document = tmp_path / "演进.md"
    if command != "init":
        document.write_text(ORIGIN, encoding="utf-8")
    args = [command, "--file", document.name, "--format", output_format]
    if command == "init":
        args += ["--from", source.name]
    result = subprocess.run(
        [sys.executable, "-m", "zendev", "evolution", *args],
        cwd=tmp_path,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0 and result.stderr == b""
    output = result.stdout.decode("utf-8")
    if output_format == "json":
        payload = json.loads(output)
        assert payload["ok"]
        assert payload["summary"] == {"path": document.name, "sections": [{"title": "初始意图", "line": 3}]}
    elif command == "list":
        assert output == "演进.md:3: 初始意图\n"
    else:
        assert output == "Validated 演进.md.\n"


def test_error_output_preserves_unicode_paths_on_non_utf8_host(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "zendev", "evolution", "check", "--file", "不存在.md"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 2 and result.stdout == b""
    assert result.stderr.decode("utf-8").startswith("不存在.md:1: evolution.input.read:")
    assert b"Traceback" not in result.stderr
