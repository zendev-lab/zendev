# Agent standing orders

Repository-wide instructions for coding agents working in this repo. Human setup,
validation gates, and pull-request rules live in
[CONTRIBUTING.md](./CONTRIBUTING.md) — read that file; do not duplicate command
matrices or workflow checklists here.

## Orientation

- Read [README.md](./README.md) for product overview and navigation.
- Public design and governance changes go through **ZFPs** (Zendev Feature
  Proposals). Follow the process in [zfps/README.md](./zfps/README.md) and
  [ZFP-0000](./zfps/ZFP-0000-governance.md). Do not invent a parallel process.

## Working in the tree

- Prefer a **dedicated git worktree** for agent edits so unrelated uncommitted
  work in the main worktree is not disturbed.
- Keep facts in one authoritative home and **link** instead of copying. Document
  ownership is defined in [CONTRIBUTING.md](./CONTRIBUTING.md#documentation-ownership).

## Do not commit

- Secrets, credentials, or `.env` files.
- Generated documentation output under `site/`.

## Pull requests

Follow [CONTRIBUTING.md](./CONTRIBUTING.md#pull-requests) and
[`.github/pull_request_template.md`](./.github/pull_request_template.md):

- Body must keep the Chinese H2 structure: **`动机`** and **`解决方案`** are
  required; **`说明`** and **`后续工作`** are optional.
- Use **Draft** until validation is ready.
- Record material validation in the solution or notes — do not add checklist
  items merely to satisfy process.

## Security

Report vulnerabilities **privately** via
[SECURITY.md](./SECURITY.md) (GitHub Security Advisories). Do not open public
issues for security findings.

## After work

Report what changed, what was validated, and what was not.
