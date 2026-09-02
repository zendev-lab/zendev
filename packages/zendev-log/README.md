# zendev-log

`zendev-log` provides a small, idempotent Loguru setup helper for command-line
applications.

```shell
uv add zendev-log
```

```python
from zendev.log import setup_log

setup_log(verbose=True)
```

Version 0.2.0 removes the former `from zendev import setup_log` re-export.
