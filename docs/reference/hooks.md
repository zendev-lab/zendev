# Hook reference

The public manifest exposes these preferred hook IDs:

| Hook ID | Stage | Behavior |
| --- | --- | --- |
| `zendev-message-check` | `commit-msg` | Checks Git's message file and suggests unambiguous repairs without writing. |
| `zendev-message-fix` | `commit-msg` | Runs `zendev message check --commit --fix` to normalize unambiguous subjects before the commit. |
| `zendev-proposal-check` | `pre-commit` | Runs `zendev proposal check` and always evaluates repository state. |
| `zendev-evolution-check` | `pre-commit` | Opt-in check for an existing `EVOLUTION.md`; runs `zendev evolution check` without changed filenames. |

All hooks install the complete `zendev` distribution from the pinned repository revision and forward configured `args`.

See [prek](../integrations/prek.md) for a complete configuration.
