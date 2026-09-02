"""Refresh the vendored gitmoji catalog from a pinned upstream revision."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Annotated, Any

import typer

DEFAULT_UPSTREAM_COMMIT = "3022406c3c0f0631572b50c7722a7f2a0bed1541"
DEFAULT_SOURCE_URL = (
    "https://raw.githubusercontent.com/carloscuesta/gitmoji/"
    f"{DEFAULT_UPSTREAM_COMMIT}/packages/gitmojis/src/gitmojis.json"
)
DEFAULT_OUTPUT = Path(__file__).parents[1] / "packages" / "zendev-commit" / "src" / "zendev" / "data" / "gitmojis.json"

app = typer.Typer(
    add_completion=False,
    help=__doc__,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
)


def _validated_catalog(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or not isinstance(payload.get("gitmojis"), list):
        raise ValueError("Upstream payload must contain a gitmojis list.")

    required = {"emoji", "code", "description", "name", "semver"}
    seen_emojis: set[str] = set()
    seen_codes: set[str] = set()
    for index, entry in enumerate(payload["gitmojis"]):
        if not isinstance(entry, dict) or not required.issubset(entry):
            raise ValueError(f"Gitmoji entry {index} is missing required fields.")
        emoji = entry["emoji"]
        code = entry["code"]
        if not isinstance(emoji, str) or not isinstance(code, str):
            raise ValueError(f"Gitmoji entry {index} has an invalid emoji or code.")
        if emoji in seen_emojis or code in seen_codes:
            raise ValueError(f"Gitmoji entry {index} duplicates {emoji!r} or {code!r}.")
        seen_emojis.add(emoji)
        seen_codes.add(code)

    return {
        "$schema": payload.get("$schema"),
        "gitmojis": payload["gitmojis"],
    }


@app.command()
def sync_catalog(
    output: Annotated[Path, typer.Option("--output", help="Vendored catalog path.")] = DEFAULT_OUTPUT,
) -> None:
    """Refresh the pinned catalog after validating its external payload."""

    with urllib.request.urlopen(DEFAULT_SOURCE_URL, timeout=30) as response:
        payload = json.load(response)

    catalog = _validated_catalog(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(catalog['gitmojis'])} gitmojis to {output}")


def main() -> None:
    app(prog_name="sync-gitmoji")


if __name__ == "__main__":
    main()
