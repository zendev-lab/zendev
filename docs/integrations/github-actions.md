# GitHub Actions

Zendev provides composite Actions for pull-request title and body validation and optional title normalization. They share the message rules from the same pinned release.

## Validate a PR title

```yaml
jobs:
  title:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: read
    steps:
      - uses: actions/checkout@v4
      - uses: zendev-lab/zendev/actions/validate-title@v0.5.0
        with:
          text: ${{ github.event.pull_request.title }}
```

Supply `text`, or at a revision containing message normalization use `pull-request-number` to read the live title instead. These inputs are mutually exclusive. Live reads use the optional `token`, which defaults to `github.token` and needs `pull-requests: read`. Omit `profile` to use repository configuration, or override with `zendev`, `conventional`, or `gitmoji`.

## Normalize a PR title and rerun policy

Use a separate workflow after your PR policy completes. This works for fork PRs while the privileged job executes only the pinned Action implementation. It does not require a checkout:

```yaml
name: Automation - PR Title
on:
  workflow_run:
    workflows: ["Policy - PR"]
    types: [completed]
permissions: {}
concurrency:
  group: pr-title-${{ github.event.workflow_run.head_repository.full_name }}-${{ github.event.workflow_run.head_branch }}
  cancel-in-progress: false
jobs:
  title:
    if: >-
      github.event.workflow_run.event == 'pull_request' &&
      github.event.workflow_run.conclusion == 'failure'
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      actions: write
    steps:
      - uses: zendev-lab/zendev/actions/normalize-title@<release-or-commit>
```

Replace the revision with a commit or release containing normalization, and match `workflows` to the name of your policy workflow. The automation must be on the default branch before `workflow_run` can trigger it. Never check out the PR head or execute its files in this job. Zendev's own workflow also invokes a pinned remote Action without checking out the repository.

The Action reads the current title and applies only [unambiguous conversions](../guides/message-checks.md#normalize-an-unambiguous-message). It requires a unique open PR matching the source repository, branch, and head SHA. It checks the head and title again before writing; an outdated or ambiguous match is skipped. Already-valid titles stay unchanged. Unfixable titles emit a notice; GitHub API errors fail the Action. Only an actual rename reruns the completed policy run, so repeated runs stop after a valid title is present.

`token` defaults to `github.token`. `profile` defaults to `zendev`; this Action uses the explicit input rather than repository configuration and does not convert other profiles. Outputs are `changed` (`true` or `false`) and `title` (empty when no current PR matches). A direct `pull_request` invocation also works when its token can write PR metadata; it does not rerun the currently executing workflow.

[Edits made with GITHUB_TOKEN do not start an edited-event workflow](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow). Configure the title check in `Policy - PR` to read live metadata when the completed run is rerun:

```yaml
- uses: zendev-lab/zendev/actions/validate-title@<release-or-commit>
  with:
    pull-request-number: ${{ github.event.pull_request.number }}
```

This validation step still needs the normal repository checkout for configuration discovery. Passing `${{ github.event.pull_request.title }}` as `text` continues to check the event snapshot, which may contain the pre-rename title on a rerun.

## Validate a PR body

```yaml
jobs:
  body:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: read
    steps:
      - uses: actions/checkout@v4
      - uses: zendev-lab/zendev/actions/validate-body@v0.5.0
        with:
          body: ${{ github.event.pull_request.body }}
          template: .github/pull_request_template.md
```

`body` is required. Omitted template/checklist inputs use repository configuration; without configuration the template is `.github/pull_request_template.md` and checklist enforcement is disabled. Override with `template`, `require-checklist`, `checklist-section`, or `fail-on-empty-checklist`. Boolean overrides accept `true` or `false`. Both Actions emit GitHub annotations from the shared diagnostic renderer.

The validation Actions require checkout because configuration discovery and the body template are repository-local inputs. Give validation jobs read-only permissions; only the separate normalization job needs write permissions.
