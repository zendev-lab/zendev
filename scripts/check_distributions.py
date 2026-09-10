"""Verify namespace ownership and evolution commands from installed wheels."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile


def run(*args: str, cwd: Path, body: str | None = None, expected: int = 0) -> str:
    result = subprocess.run(
        args, cwd=cwd, input=body, text=True, encoding="utf-8", capture_output=True, check=False, timeout=120
    )
    if result.returncode != expected:
        raise RuntimeError(f"{args}: exit {result.returncode}, expected {expected}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def check_commands(prefix: list[str], cwd: Path) -> None:
    body = "### 触发\nNew needs.\n\n### 变化\nNew direction.\n\n### 理由\nEvidence.\n"
    run(*prefix, "init", "--from", "-", cwd=cwd, body="Original intent.")
    run(*prefix, "write", "2026-09-08", "--from", "-", cwd=cwd, body=body)
    run(*prefix, "check", cwd=cwd)
    assert run(*prefix, "read", "--origin", cwd=cwd) == "## 初始意图\n\nOriginal intent.\n\n"
    assert run(*prefix, "read", "2026-09-08", cwd=cwd) == f"## 2026-09-08\n\n{body}"
    assert "EVOLUTION.md:3: 初始意图" in run(*prefix, "list", cwd=cwd)
    before = (cwd / "EVOLUTION.md").read_bytes()
    run(*prefix, "write", "2026-09-08", "--from", "-", cwd=cwd, body=body, expected=2)
    assert (cwd / "EVOLUTION.md").read_bytes() == before
    run(*prefix, "write", "2026-09-08", "--replace", "--from", "-", cwd=cwd, body=body.replace("Evidence", "Reasons"))
    assert "Reasons" in run(*prefix, "read", cwd=cwd)


def main() -> None:
    distribution_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "dist").resolve()
    wheels = sorted(distribution_dir.glob("*.whl"))
    expected = {"zendev", "zendev_commit", "zendev_evolution", "zendev_log", "zendev_proposal", "zendev_review"}
    assert len(wheels) == len(expected), f"Expected exactly six wheels in {distribution_dir}"
    assert {wheel.name.split("-")[0] for wheel in wheels} == expected
    owners: dict[str, str] = {}
    for wheel in wheels:
        with ZipFile(wheel) as archive:
            for name in archive.namelist():
                if name.startswith("zendev/") and not name.endswith("/"):
                    assert name not in owners, f"Namespace overlap: {name} in {owners.get(name)} and {wheel.name}"
                    owners[name] = wheel.name
    assert "zendev/__init__.py" not in owners, "Keep the PEP 420 namespace open."
    assert "zendev/evolution/py.typed" in owners
    evolution = next(wheel for wheel in wheels if wheel.name.startswith("zendev_evolution-"))
    with tempfile.TemporaryDirectory(prefix="zendev-distributions-") as temporary:
        root = Path(temporary)
        for kind in ("standalone", "complete"):
            working = root / kind
            working.mkdir()
            environment = working / "venv"
            run("uv", "venv", "--python", sys.executable, str(environment), cwd=working)
            binaries = environment / ("Scripts" if os.name == "nt" else "bin")
            python = binaries / ("python.exe" if os.name == "nt" else "python")
            selected = [evolution] if kind == "standalone" else wheels
            run("uv", "pip", "install", "--python", str(python), *(str(wheel) for wheel in selected), cwd=working)
            run("uv", "pip", "check", "--python", str(python), cwd=working)
            executable = binaries / ("zendev-evolution.exe" if os.name == "nt" else "zendev-evolution")
            check_commands([str(executable)], working)
            if kind == "standalone":
                run(
                    str(python),
                    "-c",
                    "import importlib.util; assert importlib.util.find_spec('zendev.proposal') is None",
                    cwd=working,
                )
            else:
                module = run(str(python), "-m", "zendev", "evolution", "read", "--origin", cwd=working)
                assert "Original intent." in module
                unified = binaries / ("zendev.exe" if os.name == "nt" else "zendev")
                run(str(unified), "evolution", "check", cwd=working)
    print("Verified six non-overlapping wheels and standalone/complete evolution workflows.")


if __name__ == "__main__":
    main()
