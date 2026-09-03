# Commits

Zendev can create a commit interactively and validate messages against one of
three profiles.

## Select a profile

Set the repository default in `pyproject.toml`:

```toml
[tool.zendev.commit]
profile = "zendev"
```

The available profiles are:

| Profile | Contract |
| --- | --- |
| `zendev` | A Gitmoji emoji or shortcode paired with its canonical commit type. |
| `conventional` | Conventional Commits 1.0.0, including scopes, breaking changes, bodies, and footers. |
| `gitmoji` | Gitmoji title syntax with Unicode or shortcode intentions and an optional scope or body. |

`auto` reads the nearest `[tool.zendev.commit]` table and falls back to the
`zendev` profile.

## Create a commit

Stage the intended files, then run:

```shell
zendev commit
```

The command prompts for type, scope, summary, body, breaking-change status, and
footer, then invokes `git commit` with the assembled message.

Examples accepted by the `zendev` profile include:

```text
✨ feat: add export
🐛 fix(parser): handle null token
:memo: docs: update README
```

Git-generated `Merge`, `Revert`, `fixup!`, `squash!`, `amend!`, and `reword!`
prefixes are accepted.

## Validate without committing

Validate a title directly:

```shell
zendev message check --title --text "✨ feat: add export"
```

Validate a complete commit-message file and select a profile explicitly:

```shell
zendev message check --profile conventional .git/COMMIT_EDITMSG
```

Install the reusable hook through [prek](../integrations/prek.md) to make this a
commit-time gate.
