"""PR metadata and policy rerun behavior with an isolated GitHub API."""

from __future__ import annotations

import copy
import io
import json
import os
import runpy
import subprocess
from email.message import Message
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / "actions/normalize-title/main.py"
normalize_title = runpy.run_path(str(ACTION))["normalize_title"]


def pull(title: str = "feat: add export") -> dict[str, Any]:
    return {
        "number": 12,
        "state": "open",
        "title": title,
        "head": {"repo": {"full_name": "contributor/project"}, "ref": "feature/export", "sha": "abc123"},
    }


def event(pr: dict[str, Any], *, workflow_run: bool = True) -> dict[str, Any]:
    if not workflow_run:
        return {"number": pr["number"], "pull_request": copy.deepcopy(pr)}
    return {
        "workflow_run": {
            "event": "pull_request",
            "conclusion": "failure",
            "head_repository": {"full_name": pr["head"]["repo"]["full_name"]},
            "head_branch": pr["head"]["ref"],
            "head_sha": pr["head"]["sha"],
            "id": 99,
        },
    }


class GitHub:
    def __init__(self, pr: dict[str, Any]) -> None:
        self.current = copy.deepcopy(pr)
        self.latest = copy.deepcopy(pr)
        self.pulls = [copy.deepcopy(pr)]
        self.calls: list[tuple[str, str, Any]] = []
        self.reads = 0

    def __call__(self, method: str, path: str, payload: Any = None) -> Any:
        self.calls.append((method, path, payload))
        if method == "GET" and path.startswith("pulls?"):
            return copy.deepcopy(self.pulls)
        if method == "GET":
            self.reads += 1
            return copy.deepcopy(self.current if self.reads == 1 else self.latest)
        if method == "PATCH":
            self.current["title"] = self.latest["title"] = payload["title"]
            return copy.deepcopy(self.current)
        if method == "POST":
            return None
        raise AssertionError((method, path, payload))

    @property
    def writes(self) -> list[tuple[str, str, Any]]:
        return [call for call in self.calls if call[0] != "GET"]


@pytest.mark.parametrize("workflow_run", [False, True])
def test_current_title_is_renamed_and_only_a_completed_policy_is_rerun(workflow_run: bool) -> None:
    pr = pull("[ImgBot] Optimize images")
    api = GitHub(pr)
    source = event(pr, workflow_run=workflow_run)
    if not workflow_run:
        source["pull_request"]["title"] = "stale event title"

    result = normalize_title(
        api, source, event_name="workflow_run" if workflow_run else "pull_request", profile="zendev"
    )

    title = "⚡️ perf(assets): optimize images"
    assert result == {"changed": "true", "title": title}
    assert api.writes == [
        ("PATCH", "pulls/12", {"title": title}),
        *([("POST", "actions/runs/99/rerun", None)] if workflow_run else []),
    ]


def test_rerun_is_idempotent() -> None:
    pr = pull()
    api = GitHub(pr)
    source = event(pr)
    normalize_title(api, source, event_name="workflow_run", profile="zendev")
    api.calls.clear()

    result = normalize_title(api, source, event_name="workflow_run", profile="zendev")

    assert result == {"changed": "false", "title": "✨ feat: add export"}
    assert not api.writes


@pytest.mark.parametrize("title", ["✨ feat: already valid", "deps: change dependencies", "ship it", "bad\ntitle"])
def test_valid_or_ambiguous_titles_do_not_write_or_rerun(title: str) -> None:
    pr = pull(title)
    api = GitHub(pr)

    result = normalize_title(api, event(pr), event_name="workflow_run", profile="zendev")

    assert result["changed"] == "false"
    assert not api.writes


@pytest.mark.parametrize("change", ["title", "sha", "repo", "closed"])
def test_concurrent_changes_are_not_overwritten(change: str) -> None:
    pr = pull()
    api = GitHub(pr)
    if change == "title":
        api.latest["title"] = "docs: authors updated title"
    elif change == "closed":
        api.latest["state"] = "closed"
    elif change == "repo":
        api.latest["head"]["repo"]["full_name"] = "different/project"
    else:
        api.latest["head"]["sha"] = "new-sha"

    result = normalize_title(api, event(pr), event_name="workflow_run", profile="zendev")

    assert result["changed"] == "false"
    assert not api.writes


@pytest.mark.parametrize("case", ["none", "multiple", "wrong-repo", "wrong-sha", "closed", "truncated"])
def test_workflow_run_requires_one_complete_current_match(case: str) -> None:
    pr = pull()
    api = GitHub(pr)
    if case == "none":
        api.pulls = []
    elif case == "multiple":
        api.pulls.append({**copy.deepcopy(pr), "number": 13})
    elif case == "truncated":
        api.pulls *= 100
    elif case == "wrong-repo":
        api.pulls[0]["head"]["repo"]["full_name"] = "impostor/project"
    elif case == "wrong-sha":
        api.current["head"]["sha"] = "new-sha"
    else:
        api.current["state"] = "closed"

    result = normalize_title(api, event(pr), event_name="workflow_run", profile="zendev")

    assert result["changed"] == "false"
    assert not api.writes


@pytest.mark.parametrize(("key", "value"), [("event", "push"), ("conclusion", "success"), ("head_repository", None)])
def test_unrelated_workflow_runs_do_not_query_prs(key: str, value: Any) -> None:
    pr = pull()
    api = GitHub(pr)
    source = event(pr)
    source["workflow_run"][key] = value

    assert normalize_title(api, source, event_name="workflow_run", profile="zendev")["changed"] == "false"
    assert not api.calls


def test_special_characters_remain_json_data() -> None:
    pr = pull('fix: handle $(touch /tmp/unwanted) `command` "quotes" %value')
    api = GitHub(pr)

    result = normalize_title(api, event(pr), event_name="workflow_run", profile="zendev")

    assert result["title"] == "🐛 " + pr["title"]
    assert api.writes[0][2] == {"title": "🐛 " + pr["title"]}


def test_api_permission_failure_is_not_silenced() -> None:
    def forbidden(*_args: Any) -> None:
        raise HTTPError("https://api.github.com", 403, "Forbidden", Message(), None)

    with pytest.raises(HTTPError):
        normalize_title(forbidden, event(pull()), event_name="workflow_run", profile="zendev")


@pytest.mark.parametrize("profile", ["conventional", "gitmoji"])
def test_other_profiles_do_not_get_a_zendev_conversion(profile: str) -> None:
    pr = pull()
    api = GitHub(pr)

    assert normalize_title(api, event(pr), event_name="workflow_run", profile=profile)["changed"] == "false"
    assert not api.writes


def test_validate_title_reads_live_metadata_when_policy_is_rerun(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    definition = yaml.safe_load((ROOT / "actions/validate-title/action.yml").read_text(encoding="utf-8"))
    script = definition["runs"]["steps"][-1]["run"]
    tools = tmp_path / "bin"
    tools.mkdir()
    for name, contents in {
        "gh": '#!/bin/sh\nprintf "%s\\n" "✨ feat: current title"\n',
        "uvx": (
            "#!/usr/bin/env python3\nimport json, os, sys\n"
            'open(os.environ["ARGUMENTS"], "w").write(json.dumps(sys.argv[1:]))\n'
        ),
    }.items():
        executable = tools / name
        executable.write_text(contents, encoding="utf-8")
        executable.chmod(0o755)
    monkeypatch.setenv("PATH", str(tools) + ":" + os.environ["PATH"])
    monkeypatch.setenv("ARGUMENTS", str(tmp_path / "arguments.json"))
    monkeypatch.setenv("GITHUB_ACTION_PATH", str(ROOT / "actions/validate-title"))
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/project")
    monkeypatch.setenv("INPUT_TEXT", "")
    monkeypatch.setenv("INPUT_PROFILE", "")
    monkeypatch.setenv("INPUT_PR_NUMBER", "12")

    process = subprocess.run(["bash", "-c", script], cwd=tmp_path, capture_output=True, text=True, check=False)

    assert process.returncode == 0, process.stderr
    args = json.loads((tmp_path / "arguments.json").read_text())
    assert args[args.index("--text") + 1] == "✨ feat: current title"


@pytest.mark.parametrize("forbidden", [False, True])
def test_action_entry_point_sends_json_and_writes_outputs_or_reports_api_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], forbidden: bool
) -> None:
    namespace = runpy.run_path(str(ACTION))
    main = namespace["main"]
    api = GitHub(pull('fix: handle "quotes" %value'))

    def urlopen(request: Any, *, timeout: int) -> io.BytesIO:
        assert timeout == 30
        assert request.get_header("Authorization") == "Bearer test-token"
        assert request.get_header("X-github-api-version") == "2026-03-10"
        if forbidden:
            raise HTTPError(request.full_url, 403, "Forbidden", Message(), None)
        path = request.full_url.removeprefix("https://api.github.com/repos/owner/project/")
        payload = json.loads(request.data) if request.data else None
        response = api(request.method, path, payload)
        return io.BytesIO(json.dumps(response).encode("utf-8") if response is not None else b"")

    monkeypatch.setitem(main.__globals__, "urlopen", urlopen)
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event(pull())), encoding="utf-8")
    output_path = tmp_path / "output"
    for key, value in {
        "GITHUB_REPOSITORY": "owner/project",
        "GITHUB_API_URL": "https://api.github.com",
        "GITHUB_EVENT_PATH": str(event_path),
        "GITHUB_EVENT_NAME": "workflow_run",
        "GITHUB_OUTPUT": str(output_path),
        "INPUT_PROFILE": "zendev",
        "INPUT_TOKEN": "test-token",
    }.items():
        monkeypatch.setenv(key, value)

    assert main() == (1 if forbidden else 0)
    if forbidden:
        assert not output_path.exists()
        assert "403" in capsys.readouterr().err
    else:
        assert output_path.read_text(encoding="utf-8") == 'changed=true\ntitle=🐛 fix: handle "quotes" %value\n'
        assert api.writes[-1] == ("POST", "actions/runs/99/rerun", None)
