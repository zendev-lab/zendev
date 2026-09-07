# zendev-commit

`zendev-commit` owns commit profiles, Conventional Commits and Gitmoji
validation, the interactive commit flow, and its vendored data. It can be
installed without the complete `zendev` toolkit.

```shell
uv add --dev zendev-commit
uvx zendev-commit --help
```

```python
from zendev.commit import CommitProfile, validate_commit_message

result = validate_commit_message(
    "feat(parser): accept empty input",
    profile=CommitProfile.CONVENTIONAL,
)
assert result.valid
```

Read the official [Commits guide](https://docs.zendev.zrr.dev/guides/commits/),
[Configuration reference](https://docs.zendev.zrr.dev/reference/configuration/),
and [hook integration](https://docs.zendev.zrr.dev/integrations/prek/)
for profiles, commands, and repository setup.

The vendored Gitmoji catalog and its retained license live under
`src/zendev/data/`. Maintainers should follow the repository contributor guide
when refreshing that data.
