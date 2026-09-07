# Package reference

The repository publishes five distributions from one uv workspace and release
tag. They contribute independent portions of the PEP 420 `zendev` namespace.

| Distribution | Ownership | Primary interfaces |
| --- | --- | --- |
| `zendev` | Complete toolkit and unified CLI | `zendev`, `python -m zendev` |
| `zendev-commit` | Commit profiles, validation, interactive commits, vendored Gitmoji data | `zendev.commit`, `zendev.conventional`, `zendev.gitmoji`, `zendev-commit` |
| `zendev-review` | Title, body, checklist, and complete-message validation | `zendev.title`, `zendev.body`, `zendev.message`, `zendev-message` |
| `zendev-proposal` | Proposal configuration, validation, history, graph, and indexes | `zendev.proposal`, `zendev-proposal` |
| `zendev-log` | Idempotent Loguru setup | `zendev.log.setup_log` |

The root `zendev` distribution requires every component. There is no optional
import path or degraded unified command. Component distributions remain
independently installable when a consumer deliberately wants a narrower surface.

`zendev-log` is imported directly:

```python
from zendev.log import setup_log

setup_log(verbose=True)
```

The former `from zendev import setup_log` re-export is not supported.
