# Configuration reference

## Commit profiles

The nearest `pyproject.toml` may select the default profile:

```toml
[tool.zendev.commit]
profile = "zendev"
```

Accepted values are `zendev`, `conventional`, and `gitmoji`. The CLI's `auto`
selection reads this value and falls back to `zendev`. Unknown values and
non-string values fail closed.

## Proposal policy

`proposal.toml` is versioned, rejects unknown keys, and resolves all configured
paths relative to its repository root. Paths may not escape that root.

A minimal stateless policy looks like:

```toml
version = 1

[proposal]
prefix = "ZFP"
number_field = "zfp"
title_field = "title"
type_field = "type"
documents_dir = "zfps"
schema = "schemas/zfp.schema.json"
index = "zfps-index.json"
number_width = 4
metadata_title = "plain"
filename_slug_pattern = "[a-z0-9]+(?:-[a-z0-9]+)*"

[templates]
Feature = "templates/zfp.md"
Governance = "templates/zfp.md"

[index]
version = 2
entries_key = "zfps"
fields = ["zfp", { name = "path", source = "path" }, "title"]
```

### Proposal table

`proposal` defines the identifier and storage contract. `status_field` is
optional; omit it for stateless records. `metadata_title` accepts `plain` or
`prefixed`. In plain mode zendev constructs `# ZFP-0001: Title`; in prefixed
mode the metadata title already includes the identifier and must equal the H1.

### Templates and summaries

Each key in `templates` is an allowed value for the configured type field. Every
H2 in its Markdown template is required in documents of that type.

An optional `summary` table configures a required prose prefix and inclusive
sentence-count bounds:

```toml
[summary]
prefix = "**Executive Summary:**"
minimum_sentences = 2
maximum_sentences = 4
```

### Drafts

Omit `drafts` when a repository has no draft directory. When present, it accepts
`directory`, optional `schema`, optional `marker`, `require_summary`, and
`pre_proposal`. A pre-proposal draft is non-normative and must not assign a
proposal number or encode lifecycle status. A lifecycle draft uses
`pre_proposal = false` and must start in `Draft` status.

If no draft schema is configured, drafts use the formal proposal schema. A
draft's H1 must match its metadata title, and a configured marker must
immediately follow that H1. `require_summary` controls summary validation for
drafts. Unnumbered drafts are validated but never indexed. Numbered formal
proposals are indexed regardless of lifecycle status, when the repository uses one.

### Graph and history

The optional `graph.fields` array names relation metadata:

```toml
[graph]
fields = ["requires", "amends", "supersedes"]
requires_field = "requires"
amends_field = "amends"
supersedes_field = "supersedes"
accepted_status = "Accepted"
superseded_status = "Superseded"
```

Every configured relation rejects duplicate, self, and missing-target edges.
Integer references and canonical strings such as `VEP-0001` identify the same
proposal. The optional roles add stronger checks:

- `requires_field` rejects cycles and prevents an accepted proposal from
  transitively requiring a non-accepted proposal.
- `amends_field` requires amendment targets to remain accepted.
- `supersedes_field` validates coordinated supersession and exactly one
  accepted forward superseder.

The optional `history` table configures `initial_status`, record protection,
bootstrap numbers, and allowed transitions:

```toml
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
```

With a base ref, zendev rejects deleted formal records, proposal-number reuse at
a different path, invalid initial status, and transitions outside this table.
Bootstrap numbers may bypass the initial-status rule.

A narrow, reviewable historical exception can be kept in repository policy:

```toml
[[history.waivers]]
path = "proposals/VEP-0001-example.md"
from_status = "Accepted"
to_status = "Draft"
reason = "One-time bootstrap correction recorded by Process VEP-0000."
```

A waiver applies only to that exact path and transition. It does not create a
second lifecycle authority.

### Defined concepts

An optional `defines` table maps a metadata list to stable HTML anchors:

```toml
[defines]
field = "defines"
anchor_prefix = "term-"
id_pattern = "[a-z][a-z0-9-]*"
```

The validator requires each declared concept to have one matching anchor and
rejects missing, undeclared, or duplicate current owners. A superseded proposal
may keep its historical definition; current ownership can move only along the
configured `supersedes` closure.

### Index fields

Each `index.fields` entry is a string shorthand or a table with a unique output
`name`, a `source`, and an optional `key`. A string such as `"title"` means
`{ name = "title", source = "metadata", key = "title" }`.
Supported sources are `metadata`, `path`, and `inverse`. Metadata and inverse
sources require a key; path sources do not. Inverse keys must belong to `graph.fields`.
The configured `proposal.number_field` must be projected exactly once as metadata,
with both name and key unchanged. Missing, renamed, or repeated identity projections
are configuration errors; the generator does not inject fields.

Graph metadata keys and inverse fields produce integer edges to existing numbered
formal proposals. Renaming a graph output does not change normalization. Invalid
references, missing targets, unnumbered drafts, and external references fail before
generation or writing, including through the public Python indexing API. Ordinary
metadata such as `authors`, `defines`, or `id` is preserved; `id` has no special meaning.

Only `index.version = 2` is supported. Remove `source = "identifier"` and
`index.include_drafts` from older configurations, then regenerate the committed
index with `zendev proposal check --fix`. The top-level config version is unchanged.
Fields are emitted in configuration order. Documents sort by proposal number. JSON uses UTF-8,
two-space indentation, and one trailing newline before byte-for-byte comparison.

Unknown tables, keys, source names, invalid types, missing schemas or templates,
and unsafe paths are configuration errors rather than silently ignored policy.
