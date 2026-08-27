# zendev-review

`zendev-review` validates pull-request titles against the configured commit
profile and pull-request bodies against repository templates.

```console
$ uvx --from zendev-review zendev-validate-title --help
$ uvx --from zendev-review zendev-validate-body --help
```

The package depends on `zendev-commit` for the shared title convention. The
complete `zendev` distribution exposes both checks under its unified command.
