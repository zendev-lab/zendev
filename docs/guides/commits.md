# Commits

Zendev creates commits interactively and checks messages against three profiles.
Select a default in `zendev.toml`:

```toml
version = 1

[message]
profile = "zendev"
```

The equivalent `[tool.zendev]` configuration in `pyproject.toml` uses
`version = 1` and `[tool.zendev.message]`. Choose one source per directory.
See [configuration discovery](../reference/configuration.md).

| Profile | Contract |
| --- | --- |
| `zendev` | A Gitmoji intention followed by an allowed change type and Conventional Commits syntax. |
| `conventional` | Conventional Commits syntax, without the ZenDev type or emoji policy. |
| `gitmoji` | Gitmoji Unicode or shortcode intention, optional scope, subject and body. |

When `--profile` is omitted, the repository setting applies, falling back to
`zendev` when no setting exists.

## Type and intention

Types classify changes: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`,
`test`, `build`, `ci`, `chore`, `deps`, and `revert`. The emoji states a more
specific intention. The pairing policy restricts which types each intention
can accompany; an error lists that intention's allowed types.

```text
✨ feat: add export
🐛 fix(parser): handle null token
:memo: docs: update README
⬆️ deps: upgrade dependencies
⬇️ deps: downgrade dependencies
📌 deps: pin a dependency
➕ deps: add a dependency
➖ deps: remove a dependency
💥 refactor!: replace the public API
```

`deps` is a category for every dependency operation. The old `deps-up`,
`deps-down`, `deps-pin`, `deps-add`, and `deps-remove` types are removed.
Generation always requires an explicit intention. `💥` requires `!` or a
`BREAKING CHANGE` footer; other intentions may also declare breaking changes.
The complete policy is defined in
[ZFP-0006](https://github.com/zendev-lab/zendev/blob/main/zfps/ZFP-0006-domain-architecture.md).

## Create and check

Stage files, then run `zendev commit`. The prompts select a type and an allowed
intention before collecting scope, summary, body, breaking status and footers.
The assembled message is validated before invoking Git.

```shell
zendev message check --title --text "✨ feat: add export"
zendev message check --commit --profile conventional .git/COMMIT_EDITMSG
```

Only commit context removes Git comments/scissors and accepts Git-generated
`Merge`, `Revert`, `fixup!`, `squash!`, `amend!`, and `reword!` prefixes. Titles
are checked literally. The [prek hook](../integrations/prek.md) explicitly
selects `--commit`, including for single-line generated messages.
