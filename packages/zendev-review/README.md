# zendev-review

`zendev-review` owns reusable commit and pull-request message checks. It
depends on `zendev-commit` so title and complete-message checks reuse commit
profiles instead of copying commit semantics.

```shell
uv add --dev zendev-review
uvx --from zendev-review zendev-message check --help
```

The complete `zendev` distribution exposes the same command as
`zendev message check`.

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

## Message check

```shell
uvx --from zendev-review zendev-message check --title --text "✨ feat: add export"
uvx --from zendev-review zendev-message check --title --profile gitmoji --text ":sparkles: Add export"
uvx --from zendev-review zendev-message check --body --text "$PR_BODY" \
    --template .github/pull_request_template.md \
    --require-checklist
```

See [`zendev-commit`](../zendev-commit/README.md) for profile semantics.

The body section contract is:

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
