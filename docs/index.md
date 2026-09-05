# Repository-native development workflows

Zendev turns repository policy into small, deterministic tools for commits,
pull-request messages, and durable proposal records.

It keeps the important state where collaborators already review it: Git,
Markdown, TOML, JSON Schema, and committed indexes. Zendev supplies reusable
mechanisms without taking ownership of a repository's terminology, templates,
or governance decisions.

## Start in five minutes

Run the complete toolkit without a global installation:

```shell
uvx zendev --help
```

Or add it to a project:

```shell
uv add --dev zendev
```

The unified command exposes three workflows:

```shell
zendev commit
zendev message check --title --text "✨ feat: add export"
zendev proposal check
```

Continue with [Getting started](getting-started.md), then choose a guide:

- [Assemble a recommended repository workflow](guides/repository-workflow.md)
- [Create consistent commits](guides/commits.md)
- [Validate commit and pull-request messages](guides/message-checks.md)
- [Maintain repository-native proposals](guides/proposals.md)
- [Install prek hooks](integrations/prek.md)
- [Add GitHub pull-request checks](integrations/github-actions.md)

## One toolkit, focused distributions

Installing `zendev` installs the complete toolkit. Each component remains an
independently installable Python distribution for consumers that only need one
contract. See the [package map](reference/packages.md) for the ownership and
entry-point boundaries.

## Source of truth

This site explains the released interfaces. The repository remains
authoritative for implementation and policy:

- [source code](https://github.com/zendev-lab/zendev)
- [Zendev Feature Proposals](https://github.com/zendev-lab/zendev/tree/main/zfps)
- [contributor instructions](https://github.com/zendev-lab/zendev/blob/main/CONTRIBUTING.md)
