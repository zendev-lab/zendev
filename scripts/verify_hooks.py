"""Exercise the published hook manifest against local, same-version wheels."""

from __future__ import annotations

import email
import json
import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    subprocess.run(["git", "diff", "--exit-code", "HEAD"], cwd=root, check=True, capture_output=True)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    with TemporaryDirectory(prefix="zendev-hooks-") as folder:
        temporary = Path(folder)
        wheels = temporary / "wheels"
        subprocess.run(["uv", "build", "--all-packages", "--wheel", "--out-dir", str(wheels)], cwd=root, check=True)
        component_wheels = sorted(wheels.glob("zendev_*.whl"))
        with ZipFile(component_wheels[0]) as archive:
            metadata = email.message_from_bytes(
                archive.read(next(n for n in archive.namelist() if n.endswith("/METADATA")))
            )
        environment = {
            **os.environ,
            "SETUPTOOLS_SCM_PRETEND_VERSION": metadata["Version"],
            "UV_NO_SOURCES": "true",
        }
        config = temporary / "prek.toml"
        dependencies = json.dumps([str(path) for path in component_wheels])
        config.write_text(
            f"[[repos]]\nrepo = {json.dumps(root.as_uri())}\nrev = {json.dumps(revision)}\nhooks = [\n"
            f'  {{ id = "zendev-proposal-check", additional_dependencies = {dependencies} }},\n'
            f'  {{ id = "zendev-message-check", additional_dependencies = {dependencies} }},\n]\n'
        )
        command = ["uvx", "prek", "run", "--config", str(config)]
        subprocess.run([*command, "zendev-proposal-check", "--all-files"], cwd=root, env=environment, check=True)
        message = temporary / "COMMIT_EDITMSG"
        message.write_text("Merge branch main\n")
        subprocess.run(
            [*command, "zendev-message-check", "--stage", "commit-msg", "--commit-msg-filename", str(message)],
            cwd=root,
            env=environment,
            check=True,
        )
        subprocess.run(["git", "diff", "--exit-code", "HEAD"], cwd=root, check=True)


if __name__ == "__main__":
    main()
