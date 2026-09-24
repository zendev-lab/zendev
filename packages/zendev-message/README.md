# zendev-message

Commit and PR message parsing, policy, rendering, body and checklist validation.
Includes the `zendev-message` checker and `zendev-commit` interactive command.
Depends only on the same-version core plus its CLI/interactive dependencies.

```shell
uv add --dev zendev-message
uvx --from zendev-message zendev-message check --help
```

```python
from zendev.message import MessageDraft, check_message, render_message

text = render_message(MessageDraft("upgrade dependencies", "deps", "arrow-up"))
assert check_message(text).ok
```

See the [commit guide](https://docs.zendev.zrr.dev/guides/commits/) and
[migration guide](https://docs.zendev.zrr.dev/guides/migration/).
