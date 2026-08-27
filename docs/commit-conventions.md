# Commit conventions

`zendev-commit-msg` validates complete commit messages. `zendev-commit`
interactively builds the default zendev format and invokes `git commit`.

## Profiles

Configure the default profile in the consuming repository:

```toml
[tool.zendev.commit]
profile = "conventional"
```

The `--profile` option overrides repository configuration. `auto` reads the
nearest `pyproject.toml` and falls back to `zendev`.

| Profile | Contract |
| --- | --- |
| `zendev` | A Gitmoji emoji or shortcode paired with its canonical commit type. |
| `conventional` | Conventional Commits 1.0.0, including scopes, breaking changes, bodies, and footers. |
| `gitmoji` | The Gitmoji title shape with Unicode or shortcode intentions and optional scope/body. |

Examples accepted by the default profile:

```text
🎉 init: begin a project
✨ feat: add export
🐛 fix(parser): handle null token
:memo: docs: update README
🚀 deploy: publish the package
```

Git-generated `Merge`, `Revert`, `fixup!`, `squash!`, `amend!`, and `reword!`
messages are accepted.

## Commit hook

With `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/zendev-lab/zendev
    rev: v0.1.0
    hooks:
      - id: zendev-commit-msg
```

With `prek.toml`:

```toml
[[repos]]
repo = "https://github.com/zendev-lab/zendev"
rev = "v0.1.0"
hooks = [
  { id = "zendev-commit-msg" },
]
```

Install the Git hook:

```console
$ uvx prek install --hook-type commit-msg
```

An explicit command is also available:

```console
$ uvx --from zendev zendev-commit-msg --profile conventional .git/COMMIT_EDITMSG
```

## Gitmoji data

The default profile uses the vendored catalog in
[`src/zendev/data/gitmojis.json`](../src/zendev/data/gitmojis.json) and the
reviewable pairing table in
[`src/zendev/data/emoji-conventions.toml`](../src/zendev/data/emoji-conventions.toml).
Validation is deterministic and does not access the network.

Maintainers can refresh the catalog from its pinned upstream commit:

```console
$ just sync-gitmoji
```

The refresh command validates the upstream payload before replacing the
vendored file. The retained upstream license is in
[`src/zendev/data/LICENSE.gitmoji`](../src/zendev/data/LICENSE.gitmoji).
