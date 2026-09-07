# Configuration ownership

Zendev owns reusable workflow mechanisms. A consuming repository owns the
meaning of its own process.

| Zendev owns | Consuming repositories own |
| --- | --- |
| Commit profile parsing and validation | The selected commit profile |
| PR template section and checklist validation | The PR template and required sections |
| Safe proposal frontmatter parsing | Proposal metadata vocabulary |
| JSON Schema execution | Repository-local schemas |
| Graph, history, and index mechanics | Lifecycle rules and relation semantics |
| Stable diagnostics and exit codes | Waivers and governance decisions |

This boundary prevents a shared package release from silently redefining a
repository's governance. It also makes policy changes reviewable alongside the
repository content they affect.

Configure commit behavior in `pyproject.toml`. Configure proposal behavior in a
repository-local TOML file, normally `proposal.toml`. See
[Configuration](../reference/configuration.md) for both interfaces.
