# PR review checks

`zendev-validate-title` and `zendev-validate-body` are the reusable PR checks.
The composite actions under `actions/` are thin adapters that execute the CLIs
from the same pinned zendev revision.

## Title validation

The title CLI uses the same profiles and repository configuration as the
commit hook:

```console
$ uvx --from zendev zendev-validate-title --profile gitmoji ":sparkles: Add export support"
```

See [Commit conventions](./commit-conventions.md) for profile semantics.

Use the composite action from another repository:

```yaml
jobs:
  title:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: read
    steps:
      - uses: actions/checkout@v4
      - uses: zendev-lab/zendev/actions/validate-title@v0.1.0
        with:
          text: ${{ github.event.pull_request.title }}
          profile: auto
```

## Body validation

The body CLI reads H2 sections from the configured PR template:

```console
$ uvx --from zendev zendev-validate-body "$PR_BODY" \
    --template .github/pull_request_template.md \
    --require-checklist
```

The section contract is:

- every template H2 is required by default
- `<!-- pr-body:optional -->` makes the following H2 optional
- `<!-- pr-body:required -->` explicitly marks the following H2 as required
- present sections must retain template order
- undeclared, duplicate, ambiguous, and dangling sections or directives fail
- directives and headings inside fenced code blocks are ignored

When `--require-checklist` is present, every checked `- [x]` row under the
configured checklist H2 must occur in the PR body. `--fail-on-empty-checklist`
makes an empty template checklist fail instead of becoming a no-op.

Use the body action:

```yaml
jobs:
  body:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: read
    steps:
      - uses: actions/checkout@v4
      - uses: zendev-lab/zendev/actions/validate-body@v0.1.0
        with:
          body: ${{ github.event.pull_request.body }}
          template: .github/pull_request_template.md
          require-checklist: "true"
```

Inside the zendev repository, replace the remote action references with
`./actions/validate-title` and `./actions/validate-body`.
