# zendev-commit

`zendev-commit` owns commit profiles, Conventional Commits and Gitmoji
validation, the interactive commit flow, and its vendored data. It can be
installed and used without the complete `zendev` toolkit.

```console
$ uv add --dev zendev-commit
$ uvx --from zendev-commit zendev-commit --help
$ uvx --from zendev-commit zendev-commit-msg --help
```

`zendev-commit-msg` validates complete commit messages. `zendev-commit`
interactively builds a message and invokes `git commit`.

## Python API

```python
from zendev.commit import CommitProfile, validate_commit_message

result = validate_commit_message(
    "feat(parser): accept empty input",
    profile=CommitProfile.CONVENTIONAL,
)
assert result.valid
```

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

The published hook runs `uv run zendev-commit-msg` in the consuming
repository, so the command version comes from its `pyproject.toml` and
`uv.lock`. The `zendev-commit` development dependency installed above is
sufficient; the complete `zendev` toolkit also provides this command.

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
$ uvx --from zendev-commit zendev-commit-msg --profile conventional .git/COMMIT_EDITMSG
```

## Gitmoji data

The default profile uses the vendored catalog in
[`src/zendev/data/gitmojis.json`](./src/zendev/data/gitmojis.json) and the
reviewable pairing table in
[`src/zendev/data/emoji-conventions.toml`](./src/zendev/data/emoji-conventions.toml).
Validation is deterministic and does not access the network.

The retained upstream license is in
[`src/zendev/data/LICENSE.gitmoji`](./src/zendev/data/LICENSE.gitmoji).
Maintainers should follow the
[vendored-data procedure](../../CONTRIBUTING.md#vendored-gitmoji-data) when
refreshing the catalog.
