# Contributing to zendev

## Development and validation

Zendev requires Python 3.12 or newer. Install the complete workspace from the lockfile and prepare the pre-commit and commit-msg hooks:

```shell
just install
```

Run the repository gates before opening or updating a pull request:

```shell
just ci
just docs-build
uv pip check
```

When ZFP documents, templates, or policy change, write a drifted index into the same change:

```shell
uv run zendev proposal check --fix
```

`just check` runs read-only pre-commit checks, then checks justfile formatting. Use `just format` for Python repairs and `just --fmt --unstable` to format the justfile. The commit-message hook still normalizes the commit subject when committing.

`just test` runs the test suite; `just coverage` also writes HTML and XML coverage reports. `just ci` combines `check` and `coverage`. Use `bash scripts/check_packages.sh` to validate isolated wheel installations. Tests should assert observable behavior and public contracts rather than implementation control flow.

Dependency checks read each distribution's Hatch metadata through `scripts/check_dependencies.py`. Deptry checks third-party imports; Import Linter enforces the CLI/component/core layers; alint checks the declared namespace owners and sibling pins. Negative controls in `tests/test_quality_tools.py` exercise missing and unused dependencies and prohibited imports.

Use upstream hooks when available. The local entries run Zendev from this checkout, adapt Hatch dependency metadata, or run ast-grep, whose pinned release provides no hook manifest. Import Linter's upstream system hook runs through `uv run --frozen` so it sees the workspace's installed namespace packages.

Structural rules under `quality/ast-grep` enforce ZFP-0006's domain boundary. Security rules under `quality/semgrep` check shell execution and unsafe YAML loading. Keep passing and failing examples with every rule. Vale checks documented names; rumdl checks Markdown structure while allowing semantic line wrapping and frontmatter titles. Test fixture documents are validated by their owning tests.

The mutation job in [CE - Quality](.github/workflows/ce-quality.yml) checks the Conventional Commits parser through `scripts/check_mutations.py`. It stages the workspace namespace in a temporary `src` tree so mutmut loads the mutated modules. [CE - Quality](.github/workflows/ce-quality.yml) reports complexity and exact clones without imposing a universal score. `just benchmark` measures parsing a 100-paragraph commit and normalizing a CRLF commit, with returned values checked outside timing. Reports go to `.artifacts/quality/`.

Regular CI runs for pull requests targeting `main` and merge groups targeting `main`; a push after merging does not repeat these checks. CE runs the periodic checks weekly and on manual dispatch with its own triggers; tool setup and maintenance commands live in the owning workflows. CodSpeed runs the same benchmark cases using CPU simulation on pull requests; local walltime samples are a separate measurement. Dependency vulnerabilities block their CI job. Codecov upload failures are errors. SonarQube Cloud automatic analysis covers Python sources and classifies tests separately; this mode does not ingest coverage, which remains available through Codecov and the local reports.

Jactionlint uses its upstream ShellCheck hook for offline workflow checks, both locally and through prek in CI. Python files use independent Ruff hooks. The workflows and composite actions currently have no `shell: python` steps, so jactionlint's Python integration is disabled. The strict online audit runs only in CE on the trusted main branch, on its weekly schedule or manual dispatch, and retains its report; failed or skipped queries are not accepted as a completed audit. Zizmor remains enabled because its bot-condition checks cover cases not detected by the pinned jactionlint release.

## Vendored Gitmoji data

The message package keeps an offline Gitmoji catalog pinned to an upstream revision. Refresh it through the maintained script:

```shell
uv run --frozen python scripts/sync_gitmoji.py
```

The script validates the upstream payload before updating the vendored file. Review both the data diff and the pairing table in [`packages/zendev-message/src/zendev/message/data`](./packages/zendev-message/src/zendev/message/data/) before committing the result.

## Documentation ownership

Documentation stays with the code or policy that owns it:

| Document | Owner |
| --- | --- |
| [`README.md`](./README.md) | GitHub and PyPI landing page, quick installation, and navigation |
| [`docs/`](./docs/) | Official concepts, guides, integrations, reference, and development documentation |
| `packages/*/README.md` | Distribution landing pages and links to the official documentation |
| [`actions/README.md`](./actions/README.md) | Composite Action landing page and official documentation link |
| [`zfps/README.md`](./zfps/README.md) | ZFP reading and submission process |
| `CONTRIBUTING.md` | Development gates, data maintenance, documentation ownership, and PR rules |

Preview the documentation with `just docs` and validate it with `just docs-build`. The strict build is also the `Documentation Checks` job in `CI - Static Checks`. Do not move or duplicate `zfps/` under `docs/`; ZFPs remain the repository's design and governance source of truth. Copyable command examples use `shell` fences and must not start with `$ `. Mixed command-and-output transcripts may keep a session fence.

## Zendev Feature Proposals

New public contracts and governance decisions begin with a ZFP. Implementing an existing ZFP, restoring its intended behavior, and maintenance that preserves public semantics can use a direct PR. Link the existing proposal when it covers the work; explain new decisions or uncertainty in the existing motivation or solution section. Compatible new interfaces still introduce public contracts. Use the [decision criteria and examples](./zfps/ZFP-0000-governance.md#何时需要提案), not change size or commit labels, to determine the route. This is a review decision, not a check inferred automatically from the diff.

ZFP authors use lowercase GitHub usernames without `@`; see the [authorship policy](./zfps/ZFP-0000-governance.md#作者身份).

ZFP prose defaults to Chinese, but another language is allowed when it makes the proposal clearer; machine metadata and technical identifiers remain English. See [`zfps/README.md`](./zfps/README.md) for authoring and pull-request titles, and [`ZFP-0000`](./zfps/ZFP-0000-governance.md) for the governance contract.

Keep the ZFP and its implementation in separate PRs. The proposal PR contains the ZFP, its generated index, and directly related proposal or contribution guidance. Implementation code, tests, package changes, CI, and feature usage documentation belong in the implementation PR, which links the ZFP and its proposal PR.

When the implementation depends on an unmerged proposal, use a PR stack: `main <- proposal <- implementation`. Set the implementation PR's base to the proposal branch and verify each PR's diff against its own base: the proposal diff must contain no implementation, and the implementation diff must not repeat the proposal. The two PRs can be prepared and reviewed together without waiting for the proposal to merge.

## Pull requests

Use a valid `zendev`-profile title. ZFP pull requests follow the title conventions in [`zfps/README.md`](./zfps/README.md).

The pull-request body must retain the Chinese H2 structure in [the repository template](./.github/pull_request_template.md): `动机` and `解决方案` are required, while `说明` and `后续工作` are optional. Do not add a checklist merely to satisfy process. Run the required checks, but do not list local test runs, commands, paths, or CI status in the body. Use `说明` only for impact on review or use, such as compatibility, migration, risk, known limitations, key trade-offs, or stack dependencies, and omit it when there is nothing to add.

PR titles are validated for every author, including bots. Renovate is exempt only from the PR body template requirement.
