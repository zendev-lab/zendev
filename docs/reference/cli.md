# CLI reference

## Unified command

```text
zendev commit
zendev message check [OPTIONS] [FILE]
zendev proposal check [OPTIONS]
```

`python -m zendev` exposes the same tree.

## Message check

| Option | Meaning |
| --- | --- |
| `FILE` | Read message text from a file; mutually exclusive with `--text`. |
| `--text TEXT` | Validate literal text; mutually exclusive with `FILE`. |
| `--title` | Check exactly one title line. |
| `--commit` | Explicit Git commit context, including single-line generated messages. |
| `--config PATH` | Select one ZenDev configuration source. |
| `--format human\|json\|github` | Select shared diagnostic output; defaults to human. |
| `--body` | Check a PR body against a template. |
| `--profile zendev\|conventional\|gitmoji` | Select the title or complete-message profile. |
| `--template PATH` | Select the PR template for `--body`. |
| `--require-checklist` | Require checked template rows with `--body`. |
| `--checklist-section TITLE` | Select the checklist H2; defaults to `Checklist`. |
| `--fail-on-empty-checklist` | Fail if checklist enforcement finds no checked template rows. |

Without `--title`, `--body`, or `--commit`, a single line selects title validation and a
multi-line input selects complete commit-message validation.

## Proposal check

| Option | Meaning |
| --- | --- |
| `--config PATH` | Explicit configuration source; otherwise use nearest-source discovery. |
| `--base-ref REF` | Exact local Git ref for lifecycle history validation. |
| `--diff` | Preview source/index repairs without writing. |
| `--select RULES` | Comma-separated repair rules. |
| `--partial` | Explicitly apply independent safe repairs; retain errors and withhold an invalid index. |
| `--fix` | Repair deterministic source omissions and update the index after successful validation. |
| `--format human\|json\|github` | Shared human, JSON envelope, or GitHub annotations. |

`PROPOSAL_BASE_REF` supplies `--base-ref` when the option is absent.

Message and proposal checks exit `0` for valid state, `1` for invalid proposal or
index content, and `2` for configuration or environment errors. The interactive commit command propagates the delegated Git exit code.

## Component entry points

| Entry point | Equivalent responsibility |
| --- | --- |
| `zendev-commit` | Interactive commit workflow. |
| `zendev-message check` | Unified `zendev message check`. |
| `zendev-proposal check` | Unified `zendev proposal check`. |

Use `<command> --help` for the exact options installed on the current machine.

## Project evolution

`zendev evolution` exposes `init --from PATH`, `list`, and `check` for creating
a document, locating its dates, and validating it. Initialization refuses to
overwrite existing paths; listing and checking are read-only.
The standalone `zendev-evolution` command exposes the same surface. All commands
accept `--file PATH` and `--format human|json|github`; see the [Evolution guide](../guides/evolution.md) for
the document format, template, diagnostics, and exit codes.
