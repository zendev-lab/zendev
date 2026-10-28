#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

rm -rf dist/
uv build --all-packages --wheel --out-dir dist
uvx --no-build check-wheel-contents==0.6.3 --package src/zendev dist/zendev-*.whl
uvx --no-build check-wheel-contents==0.6.3 --package packages/zendev-core/src/zendev dist/zendev_core-*.whl
uvx --no-build check-wheel-contents==0.6.3 --package packages/zendev-evolution/src/zendev dist/zendev_evolution-*.whl
uvx --no-build check-wheel-contents==0.6.3 --package packages/zendev-log/src/zendev dist/zendev_log-*.whl
uvx --no-build check-wheel-contents==0.6.3 --package packages/zendev-message/src/zendev dist/zendev_message-*.whl
uvx --no-build check-wheel-contents==0.6.3 --package packages/zendev-proposal/src/zendev dist/zendev_proposal-*.whl
uv run --no-build --isolated --no-project --no-config --find-links dist --with dist/zendev_core-*.whl python -I -c "import zendev.core.markdown"
uv run --no-build --isolated --no-project --no-config --find-links dist --with dist/zendev_log-*.whl python -I -c "import zendev.log"
uv run --no-build --isolated --no-project --no-config --find-links dist --with dist/zendev_evolution-*.whl zendev-evolution --help
uv run --no-build --isolated --no-project --no-config --find-links dist --with dist/zendev_message-*.whl zendev-message --help
uv run --no-build --isolated --no-project --no-config --find-links dist --with dist/zendev_message-*.whl zendev-commit --help
uv run --no-build --isolated --no-project --no-config --find-links dist --with dist/zendev_proposal-*.whl zendev-proposal --help
uv run --no-build --isolated --no-project --no-config --find-links dist --with dist/zendev-*.whl zendev --help
uv run --no-build --isolated --no-project --no-config --find-links dist --with dist/zendev-*.whl zendev --version
uv run --no-build --isolated --no-project --no-config --find-links dist --with dist/zendev-*.whl zendev message check --title --text "✨ feat: verify installed distribution"
uv run --no-build --isolated --no-project --no-config --find-links dist --with dist/zendev_message-*.whl python -I -c 'from zendev.message import normalize_message; original="feat: retain bytes\r\n\r\nBody  \r\n"; result=normalize_message(original); assert result.ok and result.text=="✨ "+original; assert not normalize_message(result.text).changed'
