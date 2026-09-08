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
the committed deterministic index. Titles must be non-empty single-line text;
extra H1 headings and repeated required H2 sections are errors. The configured
draft marker must occur exactly once directly after the H1. When a draft also
requires a summary, the summary follows the marker.

With `[defines]` enabled, concept IDs must match the configured pattern and be
unique within the declaration list. Definition anchors must use the canonical
empty HTML tag, occur once, be declared, and satisfy ownership rules. Markdown
code examples and HTML comments do not count as anchors or markers. Other
metadata, such as tag enums or date formats, remains governed by your JSON Schema.

When proposal content changes, validate it and update the index in one command:

```shell
zendev proposal check --fix
```

`--fix` plans deterministic source repairs before updating the index:

| Problem | Source of the repair |
| --- | --- |
| Missing or mismatched opening H1 | Valid title and proposal number metadata |
| Missing draft marker | Exact text in `drafts.marker` |
| One standalone marker in the wrong position | Move that marker below the H1 |
| Undeclared definition anchor | Append its ID to the configured `defines.field` |
| Declared concept without an anchor | Insert the anchor before the only H2-H6 whose text exactly equals the ID |

For example, if `drafts.marker` is configured as follows, fixing a draft that
omits it inserts this line below its title:

```markdown
> Pre-VEP design draft. Non-normative.
```

A different blockquote immediately after the title is left for review, except
for an explicitly configured summary. Duplicate markers, duplicate ownership,
invalid metadata, and ambiguous definition locations are not guessed away.
YAML aliases and unsupported layouts are left unchanged. Local edits retain
comments, unrelated formatting, and existing line endings.

The candidate repository must pass all checks, including requested history
checks, before source files or the index are written. If validation still fails,
no repairs are applied; diagnostics describe the remaining candidate errors.
Human output explains that repairs were withheld. With `--json --fix`, summary
fields `fixed_files` and `pending_files` list applied and withheld source edits,
respectively. Inspect the diff after fixing. Running the same fix again makes no
changes. File-system failures are reported as tool errors; multi-file writes are
not a filesystem transaction.

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
