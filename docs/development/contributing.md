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

Do not commit generated `site/` output or add custom CSS, JavaScript, plugins,
or a shared documentation preset without a demonstrated product requirement.
