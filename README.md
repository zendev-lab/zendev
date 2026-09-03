# zendev

Zendev is a repository-native development workflow toolkit for commit
conventions, pull-request message checks, and durable proposal repositories.

Git and committed repository files remain the source of truth. Zendev provides
typed Python mechanisms and thin hook or GitHub Action adapters; consuming
repositories continue to own their schemas, templates, terminology, lifecycle
policy, and governance decisions.

## Install

Install `zendev` for the complete toolkit and unified command:

```shell
uv add --dev zendev
uv run zendev --help
```

Run it without a global installation:

```shell
uvx --from zendev zendev --help
```

Python 3.12 or newer is required. `python -m zendev` exposes the same command
tree as `zendev`.

## Workflows

```shell
zendev commit
zendev message check --title --text "✨ feat: add export"
zendev proposal check
```

Read the [official documentation](https://zendev-lab.github.io/zendev/) for
concepts, guides, integrations, and the public reference.

## Packages

| Distribution | Purpose |
| --- | --- |
| `zendev` | Complete toolkit and unified CLI |
| `zendev-commit` | Commit profiles, validation, and interactive commits |
| `zendev-review` | Commit and pull-request message validation |
| `zendev-proposal` | Proposal validation and deterministic indexes |
| `zendev-log` | Loguru setup helper |

The component distributions remain independently installable for narrower use.
See the [package reference](https://zendev-lab.github.io/zendev/reference/packages/)
for their public boundaries.

## Contributing and design

See [CONTRIBUTING.md](./CONTRIBUTING.md) for repository gates and documentation
ownership. Public feature and governance changes begin with a
[Zendev Feature Proposal](./zfps/README.md).
