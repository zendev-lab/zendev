# Configuration reference

## Source discovery

Use `zendev.toml` or `[tool.zendev]` in `pyproject.toml` for unified configuration. Proposals also support the dedicated `proposal.toml` file with its original layout. All three sources use configuration version 1.

Discovery starts at the working directory and walks toward the Git root, including worktrees. Unrelated pyprojects are skipped. `zendev.toml` and `[tool.zendev]` in the same directory always conflict. For proposals, `proposal.toml` may coexist with a unified source that has no `proposal` table; defining proposals in both sources is an error, even if one table is empty. Message discovery ignores the dedicated file.

Each domain selects one source in its nearest configuration directory. Fields are never inherited from other files or directories. A nearest unified source without proposal settings or an adjacent `proposal.toml` produces a missing proposal configuration error; it does not fall back to an ancestor's policy. `--config PATH` selects one explicit source without considering siblings. The dedicated layout is identified by the filename `proposal.toml`; explicitly passing that file to a message command is a domain error. Paths resolve relative to the selected entry's directory, not the working directory. Symlinked files retain their entry name and directory for layout selection and relative paths.

```toml
version = 1

[message]
profile = "zendev"

[message.body]
template = ".github/pull_request_template.md"
require_checklist = false
checklist_section = "Checklist"
fail_on_empty_checklist = false
```

For `pyproject.toml`, place `version = 1` inside `[tool.zendev]` and prefix every table with `tool.zendev`, including `[tool.zendev.message.body]`. Profiles are `zendev`, `conventional`, and `gitmoji`; an explicit `--profile` overrides a valid configured value. Invalid configuration always fails closed. A missing body template is an error, even without checklist enforcement.

## Message normalization exceptions

Default normalization converts Conventional messages only. To assign meaning to a known non-Conventional subject, add an explicit mapping to the selected configuration:

```toml
[message.normalization.replacements]
"[ImgBot] Optimize images" = "⚡️ perf(assets): optimize images"
```

In `pyproject.toml`, the table is `[tool.zendev.message.normalization.replacements]`. The table defaults to empty; ZenDev has no built-in bot-title rules. Keys match the entire effective subject with exact case and whitespace, without regex, glob, variables, or recursive substitution. Values must be complete, single-line, valid zendev titles with an explicit emoji and type. Empty keys, multiline strings, invalid targets, unknown normalization keys, and incorrect value types are configuration errors even when a rule does not match.

For invalid zendev messages, an exact exception takes precedence over default Conventional conversion. Already-valid messages retain the author's choice. Other profiles do not apply replacements. Only the subject changes; the original commit body, footers, comments and line endings remain. An invalid complete candidate is not written. The [normalization guide](../guides/message-checks.md#normalize-an-unambiguous-message) explains CLI behavior; the full conversion order and dependency-word rules are specified in [ZFP-0009](https://github.com/zendev-lab/zendev/blob/codex/message-normalization-proposal/zfps/ZFP-0009-message-normalization.md).

## Proposal policy

Both dedicated and unified policies reject unknown keys and resolve configured paths relative to the selected file's directory. Paths may not escape that root.

A minimal stateless policy looks like:

```toml
version = 1

[proposal]
prefix = "ZFP"
number_field = "zfp"
documents_dir = "zfps"
schema = "schemas/zfp.schema.json"

[proposal.templates]
Feature = "templates/zfp.md"
Governance = "templates/zfp.md"

[proposal.index]
path = "zfps-index.json"
version = 2
entries_key = "zfps"
fields = ["zfp", { name = "path", source = "path" }, "title"]
```

### Dedicated proposal configuration

Existing repositories can keep `proposal.toml` without renaming the file or moving its tables. The equivalent minimal policy is:

```toml
version = 1

[proposal]
prefix = "ZFP"
number_field = "zfp"
documents_dir = "zfps"
schema = "schemas/zfp.schema.json"
index = "zfps-index.json"

[templates]
Feature = "templates/zfp.md"
Governance = "templates/zfp.md"

[index]
version = 2
entries_key = "zfps"
fields = ["zfp", { name = "path", source = "path" }, "title"]
```

In this layout, `drafts`, `templates`, `summary`, `graph`, `history`, `defines`, `index`, `sections`, `links`, and `fix` are top-level tables. Their fields have the same meaning as the `proposal.*` tables below. Only the index output path changes location: the `index` string in `[proposal]` replaces `[proposal.index] path`. Do not mix the two layouts within one file or put message settings in `proposal.toml`.

Both layouts use the same proposal rules, diagnostics, and index version 2. Checks, previews, and repairs never rewrite or migrate the configuration file. An index cannot overwrite or create `proposal.toml`, `zendev.toml`, or `pyproject.toml` in the configuration directory, including through path aliases.

### Proposal table

`proposal` requires `prefix`, `number_field`, `documents_dir`, and `schema`. The index output path is `proposal.index.path` in the unified layout, or `proposal.index` in the dedicated layout. Optional keys and their defaults are `title_field = "title"`, `type_field = "type"`, `status_field = "status"`, `number_width = 4` (`1..12`), `metadata_title = "plain"`, and `filename_slug_pattern = "[a-z0-9]+(?:-[a-z0-9]+)*"`.

`status_field` is only consulted when `[drafts]`, `[history]`, or status-aware graph roles are configured. `metadata_title` accepts `plain` or `prefixed`: in plain mode zendev constructs `# ZFP-0001: Title`; in prefixed mode the metadata title already includes the identifier and must equal the H1.

### Templates and summaries

Each key in `proposal.templates` is an allowed value for the configured type field. Every H2 in its Markdown template is required in documents of that type.

An optional `summary` table requires a Markdown blockquote (`> ...`) immediately below the H1 heading that begins with `prefix` and ends with sentence punctuation within inclusive sentence-count bounds (`minimum_sentences = 2`, `maximum_sentences = 4` by default):

```toml
[proposal.summary]
prefix = "**Executive Summary:**"
minimum_sentences = 2
maximum_sentences = 4
```

### Drafts

Omit `drafts` when a repository has no draft directory. When present, it accepts `directory`, optional `schema`, optional `marker`, `require_summary`, and `pre_proposal`. A pre-proposal draft is non-normative and must not assign a proposal number or encode lifecycle status. A lifecycle draft uses `pre_proposal = false` and must start in `Draft` status.

If no draft schema is configured, drafts use the formal proposal schema. A draft's H1 must match its metadata title, and a configured marker must immediately follow that H1. `require_summary` controls summary validation for drafts. Unnumbered drafts are validated but never indexed. Numbered formal proposals are indexed regardless of lifecycle status, when the repository uses one.

### Graph and history

The optional `graph.fields` array names relation metadata:

```toml
[proposal.graph]
fields = ["requires", "amends", "supersedes"]
requires_field = "requires"
amends_field = "amends"
supersedes_field = "supersedes"
accepted_status = "Accepted"
superseded_status = "Superseded"
```

Every configured relation rejects duplicate, self, and missing-target edges. Integer references and canonical strings such as `VEP-0001` identify the same proposal. The optional roles add stronger checks:

- `requires_field` rejects cycles and prevents an accepted proposal from
  transitively requiring a non-accepted proposal.
- `amends_field` requires amendment targets to remain accepted.
- `supersedes_field` validates coordinated supersession and exactly one
  accepted current superseder along the replacement chain.

Repositories can independently enable two additional dependency policies:

```toml
[proposal.graph]
fields = ["requires", "supersedes"]
requires_field = "requires"
require_declared_references = true
requires_earlier = true
```

Both options default to `false` and require a configured `requires_field`. `require_declared_references` requires each referenced proposal to appear directly in that metadata field. A transitive dependency or another relation does not authorize a reference. Self references do not require self dependencies.

References include canonical identifiers in prose, an inline code span containing only one canonical identifier (such as `VEP-0001`), and local links to discovered proposal documents, including fragments and reference-style links. Linked labels use their destination instead of contributing a second identifier. External links and their labels, absolute URLs, fenced or indented code, compound inline code examples, and HTML comments do not declare proposal references. An unknown canonical identifier in prose reports a missing target. Prefix and number width come from the repository configuration; unrelated navigation files are not scanned. This policy is independent of `links.check`.

`requires_earlier` requires dependency targets to have smaller proposal numbers. It uses numbers, not dates or Git history, and rejects forward dependencies even when the graph has no cycle. Unnumbered drafts still check direct declarations; they have no number to order. Existing draft, schema, and graph rules still apply.

| Diagnostic | Author action |
| --- | --- |
| `proposal.reference.undeclared-dependency` | Declare the referenced proposal directly in the dependency field, or correct the reference. |
| `proposal.reference.missing-target` | Correct the unknown canonical identifier. |
| `proposal.graph.forward-dependency` | Remove the later proposal as a prerequisite or revise the proposal's design. |

These diagnostics include the source location. Checks never add dependencies, remove references, or renumber proposals automatically, including with `--fix`. Enabling the policies may require a repository to backfill its actual direct dependencies and remove forward prerequisites. Index and metadata formats remain unchanged.

The optional `history` table configures `initial_status`, record protection, bootstrap numbers, and allowed transitions:

```toml
[proposal.history]
initial_status = "Draft"
protect_records = true
bootstrap_numbers = [0]

[proposal.history.transitions]
Draft = ["Draft", "Review", "Withdrawn"]
Review = ["Review", "Draft", "Accepted", "Rejected", "Withdrawn"]
Accepted = ["Accepted", "Superseded"]
Rejected = ["Rejected"]
Withdrawn = ["Withdrawn"]
Superseded = ["Superseded"]
```

With a base ref, zendev rejects deleted formal records, proposal-number reuse at a different path, invalid initial status, and transitions outside this table. Bootstrap numbers may bypass the initial-status rule.

A narrow, reviewable historical exception can be kept in repository policy:

```toml
[[proposal.history.waivers]]
path = "proposals/VEP-0001-example.md"
from_status = "Accepted"
to_status = "Draft"
reason = "One-time bootstrap correction recorded by Process VEP-0000."
```

A waiver applies only to that exact path and transition. It does not create a second lifecycle authority.

### Defined concepts

An optional `defines` table maps a metadata list to stable HTML anchors (all three keys are optional and default to the values shown):

```toml
[proposal.defines]
field = "defines"
anchor_prefix = "term-"
id_pattern = "[a-z][a-z0-9]*(?:-[a-z0-9]+)*"
```

The validator requires each declared concept to have exactly one matching `<a id="{anchor_prefix}{id}"></a>` anchor and rejects missing, undeclared, or duplicate current owners. A superseded proposal may keep its historical definition; current ownership can move only along the configured `supersedes` closure.

### Index fields

Each `index.fields` entry is a string shorthand or a table with a unique output `name`, a `source`, and an optional `key`. A string such as `"title"` means `{ name = "title", source = "metadata", key = "title" }`. Supported sources are `metadata`, `path`, and `inverse`. Metadata and inverse sources require a key; path sources do not. Inverse keys must belong to `graph.fields`. The configured `proposal.number_field` must be projected exactly once as metadata, with both name and key unchanged. Missing, renamed, or repeated identity projections are configuration errors; the generator does not inject fields.

Graph metadata keys and inverse fields produce integer edges to existing numbered formal proposals. Renaming a graph output does not change normalization. Invalid references, missing targets, unnumbered drafts, and external references fail before generation or writing, including through the public Python indexing API. Ordinary metadata such as `authors`, `defines`, or `id` is preserved; `id` has no special meaning.

Only `index.version = 2` is supported. Fields are emitted in configuration order. Documents sort by proposal number. JSON uses UTF-8, two-space indentation, and one trailing newline before byte-for-byte comparison.

Unknown tables, keys, source names, invalid types, missing schemas or templates, and unsafe paths are configuration errors rather than silently ignored policy.

### Additional proposal checks and repairs

```toml
[proposal.sections]
nonempty = true
ordered = true
no_skip_levels = true
placeholders = ["TBD", "TODO"]

[proposal.links]
check = true
heading_ids = "explicit"

[proposal.fix]
reference_style = "preserve"

[proposal.fix.aliases.status]
accepted = "Accepted"
```

Section constraints default to disabled. Placeholders match complete standalone prose lines, not words embedded in sentences or code examples. Required sections come from the configured template. Local link checking defaults to enabled and checks files and explicit HTML fragments. `heading_ids = "github"` additionally uses the vendored [github-slugger character tables](https://pypi.org/project/github-slugger/0.0.3/) for generated heading IDs, including duplicate suffixes and Unicode headings. Select this only for repositories rendered with that convention; `check = false` disables local link checking. External links are not fetched.

`graph.acyclic_fields` can name any configured graph fields without requiring lifecycle roles. Requires and supersedes roles are always acyclic. Drafts receive integrity checks for relationships they actually declare.

`fix.reference_style` accepts `preserve`, `number`, or `identifier`; the result must still satisfy the repository schema. Alias mappings are explicit strings and must target schema-declared fields and enum values. Chains are rejected.

Schemas and their file references are resolved offline inside the repository. Unknown formats, unresolved references, non-finite or non-JSON YAML values, output paths aliasing inputs, conflicting field roles and invalid history states are reported as errors. Optional index properties declared by a schema can remain null when absent; unknown projections cannot silently become null. Noncanonical Markdown extensions and nested proposal layouts are reported, not skipped. History paths work when the policy is in a Git subdirectory, and waivers must match the requested base transition when history checking is enabled.
