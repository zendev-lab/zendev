set lazy

# List all available commands
default:
    @just --list

# Create virtual environment
venv:
    uv venv

# Install dependencies in development mode
install:
    uv sync --all-packages --all-groups
    uvx prek install

# Format all code (Python + justfile)
format:
    just --fmt --unstable
    uvx ruff format
    uvx ruff check --fix

# Read-only formatting, lint, and type checks
check:
    just --fmt --check --unstable
    uvx ruff format --check
    uvx ruff check
    uvx ty check .
    uv run pyrefly check

# Run all tests
test:
    uv run pytest -v

# Run tests with coverage
cov:
    uv run pytest --cov=zendev --cov-report=html --cov-report=xml
    uv run coverage xml

# Generate and open HTML coverage report
cov-open:
    just cov
    open htmlcov/index.html || xdg-open htmlcov/index.html

# Clean build artifacts
clean:
    rm -rf .pytest_cache/
    rm -rf .ruff_cache/
    rm -rf htmlcov/
    rm -rf dist/
    rm -rf build/
    rm -rf *.egg-info/
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true

# Read-only CI checks and tests (generated coverage is not tracked)
ci: check cov

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

scm_version := `uvx --with hatch-vcs==0.5.0 hatchling==1.32.4 version`
hook_env := "UV_NO_SOURCES=true UV_FIND_LINKS=" + justfile_directory() / "dist" + " SETUPTOOLS_SCM_PRETEND_VERSION=" + scm_version

# Install the published hooks from the committed checkout against the wheels in dist/
hooks: packages
    git diff --exit-code HEAD
    {{ hook_env }} uvx prek try-repo . zendev-proposal-check --all-files
    echo "Merge branch main" > dist/COMMIT_EDITMSG
    {{ hook_env }} uvx prek try-repo . zendev-message-check --stage commit-msg --commit-msg-filename dist/COMMIT_EDITMSG
    git init -q dist/hook-repo
    cp templates/evolution.md dist/hook-repo/EVOLUTION.md
    git -C dist/hook-repo add EVOLUTION.md
    {{ hook_env }} uvx prek try-repo -C dist/hook-repo {{ justfile_directory() }} zendev-evolution-check --all-files
    git diff --exit-code HEAD

# Run pre-commit on all files
pre-commit:
    uvx prek run --all-files

# Serve documentation locally
docs:
    uv run --group docs zensical serve --open

# Validate and build documentation
docs-build:
    uv run --group docs zensical build --strict

# Validate the current commit message file
commit-msg:
    uvx prek run --stage commit-msg --commit-msg-filename .git/COMMIT_EDITMSG --files .git/COMMIT_EDITMSG

# Refresh the offline gitmoji catalog from its pinned upstream revision
sync-gitmoji:
    uv run python scripts/sync_gitmoji.py

# Display project information
info:
    @echo "=== zendev ==="
    @echo "uv: $(uv --version)"
    @echo "Python: $(uv run python --version)"
