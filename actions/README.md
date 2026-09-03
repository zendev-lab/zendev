# Composite Actions

The composite Actions in this directory adapt GitHub pull-request inputs to
`zendev message check` from the same pinned repository revision. Validation
semantics remain in the Python packages.

Available Actions:

- `zendev-lab/zendev/actions/validate-title@v0.3.0`
- `zendev-lab/zendev/actions/validate-body@v0.3.0`

Read the official
[GitHub Actions integration](https://docs.zendev.zrr.dev/integrations/github-actions/)
for permissions, inputs, and copyable workflows. The
[Message checks guide](https://docs.zendev.zrr.dev/guides/message-checks/)
defines title, body, template, and optional checklist behavior.

Inside this repository, use `./actions/validate-title` or
`./actions/validate-body` after checking out the repository.
