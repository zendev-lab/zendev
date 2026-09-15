"""Verify namespace ownership and evolution commands from installed wheels."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile


def run(*args: str, cwd: Path, expected: int = 0) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, encoding="utf-8", capture_output=True, check=False, timeout=120)
    if result.returncode != expected:
        raise RuntimeError(f"{args}: exit {result.returncode}, expected {expected}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def check_commands(prefix: list[str], cwd: Path) -> None:
    path = cwd / "EVOLUTION.md"
    run(*prefix, "check", cwd=cwd, expected=2)
    source = cwd / "origin.md"
    source.write_text("Original intent.\n", encoding="utf-8")
    run(*prefix, "init", "--from", str(source), cwd=cwd)
    initial = path.read_bytes()
    assert initial.decode("utf-8") == "# 项目演进\n\n## 初始意图\n\nOriginal intent.\n"
    assert run(*prefix, "list", cwd=cwd) == "EVOLUTION.md:3: 初始意图\n"
    run(*prefix, "init", "--from", str(source), cwd=cwd, expected=2)
    assert path.read_bytes() == initial
    template = Path(__file__).resolve().parents[1] / "templates" / "evolution.md"
    original = template.read_bytes()
    path.write_bytes(original)
    assert run(*prefix, "check", cwd=cwd) == "Validated EVOLUTION.md.\n"
    assert run(*prefix, "list", cwd=cwd).splitlines() == ["EVOLUTION.md:3: 初始意图", "EVOLUTION.md:8: 2026-09-08"]
    assert path.read_bytes() == original
    path.write_text("# Missing origin\n", encoding="utf-8")
    run(*prefix, "check", cwd=cwd, expected=1)
    assert path.read_text() == "# Missing origin\n"
    path.write_bytes(original)


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
                module = run(str(python), "-m", "zendev", "evolution", "check", cwd=working)
                assert module == "Validated EVOLUTION.md.\n"
                unified = binaries / ("zendev.exe" if os.name == "nt" else "zendev")
                run(str(unified), "evolution", "check", cwd=working)
                assert "2026-09-08" in run(str(unified), "evolution", "list", cwd=working)
                run(str(unified), "evolution", "init", "--from", "origin.md", "--file", "other.md", cwd=working)
    print("Verified six non-overlapping wheels and standalone/complete evolution workflows.")


if __name__ == "__main__":
    main()
