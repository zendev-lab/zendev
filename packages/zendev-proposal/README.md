# zendev-proposal

`zendev-proposal` is a validator and indexer for repositories that store durable
design proposals as Markdown. It owns safe frontmatter loading, JSON Schema
execution, structural and history validation, graph checks, deterministic
indexes, and stable diagnostics. Each repository retains ownership of its
schemas, templates, terminology, lifecycle policy, and decisions.

```shell
uv add --dev zendev-proposal
uvx zendev-proposal check --help
```

The complete toolkit exposes the same application:

```shell
uvx --from zendev zendev proposal check
```

```python
from zendev.proposal import load_config, validate_repository

config = load_config("proposal.toml")
result = validate_repository(config)
```

Read the official [Proposals guide](https://zendev-lab.github.io/zendev/guides/proposals/),
[Configuration reference](https://zendev-lab.github.io/zendev/reference/configuration/),
and [hook integration](https://zendev-lab.github.io/zendev/integrations/prek/)
for the supported repository contract.
