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
| `--body` | Check a PR body against a template. |
| `--profile auto\|zendev\|conventional\|gitmoji` | Select the title or complete-message profile. |
| `--template PATH` | Select the PR template for `--body`. |
| `--require-checklist` | Require checked template rows with `--body`. |
| `--checklist-section TITLE` | Select the checklist H2; defaults to `Checklist`. |
| `--fail-on-empty-checklist` | Fail if checklist enforcement finds no checked template rows. |

Without `--title` or `--body`, a single line selects title validation and a
multi-line input selects complete commit-message validation.

## Proposal check

| Option | Meaning |
| --- | --- |
| `--config PATH` | Proposal policy; defaults to `proposal.toml`. |
| `--base-ref REF` | Exact local Git ref for lifecycle history validation. |
| `--fix` | Write the deterministic index after successful validation. |
| `--json` | Emit stable JSON diagnostics. |

`PROPOSAL_BASE_REF` supplies `--base-ref` when the option is absent.

The proposal command exits `0` for valid state, `1` for invalid proposal or
index content, and `2` for configuration or environment errors. Other commands
exit non-zero when validation or the delegated Git operation fails.

## Component entry points

| Entry point | Equivalent responsibility |
| --- | --- |
| `zendev-commit` | Interactive commit workflow. |
| `zendev-message check` | Unified `zendev message check`. |
| `zendev-proposal check` | Unified `zendev proposal check`. |

Use `<command> --help` for the exact options installed on the current machine.
