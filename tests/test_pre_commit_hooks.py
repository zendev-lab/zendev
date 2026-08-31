"""Contract tests for the public pre-commit hook manifest."""

from pathlib import Path

import yaml


def _hooks() -> dict[str, dict[str, object]]:
    manifest = Path(__file__).parents[1] / ".pre-commit-hooks.yaml"
    payload = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert all(isinstance(hook, dict) and isinstance(hook.get("id"), str) for hook in payload)
    return {hook["id"]: hook for hook in payload}


def test_public_hook_manifest_exposes_every_supported_lifecycle() -> None:
    hooks = _hooks()

    assert set(hooks) == {
        "zendev-commit-msg",
        "zendev-proposal",
        "zendev-proposal-index",
    }
    assert hooks["zendev-commit-msg"]["stages"] == ["commit-msg"]

    proposal = hooks["zendev-proposal"]
    assert proposal["entry"] == "zendev-proposal check"
    assert proposal["pass_filenames"] is False
    assert proposal["always_run"] is True
    assert proposal["stages"] == ["pre-commit"]

    index = hooks["zendev-proposal-index"]
    assert index["entry"] == "zendev-proposal index --write"
    assert index["pass_filenames"] is False
    assert index["always_run"] is True
    assert index["stages"] == ["manual"]
