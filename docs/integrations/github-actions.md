# GitHub Actions

Zendev provides composite Actions for pull-request title and body validation.
They are thin adapters around `zendev message check` at the same pinned release.

## Validate a PR title

```yaml
jobs:
  title:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: read
    steps:
      - uses: actions/checkout@v4
      - uses: zendev-lab/zendev/actions/validate-title@v0.3.0
        with:
          text: ${{ github.event.pull_request.title }}
          profile: auto
```

`text` is required. `profile` defaults to `auto` and accepts `zendev`,
`conventional`, or `gitmoji`.

## Validate a PR body

```yaml
jobs:
  body:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: read
    steps:
      - uses: actions/checkout@v4
      - uses: zendev-lab/zendev/actions/validate-body@v0.3.0
        with:
          body: ${{ github.event.pull_request.body }}
          template: .github/pull_request_template.md
```

`body` is required. `template` defaults to
`.github/pull_request_template.md`. Checklist enforcement is optional through
`require-checklist`, `checklist-section`, and `fail-on-empty-checklist`.

The checkout step is required because `profile: auto` and the body template are
repository-local inputs. Give the job read-only permissions unless another step
has a separately justified need.
