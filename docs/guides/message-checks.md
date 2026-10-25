# Message checks

`zendev message check` validates text supplied as a file or with `--text`. Those input forms are mutually exclusive.

## Scope selection

Without a scope flag, a single-line input is checked as a title and a multi-line input is checked as a complete commit message. A newline never implicitly selects pull-request body validation.

Use an explicit scope for integrations:

```shell
zendev message check --commit .git/COMMIT_EDITMSG
zendev message check --title --text "✨ feat: add export"
zendev message check --body --text "$PR_BODY" \
  --template .github/pull_request_template.md
```

`--title` requires one line. `--body`, `--title`, and `--commit` are mutually exclusive, and `--profile` does not apply to body checks.

## Normalize an unambiguous message

A failed check suggests a valid replacement when the intention can be determined. The check remains read-only unless you add `--fix`:

```shell
zendev message check --commit --fix .git/COMMIT_EDITMSG
zendev message check --title --fix --text "feat(api): add export"
zendev message check --title --fix --text "deps: downgrade requests" --format json
```

The first command writes the corrected subject into the file. Literal text is only returned, never written to a file. JSON output uses the existing v1 envelope with `summary.changed` and `summary.text` when `--fix` is present. An unfixable message exits `1`; input or write failures exit `2`. `--fix` does not apply to `--body`.

Default conversion requires a valid Conventional Commit. Missing emoji are filled from the declared change type: for example, `feat(api): add export` becomes `✨ feat(api): add export`. Dependency descriptions need an explicit leading operation: `upgrade`, `update`, or `bump` selects ⬆️, `downgrade` selects ⬇️, `pin` selects 📌, `add` selects ➕, and `remove` selects ➖. Conflicting operations and `update`/`bump` messages containing `from` require manual choice; no version ordering is guessed. `deps: change dependencies` remains an error.

Non-Conventional titles such as `[ImgBot] Optimize images` have no built-in conversion. To give a repository-specific title an explicit meaning, declare an [exact TOML replacement](../reference/configuration.md#message-normalization-exceptions). Matching is case-sensitive and covers the complete subject. An explicit match takes precedence over default conversion, while already-valid messages remain unchanged. Each replacement is applied once and the complete candidate must still validate.

Valid messages retain their original emoji or shortcode. Incorrect emoji/type pairs, legacy types, and other free-form titles are left for the author. Conversion only repairs zendev-profile messages and always validates the candidate. Commit bodies, footers, comments, scissors, and line endings are preserved. See [prek](../integrations/prek.md) and [GitHub Actions](../integrations/github-actions.md) for automatic integration.

## PR template contract

Body validation reads H2 headings from the repository PR template. Every H2 is required by default. Override a heading's requirement with `<!-- pr-body:optional -->` or `<!-- pr-body:required -->` immediately before the heading:

```markdown
## Summary

<!-- pr-body:optional -->
## Notes
```

Present sections must retain template order. Undeclared, duplicate, ambiguous, or dangling sections and directives fail validation. Headings and directives inside code blocks, comments, quotes, and nested structures are ignored. A missing or invalid template is a configuration error; no default content is invented.

## Optional checklist enforcement

Checklist enforcement is off by default. When enabled, every checked row under the selected template H2 must have a checked task with the same visible text under that section in the body. List-marker style and inline formatting may vary; code examples and nested/quoted tasks do not count:

```shell
zendev message check --body --text "$PR_BODY" \
  --template .github/pull_request_template.md \
  --require-checklist \
  --checklist-section Checklist
```

Add `--fail-on-empty-checklist` when requesting checklist validation should fail if the template declares no checked rows.
