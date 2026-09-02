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

# Type checking and linting
check:
    uvx ruff check --fix
    uvx ty check .
    uvx pyrefly check

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

# Full CI check (format + check + test with coverage)
ci: format check cov

# Run pre-commit on all files
pre-commit:
    uvx prek run --all-files

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
