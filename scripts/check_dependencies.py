"""Adapt the workspace's Hatch dependency declarations to deptry's PEP 621 input."""

from __future__ import annotations

import json
import subprocess
import tempfile
import tomllib
from pathlib import Path


def check_distribution(root: Path) -> int:
    manifest = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project = manifest["project"]
    if "dependencies" in project.get("dynamic", []):
        dependencies = manifest["tool"]["hatch"]["metadata"]["hooks"]["custom"]["dependencies"]
    else:
        dependencies = project.get("dependencies", [])
    dependencies = [value.replace("{version}", "0") for value in dependencies]
    siblings = [value.partition("==")[0] for value in dependencies if value.startswith("zendev-")]
    # deptry resolves the shared namespace as one module. Import Linter and alint
    # enforce sibling ownership and declarations; deptry checks external dependencies.
    config = (
        f"[project]\nname = {json.dumps(project['name'])}\n"
        f"dependencies = {json.dumps(dependencies)}\n"
        '[tool.deptry]\nknown_first_party = ["zendev"]\n'
        f"[tool.deptry.per_rule_ignores]\nDEP002 = {json.dumps(siblings)}\n"
    )
    with tempfile.TemporaryDirectory(prefix="zendev-deptry-") as temporary:
        path = Path(temporary) / "pyproject.toml"
        path.write_text(config, encoding="utf-8")
        return subprocess.run(["deptry", str(root / "src"), "--config", str(path)], check=False).returncode


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    distributions = [root, *(path.parent for path in sorted((root / "packages").glob("*/pyproject.toml")))]
    return max(check_distribution(path) for path in distributions)


if __name__ == "__main__":
    raise SystemExit(main())
