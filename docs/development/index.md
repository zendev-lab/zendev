# Development

Zendev is a uv workspace containing the complete toolkit, four component
packages, composite Actions, proposal fixtures, and the documentation site.

Install everything required for local development:

```shell
uv sync --all-packages --all-groups
```

Run the repository gates before updating a pull request:

```shell
just ci
just docs-build
uvx prek run --all-files
uv pip check
```

When proposal documents, templates, or policy change, also write the index and
review its diff:

```shell
uv run zendev proposal check --fix
```

Read [Architecture](architecture.md) for ownership boundaries,
[Contributing](contributing.md) for documentation-specific work, and
[Deployment](deployment.md) for the Cloudflare release path.
