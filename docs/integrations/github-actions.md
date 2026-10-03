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
      - uses: zendev-lab/zendev/actions/validate-title@<release-or-commit>
        with:
          text: ${{ github.event.pull_request.title }}
```

`text` is required. Omit `profile` to use repository configuration, or override
with `zendev`, `conventional`, or `gitmoji`. Replace `<release-or-commit>` with
a pinned revision containing the domain-architecture migration.

## Validate a PR body

```yaml
jobs:
  body:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: read
    steps:
      - uses: actions/checkout@v4
      - uses: zendev-lab/zendev/actions/validate-body@<release-or-commit>
        with:
          body: ${{ github.event.pull_request.body }}
          template: .github/pull_request_template.md
```

`body` is required. Omitted template/checklist inputs use repository configuration;
without configuration the template is `.github/pull_request_template.md` and
checklist enforcement is disabled. Override with `template`, `require-checklist`,
`checklist-section`, or `fail-on-empty-checklist`. Boolean overrides accept `true`
or `false`. Both Actions emit GitHub annotations from the shared diagnostic renderer.

The checkout step is required because configuration discovery and the body template are
repository-local inputs. Give the job read-only permissions unless another step
has a separately justified need.
