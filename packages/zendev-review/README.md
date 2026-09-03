# zendev-review

`zendev-review` owns reusable commit and pull-request message checks. It depends
on `zendev-commit` so title and complete-message checks reuse commit profiles.

```shell
uv add --dev zendev-review
uvx --from zendev-review zendev-message check --help
```

```python
from zendev.body import BodySection, validate_body

valid, headings = validate_body(
    "## Motivation\n\nWhy.\n\n## Solution\n\nHow.\n",
    [BodySection("Motivation"), BodySection("Solution")],
)
assert valid
```

Read the official [Message checks guide](https://docs.zendev.zrr.dev/guides/message-checks/),
[CLI reference](https://docs.zendev.zrr.dev/reference/cli/), and
[GitHub Actions integration](https://docs.zendev.zrr.dev/integrations/github-actions/)
for template rules, checklist behavior, and automation.
