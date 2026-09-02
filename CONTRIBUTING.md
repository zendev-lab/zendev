# Contributing to zendev

## Development and validation

Zendev requires Python 3.12 or newer. Install the complete workspace before
changing code or generated metadata:

```shell
uv sync --all-packages --all-groups
```

Run the repository gates before opening or updating a pull request:

```shell
just ci
uvx prek run --all-files
uv pip check
```

When ZFP documents, templates, or policy change, also verify the proposal set
and its committed index:

```shell
uv run zendev proposal check
uv run zendev proposal index --check
```

`just ci` formats and lints code, runs ty and Pyrefly, and executes the test
suite with coverage. Tests should assert observable behavior and public
contracts rather than implementation control flow.

## Vendored Gitmoji data

The commit package keeps an offline Gitmoji catalog pinned to an upstream
revision. Refresh it only through the repository task:

```shell
just sync-gitmoji
```

The task validates the upstream payload before updating the vendored file.
Review both the data diff and the pairing table in
[`packages/zendev-commit/src/zendev/data`](./packages/zendev-commit/src/zendev/data/)
before committing the result.

## Documentation ownership

Documentation stays with the code or policy that owns it:

| Document | Owner |
| --- | --- |
| [`README.md`](./README.md) | Toolkit positioning, installation, unified commands, and package navigation |
| `packages/*/README.md` | Component installation, API, independent commands, and boundaries |
| [`actions/README.md`](./actions/README.md) | Composite Action inputs and integration examples |
| [`zfps/README.md`](./zfps/README.md) | ZFP reading and submission process |
| `CONTRIBUTING.md` | Development gates, data maintenance, documentation ownership, and PR rules |

Do not recreate a general `docs/` directory or duplicate component behavior in
the root README.

## Zendev Feature Proposals

Public feature and governance changes begin with a ZFP. ZFP prose defaults to
Chinese, but another language is allowed when it makes the proposal clearer;
machine metadata and technical identifiers remain English. See
[`zfps/README.md`](./zfps/README.md) and the governing
[`ZFP-0000`](./zfps/ZFP-0000-governance.md).

## Pull requests

Use a valid Gitmoji-style title. ZFP pull requests use `docs(zfp)` and one of
these verbs as a review convention, not as a machine-enforced lifecycle.
Propose and revise titles name the topic only. They do not include a
`ZFP-NNNN` identifier; that belongs in the filename, frontmatter, and index.
A superseding pull request names the replaced proposal and the new topic,
but not the new proposal number.

- `📝 docs(zfp): propose <topic>`
- `📝 docs(zfp): revise <topic>`
- `📝 docs(zfp): supersede ZFP-NNNN with <topic>`

The pull-request body must retain the Chinese H2 structure in
[the repository template](./.github/pull_request_template.md): `动机` and
`解决方案` are required, while `说明` and `后续工作` are optional. Do not add a
checklist merely to satisfy process; record material validation in the solution
or notes.
