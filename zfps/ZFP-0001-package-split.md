---
zfp: 1
title: "Split Zendev into PEP 420 Distributions"
status: Draft
type: Feature
authors:
  - "zrr1999"
created: 2026-08-26
supersedes: []
---

# ZFP-0001: Split Zendev into PEP 420 Distributions

## Summary

Publish `zendev`, `zendev-proposal`, and `zendev-log` as independent
distributions that contribute to the implicit `zendev` namespace. Version 0.2.0
removes the root logging re-export; users install `zendev-log` explicitly and
import `setup_log` from `zendev.log`.

## Motivation

The current distribution couples commit helpers, proposal management, and
logging even though their users and dependencies differ. In particular, a user
of the proposal CLI should not need the commit workflow or Loguru, and a user of
the logging helper should not need JSON Schema or YAML support.

Separating distributions makes those dependency and ownership boundaries
explicit while preserving the existing `zendev.log` and `zendev.proposal`
module names.

## Design

The repository remains one uv workspace with one lockfile and one release
version. Its distributions have these responsibilities:

| Distribution | Namespace content | Runtime dependencies | Commands |
| --- | --- | --- | --- |
| `zendev` | Commit and review modules directly under `zendev` | Questionary, Typer | `zendev-commit`, `commit-msg`, `validate-title`, `validate-body` |
| `zendev-proposal` | `zendev.proposal` | JSON Schema, PyYAML, Typer | `zendev-proposal` |
| `zendev-log` | `zendev.log` | Loguru | None |

All three use the PEP 420 implicit namespace: no distribution installs
`zendev/__init__.py`, and no two wheels own the same file. Each distribution
ships its own `py.typed` marker within the namespace portion it owns. Shared
behavior is copied only when it is small and private enough to avoid creating a
fourth public package or a dependency between these distributions.

`zendev` is not an umbrella distribution and does not depend on
`zendev-proposal` or `zendev-log`. The repository does not add
`zendev/__main__.py`; the console scripts remain the supported command entry
points. All public Zendev CLIs continue to use Typer.

The release workflow builds and publishes every workspace distribution from the
same `v0.2.0` tag. Proposal repositories install `zendev-proposal` explicitly;
the existing remote pre-commit hook is removed because a hook environment built
from the root `zendev` distribution cannot provide that independent command.

## Compatibility

This is a breaking change released as 0.2.0. Logging users migrate from:

```python
from zendev import setup_log
```

to an explicit installation and import:

```console
uv add zendev-log
```

```python
from zendev.log import setup_log
```

The old root import must fail. Existing `zendev.log` imports remain valid after
installing `zendev-log`. Proposal users install `zendev-proposal` explicitly;
commit-tool users can continue to install only `zendev`.

## Validation

Build all three wheels and verify their file lists do not overlap. Install each
wheel independently and then together in clean environments, exercise all five
console scripts from their owning distributions, and confirm that uninstalling
one distribution leaves the other namespace portions importable. Confirm that
`from zendev import setup_log` fails while `from zendev.log import setup_log`
succeeds with `zendev-log` installed. Run the repository's type checks, tests,
hooks, and dependency consistency checks against the complete workspace.
