# Hook reference

The public manifest exposes these preferred hook IDs:

| Hook ID | Stage | Behavior |
| --- | --- | --- |
| `zendev-message-check` | `commit-msg` | Runs `zendev message check` on Git's message file. |
| `zendev-proposal-check` | `pre-commit` | Runs `zendev proposal check` and always evaluates repository state. |

Both hooks install the complete `zendev` distribution from the pinned repository
revision and forward configured `args`. Version `0.3.0` removed the legacy
`zendev-commit-msg` and `zendev-proposal` IDs.

See [prek](../integrations/prek.md) for a complete configuration.
