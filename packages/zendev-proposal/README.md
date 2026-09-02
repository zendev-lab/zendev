# zendev-proposal

`zendev-proposal` is a stateless validator and indexer for repositories that
store durable design proposals as Markdown. Git history remains the lifecycle
record, YAML frontmatter remains structured proposal metadata, templates remain
the required-section authority, and the committed JSON index remains a derived
projection.

The tool owns repository mechanics:

- safe YAML frontmatter parsing with duplicate-key rejection
- JSON Schema validation
- filename, number, title, H1, and Executive Summary consistency
- required H2 sections derived from repository templates
- frontmatter-bearing drafts with either the formal or a dedicated draft schema
- proposal relation integrity and inverse index edges
- optional defined-concept IDs and matching HTML anchors
- optional Git-backed deletion, number-reuse, initial-state, and transition checks
- deterministic index checking and `--fix` writes
- stable human and JSON diagnostics

Project terminology, normative semantics, process authority, and acceptance
decisions stay in each proposal repository.

Install this tool independently of the commit workflow:

```shell
uv add --dev zendev-proposal
```

For an ad hoc run, use `uvx --from zendev-proposal zendev-proposal ...`.
The complete `zendev` distribution exposes the same application through its
unified command:

```shell
uvx --from zendev zendev proposal --help
```

## Python API

```python
from zendev.proposal import load_config, validate_repository

config = load_config("proposal.toml")
result = validate_repository(config)
if not result.ok:
    for diagnostic in result.diagnostics:
        print(diagnostic)
```

Repositories using prek can install the published hook directly:

```toml
[[repos]]
repo = "https://github.com/zendev-lab/zendev"
rev = "v0.2.0"
hooks = [
  { id = "zendev-proposal-check" },
]
```

`zendev-proposal-check` is the read-only commit gate and also checks the
committed index. It always runs, including deletion-only commits. It never
receives `--fix`. Repair drift locally, then commit the result:

```shell
zendev proposal check --fix
```

## Commands

Run commands from the proposal repository root or pass an explicit config:

```shell
zendev-proposal check [--config proposal.toml] [--base-ref REF] [--fix] [--json]
```

`check` uses `PROPOSAL_BASE_REF` when `--base-ref` is absent. History validation
is disabled when neither is present. An explicitly requested ref must exist
locally; the tool fails closed instead of silently skipping lifecycle checks.

Exit codes have stable meanings:

- `0`: repository is valid and the requested index operation succeeded
- `1`: proposal documents, graph, history, or committed index are invalid
- `2`: the tool could not load its configuration, schema, templates, or Git ref

`check` never writes. `check --fix` validates proposal documents before replacing
the configured index. The index may be absent before the first explicit
`check --fix`.

## Policy file

The root policy is versioned TOML. This example models numbered VEP documents,
lightweight pre-VEP drafts, a proposal graph, and Git lifecycle transitions:

```toml
version = 1

[proposal]
prefix = "VEP"
number_field = "vep"
title_field = "title"
type_field = "type"
status_field = "status"
documents_dir = "veps"
schema = "schemas/vep.schema.json"
index = "veps-index.json"
number_width = 4
metadata_title = "plain"
filename_slug_pattern = "[a-z0-9]+(?:-[a-z0-9]+)*"

[drafts]
directory = "drafts"
schema = "schemas/draft.schema.json"
marker = "> Pre-VEP design draft. Non-normative."
pre_proposal = true

[templates]
Technical = "templates/technical.md"
Process = "templates/process.md"
Informational = "templates/informational.md"

[summary]
prefix = "**Executive Summary:**"
minimum_sentences = 2
maximum_sentences = 4

[graph]
fields = ["requires", "amends", "supersedes"]
requires_field = "requires"
amends_field = "amends"
supersedes_field = "supersedes"
accepted_status = "Accepted"
superseded_status = "Superseded"

[history]
initial_status = "Draft"
protect_records = true
bootstrap_numbers = [0]

[history.transitions]
Draft = ["Draft", "Review", "Withdrawn"]
Review = ["Review", "Draft", "Accepted", "Rejected", "Withdrawn"]
Accepted = ["Accepted", "Superseded"]
Rejected = ["Rejected"]
Withdrawn = ["Withdrawn"]
Superseded = ["Superseded"]

[index]
version = 1
entries_key = "veps"
include_drafts = false

[[index.fields]]
name = "vep"
source = "metadata"
key = "vep"

[[index.fields]]
name = "id"
source = "identifier"

[[index.fields]]
name = "path"
source = "path"

[[index.fields]]
name = "requires"
source = "metadata"
key = "requires"

[[index.fields]]
name = "required_by"
source = "inverse"
key = "requires"
```

All configured paths must remain under the repository root. The schema and
template files must already exist. Unknown policy keys are rejected so a typo
cannot silently disable a check.

### Title modes

`metadata_title = "plain"` keeps the identifier out of metadata and constructs
the formal H1 as `# VEP-0001: Title`. `metadata_title = "prefixed"` expects the
metadata title itself to start with `VEP-0001:` and requires the H1 to equal that
title. The second mode supports existing processes that treat the display title
as a single frontmatter field.

### Draft policy

Omit `[drafts]` when the repository does not use proposal drafts. When it is
configured, drafts use YAML frontmatter. `drafts.schema` selects a dedicated
schema; if omitted, drafts use the formal proposal schema. A draft must not
assign a proposal number, its H1 must match its metadata title, and an optional
`marker` must immediately follow that H1.

`pre_proposal = true` models non-normative exploration before the proposal
lifecycle. It additionally forbids status metadata, status sections, and
concrete proposal IDs in the body. A lifecycle draft instead uses
`pre_proposal = false` and must have `status: Draft`.

`require_summary = true` applies the configured Executive Summary policy to
drafts. Set `index.include_drafts = true` only when drafts belong in the
committed index. These independent settings cover the actual VEP pre-proposal
and SEP lifecycle-draft contracts without teaching the shared tool their
repository-specific schemas.

### Templates

Each key under `[templates]` is a value accepted by the configured proposal
type field. Every H2 heading in that template is required in documents of that
type. Headings inside fenced code blocks are ignored. This keeps the executable
section policy in the template instead of duplicating it in Python.

### Graph policy

Every configured graph field rejects duplicate, self, and missing-target edges.
Integer references and canonical strings such as `VEP-0001` are normalized to
the same identifier.

The optional role fields add semantic checks:

- `requires_field`: rejects cycles and prevents an accepted proposal from
  transitively requiring a non-accepted proposal
- `amends_field`: requires amendment targets to remain accepted
- `supersedes_field`: validates coordinated supersession and exactly one
  accepted forward superseder

Index fields with `source = "inverse"` derive reverse edges without storing two
writable authorities in proposal frontmatter.

### History policy and waivers

When a base ref is supplied, the tool verifies that formal records were not
deleted, proposal numbers were not reused under another path, new proposals
begin at `initial_status`, and existing statuses follow the transition table.

Bootstrap proposal numbers may bypass the initial-status rule. A repository can
also preserve a narrow historical exception without hard-coding it into the
shared tool:

```toml
[[history.waivers]]
path = "proposals/VEP-0001-example.md"
from_status = "Accepted"
to_status = "Draft"
reason = "One-time bootstrap correction recorded by Process VEP-0000."
```

Waivers apply only to the exact path and transition. Their required reason is a
review record, not a second lifecycle state.

### Defined concepts

Omit `[defines]` when the repository does not track concept ownership. When it
is present, each `defines` ID must have exactly one matching HTML anchor, each
matching anchor must be declared, and a concept may have only one current
owner. A superseded proposal may keep the historical definition. Ownership
moves only along the `supersedes` chain: previous owners must appear in the
current proposal's `supersedes` transitive closure.

```toml
[defines]
field = "defines"
anchor_prefix = "term-"
id_pattern = "[a-z][a-z0-9]*(?:-[a-z0-9]+)*"
```

## Index fields

Index fields are emitted in configuration order. Supported sources are:

- `metadata`: copy the configured frontmatter `key`
- `identifier`: emit the formatted prefix and number
- `path`: emit the repository-relative Markdown path
- `inverse`: derive sources that point to this proposal through relation `key`

Documents sort by number, followed by unnumbered frontmatter drafts sorted by
path. JSON uses UTF-8, two-space indentation, and one trailing newline.

## JSON diagnostics

`--json` emits one object to standard output:

```json
{
  "command": "check",
  "diagnostics": [
    {
      "code": "proposal.index.drift",
      "hint": "Run `zendev-proposal check --fix` and commit the result.",
      "line": null,
      "message": "committed proposal index is missing or out of date",
      "path": "veps-index.json"
    }
  ],
  "ok": false,
  "schema_version": 1,
  "summary": {
    "drafts": 3,
    "formal_proposals": 1,
    "index": "drifted"
  }
}
```

Diagnostic codes and JSON keys are the automation contract. Human messages may
be made more actionable without requiring consumers to parse prose.
