# Contributing to zendev

## Zendev Feature Proposals

Public feature and governance changes begin with a ZFP. ZFP prose defaults to
Chinese, but another language is allowed when it makes the proposal clearer;
machine metadata and technical identifiers remain English. See
[`zfps/README.md`](./zfps/README.md) and the governing
[`ZFP-0000`](./zfps/ZFP-0000-governance.md).

## Pull requests

Use a valid Gitmoji-style title. ZFP pull requests use `docs(zfp)` and one of
these verbs as a review convention, not as a machine-enforced lifecycle:

- `📝 docs(zfp): propose ZFP-NNNN <topic>`
- `📝 docs(zfp): revise ZFP-NNNN <topic>`
- `📝 docs(zfp): supersede ZFP-NNNN with ZFP-MMMM`

The pull-request body must retain the Chinese H2 structure in
[the repository template](./.github/pull_request_template.md): `动机` and
`解决方案` are required, while `说明` and `后续工作` are optional. Do not add a
checklist merely to satisfy process.
