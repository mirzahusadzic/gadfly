"""The moved text keeps its license, the pages read on GitHub, and the docs
site renders what GitHub shows: its math, its alerts and the reference."""

import importlib
import inspect
import json
import re
from pathlib import Path

import pytest

from hooks import github_alerts, reference
from hooks.github_math import on_page_markdown
from tools import watch_data

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
    page = (ROOT / "docs/reference.md").read_text()
    modules = re.findall(r"^<!-- ::: (\S+) -->$", page, re.M)
    assert modules
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


def test_the_site_publishes_the_frame_schema_where_its_id_says(tmp_path):
    from hooks.schema import on_post_build

    on_post_build({"site_dir": str(tmp_path)})
    published = json.loads((tmp_path / "frame.schema.json").read_text())
    assert published["$id"] == "https://mirzahusadzic.github.io/gadfly/frame.schema.json"


def _transcripts():
    from tools.doc_outputs import PAGES, transcripts

    return [t for page in PAGES for t in transcripts(page)]


@pytest.mark.parametrize("transcript", _transcripts(), ids=lambda t: t.where())
def test_every_quoted_output_is_what_the_code_prints(transcript):
    # `uv run python tools/doc_outputs.py --write` brings a page back in line
    from tools.doc_outputs import printed

    assert printed(transcript) == transcript.quoted


def test_a_github_alert_becomes_an_admonition_with_its_title():
    source = (
        "Before.\n\n> [!NOTE]\n> **Predicted first**\n>\n> Block, at about 55%.\n"
        "> - a list item\n>   that wraps\n\nAfter.\n"
    )
    rendered = github_alerts.on_page_markdown(source, None, None, None)
    assert rendered == (
        'Before.\n\n!!! note "Predicted first"\n\n    Block, at about 55%.\n'
        "    - a list item\n      that wraps\n\nAfter.\n"
    )
    untitled = github_alerts.on_page_markdown("> [!IMPORTANT]\n> Read this.\n", None, None, None)
    assert untitled == "!!! abstract\n\n    Read this.\n"
    quote = "> A plain quotation stays a quotation.\n"
    assert github_alerts.on_page_markdown(quote, None, None, None) == quote


def test_the_reference_unwraps_each_module_for_mkdocstrings():
    rendered = reference.on_page_markdown("<!-- ::: gadfly.pipeline -->\n", None, None, None)
    assert rendered == "::: gadfly.pipeline\n"


# Syntax only MkDocs reads, which GitHub would show as it is written.
SITE_ONLY = {
    "an admonition": re.compile(r"^(!!!|\?\?\?\+?) ", re.M),
    "a snippet include": re.compile(r"--8<--"),
    "an attribute list": re.compile(r"\{ ?[.#:][\w-]"),
    "a mkdocstrings line": re.compile(r"^::: ", re.M),
    "a markdown div": re.compile(r"<div[^>]*\bmarkdown\b"),
}


@pytest.mark.parametrize(
    "page", ["README.md", *(str(p.relative_to(ROOT)) for p in sorted(ROOT.glob("docs/**/*.md")))]
)
def test_every_page_reads_on_github(page):
    # a callout is a GitHub alert, an included text is a copy, a module is named
    # in a comment: the hooks turn them into what the site needs
    text = (ROOT / page).read_text()
    text = re.sub(r"```.*?```", "", text, flags=re.S)  # code shows as written anyway
    found = [what for what, pattern in SITE_ONLY.items() if pattern.search(text)]
    assert found == []


def _copies():
    from tools.doc_outputs import PAGES, copies

    return [c for page in PAGES for c in copies(page)]


@pytest.mark.parametrize("copy", _copies(), ids=lambda c: c.where())
def test_every_copy_is_its_source(copy):
    # `uv run python tools/doc_outputs.py --write` brings a page back in line
    from tools.doc_outputs import copied

    assert copied(copy.source) == copy.quoted


@pytest.mark.parametrize("stem", watch_data.FRAMES)
def test_the_watch_view_plays_the_kept_runs(stem):
    # `uv run python -m tools.watch_data --write` brings a file back in line; it
    # refuses a prompt its records' digest does not name
    kept = (watch_data.OUT / f"{stem}.json").read_text(encoding="utf-8")
    assert kept == watch_data.encoded(stem)
