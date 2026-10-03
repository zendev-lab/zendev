# Integrations

Zendev keeps adapters thin so the Python command remains the behavioral owner.

- [prek](prek.md) installs the public commit-message and proposal hooks.
- [GitHub Actions](github-actions.md) validates pull-request titles and bodies
  with composite Actions.

Both integrations pin a released zendev revision. Upgrade the pin deliberately
and review behavior changes before applying them across repositories.
