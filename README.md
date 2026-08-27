# zendev

`zendev` is a repository-native development workflow toolkit. It provides
commit conventions, pull-request checks, and proposal-repository mechanics as
typed Python CLIs and thin GitHub Action or hook adapters.

## Scope

This repository owns reusable workflow mechanisms:

- commit-message creation and validation
- PR title, body, and checklist validation
- proposal frontmatter, graph, history, and index validation

Consuming repositories continue to own their schemas, templates, terminology,
semantic checks, lifecycle policy, and proposal decisions. Git and committed
repository files remain the source of truth.

## Installation

Run a published command without installing it globally:

```console
$ uvx --from zendev zendev-commit-msg --help
```

For local development:

```console
$ uv sync --all-groups
$ uv run zendev-proposal --help
```

Python 3.12 or newer is required. All command-line entry points use Typer.

## Commands

| Command | Purpose |
| --- | --- |
| `zendev-commit` | Create and run an interactive commit. |
| `zendev-commit-msg` | Validate a Git commit-message file. |
| `zendev-validate-title` | Validate a PR title. |
| `zendev-validate-body` | Validate PR body sections and optional checklist rows. |
| `zendev-proposal check` | Validate a proposal repository and its committed index. |
| `zendev-proposal index --check` | Check the deterministic proposal index. |
| `zendev-proposal index --write` | Explicitly update the proposal index. |

Use `COMMAND --help` for the authoritative option reference.

## Workflows

- [Zendev Feature Proposals](./zfps/README.md): lightweight design records
  required before public feature changes.
- [Commit conventions](./docs/commit-conventions.md): profiles, commit hook,
  configuration, and vendored Gitmoji data.
- [PR review checks](./docs/review-checks.md): title/body CLIs and composite
  GitHub Actions.
- [Proposal repositories](./docs/proposals.md): policy schema, validation,
  lifecycle history, and deterministic indexes.

## Development

```console
$ just install
$ just ci
$ just pre-commit
```

`just ci` runs formatting, linting, type checks, tests, and coverage. The
repository uses `uv`, Ruff, ty, Pyright, pytest, and prek; `pyproject.toml` is
the Python configuration source of truth.
