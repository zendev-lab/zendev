# Project evolution

Keep the original intent and subsequent changes in direction in one
`EVOLUTION.md`. Edit and read the file with your usual editor; Git records
revisions and handles collaboration. Zendev checks the document's structure.

## Start a record

Copy the [example template](https://github.com/zendev-lab/zendev/blob/main/templates/evolution.md)
into `EVOLUTION.md` and replace its example content with your project's
initial intent. Remove the example dated entry until you have a real change
to record. A document containing only the initial intent is valid.

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

## Check the document

```shell
zendev evolution check
zendev evolution check --file docs/EVOLUTION.md
```

The independently installed component provides the equivalent command:

```shell
zendev-evolution check
```

The default is the UTF-8 file `EVOLUTION.md` in the current directory.
The command does not search parent directories. Diagnostics include the file
path and line number. Exit codes are `0` for success, `1` for invalid document
structure, and `2` for usage, missing files, I/O, or UTF-8 decoding errors.

Checking never changes the file or creates auxiliary files.

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
