"""Support ``python -m zendev`` through the unified CLI owner."""

from __future__ import annotations

from zendev.cli import app, main

__all__ = ["app", "main"]


if __name__ == "__main__":
    main()
