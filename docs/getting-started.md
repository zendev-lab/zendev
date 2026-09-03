# Getting started

Zendev requires Python 3.12 or newer. The examples use
[uv](https://docs.astral.sh/uv/), but the distributions are ordinary Python
packages.

## Choose an installation

Install the complete toolkit when a repository uses more than one workflow:

```shell
uv add --dev zendev
```

Run a published command without adding a project dependency:

```shell
uvx zendev --help
```

For a narrower consumer, install a component distribution directly:

```shell
uv add --dev zendev-commit
uv add --dev zendev-review
uv add --dev zendev-proposal
uv add zendev-log
```

## Verify the unified CLI

```shell
uv run zendev --help
uv run zendev message check --title --text "✨ feat: add documentation"
```

`python -m zendev` exposes the same command tree as `zendev`.

## Pick the first workflow

Use [Commits](guides/commits.md) to choose a message profile and create commits,
[Message checks](guides/message-checks.md) to validate commit or pull-request
text, or [Proposals](guides/proposals.md) to validate a proposal repository and
its deterministic index.

For automated enforcement, continue with [prek](integrations/prek.md) or
[GitHub Actions](integrations/github-actions.md).

## Develop zendev itself

Clone the repository, then install all workspace packages and groups:

```shell
git clone https://github.com/zendev-lab/zendev.git
cd zendev
uv sync --all-packages --all-groups
just ci
```

See [Development](development/index.md) for the complete contributor gates.
