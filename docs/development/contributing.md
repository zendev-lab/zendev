# Contributing documentation

The canonical contributor contract is the repository's
[CONTRIBUTING.md](https://github.com/zendev-lab/zendev/blob/main/CONTRIBUTING.md).
This page covers the documentation projection.

## Preview locally

```shell
just docs
```

The task serves the site and opens a browser. Generated HTML is written to
`site/` and is not committed.

## Validate a change

```shell
just docs-build
```

The strict build turns Zensical warnings such as broken internal links or
anchors into failures. Pull requests run the same build as `Documentation
Checks` in `CI - Static Checks`.

## Machine-readable output

Coding agents are a primary zendev audience, so the build also publishes
`llms.txt`, `llms-full.txt`, and a Markdown copy of each page through Zensical's
built-in `llmstxt` plugin. The same copies back the **Copy as Markdown** page
action. Sections follow the site directories; a page added outside them must
also be listed under `project.plugins.llmstxt.sections` in `zensical.toml`.

## Ownership rules

- Keep GitHub and PyPI landing information in the root and package READMEs.
- Put task-oriented explanations, guides, integration recipes, and public
  reference material under `docs/`.
- Keep ZFP policy and records under `zfps/`; link to them instead of copying
  them into the site.
- Keep contributor-only operating instructions in `CONTRIBUTING.md`.
- Use copyable `shell` blocks without a leading `$ ` prompt.
- Use `uv` for Python project workflows and `uvx` for one-off Python tools.
- Use `vp` for JavaScript project workflows and `vpx` for one-off JavaScript
  tools.

Do not commit generated `site/` output or add custom CSS, JavaScript, plugins,
or a shared documentation preset without a demonstrated product requirement.

## Distribution checks

Build all six workspace wheels into `dist/`, check their contents, and run each
distribution's entry point in an isolated environment:

```shell
just packages
```

[check-wheel-contents](https://github.com/jwodder/check-wheel-contents) compares
each wheel with its source tree, so a missing, extra, or duplicated module, data
file, or `py.typed` fails the build. The pinned sibling versions exist only in
`dist/`, so each installation uses the wheels just built.
CI and the release workflow use this same entry point.

Source layout rules run on every commit: [alint](https://github.com/asamarts/alint)
enforces namespace ownership, typed subpackages, and same-version sibling pins
from `.alint.yml`, and Ruff's banned-import rule keeps Typer and CLI modules out
of domain modules. `just hooks` installs the published hooks from the committed
checkout with `prek try-repo` and resolves zendev only from the wheels in `dist/`.

Before the first release containing `zendev-evolution`, configure the PyPI
Trusted Publisher for `zendev-lab/zendev`, workflow `cd-release.yml`, environment
`pypi-zendev-evolution`, and the corresponding GitHub environment. The release
workflow publishes this component before the complete toolkit. Adding the
workflow does not provision those external settings or publish the package.
