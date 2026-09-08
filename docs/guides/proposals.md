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

## Repository governance

Each repository defines when a proposal is required and how authors are
identified. Put the authoritative rules in the governing proposal, link them
from the contribution guide, and align templates and schemas with those rules.
For example, ZFP authors use lowercase GitHub usernames; another repository may
choose display names or another identity format. The shared checker enforces
the supplied schema without imposing GitHub identities or querying accounts.
Repairs must not infer a username from a person's name.

Proposal thresholds are human review decisions. Distinguish a new public
contract or governance decision from implementation of an existing decision.
A passing check does not establish that an implementation PR has supplied every
required design proposal; file counts, commit labels and keywords cannot prove
that requirement.

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
code examples do not count as anchors, markers, status declarations or concrete
proposal references. HTML comments do not define anchors; an exact comment
explicitly configured as the draft marker is supported. Other
metadata, such as tag enums or date formats, remains governed by your JSON Schema.

When proposal content changes, validate it and update the index in one command:

```shell
zendev proposal check --fix
```

`--fix` plans deterministic source repairs before updating the index:

| Problem | Source of the repair |
| --- | --- |
| Missing number or title | Unique canonical filename or matching opening H1 |
| Redundant title prefix or surrounding whitespace | Configured title mode |
| Duplicate declaration or relationship entries | Equivalent values, retaining first occurrence |
| Missing required empty defines list | Schema requirement and absence of definition anchors |
| Missing required sections | Template headings only; content checks remain active |
| Value aliases or reference representation | Explicit `fix` policy |
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

By default, the candidate repository must pass all checks, including requested
history checks, before any source or index is written. Diagnostics always describe
the actual files. `summary.candidate_diagnostics` separately reports candidate
errors; `fixed_files`, `pending_files`, and `repairs` identify applied or proposed
source edits, their rules and evidence. Diagnostics include `fixable` and locations.

Preview without writing, or select repair rules:

```shell
zendev proposal check --diff
zendev proposal check --fix --select number,title,h1,marker,defines
```

Available rules are `number`, `title`, `h1`, `marker`, `defines`, `deduplicate`,
`references`, `aliases`, and `sections`. `--diff` takes precedence over `--fix` and
includes the patch in JSON output. It retains the actual repository's exit status.

For independent safe source fixes despite unrelated errors, explicitly use:

```shell
zendev proposal check --fix --partial --select marker,sections
```

Partial mode rejects edits introducing identity, schema, graph, ownership or
history failures. Remaining errors still produce exit code 1, and the index is
updated only when the resulting repository is valid. Empty section scaffolds do
not invent prose or bypass a configured nonempty requirement.

Before replacement, all source and index contents are prepared in temporary
files, and the input snapshot is checked again. An ordinary write failure rolls
back applied replacements where possible; the error reports `written_files`,
`rolled_back_files`, and recovery backups if rollback fails. This is not a
cross-file crash transaction. Inspect the diff after fixing; a second successful
fix makes no changes.

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
      "fixable": true,
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
