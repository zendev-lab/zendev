# zendev-review

`zendev-review` owns reusable pull-request title and body validation. It
depends on `zendev-commit` so title checks reuse commit profiles instead of
copying commit semantics.

```shell
uv add --dev zendev-review
uvx --from zendev-review zendev-validate-title --help
uvx --from zendev-review zendev-validate-body --help
```

The complete `zendev` distribution exposes the same checks as
`zendev message check --title` and `zendev message check --body`. Standalone
scripts keep their existing names for GitHub Actions and component-only
installs.

## Python API

```python
from zendev.body import BodySection, validate_body

valid, headings = validate_body(
    "## Motivation\n\nWhy.\n\n## Solution\n\nHow.\n",
    [BodySection("Motivation"), BodySection("Solution")],
)
assert valid
assert headings == ["Motivation", "Solution"]
```

## Title validation

The title CLI uses the same profiles and repository configuration as the
commit hook:

```shell
uvx --from zendev-review zendev-validate-title --profile gitmoji ":sparkles: Add export support"
```

See [`zendev-commit`](../zendev-commit/README.md) for profile semantics.

## Body validation

The body CLI reads H2 sections from the configured PR template:

```shell
uvx --from zendev-review zendev-validate-body "$PR_BODY" \
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

The [composite Actions](../../actions/README.md) expose the same behavior for
GitHub workflows.
