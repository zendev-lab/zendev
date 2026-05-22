# zendev

Personal dev workflow toolkit: unified logging + emoji commit conventions.

## Reusable `commit-msg` hook

This repository now publishes a reusable `pre-commit`/`prek` hook: `zendev-commit-msg`.

It validates commit titles against zendev's emoji commit schema:

- `✨ feat: add export`
- `🐛 fix(parser): handle null token`
- `📝 docs: update README`

It also allows common git-generated commit messages such as merge, revert, `fixup!`, and `squash!`.

Messages like `feat: add export` are rejected because the emoji prefix is required.

### Use from another repository

With `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/zendev-lab/zendev
    rev: v0.0.5
    hooks:
      - id: zendev-commit-msg
```

With `prek.toml`:

```toml
[[repos]]
repo = "https://github.com/zendev-lab/zendev"
rev = "v0.0.5"
hooks = [
  { id = "zendev-commit-msg" },
]
```

Then install the hook:

```bash
uvx prek install --hook-type commit-msg
```

### GitHub Actions: validate PR titles and bodies

This repository now ships both the Python CLIs and the thin composite-action
wrappers under [`actions/`](./actions), so one zendev revision owns the full PR
validation stack.

#### Use inside this repository

Check out the repo, then call the local actions:

```yaml
# .github/workflows/ci-pr-checks.yml
name: CI - PR Checks

on:
  pull_request:
    types: [opened, edited, synchronize, reopened]

jobs:
  title:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: read
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/validate-title
        with:
          text: ${{ github.event.pull_request.title }}

  body:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: read
    steps:
      - uses: actions/checkout@v4
      - uses: ./actions/validate-body
        with:
          body: ${{ github.event.pull_request.body }}
          require-checklist: "true"
```

#### Use from another repository

Pin the action path in this repository:

```yaml
jobs:
  title:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: read
    steps:
      - uses: zendev-lab/zendev/actions/validate-title@v0.0.7
        with:
          text: ${{ github.event.pull_request.title }}
```

```yaml
jobs:
  body:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: read
    steps:
      - uses: actions/checkout@v4
      - uses: zendev-lab/zendev/actions/validate-body@v0.0.7
        with:
          body: ${{ github.event.pull_request.body }}
          require-checklist: "true"
```

`actions/validate-body` validates the PR body's H2 sections against the repository PR template.
When `require-checklist` is true, it also parses every `- [x] …` row under the configured
`## Checklist` section and requires those exact lines (character-for-character except trailing
newline handling) to appear in the PR body. Use `checklist-section` for a different H2 title and
`fail-on-empty-checklist` to make a missing checklist section fail closed.

Each composite action resolves its bundled zendev tree from `GITHUB_ACTION_PATH`
(one level under `actions/`) and runs the matching CLI revision with `uvx --from`,
so the wrappers always stay aligned with whatever tag or revision pins the action.

### Use inside this repository

```bash
just install
```

That installs both `pre-commit` and `commit-msg` hooks for local development.
