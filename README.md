# zendev

Zendev is a repository-native development workflow toolkit. It provides commit
conventions, pull-request checks, proposal-repository mechanics, and a small
logging helper as typed Python packages and thin GitHub Action or hook adapters.

## Scope

This repository owns reusable workflow mechanisms:

- commit-message creation and validation
- PR title, body, and checklist validation
- proposal frontmatter, graph, history, and index validation

Consuming repositories continue to own their schemas, templates, terminology,
semantic checks, lifecycle policy, and proposal decisions. Git and committed
repository files remain the source of truth.

## Installation

Install `zendev` for the complete toolkit and unified command. It installs all
four component distributions as required dependencies. The components remain
available separately for narrower use:

| Distribution | Purpose |
| --- | --- |
| `zendev` | Complete toolkit and unified CLI |
| `zendev-commit` | Commit profiles, validation, and interactive commits |
| `zendev-review` | Pull-request title and body validation |
| `zendev-proposal` | Proposal validation and deterministic indexes |
| `zendev-log` | Loguru setup helper |

For example, run published commands without installing them globally:

```console
$ uvx --from zendev zendev --help
$ uvx --from zendev-commit zendev-commit-msg --help
$ uvx --from zendev-review zendev-validate-body --help
$ uvx --from zendev-proposal zendev-proposal --help
```

For local development:

```console
$ uv sync --all-packages --all-groups
$ uv run zendev --help
```

Python 3.12 or newer is required. All command-line entry points use Typer.
`python -m zendev` exposes the same command tree as `zendev`.

Version 0.2.0 removes the logging re-export from the root namespace. For
logging-only use, install `zendev-log` and import it directly:

```console
$ uv add zendev-log
```

```python
from zendev.log import setup_log
```

`from zendev import setup_log` is no longer supported.

## Commands

| Unified command | Compatibility command | Purpose |
| --- | --- | --- |
| `zendev commit` | `zendev-commit` | Create and run an interactive commit. |
| `zendev commit-msg` | `zendev-commit-msg` | Validate a Git commit-message file. |
| `zendev validate-title` | `zendev-validate-title` | Validate a PR title. |
| `zendev validate-body` | `zendev-validate-body` | Validate PR body sections and optional checklist rows. |
| `zendev proposal check` | `zendev-proposal check` | Validate a proposal repository and its committed index. |
| `zendev proposal index --check` | `zendev-proposal index --check` | Check the deterministic proposal index. |
| `zendev proposal index --write` | `zendev-proposal index --write` | Explicitly update the proposal index. |

The complete `zendev` distribution always provides the `proposal` group. The
standalone component command does not require `zendev`.

Use `COMMAND --help` for the authoritative option reference.

## Workflows

- [Zendev Feature Proposals](./zfps/README.md): lightweight design records
  required before public feature changes.
- [`zendev-commit`](./packages/zendev-commit/README.md): profiles, commit hook,
  configuration, and vendored Gitmoji data.
- [`zendev-review`](./packages/zendev-review/README.md): title and body
  validation behavior.
- [`zendev-proposal`](./packages/zendev-proposal/README.md): policy schema, validation,
  lifecycle history, and deterministic indexes.
- [Composite Actions](./actions/README.md): GitHub workflow integration for
  review checks.
- [`zendev-log`](./packages/zendev-log/README.md): Loguru initialization.

## Development

See [CONTRIBUTING.md](./CONTRIBUTING.md) for setup, validation, documentation
ownership, vendored-data maintenance, and pull-request conventions. The five
distributions share one uv workspace, lockfile, version, and release tag while
contributing independent portions of the PEP 420 `zendev` namespace.
