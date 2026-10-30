"""Negative controls for the workspace-specific dependency and import adapters."""

from __future__ import annotations

import json
import os
import runpy
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("dependencies", "source", "expected"),
    [
        (["markdown-it-py"], "import markdown_it\n", 0),
        ([], "import missing_quality_dependency\n", 1),
        (["markdown-it-py"], "import pathlib\n", 1),
    ],
)
def test_deptry_reads_hatch_dependencies(tmp_path: Path, dependencies: list[str], source: str, expected: int) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src/sample.py").write_text(source, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "quality-fixture"\ndynamic = ["dependencies"]\n'
        "[tool.hatch.metadata.hooks.custom]\n" + f"dependencies = {json.dumps(dependencies)}\n",
        encoding="utf-8",
    )
    check = runpy.run_path(str(ROOT / "scripts/check_dependencies.py"))["check_distribution"]
    assert check(tmp_path) == expected


@pytest.mark.parametrize("imported", ["zendev.cli", "zendev.proposal"])
def test_import_contract_rejects_reverse_and_sibling_dependencies(tmp_path: Path, imported: str) -> None:
    for source in [ROOT / "src", *sorted((ROOT / "packages").glob("*/src"))]:
        shutil.copytree(source, tmp_path / "src", dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
    environment = {**os.environ, "PYTHONPATH": str(tmp_path / "src")}
    command = ["lint-imports", "--no-cache"]
    baseline = subprocess.run(command, cwd=tmp_path, env=environment, capture_output=True, text=True, check=False)
    assert baseline.returncode == 0, baseline.stdout + baseline.stderr
    (tmp_path / "src/zendev/message/quality_fixture.py").write_text(f"import {imported}\n", encoding="utf-8")
    violation = subprocess.run(command, cwd=tmp_path, env=environment, capture_output=True, text=True, check=False)
    assert violation.returncode == 1, violation.stdout + violation.stderr
    assert "BROKEN" in violation.stdout
