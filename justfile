set lazy

default:
    @just --list

# Install development dependencies and Git hooks
install:
    uv sync --frozen --all-packages --all-groups
    uvx prek install --prepare-hooks --hook-type pre-commit --hook-type commit-msg

# Run the repository gate
check:
    uvx prek run --all-files
    just --fmt --check --unstable

# Run tests
test:
    uv run --frozen pytest

# Run tests with coverage
cov:
    uv run --frozen pytest --cov=zendev --cov-report=html --cov-report=xml

# Run the repository gate and tests with coverage
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
    {{ isolated }} dist/zendev-*.whl zendev --version

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

# Serve documentation locally
docs:
    uv run --frozen --group docs zensical serve --open

# Validate and build documentation
docs-build:
    uv run --frozen --group docs zensical build --strict

# Refresh the offline gitmoji catalog from its pinned upstream revision
sync-gitmoji:
    uv run --frozen python scripts/sync_gitmoji.py
