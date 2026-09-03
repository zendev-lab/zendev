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
| `zendev-review` | Commit and pull-request message validation |
| `zendev-proposal` | Proposal validation and deterministic indexes |
| `zendev-log` | Loguru setup helper |

For example, run published commands without installing them globally:

```shell
uvx --from zendev zendev --help
uvx --from zendev-commit zendev-commit --help
uvx --from zendev-review zendev-message --help
uvx --from zendev-proposal zendev-proposal --help
```

For local development:

```shell
uv sync --all-packages --all-groups
uv run zendev --help
```

Python 3.12 or newer is required. All command-line entry points use Typer.
`python -m zendev` exposes the same command tree as `zendev`.

Version 0.2.0 removes the logging re-export from the root namespace. For
logging-only use, install `zendev-log` and import it directly:

```shell
uv add zendev-log
```

```python
from zendev.log import setup_log
```

`from zendev import setup_log` is no longer supported.

## Commands

| Unified command | Component command | Purpose |
| --- | --- | --- |
| `zendev commit` | `zendev-commit` | Create and run an interactive commit. |
| `zendev message check [FILE]` | `zendev-message check [FILE]` | Validate a commit or pull-request message. |
| `zendev proposal check` | `zendev-proposal check` | Validate a proposal repository and its committed index. |
| `zendev proposal check --fix` | `zendev-proposal check --fix` | Write the deterministic proposal index. |

`message check` takes `FILE` or `--text`. Default scope is auto: one line
checks the title, and a multi-line input checks the complete commit message.
`--title` and `--body` select a single part. `--body` uses the pull-request
template schema; a complete message does not.

Public hooks are `zendev-message-check` and `zendev-proposal-check`. They run
the matching `check` command. Add CLI flags through hook `args`, for example
`args = ["--fix"]` on `zendev-proposal-check`.

The complete `zendev` distribution always provides the `proposal` group. The
standalone component command does not require `zendev`.

Use `COMMAND --help` for the authoritative option reference.

## Workflows

- [Zendev Feature Proposals](./zfps/README.md): lightweight design records
  required before public feature changes.
- [`zendev-commit`](./packages/zendev-commit/README.md): profiles, message hook,
  configuration, and vendored Gitmoji data.
- [`zendev-review`](./packages/zendev-review/README.md): message check behavior.
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
