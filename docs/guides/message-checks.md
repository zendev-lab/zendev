# Message checks

`zendev message check` validates text supplied as a file or with `--text`.
Those input forms are mutually exclusive.

## Scope selection

Without a scope flag, a single-line input is checked as a title and a
multi-line input is checked as a complete commit message. A newline never
implicitly selects pull-request body validation.

Use an explicit scope when the input is a PR title or body:

```shell
zendev message check --title --text "✨ feat: add export"
zendev message check --body --text "$PR_BODY" \
  --template .github/pull_request_template.md
```

`--title` requires one line. `--body` and `--title` are mutually exclusive, and
`--profile` does not apply to body checks.

## PR template contract

Body validation reads H2 headings from the repository PR template. Every H2 is
required by default. Mark exceptions immediately before the heading:

```markdown
## Summary

<!-- pr-body:optional -->
## Notes
```

Present sections must retain template order. Undeclared, duplicate, ambiguous,
or dangling sections and directives fail validation. Headings and directives
inside fenced code blocks are ignored.

## Optional checklist enforcement

Checklist enforcement is off by default. When enabled, every checked row under
the selected template H2 must appear verbatim in the body:

```shell
zendev message check --body --text "$PR_BODY" \
  --template .github/pull_request_template.md \
  --require-checklist \
  --checklist-section Checklist
```

Add `--fail-on-empty-checklist` when requesting checklist validation should fail
if the template declares no checked rows.
