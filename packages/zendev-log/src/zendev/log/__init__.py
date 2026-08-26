"""Loguru configuration for all projects."""

from __future__ import annotations

import os
import sys

from loguru import logger

_configured = False


def setup_log(*, verbose: bool = False, json: bool = False) -> int | None:
    """Configure loguru for CLI usage. Safe to call multiple times.

    Args:
        verbose: If True, set log level to DEBUG. Defaults to False (INFO).
        json: If True, use JSON serialization (CI-friendly). Defaults to False.

    Returns:
        The handler id on first call, ``None`` on subsequent calls.
    """
    global _configured
    if _configured:
        return None
    _configured = True

    logger.remove()

    env_level = os.environ.get("ZENDEV_LOG_LEVEL")
    level = env_level.upper() if env_level else ("DEBUG" if verbose else "INFO")

    if json:
        return logger.add(sys.stderr, level=level, serialize=True)
    fmt = "<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <7}</level> | <level>{message}</level>"
    return logger.add(sys.stderr, format=fmt, level=level, colorize=True)
