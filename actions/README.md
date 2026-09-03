# Composite Actions

The actions in this directory are thin GitHub workflow adapters around
`zendev message check` from the same pinned zendev revision. Validation
semantics belong to the
[`zendev-review` README](../packages/zendev-review/README.md).

## Validate a pull-request title

```yaml
jobs:
  title:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: read
    steps:
      - uses: actions/checkout@v4
      - uses: zendev-lab/zendev/actions/validate-title@v0.2.0
        with:
          text: ${{ github.event.pull_request.title }}
          profile: auto
```

`text` is required. `profile` defaults to `auto` and accepts `zendev`,
`conventional`, or `gitmoji` as explicit values.

## Validate a pull-request body

```yaml
jobs:
  body:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: read
    steps:
      - uses: actions/checkout@v4
      - uses: zendev-lab/zendev/actions/validate-body@v0.2.0
        with:
          body: ${{ github.event.pull_request.body }}
          template: .github/pull_request_template.md
```

`body` is required. `template` defaults to
`.github/pull_request_template.md`. Repositories that intentionally enforce
checked rows can also set `require-checklist`, `checklist-section`, and
`fail-on-empty-checklist`; all three are optional and checklist enforcement is
off by default.

Inside the zendev repository, use `./actions/validate-title` or
`./actions/validate-body` after checking out the repository.
