"""Tests for zendev.log."""

from __future__ import annotations

import io

import pytest
from loguru import logger

import zendev.log as log_mod
from zendev.log import setup_log


class TestSetupLog:
    """Tests for setup_log()."""

    def setup_method(self) -> None:
        """Reset loguru state before each test."""
        logger.remove()
        log_mod._configured = False

    def test_default_returns_handler_id(self) -> None:
        handler_id = setup_log()
        assert isinstance(handler_id, int)

    def test_idempotent(self) -> None:
        first = setup_log()
        second = setup_log()
        assert isinstance(first, int)
        assert second is None

    def test_verbose_sets_debug_level(self) -> None:
        logger.remove()
        buf = io.StringIO()
        log_mod._configured = False
        handler_id = setup_log(verbose=True)
        assert handler_id is not None
        logger.remove(handler_id)
        test_id = logger.add(buf, level="DEBUG", format="{level} {message}")
        logger.debug("test-debug-msg")
        logger.remove(test_id)
        assert "test-debug-msg" in buf.getvalue()

    def test_json_mode(self) -> None:
        logger.remove()
        buf = io.StringIO()
        log_mod._configured = False
        handler_id = setup_log(json=True)
        assert handler_id is not None
        logger.remove(handler_id)
        test_id = logger.add(buf, level="INFO", serialize=True)
        logger.info("test-json-msg")
        logger.remove(test_id)
        output = buf.getvalue()
        assert '"text"' in output

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ZENDEV_LOG_LEVEL", "WARNING")
        logger.remove()
        buf = io.StringIO()
        log_mod._configured = False
        handler_id = setup_log()
        assert handler_id is not None
        logger.remove(handler_id)
        test_id = logger.add(buf, level="WARNING", format="{level} {message}")
        logger.info("should-not-appear")
        logger.warning("should-appear")
        logger.remove(test_id)
        output = buf.getvalue()
        assert "should-not-appear" not in output
        assert "should-appear" in output
