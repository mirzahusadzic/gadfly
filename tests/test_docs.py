"""The moved text keeps its license, the pages read on GitHub, and what they
quote, copy and document is what the code prints, copies and declares."""

import ast
import functools
import importlib
import inspect
import itertools
import json
import math
import re
import subprocess
from collections import Counter
from pathlib import Path

import pytest

from midwife.cli import load_records
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


@pytest.mark.parametrize("stem", watch_data.FILES)
def test_the_watch_view_plays_the_kept_runs(stem):
    # `uv run python -m tools.watch_data --write` brings a file back in line; it
    # refuses a prompt its records' digest does not name
    kept = (watch_data.OUT / f"{stem}.json").read_text(encoding="utf-8")
    assert kept == watch_data.encoded(stem)


@pytest.mark.parametrize(
    "served, model",
    [
        (
            "google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be",
            "google/gemma-4-26B-A4B-it-qat-q4_0-gguf",
        ),
        ("meta/muse-spark-1.3-contributor via DeepInfra", "meta/muse-spark-1.3-contributor"),
        ("meta/muse-spark-1.3-contributor", "meta/muse-spark-1.3-contributor"),
    ],
)
def test_the_watch_view_names_the_model_whatever_form_served_takes(monkeypatch, served, model):
    # served is "model", "model@revision", or the unified battery's "model via endpoint"
    stem = "19-router-waist"
    runs = watch_data.runs_of(watch_data.ROOT / "examples" / f"{stem}.json")
    records = [{**r, "served": served} for r in load_records(str(runs[0]))]
    monkeypatch.setattr(watch_data, "runs_of", lambda path: [runs[0]])
    monkeypatch.setattr(watch_data, "load_records", lambda path: records)
    assert watch_data.watched(stem)["model"] == model


def test_the_watch_view_refuses_what_it_cannot_play(monkeypatch):
    # a record that does not say what served it, and an example with no run
    stem = "19-router-waist"
    runs = watch_data.runs_of(watch_data.ROOT / "examples" / f"{stem}.json")
    records = [{k: v for k, v in r.items() if k != "served"} for r in load_records(str(runs[0]))]
    monkeypatch.setattr(watch_data, "load_records", lambda path: records)
    with pytest.raises(SystemExit, match="does not say what served it"):
        watch_data.watched(stem)
    monkeypatch.setattr(watch_data, "runs_of", lambda path: [])
    with pytest.raises(SystemExit, match="no kept run to play"):
        watch_data.encoded(stem)


TEACHING = sorted(
    p for p in (ROOT / "docs/examples").glob("*.md") if "### What to take from it" in p.read_text()
)
WATCH = re.compile(r"^<!-- watch (?:dolls )?([\w -]+) -->$", re.M)


@pytest.mark.parametrize("page", TEACHING, ids=lambda p: p.stem)
def test_each_step_plays_its_own_runs_before_what_to_take_from_it(page):
    # the view plays every frame a transcript on the page reads back, and only
    # frames the page names, so no step shows another step's examples
    text = page.read_text(encoding="utf-8")
    sections = [s.split("\n", 1)[0] for s in re.split(r"^### ", text, flags=re.M)[1:]]
    assert sections[sections.index("What to take from it") - 1] == "Watch a run"
    [played] = [m.split() for m in WATCH.findall(text)]
    read = re.findall(r"examples/read\.py(?: \\\n)?\s+examples/([\w-]+)\.json", text)
    assert set(read) <= set(played)
    assert all(f"{stem}.json" in text for stem in played)


def test_the_watch_data_is_what_the_pages_play():
    pages = [*TEACHING, ROOT / "docs/first-frame.md"]
    # a frame two steps read (10c2) is played on both, from one file
    played = {s for p in pages for m in WATCH.findall(p.read_text()) for s in m.split()}
    assert played == set(watch_data.FRAMES)
    assert len(watch_data.FRAMES) == len(played)
    kept = {p.stem for p in watch_data.OUT.glob("*.json")}
    assert kept == set(watch_data.FILES)


def test_every_brushstroke_on_a_doll_is_a_line_it_says():
    # the doll stage paints a region for each line a doll says, and nothing
    # else: a line with no paint, or paint with no line, would show what the
    # reader never read
    dolls = json.loads((watch_data.OUT / "dolls.json").read_text(encoding="utf-8"))
    script = (ROOT / "docs/public/javascripts/dolls.js").read_text(encoding="utf-8")
    # the stage's own add(part, ...), not classList's
    painted = set(re.findall(r'(?<![.\w])add\("([\w-]+)"', script))
    said = {line["id"] for d in dolls["dolls"] for line in d["lines"] + d["extra"]}
    unpainted = {"inside", "holds-next", "name"}  # the links between dolls, and the label
    assert said - unpainted <= painted
    assert painted <= said
    # all five stand on the stage, each a frame of examples/dolls/, and the
    # paper's words climb and fit as midwife.recoil walks them
    assert [d["name"] for d in dolls["dolls"]] == ["Amani", "Kiran", "Sasha", "Robin", "Mirza"]
    assert dolls["piece"]["passes"] == ["Robin", "Sasha"] and dolls["piece"]["fits"] == "Kiran"
    assert dolls["gate"]["climbs"] == "Kiran reads boy" and dolls["gate"]["changed"] == ["observe"]
    page = (ROOT / "docs/examples/dolls.md").read_text(encoding="utf-8")
    [marker] = re.findall(r"^<!-- watch dolls ([\w -]+) -->$", page, re.M)
    assert [s for s in dolls["order"] if s not in ("climb", "gate")] == marker.split()


@functools.cache
def _harness(name):
    """What a Node harness in tests/ printed, read once a run."""
    done = subprocess.run(
        ["node", str(ROOT / f"tests/{name}.mjs")], capture_output=True, text=True, check=True
    )
    return json.loads(done.stdout)


def test_the_doll_stage_keeps_to_what_the_reader_picked():
    # the stage driven in Node (tests/stage_harness.mjs): a walked doll
    # picked holds the view, and later trials paint nothing on it; a climb
    # under way stops when a reader takes over; the gate's mark stays through
    # Back and Next until a doll is picked (pass 11, F7, F9, F10)
    seen = _harness("stage_harness")
    assert seen["walked"]["asked"] == [["hold"]] and seen["walked"]["amaniTrimCut"] is False
    assert seen["walked"]["caption"].startswith("Amani is walked, never asked")
    assert seen["takeover"] == {"asked": [["select", "22-kiran-paper"]], "captionKept": True}
    assert seen["gate"] == {
        "afterGate": 1,
        "afterTrial": 1,
        "note": "reframed",  # in words, beside the ring
        "afterPick": 0,
        "noteAfterPick": True,
        "selectionBack": True,
    }
    assert seen["decoyOnTop"]  # the decoy's bubble over the outline, never under it


def test_the_selection_climbs_with_the_papers_words_doll_by_doll():
    # from Mirza, the selection passes Robin and Sasha on its way to Kiran,
    # never jumping, and rests on Kiran until Kiran's frame is shown
    climb = _harness("stage_harness")["climb"]
    assert climb["steps"] == [["Robin"], ["Sasha"], ["Kiran"], []]
    assert climb["resting"] == {"passing": ["Kiran"], "travelling": True}
    assert climb["shown"] == {"pressed": ["Kiran"], "travelling": False}


def test_kirans_two_frames_stay_on_the_stage_whichever_doll_plays():
    # nothing comes and goes as the sequence moves on: the one played is pressed
    variants = _harness("stage_harness")["variants"]
    unpressed = [["With the paper", "false"], ["With a decoy too", "false"]]
    assert variants["mirza"] == variants["amani"] == unpressed
    assert variants["kiran"] == [["With the paper", "true"], ["With a decoy too", "false"]]


def test_each_visit_draws_the_dolls_names_and_colours_and_shows_them_as_read():
    # for the picture, each visit names every doll from another region of
    # the pool and paints it in another's colours, and every line that names
    # a doll or a colour says so; the box under the caption gives back the
    # set as it was read, every line word for word
    visit = _harness("stage_harness")["visit"]
    assert visit == {
        "regions": 5,
        "pooled": True,
        "named": True,
        "paper": True,
        "scarf": True,
        "renamedFrom": True,
        "asRead": {
            "names": ["Amani", "Kiran", "Sasha", "Robin", "Mirza"],
            "lines": True,
            "redrawn": [["redraw"]],
        },
    }


def test_a_dolls_own_design_fills_its_colour_lines_word_for_word():
    # the templates a visit refills give back the sentences Muse read when
    # filled with the doll's own design, so the set shown as read is exact
    dolls = watch_data.dolls()
    templates = dolls["variation"]["templates"]
    filled = 0
    for doll in dolls["dolls"]:
        for line in doll["lines"]:
            if line["id"] in templates:
                assert templates[line["id"]].format(**doll["design"]) == line["text"]
                filled += 1
    assert filled >= 25 and set(templates) == set(watch_data.COLOURS)


def test_a_readers_step_stops_a_climb_or_gate_under_way():
    # Back, Next or a chip during the climb or the gate: it stops at its next
    # step and the stage shows the frame the view plays; a gate's mark
    # already made stays (pass 12, W2)
    cancel = _harness("stage_harness")["cancel"]
    assert cancel == {
        "caption": True,
        "passing": 0,
        "travelling": False,
        "gateMarked": 0,
        "markKept": 1,
    }


def test_a_hovered_line_shows_only_while_the_pointer_is_on_it():
    # the stage's caption goes back to its narration (pass 12, W5)
    assert _harness("stage_harness")["hover"] == {"hovered": True, "restored": True}


def test_a_readers_own_step_ends_the_doll_sequence():
    # the verdict chip, as every reader's step, ends the sequence and tells
    # the stage to stop; Play stops a climb under way and plays the frame
    # again; a frame played to its end after the reader's step goes no
    # further (pass 12, W2, W3)
    assert _harness("watch_harness")["story"] == {
        "verdict": ["cancel"],
        "replay": ["cancel"],
        "afterVerdictPlayed": [],
        "back": ["cancel"],
    }


def test_the_later_of_two_quick_picks_is_the_one_shown():
    # a frame that arrives after a later pick's shows nothing (pass 12, W1)
    race = _harness("watch_harness")["race"]
    assert race == {"pressed": ["false", "true"], "shows": ["20b-incident-status"]}


def test_a_stage_that_cannot_stand_gives_the_picker_back():
    # the frames play on without the dolls, and can be picked (pass 12, W4)
    assert _harness("watch_harness")["unstaged"] == {"picker": True, "card": ["w-ask-text"]}


def test_an_address_naming_no_run_opens_the_first():
    # ?run=abc names no run: the view opens on run 1, and throws nothing
    # (pass 12, W6)
    seen = _harness("watch_harness")
    assert seen["badRun"] == ["true"] and seen["thrown"] == []


def test_the_watch_views_controls_wait_for_its_first_frame():
    # Play, Back and Next pressed while the first frame still loads do
    # nothing, rather than throw (tests/watch_harness.mjs; pass 11, F8)
    waiting = _harness("watch_harness")["waiting"]
    assert waiting == {"Back": "nothing", "Play": "nothing", "Next": "nothing"}


def test_only_play_starts_the_watch_view():
    # it plays once on first sight; after that a pick never starts it: what
    # was paused stays paused, and what was playing plays on
    assert _harness("watch_harness")["dolls"] == {
        "beforeSight": False,
        "inSight": True,
        "paused": False,
        "pickedWhilePaused": False,
        "pickedWhilePlaying": True,
    }


def test_the_dolls_stand_beside_the_question_who_read_it_under_it():
    # the question's card holds the question and the dolls; who read it, and
    # through what, are two lines
    seen = _harness("watch_harness")
    assert seen["card"] == ["w-ask-text", "w-dolls"]
    assert seen["by"] == (
        "Read by Muse Spark 1.3 Contributor, Meta's model,\n"
        "through unified-model-router (meta/muse-spark-1.3-contributor)"
    )


def test_the_pages_say_what_the_recoil_commands_and_examples_do():
    # where successor says whether its draft reframes, in each of its modes,
    # and that the guide's Python asks live while examples/dolls.py reads
    # kept runs (pass 12, D1, D2)
    line = " ".join((ROOT / "docs/command-line.md").read_text(encoding="utf-8").split())
    assert (
        "on standard error while the frame has standard output, on standard output "
        "with `--out`, and as `reframes` in the one document `--json` prints" in line
    )
    guide = " ".join((ROOT / "docs/recoil.md").read_text(encoding="utf-8").split())
    assert "asking each fit's successor live" in guide
    assert "`examples/dolls.py --gate` reads the dolls' gate from their kept runs" in guide
    source = (ROOT / "examples/dolls.py").read_text(encoding="utf-8")
    assert "until_firm(rung_frame, None, Budget(calls=1), kept=runs)" in source


def test_a_long_code_block_shows_its_first_twelve_lines():
    # the site's renderer (tests/fold_harness.mjs): with four lines or more
    # past the first twelve, the rest folds under a button that names the
    # count; the copy keeps every line. A block with fewer, whose button would
    # take the height the fold saves, and a chart, are left whole
    seen = _harness("fold_harness")
    for n in (12, 13, 15):
        assert seen[str(n)] == {
            "shown": n,
            "hidden": 0,
            "restOpensOnBreak": None,
            "button": None,
            "whole": True,
        }
    for n in (16, 45):
        block = seen[str(n)]
        assert block == {
            "shown": 12,
            "hidden": n - 12,
            "restOpensOnBreak": True,
            "button": {"label": f"Show all {n} lines", "other": "Show the first 12 lines"},
            "whole": True,
        }
    assert seen["mermaid"] is False
    assert seen["opened"] == ["true", "Show the first 12 lines", False]
    assert seen["closed"] == ["false", "Show all 45 lines", True]  # its button kept in sight
    assert seen["blanks"] == "Show all 16 lines"  # the lines drawn, not the blanks after (F1)
    assert seen["bound"] == 1  # bound once to a page, so a click toggles once (F2)


def test_the_watch_view_shows_what_a_crossings_maker_wrote():
    # the reader read the artefact, not the trial's body, so the view keeps
    # each call's artefact, and says when its record kept only the start
    data = watch_data.watched("20-incident-cause")
    calls = [c for r in data["runs"] for c in r["calls"]]
    assert all(isinstance(c["made"], str) and c["made"] and "cut" not in c for c in calls)
    assert data["maker"] == "Muse" and data["madeBy"] == data["readBy"]
    assert data["makerModel"] == data["model"] == "meta/muse-spark-1.3-contributor"
    assert data["makerInstruction"].startswith("You write the cause section")
    cut = json.dumps({"made": {"sha256": "0" * 64, "text": "The deploy"}, "read": "{}"})
    assert watch_data._made(cut) == {"raw": "{}", "made": "The deploy", "cut": True}
    assert watch_data._made("the call ended incomplete")["made"] is None


def test_a_frame_in_words_says_how_often_each_trial_is_asked():
    # the refund fixture asks each trial once, and the words say so
    page = (ROOT / "docs/write-a-frame.md").read_text(encoding="utf-8")
    assert "**The trials**, each asked once, 8 calls in all:" in page
    assert not re.search(r"asked 1 times", "\n".join((ROOT / p).read_text() for p in PAGES))


def test_the_watch_view_counts_the_asks_of_one_run():
    # a trial is asked quorum times in each run; three runs are kept, so a
    # count without "in this run" reads as a count of runs
    watch = (ROOT / "docs/public/javascripts/watch.js").read_text()
    told = re.search(r"function agreement\(.*?\n  \}\n", watch, re.S).group(0)
    assert "In this run the answers split, " in told
    assert " all ${n} times it was asked in this run." in told
    assert " ${n} of the ${calls.length} times it was asked in this run" in told


@pytest.mark.parametrize(
    ("tests", "changed", "shown", "start"),
    [
        ({6, 19}, set(), 480, 6),  # nothing changed: the first line under test
        ({6, 19}, {6, 19}, 480, 6),  # ablation: the line under test it hid
        ({6, 19}, set(range(30)), 480, 6),  # control: every line hidden
        ({18, 19}, {19}, 480, 18),  # placement: both lines under test in view
        ({18, 19}, {19}, 60, 19),  # the same, when only the moved one fits
        ({21, 22}, {26}, 480, 21),  # two lines under test, then a sham line
        ({21, 22}, {15}, 441, 21),  # a sham line too far for both and the two
        ({21, 22}, {15}, 480, 15),  # the same, when all three fit
        ({6, 19}, {20, 25}, 480, 19),  # a sham line just after a line under test
        ({13}, {12}, 480, 12),  # a sham line just before it: both in view
        ({3}, {23}, 480, 3),  # a sham line too far to share the view
        ({13}, {7}, 480, 7),  # six lines before it, in a view of eight
        ({13}, {7}, 300, 13),  # the same, when the window shows five
    ],
)
def test_the_watch_view_keeps_the_line_under_test_in_view(tests, changed, shown, start):
    # 30 lines of 60px: a sham trial once scrolled to the line it hid and
    # left the line under test out of the list, or below the window's edge
    watch = (ROOT / "docs/public/javascripts/watch.js").read_text()
    settle = re.search(r"  function settle\(.*?\n  \}\n", watch, re.S).group(0)
    rows = [
        {"top": 60 * i, "bottom": 60 * i + 56, "test": i in tests, "changed": i in changed}
        for i in range(30)
    ]
    run = f"{settle}\nprocess.stdout.write(String(settle({json.dumps(rows)}, {shown})[0]));"
    done = subprocess.run(["node", "-e", run], capture_output=True, text=True, check=True)
    assert int(done.stdout) == 60 * start


@pytest.mark.parametrize(
    ("line", "skip", "scrolled"),
    [
        (29, 0, 1320),  # the last line: the list ends at it, the lines before it shown
        (10, 0, 388),  # a middle line, centred in a view of eight
        (0, 0, 0),  # the first line: the list starts at it
        (10, 100, 288),  # under the site's bar, centred in what is left
    ],
)
def test_the_watch_view_centres_the_lines_it_shows(line, skip, scrolled):
    # 30 lines of 60px in a 480px view: the line under test once went to the
    # top, with padding after it, so a last line stood alone in an empty panel
    watch = (ROOT / "docs/public/javascripts/watch.js").read_text()
    centred = re.search(r"  function centred\(.*?\n  \}\n", watch, re.S).group(0)
    shown = [60 * line, 60 * line + 56]
    run = f"{centred}\nprocess.stdout.write(String(centred({shown}, 480, {skip}, 1800 - 480)));"
    done = subprocess.run(["node", "-e", run], capture_output=True, text=True, check=True)
    assert int(done.stdout) == scrolled


def test_the_watch_view_lists_every_answer_an_instruction_names():
    # each frame's answer key is a row an answer, never a sentence to dig
    # through: every answer the instruction names, quoted or bare, gets a row,
    # and only what names none is a line of its own
    watch = (ROOT / "docs/public/javascripts/watch.js").read_text()
    answers = re.search(r"  function answers\(.*?\n  \}\n", watch, re.S).group(0)
    shown = {}
    for path in watch_data.OUT.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        runs = data.get("runs", [])  # the demo's index lists questions, and plays none
        for told in {data.get("instruction"), *(r.get("instruction") for r in runs)}:
            if told and "Answer " in told:
                shown[told] = data["labels"]
    run = (
        "const escape = (s) => s.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');\n"
        f"{answers}\nconst shown = {json.dumps(shown)};\n"
        "const listed = ([told, labels]) =>"
        " [told, answers(told.slice(told.indexOf('Answer ') + 7), labels.map(escape).join('|'))];\n"
        "process.stdout.write(JSON.stringify(Object.entries(shown).map(listed)));"
    )
    done = subprocess.run(["node", "-e", run], capture_output=True, text=True, check=True)
    for told, listed in json.loads(done.stdout):
        assert listed, told
        rows = [i["label"] for i in listed["items"] if "label" in i]
        named = re.findall(r"'([^']+)'", told)
        assert set(named) <= set(rows), told
        assert all(" if " not in i.get("condition", "")[3:] for i in listed["items"]), told
        notes = [i["text"] for i in listed["items"] if "text" in i]
        lines = ["the one person they make the answer", "Give the one answer the statements make"]
        assert notes in ([], *([n] for n in lines)), told


def test_every_kind_of_trial_is_told_in_words():
    # a frame that declares every intervention plans every kind of trial
    from midwife.interventions import plan
    from midwife.pipeline import situate
    from tools.doc_outputs import TESTS

    raw = json.loads((ROOT / "tests/fixtures/restore-inversion.json").read_text())
    raw["anchors"] = ["s15", "s14"]
    raw["interventions"].update(
        eachAnchor=True,
        cumulative=["s19"],
        sham=True,
        presentation={"Jordan": "Casey"},
        placement={"span": "s15", "after": "s30"},
        inputInversion={"has approved": "has not approved"},
        bypass=["s30"],
    )
    raw["allowed"]["inputInversion"] = ["No"]
    kinds = {trial.kind for trial in plan(situate(raw))}
    assert kinds == set(TESTS)
    watch = (ROOT / "docs/public/javascripts/watch.js").read_text()
    told = re.search(r"const TRIALS = \{(.*?)\n  \};", watch, re.S).group(1)
    assert kinds == set(re.findall(r'^\s+"?([\w-]+)"?: \[', told, re.M))


def _references():
    from tools.doc_outputs import PAGES, apis

    return [a for page in PAGES for a in apis(page)]


@pytest.mark.parametrize("block", _references(), ids=lambda a: a.where())
def test_every_reference_is_its_docstrings(block):
    # `uv run python tools/doc_outputs.py --write` brings a page back in line
    from tools.doc_outputs import documented

    assert documented(block.source) == block.quoted


def test_every_shipped_battery_has_its_reference():
    # a battery's promises live in its docstrings, and the reference shows
    # them: one added without its block is a battery no page documents
    shipped = {
        f"midwife.batteries.{path.stem}"
        for path in (ROOT / "midwife" / "batteries").glob("*.py")
        if path.stem != "__init__"
    }
    assert shipped <= {block.source for block in _references()}


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
    # the page quotes messages and notes word for word, each row under its
    # class, so a changed message must change it too
    from midwife import errors

    printed = _printed()
    raised = [*errors.GadflyError.__subclasses__(), *errors.GadflyWarning.__subclasses__()]
    classes = {kind.__name__: kind.__name__ for kind in raised}
    files = (
        "FileNotFoundError",
        "FileExistsError",
        "PermissionError",
        "IsADirectoryError",
        "NotADirectoryError",
    )
    classes |= dict.fromkeys(files, "File errors")
    classes["KeyboardInterrupt"] = "KeyboardInterrupt"

    def known(text: str, kind: str = "") -> bool:
        if text.startswith("No module named"):
            return True  # Python's own words, as the battery's import gave them
        if any(pattern.fullmatch(text) for pattern in printed):
            return True
        # a file error names its path, then Python's words said plainly
        return (
            kind in classes
            and classes[kind] == "File errors"
            and any(pattern.fullmatch(text.partition(" ")[2]) for pattern in printed)
        )

    quoted, unknown, astray, section, rowed = 0, [], [], "", set()
    for row in (ROOT / "docs/troubleshooting.md").read_text(encoding="utf-8").splitlines():
        if row.startswith("### "):
            section = row[4:]
        if not row.startswith("| `"):
            continue
        cells = row.split(" | ")
        for a, b in re.findall(r"``(.+?)``|`([^`]+)`", cells[0][2:]):
            text = a or b
            kind, _, message = text.partition(": ")
            if kind in classes:
                astray += [] if classes[kind] == section else [f"{kind} under {section}"]
                rowed.add(kind)
            elif kind in ("stopped", "openings"):  # lines run no longer prints: a warning now
                unknown.append(text)
                continue
            elif text.startswith('"') and text.endswith('"'):
                kind, message = "", text[1:-1]  # an opening, as run names it
            else:
                continue
            quoted += 1
            unknown += [] if known(message, kind) else [message]
        note = re.match(r"`([^`]+)`", cells[1])  # what Gadfly prints to do, first
        if note:
            unknown += [] if known(note[1]) else [note[1]]
    assert quoted > 30 and unknown == [] and astray == []
    assert set(classes) - rowed == set()  # and every class Gadfly raises has a row


# what the command line says: every refusal, warning and Ctrl-C it makes
SAID = {
    "UsageError", "FrameError", "RecordsError", "BatteryError", "FileExistsError",
    "FileNotFoundError", "PermissionError", "IsADirectoryError", "NotADirectoryError",
    "KeyboardInterrupt", "OpeningWarning", "StoppedWarning",
}  # fmt: skip


def test_every_message_the_command_line_says_has_its_row():
    # the other way round from the test above: each message cli.py and
    # recoil.py make, wherever they make it, is a row under its class, so a
    # new one cannot go untabled (pass 12, D3)
    import ast

    rows = []
    for row in (ROOT / "docs/troubleshooting.md").read_text(encoding="utf-8").splitlines():
        if row.startswith("| `"):
            for a, b in re.findall(r"``(.+?)``|`([^`]+)`", row.split(" | ")[0][2:]):
                kind, _, message = (a or b).partition(": ")
                rows.append((kind, message))
    untabled = []
    for path in ("midwife/cli.py", "midwife/recoil.py"):
        source = (ROOT / path).read_text(encoding="utf-8")
        for call in ast.walk(ast.parse(source)):
            if not (isinstance(call, ast.Call) and getattr(call.func, "id", "") in SAID):
                continue
            first = call.args[0] if call.args else None
            if isinstance(first, ast.JoinedStr):
                values = first.values
            elif isinstance(first, ast.Constant):
                values = [first]
            else:
                continue  # its words are another's, said in a note
            texts = [v.value if isinstance(v, ast.Constant) else None for v in values]
            pattern = re.compile("".join("(.+?)" if t is None else re.escape(t) for t in texts))
            if not any(k == call.func.id and pattern.fullmatch(m) for k, m in rows):
                untabled.append(f"{path}:{call.lineno} {ast.get_source_segment(source, first)}")
    assert untabled == []


def test_the_exit_statuses_troubleshooting_tables_are_the_codes():
    from midwife import errors

    table = {}
    page = (ROOT / "docs/troubleshooting.md").read_text(encoding="utf-8")
    for row in page.split("### Exit statuses", 1)[1].split("\n---\n", 1)[0].splitlines():
        cells = row.split(" | ")
        if row.startswith("| ") and cells[0][2:].isdigit():
            for name in re.findall(r"`(\w+)`", cells[1]) or [cells[1]]:
                table[name] = int(cells[0][2:])
    raised = [*errors.GadflyError.__subclasses__(), *errors.GadflyWarning.__subclasses__()]
    statuses = {kind.__name__: kind.exit for kind in raised}
    files = (
        "FileNotFoundError",
        "FileExistsError",
        "PermissionError",
        "IsADirectoryError",
        "NotADirectoryError",
    )
    statuses |= dict.fromkeys(files, errors.FILE)
    statuses |= {"KeyboardInterrupt": errors.INTERRUPTED, "any other": errors.BUG}
    assert {name: table.get(name) for name in statuses} == statuses


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


def test_a_folded_blocks_button_reads_at_5_to_1_on_every_study():
    # its label and its hover are inks of the code itself, held at 5:1 on
    # the code's ground in every study, a dark terminal on a light page too
    css = THEMES.read_text(encoding="utf-8")
    fold = re.search(r"> button\.fold \{(.*?)\}", css, re.S).group(1)
    hover = re.search(r"> button\.fold:hover \{(.*?)\}", css, re.S).group(1)
    inks = [re.search(r"\bcolor: var\(--([a-z-]+)\)", rule).group(1) for rule in (fold, hover)]
    faint = []
    for name, body in re.findall(r"\[data-theme='([a-z]+)'\] \{(.*?)\n\}", css, re.S):
        ground = re.search(r"--gf-console-bg: (#[0-9a-f]{6});", body).group(1)
        for ink in inks:
            colour = re.search(rf"--{ink}: (#[0-9a-f]{{6}});", body)
            if colour is None:
                faint.append(f"{name}: {ink} is not one of its code's inks")
            elif _contrast(colour.group(1), ground) < 5:
                faint.append(f"{name}: {ink} at {_contrast(colour.group(1), ground):.2f}")
    assert faint == []


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


def test_the_site_splits_nothing_with_a_dot():
    # site text has no "·" separators; the README's closing row of links,
    # read on GitHub and PyPI, is outside the site
    site = [ROOT / page for page in PAGES if page.startswith("docs/")]
    site += sorted((ROOT / "docs/.vitepress").glob("*.mjs"))
    site += sorted((ROOT / "docs/.vitepress/theme").glob("*.*"))
    dotted = [str(path.relative_to(ROOT)) for path in site if "·" in path.read_text()]
    assert dotted == []


def test_the_version_badge_reads_the_release_tags():
    # CI's badge leads; shields keeps a PyPI badge for six hours, a tag's for
    # five minutes; the tag names the published version, as publish.yml
    # checks before it uploads
    ci, version = (ROOT / "README.md").read_text(encoding="utf-8").split("\n")[2:4]
    assert ci.startswith("[![CI](")
    assert "img.shields.io/github/v/tag/mirzahusadzic/gadfly?sort=semver" in version
    assert version.endswith("(https://pypi.org/project/midwife/)")


def test_the_local_json_page_promises_only_what_the_battery_checks():
    # the battery checks JSON and the label pointer; the answer's schema is
    # the evaluator's (pass 4, R12: the page had promised a schema check)
    page = " ".join((ROOT / "docs/breadth/local-json-battery.md").read_text().split())
    assert "invalid JSON/schema" not in page
    assert "held to its schema by the evaluator, not here" in page


def test_the_upgrade_page_names_each_class_with_its_status():
    # what a caller of 0.6.0 meets: every refusal class and warning, as raised
    from midwife import errors

    page = " ".join((ROOT / "docs/upgrading.md").read_text(encoding="utf-8").split())
    for kind in (errors.UsageError, errors.FrameError, errors.RecordsError, errors.BatteryError):
        assert f"`{kind.__name__}` {kind.exit}" in page, kind.__name__
    for kind in (errors.OpeningWarning, errors.StoppedWarning):
        assert f"`{kind.__name__}`" in page, kind.__name__
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "gadfly/upgrading)" in readme
