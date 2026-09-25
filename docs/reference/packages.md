# Package reference

Five distributions share a release version and contribute disjoint portions of
the PEP 420 `zendev` namespace.

| Distribution | Ownership | Primary interfaces |
| --- | --- | --- |
| `zendev` | Complete toolkit and CLI composition | `zendev`, `python -m zendev` |
| `zendev-core` | Configuration discovery, diagnostics, source snapshots, Markdown facts | `zendev.core` |
| `zendev-message` | Message parsing, policy, rendering, body checks, interactive adapter | `zendev.message`, `zendev-message`, `zendev-commit` |
| `zendev-proposal` | Proposal policy, validation, history, graph, index, repair plans | `zendev.proposal`, `zendev-proposal` |
| `zendev-log` | Idempotent Loguru setup | `zendev.log.setup_log` |

The root requires every component at its exact version. Message and proposal
each require the same-version core. Core has no domain, CLI, or Git dependency;
log remains independent. Every component is separately installable. The root CLI
always exposes `commit`, `message`, and `proposal`.

The old `zendev-commit` and `zendev-review` **distributions** are removed;
`zendev-commit` remains an executable supplied by `zendev-message`.
See the [migration guide](../guides/migration.md) for Python API changes.
