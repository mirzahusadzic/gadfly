"""The moved text keeps its license, the pages read on GitHub, and what they
quote, copy and document is what the code prints, copies and declares."""

import importlib
import inspect
import json
import re
from collections import Counter
from pathlib import Path

import pytest

from tools import watch_data

ROOT = Path(__file__).parent.parent
PAGES = ["README.md", *(str(p.relative_to(ROOT)) for p in sorted(ROOT.glob("docs/**/*.md")))]


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


def test_every_public_name_in_the_reference_has_a_docstring():
    # the reference is written from docstrings, so a name without one shows nothing
    page = (ROOT / "docs/reference.md").read_text()
    modules = re.findall(r"^<!-- api (\S+) -->$", page, re.M)
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


def test_the_site_publishes_the_frame_schema_where_its_id_says():
    # the site's public files are served at its root, /gadfly/
    published = ROOT / "docs/public/frame.schema.json"
    assert published.resolve() == (ROOT / "gadfly/frame.schema.json").resolve()
    assert "base: '/gadfly/'" in (ROOT / "docs/.vitepress/config.mjs").read_text()
    schema = json.loads(published.read_text())
    assert schema["$id"] == "https://mirzahusadzic.github.io/gadfly/frame.schema.json"


def _transcripts():
    from tools.doc_outputs import PAGES, transcripts

    return [t for page in PAGES for t in transcripts(page)]


@pytest.mark.parametrize("transcript", _transcripts(), ids=lambda t: t.where())
def test_every_quoted_output_is_what_the_code_prints(transcript):
    # `uv run python tools/doc_outputs.py --write` brings a page back in line
    from tools.doc_outputs import printed

    assert printed(transcript) == transcript.quoted


# Syntax only a site generator reads, which GitHub would show as it is written.
SITE_ONLY = {
    "an admonition": re.compile(r"^(!!!|\?\?\?\+?) ", re.M),
    "a snippet include": re.compile(r"--8<--"),
    "an attribute list": re.compile(r"\{ ?[.#:][\w-]"),
    "a container line": re.compile(r"^::: ", re.M),
    "a markdown div": re.compile(r"<div[^>]*\bmarkdown\b"),
}


@pytest.mark.parametrize("page", PAGES)
def test_every_page_reads_on_github(page):
    # a callout is a GitHub alert, an included text is a copy, a module's
    # reference is written out from its docstrings
    text = (ROOT / page).read_text()
    text = re.sub(r"```.*?```", "", text, flags=re.S)  # code shows as written anyway
    found = [what for what, pattern in SITE_ONLY.items() if pattern.search(text)]
    assert found == []


LINK = re.compile(r"\]\(([^)\s]+)\)")
HEADING = re.compile(r"^#{1,6} (.+?)\s*$", re.M)


def _prose(path: Path) -> str:
    # a page without its code, where a bracket is not a link
    return re.sub(r"```.*?```|`[^`\n]*`", "", path.read_text(encoding="utf-8"), flags=re.S)


def _anchors(path: Path) -> set[str]:
    # GitHub's anchors, which the site makes too: a heading's words in lower
    # case, punctuation dropped, spaces as hyphens, a repeat numbered
    seen, anchors = Counter(), set()
    for heading in HEADING.findall(_prose(path)):
        words = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)
        slug = re.sub(r"[^\w\- ]", "", words.lower()).replace(" ", "-")
        anchors.add(f"{slug}-{seen[slug]}" if seen[slug] else slug)
        seen[slug] += 1
    return anchors


def _a_line_of(path: Path, anchor: str) -> bool:
    # a file's line, as GitHub numbers it: #L12
    number = re.fullmatch(r"L(\d+)", anchor)
    return bool(number) and 1 <= int(number[1]) <= len(path.read_text().splitlines())


@pytest.mark.parametrize("page", PAGES)
def test_every_link_lands(page):
    # a moved section or a renamed heading leaves no link behind: a relative
    # link names a file the repository holds, its anchor a heading there
    path = ROOT / page
    broken = []
    for target in LINK.findall(_prose(path)):
        if re.match(r"[a-z]+:", target):
            continue
        name, _, anchor = target.partition("#")
        landed = (path.parent / name).resolve() if name else path
        if not landed.exists():
            broken.append(target)
        elif landed.suffix == ".md" and anchor and anchor not in _anchors(landed):
            broken.append(target)
        elif landed.suffix != ".md" and anchor and not _a_line_of(landed, anchor):
            broken.append(target)
    assert broken == []


CONFIG = (ROOT / "docs/.vitepress/config.mjs").read_text(encoding="utf-8")


def test_every_page_is_in_the_sidebar_or_kept_off_the_site():
    # an unlisted page is still built and searchable, so a draft is excluded
    listed = set(re.findall(r"link: '/([^']*)'", CONFIG))
    excluded = set(
        re.findall(r"'([^']+\.md)'", "".join(re.findall(r"srcExclude: \[(.*?)\]", CONFIG)))
    )
    unreachable = []
    for path in sorted((ROOT / "docs").glob("**/*.md")):
        if "[" in path.name:
            continue  # a route's template: its pages are linked from the pages they serve
        page = str(path.relative_to(ROOT / "docs"))
        route = re.sub(r"(^|/)index\.md$", r"\1", page).removesuffix(".md")
        if route not in listed and page not in excluded:
            unreachable.append(page)
    assert unreachable == []


def test_each_top_bar_link_opens_its_sidebar_group():
    # the top bar's "Start here" lands on the first page under "Start here"
    first = dict(
        re.findall(r"text: '([^']+)',\s*items: \[\s*\{ text: '[^']+', link: '([^']+)'", CONFIG)
    )
    nav = re.findall(r"\{ text: '([^']+)', link: '([^']+)', activeMatch", CONFIG)
    assert nav and all(name in first for name, _ in nav)
    assert [(name, link) for name, link in nav if first[name] != link] == []


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


def _references():
    from tools.doc_outputs import PAGES, apis

    return [a for page in PAGES for a in apis(page)]


@pytest.mark.parametrize("block", _references(), ids=lambda a: a.where())
def test_every_reference_is_its_docstrings(block):
    # `uv run python tools/doc_outputs.py --write` brings a page back in line
    from tools.doc_outputs import documented

    assert documented(block.source) == block.quoted


def _frames():
    from tools.doc_outputs import PAGES, frames

    return [f for page in PAGES for f in frames(page)]


@pytest.mark.parametrize("block", _frames(), ids=lambda f: f.where())
def test_every_frame_shown_in_words_is_its_frame(block):
    # `uv run python tools/doc_outputs.py --write` brings a page back in line
    from tools.doc_outputs import readable

    assert readable(block.source, block.page) == block.quoted


def test_the_site_publishes_each_frame_with_the_hash_its_records_name():
    from tools.doc_outputs import INDEX, frame_index

    assert INDEX.read_text(encoding="utf-8") == frame_index()


@pytest.mark.parametrize("page", PAGES)
def test_no_page_shows_a_whole_frame_as_json(page):
    # a reader meets a frame in words; its JSON is the source, one link away
    text = (ROOT / page).read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)```", text, flags=re.S)
    assert [b for b in blocks if '"relation"' in b and '"body"' in b] == []


def test_the_notices_name_what_the_site_ships():
    # the site ships others' work, and ELK's licence asks that its source be named
    notices = (ROOT / "docs/notices.md").read_text(encoding="utf-8")
    built_with = json.loads((ROOT / "package.json").read_text())["devDependencies"]
    named = {"vitepress": "VitePress", "mermaid": "Mermaid", "@mermaid-js/layout-elk": "ELK",
             "markdown-it-mathjax3": "markdown-it-mathjax3"}  # fmt: skip
    assert sorted(built_with) == sorted(named)
    assert [name for name in named.values() if name not in notices] == []
    assert "github.com/kieler/elkjs" in notices and "Eclipse Public License 2.0" in notices
    fonts = sorted(p.name for p in (ROOT / "docs/.vitepress/theme/fonts").glob("*-OFL.txt"))
    assert fonts == ["albert-sans-OFL.txt", "fraunces-OFL.txt"]
    assert "Albert Sans" in notices and "Fraunces" in notices
