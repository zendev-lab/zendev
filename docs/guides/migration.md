# Migrate to the domain architecture

Message interfaces require a breaking migration. Migrate their configuration and consumer code together; historical Git commit messages do not need rewriting. Existing `proposal.toml` files remain supported with their original layout.

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

`zendev`, `zendev commit`, `zendev message check`, and `zendev proposal check` remain. Standalone `zendev-commit`, `zendev-message` and `zendev-proposal` executables remain. JSON output now uses `--format json`; `--json` is removed. Human output is the default, and `--format github` emits annotations. Message and proposal checks return 0 for success, 1 for invalid content and 2 for configuration/environment errors.

## Configuration

For messages, choose `zendev.toml` or `[tool.zendev]` in `pyproject.toml`, not both in one directory. Move `[tool.zendev.commit]` to `[tool.zendev.message]` and add `[tool.zendev]` with `version = 1`; alternatively use `[message]` in `zendev.toml`. Old message tables still produce migration errors.

For proposals, keep the existing version 1 `proposal.toml`, including its top-level auxiliary tables and `[proposal] index = "..."` path. It may coexist with a unified file for messages, provided that file has no `proposal` table. Both layouts use the same current proposal validation rules and index version 2.

Moving proposals into a unified source is optional. If you choose to do so:

1. Keep metadata keys in `[proposal]` and nest auxiliary tables: `[templates]`
   becomes `[proposal.templates]`, `[graph]` becomes `[proposal.graph]`, etc.
2. Move `[proposal] index = "..."` to `[proposal.index] path = "..."`.
   Retain `version = 2` inside the index table.
3. For an embedded source, prefix every table with `tool.zendev`, including
   `[tool.zendev.proposal.index]`. Paths remain relative to the source's directory.
4. Remove the redundant dedicated file to avoid duplicate proposal definitions,
   then run `zendev proposal check --diff` and review the result before using `--fix`.

Discovery selects a source from the working directory up to the Git root; unrelated pyprojects are skipped. `--config PATH` selects a single source explicitly. Files are never merged and invalid configuration never falls back to another source. See [source discovery](../reference/configuration.md#source-discovery).

## Message policy and integrations

Replace intention-specific types with the fixed category types in the [commit guide](commits.md). All five dependency operations use `deps`; choose the operation's emoji explicitly. Old aliases are not accepted.

Use `--commit` for a commit-msg integration, including single-line messages. Use `--title` for literal PR titles. A missing PR body template is an error; there is no fallback English template. Only actual top-level Markdown sections and task items satisfy policy. Code examples, comments, quotes, and nested lists cannot satisfy checklist requirements.

Update all packages, hooks and Actions to the release containing this migration together. Do not combine a new CLI with old components or old hook revisions.
