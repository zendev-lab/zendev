# Project evolution

Keep the original intent and subsequent changes in direction together in one
`EVOLUTION.md`. Read the origin and latest change without loading the whole
history into a conversation, or select a date when investigating an earlier
decision.

## Document format

```markdown
# 项目演进

## 初始意图

最初希望用一组工作流改善已有 Agent 的开发体验，
基于宿主可以提供执行生命周期的假设。

## 2026-09-08

### 触发
持久会话与执行调度逐渐超出宿主扩展能够承载的范围。

### 变化
目标调整为独立 Agent 产品，保留可追溯开发流程的初衷。

### 理由
接受维护运行时的成本，以获得完整的执行控制。
```

The title is `# 项目演进`. A single `## 初始意图` comes first and contains
nonempty prose. Its internal structure is free: explain the original problem,
audience, goal, and assumptions. No historical start date is required.

Each subsequent section is headed exactly `## YYYY-MM-DD`, using a real date.
Dates are unique and in ascending order. Each day contains exactly these
three nonempty H3 subsections in order: `触发`, `变化`, `理由`. Keep
multiple changes on the same day within these subsections. Use paragraphs,
lists, ordinary links, or H4 and lower headings for details. The first entry
is optional: a document containing only the initial intent is valid.

Use ATX (`#`) headings for the document structure. Fenced code examples,
including backtick and tilde fences, are ignored when identifying headings;
close each fence before continuing the document. The format has no
frontmatter, IDs, topic fields, separate index, or configuration file.

## Create and write

Put the original intent prose in `origin.md`, without the document or
`初始意图` heading:

```shell
zendev evolution init --from origin.md
```

Put a day's three H3 subsections in `change.md`, without a date heading:

```shell
zendev evolution write 2026-09-08 --from change.md
zendev evolution write 2026-09-08 --from change.md --replace
```

`init` refuses to overwrite any existing document. `write` requires an
initialized document, inserts a new date in chronological order, and refuses
to overwrite an existing date unless `--replace` is supplied. Replacement
requires that date to exist. `--from -` reads UTF-8 text from standard input:

```shell
cat change.md | zendev evolution write 2026-09-08 --from -
```

Historical text can be corrected with a normal editor, with Git preserving
the edits. Record a change in direction as a new dated entry rather than
rewriting the original intent to match today's goals.

## Read and validate

```shell
zendev evolution list
zendev evolution read
zendev evolution read --origin
zendev evolution read 2026-09-08
zendev evolution check
```

`list` prints the origin and dates with file paths and line numbers.
`read` without a date prints the original intent and latest day's record;
before the first change, it prints only the origin. `read --origin` prints
only the origin, while `read DATE` prints only that day. These outputs
preserve the selected Markdown source. A date and `--origin` cannot be combined.

Every command accepts `--file PATH`. The default is `EVOLUTION.md` in the
current directory; commands do not search parent directories. All reads and
writes validate the entire document so malformed sections cannot disappear
silently from the timeline. Validation checks structure, not the truth of
a rationale or the availability of external links.

Exit codes are `0` for success, `1` for invalid document or input content,
and `2` for usage, missing dates, I/O errors, or write conflicts. Diagnostics
include a path and line number on stderr. No command automatically fixes or
summarizes the history.

## Write conflicts

Writes preserve the source outside the selected date and use an atomic file
replacement. CLI writers coordinate through an exclusive sibling
`.EVOLUTION.md.lock` file (the name follows `--file`). A competing writer
fails immediately. The lock is removed when the writer exits normally.

If a writer crashes, confirm the process recorded in the lock is no longer
running before manually removing the stale lock. A snapshot check before
saving rejects external edits detected during preparation. Editors do not
participate in the CLI lock, so this is optimistic conflict detection, not a
filesystem-wide transaction; avoid editing the document during a CLI write.
Symlinks and non-regular document paths are rejected.

## Migrate an existing SPARK.md

First identify the initial intent from the existing document, Git history,
or dated discussions. Put only what those sources support in the origin.
If the original intent cannot be recovered completely, state that uncertainty
instead of presenting current goals as the original ones.

For example, an early record may describe a workflow extension while a later
discussion changes the goal to an independent product. Put the extension's
motivation in `初始意图`, and put the product transition under the date
supported by that discussion, using `触发`, `变化`, and `理由`.
Link the relevant proposal or PR in the prose. Do not invent missing dates.

There is no bulk migration command. Keep the source material until the new
record has been reviewed, then update repository links deliberately.

## Optional prek hook

Consumers can enable `zendev-evolution-check` from the same pinned repository
revision as their other zendev hooks:

```toml
hooks = [
  { id = "zendev-evolution-check" },
]
```

This hook runs `zendev evolution check` on every pre-commit invocation, without
passing changed filenames. It is opt-in: enable it only for a repository
with an initialized document. For a different location, configure
`args = ["--file", "docs/EVOLUTION.md"]`.
See [prek integration](../integrations/prek.md) for repository configuration.
