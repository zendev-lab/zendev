"""Shared Markdown scanning helpers for PR template validators."""

from __future__ import annotations

from collections.abc import Iterator


def iter_lines_outside_fences(markdown: str) -> Iterator[str]:
    """Yield each raw line that lies outside `` ``` `` fenced blocks.

    Toggle fence state on lines whose stripped form starts with `` ``` `` (CommonMark / GFM style).
    Opening/closing fences are not yielded.
    """
    in_fence = False
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        yield line
