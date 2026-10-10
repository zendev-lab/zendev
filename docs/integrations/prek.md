# prek

Zendev publishes read-only hooks for commit-message and proposal validation.

## Configure hooks

Add the released repository to `prek.toml`:

```toml
default_install_hook_types = ["pre-commit", "commit-msg"]
default_stages = ["pre-commit"]

[[repos]]
repo = "https://github.com/zendev-lab/zendev"
rev = "<release-or-commit>"
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

`zendev-message-check` runs at `commit-msg`. `zendev-proposal-check` always
runs, including deletion-only changes, so index and history drift cannot be
skipped by a file-pattern mismatch.

## Pass command options

Hook `args` are forwarded to the matching command. For example:

```toml
hooks = [
  { id = "zendev-message-check", args = ["--profile", "conventional"] },
  { id = "zendev-proposal-check", args = ["--config", "zendev.toml"] },
]
```

Keep proposal checks read-only in normal commits. Run
`zendev proposal check --fix` explicitly when the committed index must be
updated.

Version `0.3.0` replaced the legacy IDs `zendev-commit-msg` and
`zendev-proposal` with the names above. The old IDs are no longer published.

Replace `<release-or-commit>` with the release containing the migration. A
released hook installs the complete toolkit and its exact-version components.
For unreleased development, use the workspace `uv run zendev` command or build
all components together with `just packages` to validate their contents and
isolated installations.
