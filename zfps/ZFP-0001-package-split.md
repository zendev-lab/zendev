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

Publish `zendev`, `zendev-proposal`, and `zendev-log` as distributions that
contribute to the implicit `zendev` namespace. The root `zendev` distribution
depends on both component distributions and provides the unified `zendev`
command and `python -m zendev` entry point. Version 0.2.0 removes the root
logging re-export; users import `setup_log` from `zendev.log`.

## Motivation

The current distribution couples commit helpers, proposal management, and
logging even though their users and dependencies differ. In particular, a user
of the proposal CLI should not need the commit workflow or Loguru, and a user of
the logging helper should not need JSON Schema or YAML support.

Separating distributions makes those ownership boundaries explicit and permits
component-only installation, while the root distribution remains the complete
toolkit. The existing `zendev.log` and `zendev.proposal` module names remain
stable.

## Design

The repository remains one uv workspace with one lockfile and one release
version. Its distributions have these responsibilities:

| Distribution | Namespace content | Runtime dependencies | Commands |
| --- | --- | --- | --- |
| `zendev` | Commit and review modules plus `zendev.__main__` | Questionary, Typer, `zendev-proposal`, `zendev-log` | `zendev`; compatibility commands `zendev-commit`, `zendev-commit-msg`, `zendev-validate-title`, `zendev-validate-body` |
| `zendev-proposal` | `zendev.proposal` | JSON Schema, PyYAML, Typer | `zendev-proposal` |
| `zendev-log` | `zendev.log` | Loguru | None |

All three use the PEP 420 implicit namespace: no distribution installs
`zendev/__init__.py`, and no two wheels own the same file. Each distribution
ships its own `py.typed` marker within the namespace portion it owns. Shared
behavior is copied only when it is small and private enough to avoid creating a
fourth public package or a dependency between these distributions.

`zendev` is the complete toolkit distribution and depends on
`zendev-proposal` and `zendev-log`. It owns `zendev/__main__.py` and the
`zendev` console script, providing these commands:

- `zendev commit`
- `zendev commit-msg`
- `zendev validate-title`
- `zendev validate-body`
- `zendev proposal`

`python -m zendev` exposes the same command tree. The root CLI directly mounts
the proposal Typer application and does not define behavior for missing
component packages. The standalone `zendev-proposal` command remains available
when that distribution is installed by itself. All public Zendev CLIs continue
to use Typer.

The release workflow builds and publishes every workspace distribution from the
same `v0.2.0` tag. Because installing `zendev` also installs the proposal
distribution, the existing remote proposal hook remains supported.

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

The old root import must fail. Installing `zendev` provides `zendev.log` and
`zendev.proposal` through its required component distributions. Users needing
only one component may instead install `zendev-log` or `zendev-proposal`
directly. The existing commands remain compatibility entry points, while new
interactive usage can use the unified `zendev` command.

## Validation

Build all three wheels and verify their file lists do not overlap. Install each
component wheel independently, then install the root wheel with the component
wheels available and verify both dependencies are resolved. Exercise all five
compatibility console scripts plus `zendev` and `python -m zendev`, including
`zendev proposal`. Confirm that uninstalling one component leaves the other
namespace portions importable. Confirm that `from zendev import setup_log`
fails while `from zendev.log import setup_log` succeeds with `zendev-log`
installed. Run
the repository's type checks, tests, hooks, and dependency consistency checks
against the complete workspace.
