# Migrate to the domain architecture

This is one breaking migration. Migrate active repository configuration and
consumer code together; historical Git commit messages do not need rewriting.

## Dependencies and imports

| Removed interface | Replacement |
| --- | --- |
| `zendev-commit` distribution | `zendev-message` |
| `zendev-review` distribution | `zendev-message` |
| `zendev.commit`, `zendev.conventional`, `zendev.gitmoji` | `zendev.message`, `zendev.message.conventional`, `zendev.message.gitmoji` |
| `zendev.title`, `zendev.body`, `zendev.checklist` | `zendev.message.check_message`, `zendev.message.body.check_body` |
| `schema_pattern()`, emoji/type alias maps | `parse_message()`, `check_message()`, `zendev.message.policy.load_policy()` |
| `message(answers)` | `render_message(MessageDraft(...))` with explicit intention |
| Proposal `write_index` / source-only writers | `plan_changes(config)` then `apply_plan(plan)` |

`zendev`, `zendev commit`, `zendev message check`, and `zendev proposal check`
remain. Standalone `zendev-commit`, `zendev-message` and `zendev-proposal`
executables remain. JSON output now uses `--format json`; `--json` is removed.
Human output is the default, and `--format github` emits annotations. Message
and proposal checks return 0 for success, 1 for invalid content and 2 for
configuration/environment errors.

## Configuration

Choose `zendev.toml` or `[tool.zendev]` in `pyproject.toml`, not both in one
directory. Both use configuration version 1.

1. Move `[tool.zendev.commit]` to `[tool.zendev.message]` and add
   `[tool.zendev]` with `version = 1`; alternatively use `[message]` in `zendev.toml`.
2. Move `proposal.toml` settings into the same source. Keep metadata keys in
   `[proposal]` and nest auxiliary tables: `[templates]` becomes
   `[proposal.templates]`, `[graph]` becomes `[proposal.graph]`, etc.
3. Move the former `[proposal] index = "..."` string to
   `[proposal.index] path = "..."`. Retain `version = 2` inside that index table.
4. For the embedded source, prefix every table with `tool.zendev`, including
   `[tool.zendev.proposal.index]`. All paths remain relative to the source's directory.
5. Remove the old file/table, run `zendev proposal check --diff`, review the
   result, then run `--fix` if a generated index needs updating.

The CLI now discovers the nearest valid source from the working directory up
to the Git root. An unrelated `pyproject.toml` does not stop discovery.
`--config PATH` selects a single source explicitly. Old keys and conflicts fail
with migration diagnostics.

## Message policy and integrations

Replace intention-specific types with the fixed category types in the
[commit guide](commits.md). All five dependency operations use `deps`; choose
the operation's emoji explicitly. Old aliases are not accepted.

Use `--commit` for a commit-msg integration, including single-line messages.
Use `--title` for literal PR titles. A missing PR body template is an error;
there is no fallback English template. Only actual top-level Markdown sections
and task items satisfy policy. Code examples, comments, quotes, and nested
lists cannot satisfy checklist requirements.

Update all packages, hooks and Actions to the release containing this migration
together. Do not combine a new CLI with old components or old hook revisions.
