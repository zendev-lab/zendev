# Recommended repository workflow

A mature repository combines Zendev's focused commands into one reviewable
development contract. It does not ask Zendev to decide what the repository
means.

> **The repository owns policy. Zendev validates and automates it.**

This guide is a recommended starting point, not a universal policy. Keep the
parts that match the repository and change policy through ordinary review.

## Principles

Keep four responsibilities separate:

| Layer | Responsibility |
| --- | --- |
| Repository files | Own profiles, templates, schemas, terminology, lifecycle rules, and waivers. |
| Documentation | Explain intent and provide examples for people and Agents. |
| Zendev CLI | Execute the validation and deterministic update contract. |
| Agent skill | Route behavior and checks without copying the reference manual. |

Use the same repository-owned contract locally and in CI. A CI workflow should
invoke Zendev or its published adapters instead of maintaining a second set of
regular expressions and parsing rules.

## Recommended repository shape

Start with the files needed by the workflows the repository actually adopts:

```text
.
├── .github/
│   ├── pull_request_template.md
│   └── workflows/
│       ├── policy-pr.yml
│       └── ci-static-checks.yml
├── .agents/
│   └── skills/
│       └── zendev/
│           └── SKILL.md          # optional, and intentionally small
├── proposals/                    # names are selected in proposal.toml
├── schemas/
├── templates/
├── proposals-index.json          # generated, reviewed, and committed
├── prek.toml
├── proposal.toml
└── pyproject.toml
```

The directory and index names are examples. A proposal repository defines its
own shape in `proposal.toml`; do not rename existing policy files just to match
this tree.

## Minimal setup

Add the complete toolkit to the development environment:

```shell
uv add --dev zendev
```

Select the repository's commit profile in `pyproject.toml`:

```toml
[tool.zendev.commit]
profile = "zendev"
```

Install released validation hooks through `prek.toml`:

```toml
[[repos]]
repo = "https://github.com/zendev-lab/zendev"
rev = "v0.3.0"
hooks = [
  { id = "zendev-message-check" },
  { id = "zendev-proposal-check" },
]
```

Install the commit-message hook and exercise the repository gate:

```shell
uvx prek install --hook-type commit-msg
uvx prek run --all-files
```

See the [prek integration](../integrations/prek.md) for hook stages and argument
forwarding. Repositories that do not maintain proposals should omit the
proposal hook rather than add unused policy files.

## Golden path

Use one path from repository policy to reviewed change:

```text
inspect repository configuration
             ↓
            edit
             ↓
validate deterministic proposal state, when applicable
             ↓
       run the local gate
             ↓
        create a commit
             ↓
       open a pull request
             ↓
     run the same contract in CI
```

### Local development

Before changing policy-driven content, inspect the files that own it:

- `pyproject.toml` for the commit profile;
- `.github/pull_request_template.md` for the PR body contract;
- `proposal.toml`, its schemas, and its templates for proposal policy;
- `prek.toml` and repository tasks for the normal local gate.

Run read-only validation before mutation. When proposals are in scope:

```shell
uv run zendev proposal check
```

If valid proposal changes make the committed index drift, let Zendev update
only that deterministic state, then review the result:

```shell
uv run zendev proposal check --fix
git diff
uv run zendev proposal check
```

Finish with the repository's complete local gate:

```shell
uvx prek run --all-files
```

### Commits

Stage only the intended files, then use the configured profile:

```shell
uv run zendev commit
```

For a non-interactive check, pass the exact text and scope:

```shell
uv run zendev message check --title --text "✨ feat: add export"
```

The repository selects the profile. An Agent should not infer a different
convention from recent commit messages or replace the configured policy.

### Pull requests and CI

A PR body is a repository-owned schema expressed by its template. Validate both
inputs explicitly when testing locally or composing a CI adapter:

```shell
uv run zendev message check --title --text "📝 docs: explain repository workflow"
uv run zendev message check --body --text "$PR_BODY" \
  --template .github/pull_request_template.md
```

In GitHub Actions, prefer the published title and body Actions. They are thin
adapters around the same CLI contract and read the repository-local profile and
template. See the [GitHub Actions integration](../integrations/github-actions.md)
for copyable jobs.

Keep CI permissions read-only unless another step has a separately justified
need. The validation job should report policy violations; it should not rewrite
the pull request or generated repository state.

## Decide when a proposal is warranted

Proposal commands are simple; deciding what belongs in a durable proposal
system is the important policy choice.

| Change | Recommended home |
| --- | --- |
| Typo or editorial correction | Direct code or documentation change. |
| Local implementation choice | Pull request or issue. |
| Temporary exploration | Draft document or branch under repository policy. |
| Durable public contract, architecture, or governance decision | Proposal. |
| Semantic change to an accepted decision | New proposal or repository-defined amendment. |

When history validation is part of the repository contract, fetch and name the
base explicitly:

```shell
git fetch origin main
uv run zendev proposal check --base-ref origin/main
```

Do not create a proposal merely because a change is large. Use one when future
contributors need a durable, reviewable account of a decision and its
lifecycle.

## Work safely with Agents

An Agent working in a Zendev repository should follow this sequence:

1. Locate repository-owned configuration before editing.
2. Read the selected templates and schemas instead of inventing policy.
3. Run a read-only check to establish the current state.
4. Use Zendev commands instead of reproducing their validation logic.
5. Use `--fix` only for deterministic generated state, then inspect the diff.
6. Prefer structured diagnostics when automation needs stable data.
7. Run the repository's normal local gate before reporting completion.

For proposal automation, consume the versioned JSON envelope and diagnostic
codes:

```shell
uv run zendev proposal check --json
```

Human-readable messages may improve over time. Agents should depend on command
exit codes, JSON keys, and diagnostic codes instead of parsing that prose.

A repository-local `SKILL.md` can preserve the seven behavioral rules above
and link to this guide. Keep CLI flags, proposal fields, and parser behavior in
the official documentation or `--help`; a skill is a workflow router, not a
second manual.

## Common anti-patterns

| Avoid | Prefer |
| --- | --- |
| Reimplementing PR-title rules with a CI regular expression. | Call `zendev message check` or the published Action. |
| Parsing human-readable diagnostics in automation. | Use `--json`, exit codes, and diagnostic codes. |
| Editing a generated proposal index by hand. | Run the read-only check, use `--fix`, and review the diff. |
| Replacing an existing schema with a presumed Zendev default. | Read `proposal.toml` and preserve repository-owned policy. |
| Running a mutating command before understanding current failures. | Establish state with a read-only check first. |
| Maintaining different local and CI rules. | Run the same repository contract in both places. |

## Complete example

[Zendev uses its own workflow](https://github.com/zendev-lab/zendev). The
repository provides a concrete, CI-validated example:

- [`pyproject.toml`](https://github.com/zendev-lab/zendev/blob/main/pyproject.toml)
  selects the commit profile and development dependencies.
- [`prek.toml`](https://github.com/zendev-lab/zendev/blob/main/prek.toml) defines
  the local gate.
- [`proposal.toml`](https://github.com/zendev-lab/zendev/blob/main/proposal.toml),
  [`schemas/zfp.schema.json`](https://github.com/zendev-lab/zendev/blob/main/schemas/zfp.schema.json),
  and [`templates/zfp.md`](https://github.com/zendev-lab/zendev/blob/main/templates/zfp.md)
  own proposal policy.
- [`.github/pull_request_template.md`](https://github.com/zendev-lab/zendev/blob/main/.github/pull_request_template.md)
  owns the PR body contract.
- [`policy-pr.yml`](https://github.com/zendev-lab/zendev/blob/main/.github/workflows/policy-pr.yml)
  and [`ci-static-checks.yml`](https://github.com/zendev-lab/zendev/blob/main/.github/workflows/ci-static-checks.yml)
  apply the same contracts in CI.
- [`zfps/`](https://github.com/zendev-lab/zendev/tree/main/zfps) and the
  [committed index](https://github.com/zendev-lab/zendev/blob/main/zfps-index.json)
  keep durable decisions reviewable in Git.

Use this repository as an example of composition, not as a policy template to
copy unchanged.
