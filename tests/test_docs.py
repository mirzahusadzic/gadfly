"""The moved text keeps its license, and the docs site can render its math."""

import importlib
import inspect
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


def test_every_public_name_in_the_reference_has_a_docstring():
    # mkdocstrings leaves out what has none, so the reference would not show it
    page = (ROOT / "docs/reference.md").read_text().splitlines()
    modules = [line.removeprefix("::: ").strip() for line in page if line.startswith("::: ")]
    missing = []
    for name in modules:
        module = importlib.import_module(name)
        for attr, obj in vars(module).items():
            if attr.startswith("_") or getattr(obj, "__module__", None) != name:
                continue
            if not (inspect.isfunction(obj) or inspect.isclass(obj)):
                continue
            doc = (obj.__doc__ or "").strip()
            if not doc or doc.startswith(f"{attr}("):  # a dataclass's generated signature
                missing.append(f"{name}.{attr}")
            if inspect.isclass(obj):
                missing += [
                    f"{name}.{attr}.{method}"
                    for method, function in vars(obj).items()
                    if not method.startswith("_")
                    and inspect.isfunction(function)
                    and not function.__doc__
                ]
    assert missing == []
