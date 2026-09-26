# zendev

Zendev is a repository-native development workflow toolkit for commit
conventions, pull-request message checks, durable proposal repositories, and project evolution.

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
uvx zendev --help
```

Python 3.12 or newer is required. `python -m zendev` exposes the same command
tree as `zendev`.

## Workflows

```shell
zendev commit
zendev message check --title --text "✨ feat: add export"
zendev proposal check
# For repositories with an EVOLUTION.md:
zendev evolution check
```

Read the [official documentation](https://docs.zendev.zrr.dev/) for
concepts, guides, integrations, and the public reference.

## Packages

| Distribution | Purpose |
| --- | --- |
| `zendev` | Complete toolkit and unified CLI |
| `zendev-core` | Configuration, diagnostics, source snapshots, Markdown facts |
| `zendev-message` | Message parsing, validation, rendering, interactive commits |
| `zendev-proposal` | Proposal validation and deterministic indexes |
| `zendev-evolution` | Initial intent and dated evolution records |
| `zendev-log` | Loguru setup helper |

The component distributions remain independently installable for narrower use.
See the [package reference](https://docs.zendev.zrr.dev/reference/packages/)
for their public boundaries.

## Agent skills

The repository also provides optional, self-contained agent skills under `skills/`.
Load the one matching the task; they use the target project's configuration and
contracts rather than imposing one language, formatter, or workflow.

| Skill | Result |
| --- | --- |
| [add-proposal](./skills/add-proposal/SKILL.md) | Decide whether a new decision has substantial impact, then prepare and validate a proposal when needed |
| [code-style](./skills/code-style/SKILL.md) | Write or simplify code with explicit types, ownership, control flow, and effects |
| [test-behavior](./skills/test-behavior/SKILL.md) | Add meaningful regression, ordering, numerical, and backend-equivalence tests |
| [measure-performance](./skills/measure-performance/SKILL.md) | Produce comparable latency, throughput, memory, or startup measurements |

These skills are repository assets, separate from the Python CLI installation.
Load them through the agent host's skill support. Project planning, code review,
and Git delivery retain their own workflows; loading a skill does not authorize
installation, publication, or changes outside the requested task.

## Contributing and design

See [CONTRIBUTING.md](./CONTRIBUTING.md) for repository gates and documentation
ownership. Public feature and governance changes begin with a
[Zendev Feature Proposal](./zfps/README.md).
