"""The moved text keeps its license, the pages read on GitHub, and what they
quote, copy and document is what the code prints, copies and declares."""

import ast
import importlib
import inspect
import itertools
import json
import math
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
    assert published.resolve() == (ROOT / "midwife/frame.schema.json").resolve()
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
    named = {"vitepress": "VitePress", "vue": "Vue", "mermaid": "Mermaid",
             "@mermaid-js/layout-elk": "ELK", "markdown-it-mathjax3": "markdown-it-mathjax3",
             "shiki": "Shiki"}  # fmt: skip
    assert sorted(built_with) == sorted(named)
    assert [name for name in named.values() if name not in notices] == []
    assert "github.com/kieler/elkjs" in notices and "Eclipse Public License 2.0" in notices
    assert "gadfly/notices/third-party.txt" in notices  # the texts the build writes
    fonts = sorted(p.name for p in (ROOT / "docs/.vitepress/theme/fonts").glob("*-OFL.txt"))
    assert fonts == ["albert-sans-OFL.txt", "fraunces-OFL.txt"]
    assert "Albert Sans" in notices and "Fraunces" in notices


def _printed():
    # every message the package can print, as a pattern: an f-string's fields match anything
    import ast

    def bare(text: str) -> str:  # without the prefix main adds
        return text.lstrip("\n").removeprefix("gadfly: ")

    patterns = []
    for path in (ROOT / "midwife").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.JoinedStr):
                values = node.values
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                values = [node]
            else:
                continue
            texts = [
                (bare(v.value) if i == 0 else v.value) if isinstance(v, ast.Constant) else None
                for i, v in enumerate(values)
            ]
            if sum(len(text) for text in texts if text) >= 8:  # f"gadfly: {error}" says nothing
                parts = ["(.+?)" if text is None else re.escape(text) for text in texts]
                patterns.append(re.compile("".join(parts), re.S))
    return patterns


def test_every_message_troubleshooting_quotes_is_one_gadfly_prints():
    # the page quotes messages word for word, so a changed message must change it too
    printed = _printed()
    quoted = []
    for row in (ROOT / "docs/troubleshooting.md").read_text(encoding="utf-8").splitlines():
        if row.startswith("| `"):
            cell = row.split(" | ")[0][2:]
            quoted += [a or b for a, b in re.findall(r"``(.+?)``|`([^`]+)`", cell)]
    unknown = []
    for text in quoted:
        if text.startswith("gadfly: "):
            message = text.removeprefix("gadfly: ")
        elif text.startswith('"') and text.endswith('"'):
            message = text[1:-1]  # an opening, as run names it
        else:
            continue
        if message.startswith(("[Errno", "No module named")):
            continue  # Python's own words
        if not any(pattern.fullmatch(message) for pattern in printed):
            unknown.append(message)
    assert quoted and unknown == []


SITE = "https://mirzahusadzic.github.io/gadfly/"
BLOB = "https://github.com/mirzahusadzic/gadfly/blob/main/"


def test_the_readme_links_work_on_pypi():
    # PyPI shows the README without the repository, so a relative link breaks
    # there: each link is absolute, and lands on a page or file that exists
    broken = []
    for target in LINK.findall(_prose(ROOT / "README.md")):
        url, _, anchor = target.partition("#")
        if url.startswith(SITE):
            route = url.removeprefix(SITE)
            page = (
                ROOT
                / "docs"
                / (f"{route}index.md" if route.endswith("/") or not route else f"{route}.md")
            )
        elif url.startswith(BLOB):
            page = ROOT / url.removeprefix(BLOB)
        elif re.match(r"[a-z]+:", url):
            continue
        else:
            broken.append(target)  # relative: lost on PyPI
            continue
        if not page.exists() or (anchor and page.suffix == ".md" and anchor not in _anchors(page)):
            broken.append(target)
    assert broken == []


THEMES = ROOT / "docs/.vitepress/theme/custom.css"
# Machado, Oliveira and Fernandes (2009) at full severity, on linear RGB
CVD = {
    "deutan": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413],
               [-0.011820, 0.042940, 0.968881]],
    "protan": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216],
               [-0.003882, -0.048116, 1.051998]],
}  # fmt: skip


def _linear(colour: str) -> list[float]:
    channels = (int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]


def _oklab(rgb: list[float]) -> tuple[float, float, float]:
    r, g, b = rgb
    lms = [
        (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3),
        (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3),
        (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3),
    ]
    rows = [
        (0.2104542553, 0.7936177850, -0.0040720468),
        (1.9779984951, -2.4285922050, 0.4505937099),
        (0.0259040371, 0.7827717662, -0.8086757660),
    ]
    return tuple(100 * sum(w * x for w, x in zip(row, lms, strict=True)) for row in rows)


def _lightness(colour: str) -> float:
    return _oklab(_linear(colour))[0]


def _saturation(colour: str) -> float:
    lightness, a, b = _oklab(_linear(colour))
    return math.hypot(a, b) / lightness


def _seen(colour: str, cvd: str) -> tuple[float, float, float]:
    rgb = _linear(colour)
    return _oklab([max(0.0, sum(m * c for m, c in zip(row, rgb, strict=True))) for row in CVD[cvd]])


def _contrast(ink: str, ground: str) -> float:
    def luminance(colour):
        r, g, b = _linear(colour)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    high, low = sorted((luminance(ink), luminance(ground)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _themes() -> dict[str, dict[str, str]]:
    css = THEMES.read_text(encoding="utf-8")
    return {
        name: dict(re.findall(r"--gf-([a-z0-9-]+): (#[0-9a-f]{6});", body))
        for name, body in re.findall(r"\[data-theme='([a-z]+)'\] \{(.*?)\n\}", css, re.S)
    }


def test_every_theme_sets_its_surfaces_apart_as_paper_and_iris_does():
    # each surface at the same lightness offset from the page, the sidebar
    # darker and the rest away from the page, so a theme reads by lightness
    themes = _themes()
    assert set(themes) == {"dusk", "light", "daylight", "play"}
    paper = themes["daylight"]
    offsets = {
        key: abs(_lightness(paper[key]) - _lightness(paper["panel"]))
        for key in ("bg", "panel2", "line", "source-code")
    }
    drift = []
    for name, theme in themes.items():
        page = _lightness(theme["panel"])
        away = 1 if page < 50 else -1
        for key, offset in offsets.items():
            expected = page + (-offset if key == "bg" else away * offset)
            if abs(_lightness(theme[key]) - expected) > 0.6:
                drift.append(f"{name} {key}: L {_lightness(theme[key]):.1f}, not {expected:.1f}")
        if page < 50 and abs(_saturation(theme["bg"]) - _saturation(theme["panel"])) > 0.02:
            drift.append(f"{name} bg: more saturated than its page")
    assert drift == []


def test_code_sits_in_the_sidebars_colour_and_reads_at_5_to_1():
    # a well the colour of the sidebar, unless a study keeps a dark terminal
    # on its light page; every colour of the code at 5:1 on it
    css = THEMES.read_text(encoding="utf-8")
    off = []
    for name, body in re.findall(r"\[data-theme='([a-z]+)'\] \{(.*?)\n\}", css, re.S):
        theme = dict(re.findall(r"--gf-([a-z0-9-]+): (#[0-9a-f]{6});", body))
        console = theme["console-bg"]
        terminal = _lightness(console) < 50 < _lightness(theme["panel"])
        if console != theme["bg"] and not terminal:
            off.append(f"{name}: code on {console}, its sidebar {theme['bg']}")
        inks = re.findall(
            r"--(shiki-token-[a-z-]+|shiki-foreground|gf-console-text): (#[0-9a-f]{6});", body
        )
        assert inks
        off += [
            f"{name}: {token} at {_contrast(ink, console):.2f}"
            for token, ink in inks
            if _contrast(ink, console) < 5
        ]
    assert off == []


def test_the_line_under_test_stands_off_its_panel_for_every_eye():
    # the wash marks the line under test on a panel: lighter or darker than
    # it, never only another hue, and apart under red-green colour blindness
    # (6 is the floor beside the line's rule and tag, which say it in shape);
    # the line is set in the inks its theme gives the wash, read below
    faint = []
    for name, theme in _themes().items():
        panel, wash = theme["panel2"], theme["action-wash"]
        step = _lightness(wash) - _lightness(panel)
        if abs(step) < 5.5:
            faint.append(f"{name}: the wash is {step:+.1f} from its panel")
        for cvd in CVD:
            if math.dist(_seen(panel, cvd), _seen(wash, cvd)) < 6:
                faint.append(f"{name}: wash and panel alike under {cvd}")
    assert faint == []
    watch = (ROOT / "docs/.vitepress/theme/watch.css").read_text(encoding="utf-8")
    line = re.search(r"\n\.w-line\.is-anchor \{(.*?)\}", watch, re.S).group(1)
    assert "--w-ink: var(--gf-action-wash-ink" in line
    assert "--w-muted: var(--gf-action-wash-muted" in line


def test_every_theme_keeps_its_text_readable_on_every_surface():
    # body ink at 7:1 on the page; every ink at 4.5:1 wherever it is set; on
    # the wash, the line under test's own inks, its text and its muted words
    low = []
    for name, theme in _themes().items():
        grounds = ("panel", "bg", "panel2", "source-code")
        for ink in ("text", "muted", "action", "title"):
            for ground in grounds[:3] if ink == "title" else grounds:
                need = 7 if (ink, ground) == ("text", "panel") else 4.5
                ratio = _contrast(theme[ink], theme[ground])
                if ratio < need:
                    low.append(f"{name}: {ink} on {ground} at {ratio:.2f}")
        for ink, own in (("text", "action-wash-ink"), ("muted", "action-wash-muted")):
            ratio = _contrast(theme.get(own, theme[ink]), theme["action-wash"])
            if ratio < 4.5:
                low.append(f"{name}: the line's {ink} on the wash at {ratio:.2f}")
    assert low == []


def test_the_watch_view_tells_every_answer_apart_for_every_eye():
    # the answers' dots, in the light and the dark themes, apart under
    # red-green colour blindness: the validator's target, every pair
    css = (ROOT / "docs/.vitepress/theme/watch.css").read_text(encoding="utf-8")
    alike = []
    for scheme, rule in (
        ("light", r"\n\.gadfly-watch \{"),
        ("dark", r"\n\.dark \.gadfly-watch \{"),
    ):
        block = re.search(rule + r"(.*?)\n\}", css, re.S).group(1)
        dots = dict(re.findall(r"--w-([abcu]): (#[0-9a-f]{6});", block))
        assert set(dots) == set("abcu")
        for one, other in itertools.combinations(sorted(dots), 2):
            for cvd in CVD:
                if math.dist(_seen(dots[one], cvd), _seen(dots[other], cvd)) < 8:
                    alike.append(f"{scheme}: {one} and {other} under {cvd}")
    assert alike == []


def test_every_name_a_module_defines_has_its_entry_in_the_reference():
    # a function, a class, or a name given to a function it imports (the
    # pipeline's situate, plan and overall): each has its own entry
    page = (ROOT / "docs/reference.md").read_text(encoding="utf-8")
    missing = []
    for module in re.findall(r"^<!-- api (\S+) -->$", page, re.M):
        section = page.split(f"### {module}\n", 1)[1].split("\n### ", 1)[0]
        tree = ast.parse((ROOT / (module.replace(".", "/") + ".py")).read_text())
        names = [
            getattr(node, "name", None) or node.targets[0].id
            for node in tree.body
            if isinstance(node, ast.FunctionDef | ast.ClassDef)
            or (
                isinstance(node, ast.Assign)
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Name)
                and callable(getattr(importlib.import_module(module), node.targets[0].id))
            )
        ]
        missing += [
            f"{module}.{name}"
            for name in names
            if not name.startswith("_") and f"#### {name}\n" not in section
        ]
    assert missing == []
