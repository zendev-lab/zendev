"""Steady-state parsing and normalization; input construction is outside timing."""

from pytest_benchmark.fixture import BenchmarkFixture

from zendev.message import normalize_message
from zendev.message.conventional import parse_conventional_commit


def test_parse_long_commit(benchmark: BenchmarkFixture) -> None:
    body = "\n\n".join(f"Paragraph {index}: retain the original description." for index in range(100))
    message = f"feat(api)!: add export\n\n{body}\n\nBREAKING CHANGE: use v2\nRefs: #42"
    parsed, issue = benchmark(parse_conventional_commit, message)
    assert issue is None
    assert parsed is not None
    assert parsed.body == body
    assert parsed.is_breaking
    assert [(footer.token, footer.value) for footer in parsed.footers] == [
        ("BREAKING CHANGE", "use v2"),
        ("Refs", "#42"),
    ]


def test_normalize_commit(benchmark: BenchmarkFixture) -> None:
    message = "# template\r\nfeat(api): add export\r\n\r\nRetain body bytes.  \r\n\r\nRefs: #42\r\n"
    result = benchmark(normalize_message, message, commit=True)
    assert result.ok
    assert result.changed
    assert result.text == message.replace("feat(api):", "✨ feat(api):", 1)
