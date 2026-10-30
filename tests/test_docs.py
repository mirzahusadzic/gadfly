"""The moved text keeps its license, and the docs site can render its math."""

from pathlib import Path

from hooks.github_math import on_page_markdown

ROOT = Path(__file__).parent.parent


def test_the_load_bearing_text_keeps_its_cc_by_license():
    assert (
        (ROOT / "LICENSES/CC-BY-4.0.txt")
        .read_text()
        .startswith("Creative Commons Attribution 4.0 International")
    )
    page = (ROOT / "docs/load-bearing.md").read_text()
    assert "Text © 2026 Mirza Husadzic, licensed under" in page
    assert "https://creativecommons.org/licenses/by/4.0/" in page
    assert "LICENSES/CC-BY-4.0.txt" in (ROOT / "README.md").read_text()


def test_github_math_becomes_arithmatex_math():
    source = (
        'Use $`X=\\{x\\}`$, then\n\n<div align="center">\n\n$`\\displaystyle L=(I,B),`$\n\n</div>\n'
    )
    rendered = on_page_markdown(source, None, None, None)
    assert "$X=\\{x\\}$" in rendered and "$$\n\\displaystyle L=(I,B),\n$$" in rendered
    assert "$`" not in rendered and "<div" not in rendered
