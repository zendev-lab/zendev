"""Markdown scanning used internally by proposal validation."""

from __future__ import annotations

from collections.abc import Iterator


def iter_lines_outside_fences(markdown: str) -> Iterator[str]:
    """Yield raw lines outside fenced code blocks."""

    in_fence = False
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield line
