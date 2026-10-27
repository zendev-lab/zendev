default:
    @just --list

# Install development dependencies and Git hooks
install:
    uv sync --frozen --all-packages --all-groups
    uvx prek==0.5.7 install --prepare-hooks

# Run the repository gate
check:
    uvx prek==0.5.7 run --all-files
    just --fmt --check --unstable

# Run tests
test:
    uv run --frozen pytest

# Run tests with coverage
cov:
    uv run --frozen pytest --cov=zendev --cov-report=html --cov-report=xml

# Run the repository gate and tests with coverage
ci: check cov

# Report a bounded mutation campaign against the Conventional Commits parser
mutate:
    uv run --frozen --group quality python scripts/check_mutations.py

# Record local walltime samples; CodSpeed uses the same cases in CI
benchmark:
    mkdir -p .artifacts/quality
    uv run --frozen --group quality pytest benchmarks --benchmark-json=.artifacts/quality/benchmark.json

# Complexity remains a report until a project-specific budget is established
complexity:
    mkdir -p .artifacts/quality
    uv run --frozen --group quality radon cc src packages -s -j > .artifacts/quality/complexity.json

# Report exact clones in production Python without a universal percentage gate
duplication:
    npx --yes jscpd@5.4.2 --format python --reporters json,console --output .artifacts/quality/duplication src packages

# Explicit local repair commands
fix:
    uvx ruff==0.17.2 check --fix .
    uvx ruff==0.17.2 format .

wheel_check := "uvx check-wheel-contents==0.6.3"
isolated := "uv run --isolated --no-project --no-config --find-links dist --with"

# Build wheels, then check their contents and isolated installations
packages:
    rm -rf dist/
    uv build --all-packages --wheel --out-dir dist
    {{ wheel_check }} --package src/zendev dist/zendev-*.whl
    {{ wheel_check }} --package packages/zendev-core/src/zendev dist/zendev_core-*.whl
    {{ wheel_check }} --package packages/zendev-evolution/src/zendev dist/zendev_evolution-*.whl
    {{ wheel_check }} --package packages/zendev-log/src/zendev dist/zendev_log-*.whl
    {{ wheel_check }} --package packages/zendev-message/src/zendev dist/zendev_message-*.whl
    {{ wheel_check }} --package packages/zendev-proposal/src/zendev dist/zendev_proposal-*.whl
    {{ isolated }} dist/zendev_core-*.whl python -I -c "import zendev.core.markdown"
    {{ isolated }} dist/zendev_log-*.whl python -I -c "import zendev.log"
    {{ isolated }} dist/zendev_evolution-*.whl zendev-evolution --help
    {{ isolated }} dist/zendev_message-*.whl zendev-message --help
    {{ isolated }} dist/zendev_message-*.whl zendev-commit --help
    {{ isolated }} dist/zendev_proposal-*.whl zendev-proposal --help
    {{ isolated }} dist/zendev-*.whl zendev --help
    {{ isolated }} dist/zendev-*.whl zendev --version
    {{ isolated }} dist/zendev-*.whl zendev message check --title --text "✨ feat: verify installed distribution"
    {{ isolated }} dist/zendev_message-*.whl python -I -c 'from zendev.message import normalize_message; original="feat: retain bytes\r\n\r\nBody  \r\n"; result=normalize_message(original); assert result.ok and result.text=="✨ "+original; assert not normalize_message(result.text).changed'

# Serve documentation locally
docs:
    uv run --frozen --group docs zensical serve --open

# Validate and build documentation
docs-build:
    uv run --frozen --group docs zensical build --strict

# Refresh the offline gitmoji catalog from its pinned upstream revision
sync-gitmoji:
    uv run --frozen python scripts/sync_gitmoji.py
