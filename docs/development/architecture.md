# Architecture

The root distribution assembles focused packages behind one command tree:

```text
zendev CLI
├── zendev-commit
├── zendev-review
├── zendev-evolution
├── zendev-proposal
└── zendev-log
```

The component packages remain independently installable, but the complete
toolkit has hard dependencies on all of them. This makes the unified CLI stable:
an installed `zendev` always exposes `commit`, `message`, `proposal`, and `evolution`.

## Adapter boundary

Public prek hooks and composite GitHub Actions are adapters. They translate host
inputs into the same Python commands; they do not implement a second copy of
validation semantics.

## Proposal boundary

The proposal package owns safe loading, typed policy, structural validation,
history comparison, graph checks, deterministic indexing, and diagnostics.
Repository-local TOML, JSON Schema, templates, and Markdown own the actual
proposal process.

## Documentation boundary

`README.md` and package READMEs are landing pages for GitHub and PyPI. `docs/`
owns task-oriented user documentation. `zfps/` remains the design and governance
source of truth and is linked from the site without being moved or duplicated.

## Evolution boundary

The evolution package owns the fixed single-file Markdown format, source slices,
structural checks, and atomic date writes. It has no dependency on proposal
configuration or indexes. Git records corrections to the original intent; dated
entries explain subsequent changes in direction.
