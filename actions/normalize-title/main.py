"""GitHub metadata adapter; never reads PR files or workflow artifacts."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from zendev.message import MessageProfile, normalize_message

Api = Callable[..., Any]
Head = tuple[str, str, str]


def _head(pr: dict[str, Any]) -> Head:
    head = pr["head"]
    return (head.get("repo") or {}).get("full_name", ""), head["ref"], head["sha"]


def _notice(message: str) -> None:
    print("::notice::" + message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A"))


def _target(api: Api, event: dict[str, Any], event_name: str) -> tuple[int, Head, int | None] | None:
    if event_name == "pull_request":
        return int(event["number"]), _head(event["pull_request"]), None
    if event_name != "workflow_run":
        raise ValueError("normalize-title requires a pull_request or workflow_run event")
    run = event["workflow_run"]
    if run["event"] != "pull_request" or run["conclusion"] != "failure":
        return None
    head_repo = (run.get("head_repository") or {}).get("full_name", "")
    if not head_repo or not run.get("head_branch") or not run.get("head_sha"):
        return None
    expected = head_repo, run["head_branch"], run["head_sha"]
    query = urlencode({"state": "open", "head": f"{head_repo.split('/')[0]}:{expected[1]}", "per_page": 100})
    pulls = api("GET", f"pulls?{query}")
    candidates = [pr for pr in pulls if pr["state"] == "open" and _head(pr) == expected]
    if len(pulls) == 100 or len(candidates) != 1:
        return None
    return int(candidates[0]["number"]), expected, int(run["id"])


def normalize_title(api: Api, event: dict[str, Any], *, event_name: str, profile: str) -> dict[str, str]:
    selected = MessageProfile(profile)
    output = {"changed": "false", "title": ""}
    target = _target(api, event, event_name)
    if target is None:
        return output
    number, expected, run_id = target

    path = f"pulls/{number}"
    current = api("GET", path)
    if current["state"] != "open" or _head(current) != expected:
        return output
    title = current["title"]
    if "\n" in title or "\r" in title:
        _notice("The PR title must be a single line; choose a normalized title manually.")
        return output
    output["title"] = title
    result = normalize_message(title, profile=selected)
    if not result.ok:
        _notice("The PR title needs an explicit intention: " + result.diagnostics[0].message)
        return output
    if not result.changed:
        return output

    latest = api("GET", path)
    if latest["state"] != "open" or _head(latest) != expected or latest["title"] != title:
        _notice("The PR changed while its title was being checked; skipping this event.")
        return {"changed": "false", "title": ""}
    renamed = api("PATCH", path, {"title": result.text})
    if renamed["title"] != result.text:
        raise ValueError("GitHub did not return the requested title after the rename")
    output = {"changed": "true", "title": result.text}
    print("Normalized PR title: " + result.text)
    if run_id is not None:
        api("POST", f"actions/runs/{run_id}/rerun")
    return output


def main() -> int:
    repository = os.environ["GITHUB_REPOSITORY"]
    base_url = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    token = os.environ["INPUT_TOKEN"]

    def api(method: str, path: str, payload: dict[str, str] | None = None) -> Any:
        request = Request(
            f"{base_url}/repos/{repository}/{path}",
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2026-03-10",
            },
            method=method,
        )
        with urlopen(request, timeout=30) as response:
            content = response.read()
        return json.loads(content) if content else None

    try:
        output = normalize_title(
            api,
            json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8")),
            event_name=os.environ["GITHUB_EVENT_NAME"],
            profile=os.environ["INPUT_PROFILE"],
        )
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as stream:
            for key, value in output.items():
                stream.write(f"{key}={value}\n")
    except (OSError, ValueError) as error:
        print(f"PR title normalization failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
