default:
    @just --list

# Install development dependencies and Git hooks
install:
    uv sync --frozen --all-packages --all-groups
    uvx --isolated prek install --prepare-hooks

# Run the repository gate
check:
    uvx --isolated prek run --all-files
    just --fmt --check --unstable

# Run tests
test:
    uv run --frozen pytest

# Run tests with coverage
coverage:
    uv run --frozen pytest --cov=zendev --cov-report=html --cov-report=xml

# Run the repository gate and tests with coverage
ci: check coverage

# Record local walltime samples; CodSpeed uses the same cases in CI
benchmark:
    mkdir -p .artifacts/quality
    uv run --frozen --group quality pytest benchmarks --benchmark-json=.artifacts/quality/benchmark.json

# Explicit local repair commands
format:
    uvx ruff==0.17.2 check --fix .
    uvx ruff==0.17.2 format .

# Build all workspace distributions
build:
    uv build --all-packages

# Serve documentation locally
docs:
    uv run --frozen --group docs zensical serve --open

# Validate and build documentation
docs-build:
    uv run --frozen --group docs zensical build --strict
