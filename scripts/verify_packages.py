"""Build and exercise each distribution in an isolated consumer environment."""

from __future__ import annotations

import email
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

PACKAGES = {
    "zendev": {"zendev", "zendev-core", "zendev-message", "zendev-proposal", "zendev-log"},
    "zendev-core": {"zendev-core"},
    "zendev-message": {"zendev-message", "zendev-core"},
    "zendev-proposal": {"zendev-proposal", "zendev-core"},
    "zendev-log": {"zendev-log"},
}


def run(*args: str, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def verify(directory: Path, temporary: Path) -> None:
    wheels: dict[str, Path] = {}
    versions = set()
    owned: dict[str, str] = {}
    for path in sorted(directory.glob("*.whl")):
        with ZipFile(path) as archive:
            metadata = email.message_from_bytes(
                archive.read(next(n for n in archive.namelist() if n.endswith("/METADATA")))
            )
            name, version = metadata["Name"], metadata["Version"]
            assert name in PACKAGES and name not in wheels, f"Unexpected/duplicate wheel: {path}"
            wheels[name] = path
            versions.add(version)
            siblings = set()
            for requirement in metadata.get_all("Requires-Dist", []):
                if requirement.startswith("zendev-"):
                    sibling, separator, pinned = requirement.partition("==")
                    assert separator and pinned == version, (name, requirement, version)
                    siblings.add(sibling)
            expected = (
                PACKAGES[name] - {name}
                if name == "zendev"
                else ({"zendev-core"} if name in {"zendev-message", "zendev-proposal"} else set())
            )
            assert siblings == expected, (name, siblings)
            for member in archive.namelist():
                if not member.startswith("zendev/") or member.endswith("/"):
                    continue
                assert member not in owned, (member, name, owned.get(member))
                owned[member] = name
    assert set(wheels) == set(PACKAGES) and len(versions) == 1, (wheels, versions)
    assert "zendev/__init__.py" not in owned
    for component in ("core", "message", "proposal", "log"):
        assert f"zendev/{component}/py.typed" in owned
    for name, expected in PACKAGES.items():
        environment = temporary / name
        run("uv", "venv", "--python", sys.executable, str(environment), cwd=temporary)
        executable = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        run(
            "uv",
            "pip",
            "install",
            "--python",
            str(executable),
            "--find-links",
            str(directory),
            str(wheels[name]),
            cwd=temporary,
        )
        run("uv", "pip", "check", "--python", str(executable), cwd=temporary)
        program = """
import importlib.metadata as md
installed = {d.metadata["Name"] for d in md.distributions() if d.metadata["Name"].startswith("zendev")}
assert installed == EXPECTED, installed
if "zendev-core" in installed:
    from zendev.core.markdown import scan_markdown
    assert scan_markdown("## Heading").headings[0].text == "Heading"
if "zendev-message" in installed:
    from zendev.message import MessageDraft, check_message, render_message
    from zendev.message.gitmoji import load_gitmojis
    assert len(load_gitmojis()) == 75
    assert check_message("⬇️ deps: downgrade").ok
    assert not check_message("⬆️ deps-up: upgrade").ok
    assert render_message(MessageDraft("add", "feat", "sparkles")) == "✨ feat: add"
if "zendev-proposal" in installed:
    from zendev.proposal import load_config, check_project, plan_changes
if "zendev-log" in installed:
    from zendev.log import setup_log
    setup_log()
""".replace("EXPECTED", repr(expected))
        run(str(executable), "-I", "-c", program, cwd=temporary)
        bin_dir = executable.parent
        commands = []
        if name == "zendev":
            commands += [
                ("zendev", ["--help"]),
                ("zendev", ["message", "check", "--commit", "--text", "Merge branch main"]),
            ]
        if "zendev-message" in expected:
            commands += [
                ("zendev-commit", ["--help"]),
                ("zendev-message", ["check", "--title", "--text", "✨ feat: add", "--format", "json"]),
            ]
        if "zendev-proposal" in expected:
            commands += [("zendev-proposal", ["--help"])]
        for command, args in commands:
            binary = bin_dir / (command + ".exe" if sys.platform == "win32" else command)
            completed = subprocess.run([str(binary), *args], cwd=temporary, check=True, capture_output=True, text=True)
            if args[-1] == "json":
                assert json.loads(completed.stdout)["ok"]
        print(f"Verified independent installation: {name}", flush=True)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    with TemporaryDirectory(prefix="zendev-packages-") as folder:
        temporary = Path(folder)
        directory = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else temporary / "wheels"
        if len(sys.argv) == 1:
            run("uv", "build", "--all-packages", "--wheel", "--out-dir", str(directory), cwd=root)
        verify(directory, temporary)


if __name__ == "__main__":
    main()
