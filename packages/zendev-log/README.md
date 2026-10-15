# zendev-log

`zendev-log` provides a small, idempotent Loguru setup helper for command-line
applications.

```shell
uv add zendev-log
```

```python
from zendev.log import setup_log

setup_log(verbose=True, json=False)
```

Set `ZENDEV_LOG_LEVEL` to override the configured log level (`INFO` by default,
or `DEBUG` when `verbose=True`).

See the official [package reference](https://docs.zendev.zrr.dev/reference/packages/)
for the distribution boundary.
