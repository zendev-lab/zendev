"""Public homepage contract from ZFP-0008."""

from pathlib import Path

ROOT = Path(__file__).parents[1]
HOME = ROOT / "homepage"

COMMANDS = (
    "uvx zendev --help",
    "zendev commit",
    "zendev message check",
    "zendev proposal check",
    "zendev evolution check",
)
GUIDES = (
    "https://docs.zendev.zrr.dev/getting-started/",
    "https://docs.zendev.zrr.dev/guides/commits/",
    "https://docs.zendev.zrr.dev/guides/message-checks/",
    "https://docs.zendev.zrr.dev/guides/proposals/",
    "https://docs.zendev.zrr.dev/guides/evolution/",
    "https://docs.zendev.zrr.dev/concepts/repository-native/",
)
PACKAGES = (
    "zendev-core",
    "zendev-message",
    "zendev-proposal",
    "zendev-evolution",
    "zendev-log",
)


def test_homepage_keeps_positioning_and_exits() -> None:
    page = (HOME / "index.html").read_text(encoding="utf-8")
    assert 'lang="en"' in page
    assert "<h1>Repository-native development workflows</h1>" in page
    assert "Git and committed repository files stay the source of truth." in page
    assert "project evolution" in page
    for command in COMMANDS:
        assert f"<code>{command}</code>" in page
    assert 'data-copy="uvx zendev --help"' in page
    for guide in GUIDES:
        assert f'href="{guide}"' in page
    assert 'href="https://docs.zendev.zrr.dev/"' in page
    assert 'href="https://github.com/zendev-lab/zendev"' in page
    assert 'href="https://pypi.org/project/zendev/"' in page
    assert 'href="https://github.com/zendev-lab/zendev/tree/main/zfps"' in page
    for package in PACKAGES:
        assert package not in page
    assert "fonts.googleapis" not in page
    assert "cdn." not in page


def test_homepage_styles_are_local() -> None:
    css = (HOME / "site.css").read_text(encoding="utf-8")
    assert "ui-monospace" in css
    assert "url(" not in css
    assert "@media (prefers-color-scheme: dark)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "fonts.googleapis" not in css


def test_unknown_paths_have_a_homepage_404() -> None:
    missing = (HOME / "404.html").read_text(encoding="utf-8")
    assert 'href="/"' in missing
    assert 'href="/site.css"' in missing
    worker = (HOME / "wrangler.toml").read_text(encoding="utf-8")
    assert 'pattern = "zendev.zrr.dev"' in worker
    assert "docs.zendev.zrr.dev" not in worker
    assert 'not_found_handling = "404-page"' in worker


def test_docs_site_and_wheels_do_not_own_the_homepage() -> None:
    assert "homepage/" not in (ROOT / "zensical.toml").read_text(encoding="utf-8")
    root_worker = (ROOT / "wrangler.toml").read_text(encoding="utf-8")
    assert 'pattern = "docs.zendev.zrr.dev"' in root_worker
    assert 'pattern = "zendev.zrr.dev"' not in root_worker
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'packages = ["src/zendev"]' in project
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "homepage/" in contributing
    assert "ZFP-0008" in contributing
