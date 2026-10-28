# prek

Zendev publishes hooks for message validation, optional message normalization, and read-only proposal validation.

## Configure hooks

Add the released repository to `prek.toml`:

```toml
default_install_hook_types = ["pre-commit", "commit-msg"]
default_stages = ["pre-commit"]

[[repos]]
repo = "https://github.com/zendev-lab/zendev"
rev = "v0.5.0"
hooks = [
  { id = "zendev-message-check" },
  { id = "zendev-proposal-check" },
]
```

Install the configured Git hooks and exercise every file:

```shell
uvx prek install --prepare-hooks
uvx prek run --all-files
```

`zendev-message-check` runs at `commit-msg`. `zendev-proposal-check` always runs, including deletion-only changes, so index and history drift cannot be skipped by a file-pattern mismatch.

## Pass command options

Hook `args` are forwarded to the matching command. For example:

```toml
hooks = [
  { id = "zendev-message-check", args = ["--profile", "conventional"] },
  { id = "zendev-proposal-check", args = ["--config", "zendev.toml"] },
]
```

Keep proposal checks read-only in normal commits. Run `zendev proposal check --fix` explicitly when the committed index must be updated.

## Normalize commit messages

At a pinned revision containing message normalization, choose `zendev-message-fix` in place of `zendev-message-check`:

```toml
[[repos]]
repo = "https://github.com/zendev-lab/zendev"
rev = "<release-or-commit>"
hooks = [
  { id = "zendev-message-fix" },
  { id = "zendev-proposal-check" },
]
```

Both message hooks run at `commit-msg`. The fix hook adds `--fix`, so a message such as `feat: add export` is committed as `✨ feat: add export`. It preserves the body and Git's message-file formatting. An ambiguous message still blocks the commit. The check hook only shows a suggested replacement and leaves the file unchanged. You can also enable fixes by adding `args = ["--fix"]` to the existing check hook; select one message hook per repository.

Both message hooks load [exact exceptions from repository TOML](../reference/configuration.md#message-normalization-exceptions); no bot title is recognized by default. Forward `--config` through hook `args` to select one explicit configuration file.

For a workspace-local hook, use `entry = "uv run zendev message check --commit --fix"` with `language = "system"` and `stages = ["commit-msg"]`. See the [message checks guide](../guides/message-checks.md#normalize-an-unambiguous-message) for the conversion boundaries.

A released hook installs the complete toolkit and its exact-version components. For unreleased development, use the workspace `uv run zendev` command or build all components together with `bash scripts/check_packages.sh` to validate their contents and isolated installations.
