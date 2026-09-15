# Project evolution

Keep the original intent and subsequent changes in direction in one
`EVOLUTION.md`. Edit and read the file with your usual editor; Git records
revisions and handles collaboration. Zendev initializes the document, lists its
dates, and checks its structure.

## Start a record

Write the initial intent as plain Markdown in `origin.md`, then create the
document with its required title and initial-intent heading:

```shell
zendev evolution init --from origin.md
```

The input must contain nonempty initial intent, without dated entries. It is
validated before creating the file. Existing files, directories, and symlinks
are never overwritten; concurrent initialization allows only one creator.
For UTF-8 standard input, use `--from -`:

```shell
zendev evolution init --from - < origin.md
```

A document containing only initial intent is valid. The
[example template](https://github.com/zendev-lab/zendev/blob/main/templates/evolution.md)
shows how to add a dated entry when there is a real change to record.

The format uses these top-level Markdown headings:

- `# 项目演进` is the document title.
- One nonempty `## 初始意图` comes first.
- Each subsequent `## YYYY-MM-DD` uses a real date, once per day, in ascending order.
- Each date contains `### 触发`, `### 变化`, and `### 理由`, in that order,
  with content beneath each heading.

Initial intent may contain lower-level subsections. A dated entry can use
H4 and lower headings inside its three required sections. Structural headings
use ATX syntax; headings inside code, HTML comments, lists, and blockquotes
do not define record sections. Blank space, comments, and subordinate headings
alone do not count as section content.

When the project's direction changes, append a date and explain the trigger,
change, and reason. Consolidate multiple changes on the same day in that day's
section. Correct existing prose in the editor and review the Git diff.

## Navigate and check the document

```shell
zendev evolution list
zendev evolution check
zendev evolution check --file docs/EVOLUTION.md
```

`list` validates the document before listing the initial intent and dates in
document order as `PATH:LINE: TITLE`. Open those lines in your editor to read
or edit the corresponding record. Invalid documents produce a diagnostic and
no partial list.

The independently installed component provides the same three commands:

```shell
zendev-evolution init --from origin.md
zendev-evolution list
zendev-evolution check
```

All three commands accept `--file PATH`; the default is the UTF-8 file
`EVOLUTION.md` in the current directory, without searching parent directories.
Diagnostics include the file
path and line number. Exit codes are `0` for success, `1` for invalid document
structure or invalid initial intent, and `2` for usage, missing files, existing
initialization targets, I/O, or UTF-8 decoding errors.

Listing and checking never change the file. No command creates locks or indexes.

## Recover earlier intent

Use existing documents, Git history, or dated discussions as evidence.
State uncertainty when the original intent cannot be recovered. Do not present
current goals as the original ones or invent dates. Link supporting proposals
and PRs in the prose. Keep source material until the new record has been reviewed.

## Optional prek hook

Enable `zendev-evolution-check` only after adding a document:

```toml
hooks = [
  { id = "zendev-evolution-check" },
]
```

The hook runs the same check without passing changed filenames. For a different
location, use `args = ["--file", "docs/EVOLUTION.md"]`.
See [prek integration](../integrations/prek.md) for repository configuration.
