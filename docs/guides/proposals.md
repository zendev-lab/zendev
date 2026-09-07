# Proposals

`zendev-proposal` validates repositories that keep durable design records as
Markdown. The complete toolkit exposes the same application as
`zendev proposal`.

## Repository shape

A proposal repository supplies its own policy and content:

```text
proposal.toml
schemas/
templates/
proposals/
proposals-index.json
```

Directory names are configurable. The repository owns its schema, template
headings, terminology, graph fields, lifecycle rules, and waivers.

## Check committed state

Run the read-only gate from the proposal repository root:

```shell
zendev proposal check
```

The command validates configuration, frontmatter, JSON Schema, filenames,
headings, summaries, optional drafts, optional relationships and history, and
the committed deterministic index.

When proposal content changes, validate it and update the index in one command:

```shell
zendev proposal check --fix
```

`--fix` writes only after proposal validation succeeds. It reports whether the
index changed or was already current.

## Validate history

Pass an exact local Git ref or set `PROPOSAL_BASE_REF`:

```shell
git fetch origin main
zendev proposal check --base-ref origin/main
```

History validation is disabled when no base ref is provided. An explicitly
requested ref must exist locally; zendev fails closed rather than silently
skipping history checks.

## Consume diagnostics

Human diagnostics include a stable code, path, and line when available. Use
`--json` for a stable envelope suitable for other tools:

```shell
zendev proposal check --json
```

Exit codes distinguish valid state (`0`), invalid repository content (`1`),
and configuration or environment errors (`2`).

The JSON envelope is versioned independently of human wording:

```json
{
  "command": "check",
  "diagnostics": [
    {
      "code": "proposal.index.drift",
      "hint": "Run `zendev-proposal check --fix` and commit the result.",
      "line": null,
      "message": "committed proposal index is missing or out of date",
      "path": "proposals-index.json"
    }
  ],
  "ok": false,
  "schema_version": 1,
  "summary": {
    "drafts": 0,
    "formal_proposals": 3,
    "index": "drifted"
  }
}
```

Diagnostic codes and JSON keys are the automation contract. Human diagnostics
may become more actionable without requiring consumers to parse prose.

See [Configuration](../reference/configuration.md) for the policy surface and
[Hooks](../reference/hooks.md) for commit-time enforcement.
