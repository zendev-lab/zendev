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

Build all workspace wheels and exercise the evolution workflow in isolated
standalone and complete-toolkit installations:

```shell
uv build --all-packages --wheel
uv run python scripts/check_distributions.py
```

Use a clean `dist/` containing one wheel per package. The check also rejects
namespace file overlap. CI runs it after building wheels.

Before the first release containing `zendev-evolution`, configure the PyPI
Trusted Publisher for `zendev-lab/zendev`, workflow `cd-release.yml`, environment
`pypi-zendev-evolution`, and the corresponding GitHub environment. The release
workflow publishes this component before the complete toolkit. Adding the
workflow does not provision those external settings or publish the package.
