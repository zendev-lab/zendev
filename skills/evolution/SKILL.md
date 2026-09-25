---
name: evolution
description: >
  Create or update one EVOLUTION.md: initialize the original intent, or append a real dated entry when the direction changes, then validate with zendev evolution check. Use when recording project intent, initializing an evolution document, or writing down why the direction changed, including “写演进记录”, “初始化 EVOLUTION.md”, and “方向变了帮我记下来”. Do not use for weekly plans, task lists, design tradeoffs, or Git delivery. Do not invent dates or present current goals as the original intent.
---

# Project evolution

Keep the original intent and later direction changes in one `EVOLUTION.md`.
The document shape and commands are defined by the
[evolution guide](../../docs/guides/evolution.md)
([published copy](https://docs.zendev.zrr.dev/guides/evolution/)) and the
installed `zendev evolution --help`. This skill decides when to write, what may be
inferred, and when to stop. It does not define a second format, and it does
not replace that guide with a `SPARK.md` or any other intent note.

## Decide whether to change the file

- Create the document when the project has an initial intent worth keeping and
  no `EVOLUTION.md` yet.
- Append one dated entry only when the direction actually changes. Record the
  trigger, the change, and the reason in that entry.
- Same-day changes belong in that day's entry. Do not invent a date, reuse a
  date, or place today's goals into the original intent.
- Correct existing prose in the editor. Git records the revision. Do not add
  locks, indexes, or a task list.

Prose follows the user's language, or the language already used in the file.
Structural headings stay as the guide requires; do not translate them.

## Draft, then validate

Ask only for a gap that would change what gets recorded. Give a concrete draft
before writing. Mark a reasonable but unconfirmed inference in an HTML comment.
That comment does not count as section content.

Initialize from validated initial intent with `init`. Initialization must not
overwrite an existing file, directory, or symlink. `list` and `check` are
read-only. The default file is `EVOLUTION.md` in the current directory; pass
`--file` for another path and do not search parent directories.

Exact flags come from the installed `--help` of `zendev evolution` or
`zendev-evolution`. After a write, run `check`. Exit `0` means the document is
valid, `1` means the document or initial intent is invalid, and `2` means
usage, I/O, encoding, a missing file, or an existing initialization target.
Do not claim the file is valid without that result. If the command is missing,
say so and keep the draft; do not invent a checker.

Use existing documents, Git history, or dated discussions as evidence. When
the original intent cannot be recovered, say what is unknown. Link supporting
proposals and pull requests in the prose, and keep the source material until
the new record has been reviewed.

## Stop

Writing the Markdown does not authorize a commit, push, hook install, or
history rewrite. Enable `zendev-evolution-check` only after the document
exists, and leave repository hook setup to the project's existing
configuration. Weekly planning, design tradeoffs, and delivery stay outside
this skill.
