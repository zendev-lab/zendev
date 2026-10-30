"""Run mutmut against a temporary src layout for the PEP 420 workspace."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    config = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["mutmut"]
    artifacts = root / ".artifacts/quality/mutation"
    if artifacts.exists():
        shutil.rmtree(artifacts)
    artifacts.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="zendev-mutmut-") as temporary:
        staged = Path(temporary)
        for source in [root / "src", *sorted((root / "packages").glob("*/src"))]:
            shutil.copytree(source, staged / "src", dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
        (staged / "tests").mkdir()
        shutil.copy2(root / "tests/test_conventional.py", staged / "tests/test_conventional.py")
        (staged / "pyproject.toml").write_text(
            "[tool.mutmut]\n" + "\n".join(f"{key} = {json.dumps(value)}" for key, value in config.items()) + "\n",
            encoding="utf-8",
        )
        result = subprocess.run([sys.executable, "-m", "mutmut", "run", "--max-children", "4"], cwd=staged, check=False)
        if result.returncode:
            return result.returncode
        report = subprocess.run(
            [sys.executable, "-m", "mutmut", "results"], cwd=staged, check=False, capture_output=True, text=True
        )
        print(report.stdout, end="")
        (artifacts / "results.txt").write_text(report.stdout, encoding="utf-8")
        for metadata in (staged / "mutants").rglob("*.meta"):
            shutil.copy2(metadata, artifacts / metadata.name)
        with (artifacts / "survivors.diff").open("w", encoding="utf-8") as output:
            for line in report.stdout.splitlines():
                if line.endswith(": survived"):
                    subprocess.run(
                        [sys.executable, "-m", "mutmut", "show", line.strip().removesuffix(": survived")],
                        cwd=staged,
                        stdout=output,
                        check=True,
                    )
        return report.returncode


if __name__ == "__main__":
    raise SystemExit(main())
