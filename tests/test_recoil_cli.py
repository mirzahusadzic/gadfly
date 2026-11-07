"""Recoil from the command line: walk, successor, firm and gate, as a person
or an agent runs them. Each `--json` is what `midwife.recoil`'s function of
the same name returns, and each refusal says what to fix, with its status."""

import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from shlex import quote

import pytest

from midwife.cli import load_frame, load_records, main
from midwife.pipeline import calls_needed, run, situate
from midwife.recoil import (
    Piece,
    calls_until_firm,
    decided,
    found,
    gate,
    sha256,
    successor,
    until_firm,
    walk,
)
from midwife.types import Budget

ROOT = Path(__file__).parent.parent
DOLLS = ROOT / "examples/dolls"
CHAIN = [str(DOLLS / f"{doll}.json") for doll in ("1-amani", "2-kiran", "3-sasha", "4-robin")]
AMANI, KIRAN, MIRZA = (str(DOLLS / f"{doll}.json") for doll in ("1-amani", "2-kiran", "5-mirza"))
ASKED = str(ROOT / "examples/22-kiran-paper.json")
DECOY = str(ROOT / "examples/22b-kiran-paper-decoy.json")
RUNS = str(ROOT / "examples/runs/22-kiran-paper")
DECOY_RUNS = str(ROOT / "examples/runs/22b-kiran-paper-decoy")
PAPER = 'The paper says: "My name is Kiran, and I am a boy."'
REFUND = ROOT / "tests/fixtures/refund.json"


@pytest.fixture(autouse=True)
def at_root(monkeypatch):
    monkeypatch.chdir(ROOT)  # the battery is imported from here


@pytest.fixture
def thrice(tmp_path):
    # the refund frame asked three times a trial, as until_firm needs, and an
    # empty folder for its runs
    raw = json.loads(REFUND.read_text(encoding="utf-8"))
    raw["standing"] = {"quorum": 3, "agree": 2}
    frame = tmp_path / "refund.json"
    frame.write_text(json.dumps(raw), encoding="utf-8")
    (tmp_path / "runs").mkdir()
    return frame, tmp_path / "runs"


def firm(frame, runs, reader, *more):
    battery = f"tests.fixtures.refund:{reader}"
    return main(["firm", str(frame), "--battery", battery, "--runs", str(runs), *more])


def told(capsys, stream="out"):
    return getattr(capsys.readouterr(), stream).splitlines()


# ---- walk


def test_walk_climbs_the_paper_to_the_hole_it_fits_without_a_call(capsys):
    assert main(["walk", *CHAIN, "--from", MIRZA, "--span", "says"]) == 0
    lines = told(capsys)
    assert lines[0].startswith(f"piece: {PAPER!r}, of kind kiran-paper, from Mirza (")
    assert [line.split(" (")[0] for line in lines[1:]] == [
        "fits: Kiran",
        "passed: Robin",
        "passed: Sasha",
        "passed: Amani",
        "complete: yes",
    ]
    assert lines[1].endswith("), hole paper")


def test_walk_json_is_what_midwife_recoil_walk_returns(capsys):
    source = load_frame(MIRZA)
    walked = walk(found(source, "says"), source, [load_frame(path) for path in CHAIN])
    assert main(["walk", *CHAIN, "--from", MIRZA, "--span", "says", "--json"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document == {
        "piece": {
            "text": PAPER,
            "kind": "kiran-paper",
            "sha256": sha256(PAPER),
            "from": {"frame": "Mirza", "hash": source.hash},
        },
        "fits": [
            {
                "frame": frame.name,
                "hash": frame.hash,
                "sideways": False,
                "made": [],
                "holes": list(holes),
            }
            for frame, holes in walked.fits
        ],
        "order": [
            {
                "frame": fit.frame.name,
                "hash": fit.frame.hash,
                "sideways": False,
                "made": [],
                "hole": fit.hole,
            }
            | {"cosine": None, "unordered": None, "calls": None, "asked": None}
            for fit in walked.order
        ],
        "deferred": [],
        "passed": [
            {"frame": frame.name, "hash": frame.hash, "sideways": False, "made": []}
            for frame in walked.passed
        ],
        "frontier": list(walked.frontier),
        "complete": walked.complete,
        "budget": None,
        "most": None,
        "space": None,
        "vectors": None,
    }


def test_walk_counts_the_fits_its_calls_cover_before_the_first(capsys):
    # Kiran's successor takes at most 45 calls until firm: 45 calls cover it
    source = load_frame(MIRZA)
    kiran = load_frame(KIRAN)
    walked = walk(found(source, "says"), source, [load_frame(path) for path in CHAIN], calls=45)
    assert main(["walk", *CHAIN, "--from", MIRZA, "--span", "says", "--calls", "45"]) == 0
    lines = told(capsys)
    assert f"fits: Kiran ({kiran.hash[:12]}), hole paper, at most 45 calls until firm" in lines
    assert (
        lines[-1]
        == "budget: 45 calls cover 1 fit of 1, at most 45 calls in all, each fit at most 5 runs"
    )
    argv = ["walk", *CHAIN, "--from", MIRZA, "--span", "says", "--calls", "45", "--json"]
    assert main(argv) == 0
    document = json.loads(capsys.readouterr().out)
    [fit] = walked.order
    assert document["order"] == [
        {"frame": "Kiran", "hash": kiran.hash, "sideways": False, "made": [], "hole": "paper"}
        | {"cosine": None, "unordered": None, "calls": 45, "asked": True}
    ]
    assert (document["budget"], document["most"]) == (45, 5) == (walked.budget, walked.most)
    # one call fewer, or one run fewer a fit, and the order says so
    assert main(["walk", *CHAIN, "--from", MIRZA, "--span", "says", "--calls", "44"]) == 0
    lines = told(capsys)
    assert lines[1].endswith(", at most 45 calls until firm, not asked, past the budget")
    assert lines[-1] == "budget: 44 calls cover 0 fits of 1, each fit at most 5 runs"
    argv = ["walk", *CHAIN, "--from", MIRZA, "--span", "says", "--calls", "44", "--most", "4"]
    assert main(argv) == 0
    assert told(capsys)[1].endswith("hole paper, at most 36 calls until firm")
    # one call, one run: said in the singular (pass 14, R7)
    assert main(["walk", *CHAIN, "--from", MIRZA, "--span", "says", "--calls", "1"]) == 0
    assert told(capsys)[-1] == "budget: 1 call covers 0 fits of 1, each fit at most 5 runs"
    argv = ["walk", *CHAIN, "--from", MIRZA, "--span", "says", "--calls", "9", "--most", "1"]
    assert main(argv) == 0
    assert told(capsys)[-1] == (
        "budget: 9 calls cover 1 fit of 1, at most 9 calls in all, each fit at most 1 run"
    )


def test_walk_climbs_from_a_frame_quoting_an_artefact_to_its_crossing(tmp_path, capsys):
    from tests.fixtures.incident import INCIDENT, crossing
    from tests.test_recoil import CAUSE, made_cause, review

    raw = {**INCIDENT, "holes": [{"id": "m5", "kind": "metric"}]}
    incident = tmp_path / "incident.json"
    incident.write_text(json.dumps(raw), encoding="utf-8")
    frame = load_frame(str(incident))
    records = run(frame, crossing, Budget(calls=calls_needed(frame))).records
    kept = tmp_path / "made.jsonl"
    kept.write_text("".join(json.dumps(r.as_dict()) + "\n" for r in records), encoding="utf-8")
    start = tmp_path / "review.json"
    start.write_text(json.dumps(review().raw), encoding="utf-8")
    argv = ["walk", str(incident), "--from", str(start), "--span", "found"]
    assert main([*argv, "--made", str(kept)]) == 0
    pairs = made_cause(records)
    said = ", ".join(f"{trial} for {input_}" for trial, input_ in pairs)
    head = f"fits: rollback-from-cause ({frame.hash[:12]}), hole m5"
    assert f"{head}, through the artefact made in {said}" in told(capsys)
    assert main([*argv, "--made", str(kept), "--json"]) == 0
    document = json.loads(capsys.readouterr().out)
    made = [{"trial": t, "input": x} for t, x in pairs]
    assert document["fits"][0]["made"] == made == document["order"][0]["made"]
    # without the records, the cause is the frontier; with another frame's, refused
    assert main(argv) == 0 and told(capsys)[-2].startswith(f"frontier: {sha256(CAUSE)}")
    assert main(["walk", KIRAN, *argv[2:], "--made", str(kept)]) == 5
    assert told(capsys, "err")[0] == (
        f"RecordsError: a made record names frame {frame.hash!r}, "
        "which is not among the frames given"
    )


def test_walk_sideways_offers_the_piece_to_the_siblings_of_its_start(tmp_path, capsys):
    from tests.test_recoil import sideways_case

    frames = []
    for frame in sideways_case():
        path = tmp_path / f"{frame.name}.json"
        path.write_text(json.dumps(frame.raw), encoding="utf-8")
        frames.append((frame, str(path)))
    (start, first), *others = frames
    argv = ["walk", *(path for _, path in others), "--from", first, "--span", "own"]
    assert main(argv) == 0
    assert not any(line.startswith("fits: ") for line in told(capsys))
    assert main([*argv, "--sideways"]) == 0
    lines = told(capsys)
    [sibling, quiet] = [frame for frame, _ in others if frame.name in ("sibling", "quiet")]
    assert f"fits: sibling ({sibling.hash[:12]}), hole h, sideways" in lines
    assert f"passed: quiet ({quiet.hash[:12]}), sideways" in lines
    assert not any("cousin" in line for line in lines)
    assert main([*argv, "--sideways", "--json"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert [(fit["frame"], fit["sideways"]) for fit in document["order"]] == [
        ("sibling", True),
        ("workshop", False),
    ]


def test_walk_orders_its_fits_by_the_vectors_given(tmp_path, capsys, monkeypatch):
    about = "who the second doll is, in its own words"
    kiran = deferring(tmp_path, salience="consider", about=about)
    chain = [AMANI, kiran, *CHAIN[2:]]
    lines = [
        {"text": sha256(PAPER), "space": "e128", "values": [1, 0]},
        {"text": sha256(about), "space": "e128", "values": [3, 4]},
    ]
    data = "".join(json.dumps(line) + "\n" for line in lines).encode()
    vectors = tmp_path / "vectors.jsonl"
    vectors.write_bytes(data)
    argv = ["walk", *chain, "--from", MIRZA, "--span", "says", "--vectors", str(vectors)]
    assert main(argv) == 0
    said = told(capsys)
    held = load_frame(kiran)
    digest = hashlib.sha256(data).hexdigest()
    assert f"fits: Kiran ({held.hash[:12]}), hole paper, cosine 0.6000" in said
    assert said[-1] == f"ordered: by cosine in space e128, vectors {digest}"
    assert main([*argv, "--json"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert (document["space"], document["vectors"]) == ("e128", digest)
    assert document["order"][0]["cosine"] == 0.6 and document["order"][0]["unordered"] is None
    # read from standard input as from a file; with no vector for the piece, it keeps its place
    piped = io.TextIOWrapper(io.BytesIO(data[data.index(b"\n") + 1 :]), encoding="utf-8")
    monkeypatch.setattr("sys.stdin", piped)
    assert main([*argv[:-1], "-"]) == 0
    assert f"fits: Kiran ({held.hash[:12]}), hole paper, kept in its place, " in told(capsys)[1]
    monkeypatch.setattr("sys.stdin", io.StringIO(data.decode()))  # a text stream of a caller's
    assert main([*argv[:-1], "-"]) == 0
    assert told(capsys)[1].endswith("hole paper, cosine 0.6000")


def test_walk_reads_standard_input_once_for_its_vectors_and_runs_too(capsys):
    argv = ["walk", *CHAIN, "--from", "-", "--span", "says", "--vectors", "-"]
    assert main(argv) == 2
    assert told(capsys, "err")[0] == "UsageError: standard input is read once"
    argv = ["walk", *CHAIN, "--from", MIRZA, "--span", "says", "--made", "-", "--made", "-"]
    assert main(argv) == 2


@pytest.mark.parametrize(
    "lines, more, message",
    [
        (None, ["--space", "e128"], "UsageError: --space is given without --vectors"),
        (
            ['{"text": "%s", "space": "e", "values": [1]}' % sha256(PAPER)] * 2,
            [],
            f"UsageError: file 'v.jsonl' holds text {sha256(PAPER)!r} in space 'e' twice, "
            "at lines 1 and 2",
        ),
        (["{"], [], "UsageError: file 'v.jsonl' cannot be read as JSON at line 1"),
        (
            ['{"text": "%s", "space": "\\ud800", "values": [1]}' % sha256(PAPER)],
            [],
            "UsageError: file 'v.jsonl' names space '\\ud800' at line 1, not one plain name",
        ),
        (
            ['{"text": "%s", "space": "e", "values": [1]}' % sha256(PAPER)],
            ["--space", "f"],
            "UsageError: the vectors hold no vector in space 'f'",
        ),
    ],
)
def test_walk_refuses_vectors_it_cannot_order_by(lines, more, message, tmp_path, capsys):
    frames = [str(Path(path).resolve()) for path in (*CHAIN, MIRZA)]
    os.chdir(tmp_path)  # at_root goes back after
    if lines is not None:
        Path("v.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        more = ["--vectors", "v.jsonl", *more]
    assert main(["walk", *frames[:-1], "--from", frames[-1], "--span", "says", *more]) == 2
    assert told(capsys, "err")[0] == message


@pytest.mark.parametrize(
    "more, message",
    [
        (["--most", "3"], "UsageError: --most is given without --calls"),
        (
            ["--calls", "45", "--most", "0"],
            "UsageError: --most is a whole number of runs, at least 1",
        ),
        (["--calls", "0"], "UsageError: a walk's budget is a whole number of calls, at least 1"),
    ],
)
def test_walk_refuses_a_budget_it_cannot_count(more, message, capsys):
    assert main(["walk", *CHAIN, "--from", MIRZA, "--span", "says", *more]) == 2
    assert told(capsys, "err")[0] == message
    # before any file is read: a frame missing, or no frame at all, is not said first
    # (pass 14, R4)
    missing = str(ROOT / "tests/fixtures/no-such-frame.json")
    assert main(["walk", missing, "--from", missing, "--span", "says", *more]) == 2
    assert told(capsys, "err")[0] == message


def test_walk_refuses_a_space_without_vectors_before_any_file(capsys):
    missing = str(ROOT / "tests/fixtures/no-such-frame.json")
    assert main(["walk", missing, "--from", missing, "--span", "says", "--space", "e"]) == 2
    assert told(capsys, "err")[0] == "UsageError: --space is given without --vectors"


def deferring(tmp_path, **hole):
    # Kiran, its paper hole deferred, or otherwise salient as `hole` says
    raw = json.loads(Path(KIRAN).read_text(encoding="utf-8"))
    raw["holes"] = [{**raw["holes"][0], "salience": "defer", **hole}]
    path = tmp_path / "kiran.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return str(path)


def test_walk_lists_a_deferred_fit_kept_and_not_asked(tmp_path, capsys):
    kiran = deferring(tmp_path, about="who the second doll is, in its own words")
    chain = [AMANI, kiran, *CHAIN[2:]]
    assert main(["walk", *chain, "--from", MIRZA, "--span", "says"]) == 0
    lines = told(capsys)
    held = load_frame(kiran)
    assert f"deferred: Kiran ({held.hash[:12]}), hole paper, kept and not asked" in lines
    assert not any(line.startswith(("fits: ", "passed: Kiran")) for line in lines)
    assert main(["walk", *chain, "--from", MIRZA, "--span", "says", "--json"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["fits"] == []
    assert document["deferred"] == [
        {"frame": "Kiran", "hash": held.hash, "sideways": False, "made": [], "holes": ["paper"]}
    ]


def test_walk_names_each_text_it_could_not_follow(capsys):
    # Robin quotes Sasha, who is not given: the walk is not complete
    assert main(["walk", str(DOLLS / "4-robin.json"), "--from", MIRZA, "--span", "says"]) == 0
    lines = told(capsys)
    assert lines[-1] == "complete: no"
    assert lines[-2].startswith("frontier: ")
    assert lines[-2].endswith(", quoted by a frame and held by none given")


def test_walk_climbs_a_decision_as_the_kind_its_frame_offers(capsys):
    assert main(["walk", AMANI, "--from", ASKED, "--decision", "boy", "--json"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert (document["piece"]["text"], document["piece"]["kind"]) == ("Kiran reads boy", "role")
    assert [(fit["frame"], fit["holes"]) for fit in document["fits"]] == [("Amani", ["inside"])]


@pytest.mark.parametrize(
    "argv, said",
    [
        (["--from", MIRZA, "--span", "nope"], "UsageError: frame 'Mirza' has no span 'nope'"),
        (
            ["--from", MIRZA, "--decision", "boy"],
            "UsageError: frame 'Mirza' offers no kind for its decision to climb as",
        ),
        (
            ["--from", ASKED, "--decision", "maybe"],
            "UsageError: frame 'Kiran' has no label 'maybe'",
        ),
        (["--from", MIRZA], "UsageError: missing one of --span, --decision"),
    ],
)
def test_walk_refuses_a_piece_it_cannot_find(argv, said, capsys):
    assert main(["walk", AMANI, *argv]) == 2
    assert told(capsys, "err")[0] == said


@pytest.mark.parametrize(
    "argv, said",
    [
        # a mistyped flag is named, rather than the flag it was meant to be (pass 12, C1)
        (["walk", KIRAN, "--from", MIRZA, "--spa", "says"], "unrecognized arguments --spa"),
        (
            ["run", REFUND.as_posix(), "--battry", "x", "--calls", "1", "--out", "-"],
            "unrecognized arguments --battry",
        ),
        # argparse's own words said in Gadfly's (pass 12, D3)
        (
            ["walk", AMANI, "--from", MIRZA, "--span", "says", "--decision", "boy"],
            "--decision and --span cannot be given together",
        ),
        (["walk", "--from", MIRZA, "--span", "says"], "missing frames"),
        (["gate"], "missing before, after"),
    ],
)
def test_the_command_line_says_which_argument_is_wrong(argv, said, capsys):
    assert main(argv) == 2
    assert told(capsys, "err")[0] == f"UsageError: {said}"


def test_a_negative_number_is_a_value_not_a_flag(thrice, capsys):
    frame, runs = thrice
    assert firm(frame, runs, "RuleReader", "--calls", "100", "--firm", "-1") == 2
    assert told(capsys, "err")[0] == "UsageError: --firm is a share above 0, up to 1"


def test_walk_reads_standard_input_once(capsys):
    assert main(["walk", "-", "--from", "-", "--span", "says"]) == 2
    assert told(capsys, "err") == [
        "UsageError: standard input is read once",
        "name - for one file at most",
    ]


# ---- successor


def test_successor_drafts_the_frame_a_fit_is_asked_again_as(capsys):
    assert main(["successor", KIRAN, "--hole", "paper", "--from", MIRZA, "--span", "says"]) == 0
    said = capsys.readouterr()
    draft = json.loads(said.out)  # the frame owns standard output
    before = load_frame(KIRAN)
    assert draft == successor(before, "paper", found(load_frame(MIRZA), "says"))
    assert draft["anchors"] == ["paper"] and "holes" not in draft
    assert draft["body"]["spans"][-1] == {
        "id": "paper",
        "text": PAPER,
        "kind": "kiran-paper",
        "source": {"sha256": sha256(PAPER)},
    }
    after = situate(draft)
    assert said.err.splitlines() == [
        f"successor: Kiran ({after.hash[:12]}), of Kiran ({before.hash[:12]}), "
        "its hole paper filled",
        "reframes: nothing, so it asks the same question, read from its own runs",
    ]


def test_successor_places_the_piece_after_the_line_it_amends(capsys):
    argv = ["successor", KIRAN, "--hole", "paper", "--from", MIRZA, "--span", "says"]
    assert main([*argv, "--after", "name"]) == 0
    said = capsys.readouterr()
    draft = json.loads(said.out)
    paper = found(load_frame(MIRZA), "says")
    assert draft == successor(load_frame(KIRAN), "paper", paper, after="name")
    ids = [each["id"] for each in draft["body"]["spans"]]
    assert ids[ids.index("name") + 1] == "paper"
    assert said.err.splitlines()[0].endswith("its hole paper filled, after span name")
    assert main([*argv, "--after", "name", "--json"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["after"] == "name" and document["draft"] == draft
    assert main([*argv, "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["after"] is None


def test_successor_takes_a_piece_found_in_no_frame_as_its_text_and_kind(capsys):
    # a piece from a store of its own, as Piece(text, kind) is in Python:
    # the same text and kind draft the same successor as the span found
    argv = ["successor", KIRAN, "--hole", "paper", "--text", PAPER, "--kind", "kiran-paper"]
    assert main(argv) == 0
    draft = json.loads(capsys.readouterr().out)
    assert draft == successor(load_frame(KIRAN), "paper", Piece(PAPER, "kiran-paper"))
    assert main(["successor", KIRAN, "--hole", "paper", "--from", MIRZA, "--span", "says"]) == 0
    assert json.loads(capsys.readouterr().out) == draft
    assert main([*argv, "--json"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["piece"] == {
        "text": PAPER,
        "kind": "kiran-paper",
        "sha256": sha256(PAPER),
        "from": None,
    }


@pytest.mark.parametrize(
    "more, said",
    [
        (["--text", PAPER], ["missing --kind", "a --text piece fills only a hole of its own kind"]),
        (
            ["--text", PAPER, "--kind", "kiran-paper", "--from", MIRZA],
            [
                "--from and --text cannot be given together",
                "a piece is a text of its own, or one found in the frame --from names",
            ],
        ),
        (
            ["--from", MIRZA, "--span", "says", "--kind", "kiran-paper"],
            [
                "--kind is given without --text",
                "a piece found in a frame is of its span's kind, or the kind its frame offers",
            ],
        ),
        (["--span", "says"], ["missing --from", "name the frame the piece was found in"]),
        (["--from", MIRZA], ["missing one of --span, --decision, --text"]),
        (["--text", PAPER, "--span", "says"], ["--span and --text cannot be given together"]),
    ],
)
def test_successor_says_which_piece_it_was_not_given(more, said, capsys):
    assert main(["successor", KIRAN, "--hole", "paper", *more]) == 2
    err = told(capsys, "err")
    assert err[0] == f"UsageError: {said[0]}" and err[1 : len(said)] == said[1:]


@pytest.mark.parametrize(
    "first, second, said",
    [
        (["--span", "says"], ["--text", PAPER], "--span and --text"),
        (["--decision", "boy"], ["--text", PAPER], "--decision and --text"),
        (["--span", "says"], ["--decision", "boy"], "--decision and --span"),
    ],
)
def test_a_clash_is_named_alike_whichever_flag_came_first(first, second, said, capsys):
    # one mistake, one message, whatever order it was typed in (pass 13, F4)
    for flags in ([*first, *second], [*second, *first]):
        assert main(["successor", KIRAN, "--hole", "paper", "--from", MIRZA, *flags]) == 2
        assert told(capsys, "err")[0] == f"UsageError: {said} cannot be given together"


def test_walk_takes_no_text_piece(capsys):
    # a walk climbs from the frame a piece was found in, so it needs that frame
    assert main(["walk", KIRAN, "--from", MIRZA, "--text", PAPER, "--kind", "x"]) == 2
    assert told(capsys, "err")[0] == "UsageError: unrecognized arguments --text --kind"


def test_successor_writes_a_new_file_and_never_over_one(tmp_path, capsys):
    out = tmp_path / "kiran.json"
    argv = ["successor", KIRAN, "--hole", "paper", "--from", MIRZA, "--span", "says"]
    assert main([*argv, "--out", str(out)]) == 0
    assert told(capsys)[-1] == f"wrote it to {quote(str(out))}"
    first = out.read_text(encoding="utf-8")
    assert situate(json.loads(first)).name == "Kiran"
    assert main([*argv, "--out", str(out)]) == 7
    assert told(capsys, "err") == [
        f"FileExistsError: file {str(out)!r} exists already",
        "a frame is never written over; choose a new --out",
    ]
    assert out.read_text(encoding="utf-8") == first


def test_successor_says_when_it_asks_another_question(capsys):
    # Kiran's decision fills Amani's hole, but a boy inside needs a label
    # the set as asked lacks: the successor reframes
    observe = load_frame(AMANI).raw["observe"]
    labels = [observe["labels"][0], "boys", "mixed", *observe["labels"][1:]]
    changed = json.dumps({**observe, "labels": labels})
    argv = ["successor", AMANI, "--hole", "inside", "--from", ASKED, "--decision", "boy"]
    assert main([*argv, "--set", "observe", changed, "--json"]) == 0
    document = json.loads(capsys.readouterr().out)
    asked = load_frame(ASKED)
    assert document["piece"] == {
        "text": "Kiran reads boy",
        "kind": "role",
        "sha256": sha256("Kiran reads boy"),
        "from": {"frame": "Kiran", "hash": asked.hash},
    }
    assert document["reframes"] == ["observe"] and document["out"] is None
    assert document["of"] == {"frame": "Amani", "hash": load_frame(AMANI).hash}
    assert document["hash"] == situate(document["draft"]).hash
    assert main([*argv, "--set", "observe", changed]) == 0
    assert told(capsys, "err")[1] == (
        "reframes: observe, so it asks another question, read against no category"
    )


@pytest.mark.parametrize(
    "more, status, said",
    [
        (
            ["--hole", "nope", "--span", "says"],
            2,
            ["UsageError: frame 'Kiran' has no hole 'nope'"],
        ),
        (
            ["--hole", "paper", "--span", "face"],
            2,
            ["UsageError: hole 'paper' is of kind 'kiran-paper', and the piece is of kind 'paint'"],
        ),
        (
            ["--hole", "paper", "--span", "says", "--after", "nope"],
            2,
            [
                "UsageError: frame 'Kiran' has no span 'nope' to place the piece after",
                "name one of its spans, the line the piece amends",
            ],
        ),
        (
            ["--hole", "paper", "--span", "says", "--set", "standing", "three"],
            2,
            [
                "UsageError: --set 'standing' is given 'three', which is not JSON",
                "give the value as JSON, quoted for the shell",
            ],
        ),
        (
            ["--hole", "paper", "--span", "says", "--set", "anchors", '["nope"]'],
            4,
            [
                "FrameError: the body has no span 'nope'",
                "anchors name spans of the body",
                "the successor of frame 'Kiran' is checked as any frame is",
            ],
        ),
    ],
)
def test_successor_refuses_what_it_cannot_draft(more, status, said, capsys):
    assert main(["successor", KIRAN, "--from", MIRZA, *more]) == status
    assert told(capsys, "err") == said


# ---- plan, for a climb


def test_plan_counts_the_calls_until_firm_before_the_first(capsys):
    frame = load_frame(ASKED)
    each = calls_until_firm(frame, most=1)
    assert main(["plan", ASKED, "--runs", RUNS]) == 0
    lines = told(capsys)
    assert lines[1] == (
        f"until firm: at most {4 * each} calls, 4 more runs of {each} calls, 1 kept of 5 at most"
    )
    assert main(["plan", ASKED, "--most", "2", "--runs", RUNS, "--json"]) == 0
    kept = [load_records(str(Path(RUNS) / "1.jsonl"))]
    climb = json.loads(capsys.readouterr().out)["climb"]
    assert climb == {"most": 2, "kept": 1, "calls": calls_until_firm(frame, kept=kept, most=2)}
    assert climb["calls"] == each
    assert main(["plan", ASKED, "--most", "1", "--runs", RUNS]) == 0
    assert (
        told(capsys)[1]
        == "until firm: at most 0 calls, 0 more runs of 21 calls, 1 kept of 1 at most"
    )
    assert main(["plan", ASKED]) == 0
    assert not any(line.startswith("until firm") for line in told(capsys))


@pytest.mark.parametrize(
    "more, said",
    [
        (["--most", "0"], ["UsageError: --most is a whole number of runs, at least 1"]),
        (
            ["--runs", "nowhere"],
            [
                "FileNotFoundError: folder 'nowhere' does not exist",
                "name the folder gadfly firm keeps the frame's runs in",
            ],
        ),
    ],
)
def test_plan_refuses_a_climb_it_cannot_count(more, said, capsys):
    assert main(["plan", ASKED, *more]) == (7 if "FileNotFoundError" in said[0] else 2)
    assert told(capsys, "err") == said


def test_plan_refuses_a_climb_of_a_frame_asked_once_a_trial(capsys):
    assert main(["plan", REFUND.as_posix(), "--most", "3"]) == 2
    assert told(capsys, "err") == [
        "UsageError: frame 'refund-receipt' asks each trial once, "
        "so a run has no calls to draw again",
        "give it a quorum of 2 or more",
    ]


# ---- firm


def test_firm_keeps_each_run_and_reads_them_back_as_runs_made(thrice, capsys):
    frame, runs = thrice
    assert firm(frame, runs, "RuleReader", "--calls", "100") == 0
    assert told(capsys)[1:] == [
        "run 1: carried, asked now",
        "firm: yes, carried after 1 run, read alike in 100% of draws; 24 calls made now",
    ]
    assert [path.name for path in runs.iterdir()] == ["1.jsonl"]
    kept = load_records(str(runs / "1.jsonl"))
    assert len(kept) == 24
    # asked again, the kept run is a run made, and nothing more is asked
    assert firm(frame, runs, "RuleReader", "--calls", "100", "--json") == 0
    document = json.loads(capsys.readouterr().out)
    asked = until_firm(load_frame(str(frame)), None, Budget(calls=1), kept=[kept])
    assert document == {
        "frame": "refund-receipt",
        "hash": asked.frame.hash,
        "runs": [{"file": str(runs / "1.jsonl"), "kept": True, "category": "carried"}],
        "made": 0,
        "usage": {},
        "unthought": {"calls": 0, "unthought": 0, "trials": {}},
        "firm": asked.firm,
        "category": asked.category,
        "shares": asked.shares,
        "findings": [finding.as_dict() for finding in asked.findings],
        "stopped": asked.stopped,
        "openings": {},
        "exit": 0,
        "warnings": [],
    }
    assert [path.name for path in runs.iterdir()] == ["1.jsonl"]


def test_firm_reads_as_many_runs_as_the_frame_declares(thrice, capsys):
    # standing.most in the frame binds firm; --most may only repeat it
    frame, runs = thrice
    raw = json.loads(frame.read_text(encoding="utf-8"))
    raw["standing"]["most"] = 2
    frame.write_text(json.dumps(raw), encoding="utf-8")
    assert firm(frame, runs, "Wavering", "--calls", "1000") == 0
    assert len(list(runs.iterdir())) <= 2
    assert told(capsys)[-1].startswith("firm: ")
    assert firm(frame, runs, "Wavering", "--calls", "1000", "--most", "5") == 2
    assert told(capsys, "err")[-2].startswith(
        "UsageError: frame 'refund-receipt' declares most 2, and 5 is asked"
    )


def test_gate_refuses_a_different_most_for_a_reframing_too(tmp_path, capsys):
    # pass 16 R6: one rule for every command, whether or not runs are read
    before_path = ROOT / "examples/dolls/1-amani.json"
    before = load_frame(str(before_path))
    observe = before.raw["observe"]
    labels = [observe["labels"][0], "boys", "mixed", *observe["labels"][1:]]
    asked = load_frame(str(ROOT / "examples/22-kiran-paper.json"))
    after = successor(
        before,
        "inside",
        decided(asked, "boy"),
        observe={"instruction": observe["instruction"], "labels": labels},
    )
    after["standing"]["most"] = 2
    after_path = tmp_path / "after.json"
    after_path.write_text(json.dumps(after), encoding="utf-8")
    assert main(["gate", str(before_path), str(after_path), "--most", "5"]) == 2
    assert "declares most 2, and 5 is asked" in capsys.readouterr().err
    assert main(["gate", str(before_path), str(after_path)]) == 0


def test_plan_help_names_the_frames_own_most(capsys):
    # pass 16 R9
    with pytest.raises(SystemExit):
        main(["plan", "--help"])
    assert "the frame's standing.most, else 5" in " ".join(capsys.readouterr().out.split())


def test_a_full_folder_of_a_declared_most_is_told_only_to_move_runs_out(thrice, capsys):
    # pass 16 R10: raising --most would be refused for this frame
    frame, runs = thrice
    raw = json.loads(frame.read_text(encoding="utf-8"))
    raw["standing"]["most"] = 1
    frame.write_text(json.dumps(raw), encoding="utf-8")
    assert firm(frame, runs, "RuleReader", "--calls", "auto") == 0
    (runs / "2.jsonl").write_text((runs / "1.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
    assert firm(frame, runs, "RuleReader", "--calls", "auto") == 2
    said = told(capsys, "err")
    assert said[-2].endswith("keeps 2 runs, more than --most reads")
    assert said[-1] == "move the earliest runs out"


def test_firm_makes_calls_at_once_within_each_run(thrice, capsys):
    # --parallel passes the battery's calls at once into each run firm makes
    from tests.fixtures import refund

    frame, runs = thrice
    refund.AtOnce.most = 0
    assert firm(frame, runs, "AtOnce", "--calls", "100", "--parallel", "4") == 0
    assert refund.AtOnce.most > 1
    assert told(capsys)[1:] == [
        "run 1: carried, asked now",
        "firm: yes, carried after 1 run, read alike in 100% of draws; 24 calls made now",
    ]
    assert len(load_records(str(runs / "1.jsonl"))) == 24


def test_firm_says_the_tokens_its_calls_reported_on_its_last_line(thrice, capsys):
    # the readers' cost beside the calls: summed from each record's usage
    frame, runs = thrice
    assert firm(frame, runs, "Metered", "--calls", "100") == 0
    assert told(capsys)[-1] == (
        "firm: yes, carried after 1 run, read alike in 100% of draws; 24 calls made now, "
        "24,000 tokens in, 960 out, 720 of them reasoning, 0 of 24 calls unthought"
    )
    again = runs.parent / "again"
    again.mkdir()
    assert firm(frame, again, "Metered", "--calls", "100", "--json") == 0
    document = json.loads(capsys.readouterr().out)
    assert document["usage"] == {
        "input_tokens": 24000,
        "output_tokens": 960,
        "reasoning_tokens": 720,
    }


def test_firm_counts_the_calls_that_reported_no_reasoning(thrice, capsys):
    # report-only: the reflex answers are counted beside firmness, never resent
    from midwife.pipeline import unthought

    frame, runs = thrice
    assert firm(frame, runs, "Reflex", "--calls", "100", "--json") == 0
    document = json.loads(capsys.readouterr().out)
    kept = load_records(str(runs / "1.jsonl"))
    reflexes = [r for r in kept if r["observation"] == "unclear"]
    assert reflexes and document["unthought"] == unthought(kept)
    assert document["unthought"]["calls"] == 24
    assert document["unthought"]["unthought"] == len(reflexes)
    assert sum(document["unthought"]["trials"].values()) == len(reflexes)


def test_firm_takes_auto_calls_as_the_most_its_runs_can_take(thrice, capsys):
    # --calls auto reserves calls_until_firm: whole runs up to --most, past the kept
    frame, runs = thrice
    assert firm(frame, runs, "RuleReader", "--calls", "auto") == 0
    assert told(capsys)[-1].endswith("; 24 calls made now")
    # a folder already holding --most runs leaves nothing to ask, and none is
    assert firm(frame, runs, "RuleReader", "--calls", "auto", "--most", "1") == 0
    assert told(capsys)[-1].endswith("; 0 calls made now")
    assert [path.name for path in runs.iterdir()] == ["1.jsonl"]


def test_firm_refuses_calls_at_once_a_battery_does_not_take(thrice, capsys):
    # refused before any call, and no run file is made
    frame, runs = thrice
    assert firm(frame, runs, "RuleReader", "--calls", "100", "--parallel", "2") == 2
    refused = "UsageError: battery 'rule-reader' does not take calls at once"
    assert told(capsys, "err")[-1] == refused
    assert list(runs.iterdir()) == []


def test_firm_says_when_its_budget_stops_it_before_the_verdict_is_firm(thrice, capsys):
    frame, runs = thrice
    assert firm(frame, runs, "Wavering", "--calls", "24") == 3
    said = capsys.readouterr()
    assert said.out.splitlines()[-1].startswith("firm: no, ")
    assert said.out.splitlines()[-1].endswith("; 24 calls made now")
    assert said.err.splitlines() == [
        "StoppedWarning: asking stopped after 1 of at most 5 runs, its verdict not yet firm; "
        "the budget covers no further run of 24 calls",
        "raise --calls or --token-budget, and ask again with the same --runs",
    ]


def test_firm_stops_at_the_most_runs_it_reads_and_says_so(thrice, capsys):
    frame, runs = thrice
    assert firm(frame, runs, "Wavering", "--calls", "100", "--most", "2") == 0
    last = told(capsys)[-1]
    assert last.startswith("firm: no, ") and last.endswith(
        ", as many runs as --most reads; 48 calls made now"
    )
    assert sorted(path.name for path in runs.iterdir()) == ["1.jsonl", "2.jsonl"]
    assert firm(frame, runs, "RuleReader", "--calls", "100", "--most", "1") == 2
    assert told(capsys, "err") == [
        f"UsageError: folder {str(runs)!r} keeps 2 runs, more than --most reads",
        "raise --most, or move the earliest runs out",
    ]


def test_firm_says_when_every_call_came_back_as_an_opening(thrice, capsys):
    frame, runs = thrice
    assert firm(frame, runs, "Unreachable", "--calls", "24", "--json") == 1
    document = json.loads(capsys.readouterr().out)
    assert document["exit"] == 1 and document["openings"]
    opening = document["warnings"][0]
    assert opening["type"] == "OpeningWarning" and opening["exit"] == 1
    assert opening["notes"] == ["nothing was read; ask again once it answers"]


def test_firm_names_the_run_a_battery_cut_short_and_never_reads_it_as_firm(thrice, capsys):
    frame, runs = thrice
    assert firm(frame, runs, "Overspending", "--calls", "100") == 3
    lines = told(capsys, "err")
    assert lines[0].startswith("StoppedWarning: the run stopped after 1 of 24 calls; the battery")
    assert (
        lines[1]
        == f"the run cut short is in file {str(runs / '1.jsonl')!r}; move it out of the folder"
    )
    assert firm(frame, runs, "RuleReader", "--calls", "100") == 5
    assert told(capsys, "err") == [
        f"RecordsError: file {str(runs / '1.jsonl')!r} holds 1 of a run's 24 calls",
        "a run cut short is never read as firm; move it out of the folder",
    ]


def test_firm_after_ctrl_c_names_the_run_cut_short(thrice, capsys):
    frame, runs = thrice
    assert firm(frame, runs, "Interrupted", "--calls", "100") == 130
    assert told(capsys, "err") == [
        "KeyboardInterrupt: stopped by Ctrl-C after 2 calls; "
        f"the run cut short is in file {str(runs / '1.jsonl')!r}",
        "a run cut short is never read as firm; move it out of the folder",
    ]
    assert len(load_records(str(runs / "1.jsonl"))) == 2


@pytest.mark.parametrize(
    "reader, said",
    [
        (
            "InterruptedAtOnce",
            ["KeyboardInterrupt: stopped by Ctrl-C after 0 calls, and no record was kept"],
        ),
        (
            "InterruptedBetweenRuns",
            [
                "KeyboardInterrupt: stopped by Ctrl-C after 24 calls; "
                "each run made is whole and kept"
            ],
        ),
    ],
)
def test_firm_after_ctrl_c_says_when_no_run_was_cut_short(thrice, reader, said, capsys):
    frame, runs = thrice
    assert firm(frame, runs, reader, "--calls", "100") == 130
    assert told(capsys, "err") == said
    kept = sorted(path.name for path in runs.iterdir())
    assert kept == ([] if reader == "InterruptedAtOnce" else ["1.jsonl"])


def test_firm_reads_each_input_alike_on_its_own(thrice, capsys):
    frame, runs = thrice
    raw = json.loads(frame.read_text(encoding="utf-8"))
    raw["inputs"].append({**raw["inputs"][0], "id": "again"})
    frame.write_text(json.dumps(raw), encoding="utf-8")
    assert firm(frame, runs, "RuleReader", "--calls", "100") == 0
    assert told(capsys)[-1] == (
        "firm: yes, carried after 1 run, read alike in no-receipt 100%, again 100% of draws; "
        "48 calls made now"
    )


def test_firm_counts_its_calls_in_a_terminal(thrice, capsys, monkeypatch):
    frame, runs = thrice
    monkeypatch.setattr("sys.stderr.isatty", lambda: True)
    assert firm(frame, runs, "RuleReader", "--calls", "100") == 0
    assert capsys.readouterr().err.endswith("\r24 calls made\n")


def test_firm_shows_another_librarys_warning_as_python_would(thrice):
    # run as a person runs it: pytest would take the warning for itself
    frame, runs = thrice
    battery = "tests.fixtures.refund:Warned"
    argv = ["firm", str(frame), "--battery", battery, "--runs", str(runs), "--calls", "100"]
    done = subprocess.run(
        [sys.executable, "-m", "midwife", *argv],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert done.returncode == 0
    assert "UserWarning: a library of the reader's warned" in done.stderr


def test_firm_numbers_a_new_run_after_every_name_a_run_could_hold(thrice, capsys):
    frame, runs = thrice
    (runs / "2.jsonl").mkdir()  # not a run, but its name is taken
    (runs / "notes.txt").write_text("left alone", encoding="utf-8")
    assert firm(frame, runs, "RuleReader", "--calls", "100") == 0
    assert told(capsys)[1] == "run 1: carried, asked now"
    assert sorted(path.name for path in runs.iterdir()) == ["2.jsonl", "3.jsonl", "notes.txt"]


@pytest.mark.skipif(os.name == "nt", reason="Windows takes no folder's write bit from chmod")
def test_firm_refuses_a_runs_folder_it_cannot_write(thrice, capsys):
    frame, runs = thrice
    runs.chmod(0o500)
    try:
        assert firm(frame, runs, "RuleReader", "--calls", "100") == 7
    finally:
        runs.chmod(0o700)
    assert told(capsys, "err") == [
        f"PermissionError: folder {str(runs)!r} cannot be written",
        "choose another --runs",
    ]


@pytest.mark.parametrize(
    "more, said",
    [
        (["--calls", "10"], ["UsageError: a run needs 24 calls; --calls allows 10"]),
        (["--calls", "100", "--firm", "0"], ["UsageError: --firm is a share above 0, up to 1"]),
        (["--calls", "100", "--firm", "nan"], ["UsageError: --firm is a share above 0, up to 1"]),
        (
            ["--calls", "100", "--most", "0"],
            ["UsageError: --most is a whole number of runs, at least 1"],
        ),
    ],
)
def test_firm_refuses_before_any_call_and_makes_no_file(thrice, more, said, capsys):
    frame, runs = thrice
    assert firm(frame, runs, "RuleReader", *more) == 2
    lines = told(capsys, "err")
    assert lines[: len(said)] == said
    assert list(runs.iterdir()) == []


def test_firm_refuses_a_frame_asked_once_a_trial(tmp_path, capsys):
    (tmp_path / "runs").mkdir()
    assert firm(REFUND, tmp_path / "runs", "RuleReader", "--calls", "100") == 2
    assert told(capsys, "err") == [
        "UsageError: frame 'refund-receipt' asks each trial once, "
        "so a run has no calls to draw again",
        "give it a quorum of 2 or more",
    ]


def test_firm_refuses_a_runs_folder_it_cannot_use(thrice, capsys):
    frame, runs = thrice
    missing = runs / "nope"
    assert firm(frame, missing, "RuleReader", "--calls", "100") == 7
    assert told(capsys, "err") == [
        f"FileNotFoundError: folder {str(missing)!r} does not exist",
        "make it, or choose another --runs",
    ]
    assert firm(frame, frame, "RuleReader", "--calls", "100") == 7
    assert told(capsys, "err") == [
        f"NotADirectoryError: {str(frame)!r} is a file, not a folder",
        "--runs names the folder that keeps the frame's runs",
    ]


# ---- gate


def test_gate_reads_a_successors_runs_without_a_call(capsys):
    assert main(["gate", KIRAN, ASKED, "--runs", RUNS]) == 0
    assert told(capsys)[1:] == [
        "runs: 1 read, firm",
        "gate: climbs",
        "category: carried",
        "climbs: 'Kiran reads boy', of kind role",
    ]
    assert main(["gate", KIRAN, DECOY, "--runs", DECOY_RUNS]) == 0
    assert told(capsys)[1:] == [
        "runs: 5 read, not firm",
        "gate: stops",
        "category: coupled but misaligned",
        "open: its verdict was not firm after 5 runs",
    ]


def test_gate_json_is_what_midwife_recoil_gate_returns(capsys):
    before, after = load_frame(KIRAN), load_frame(ASKED)
    runs = [load_records(str(path)) for path in sorted(Path(RUNS).glob("*.jsonl"))]
    asked = until_firm(after, None, Budget(calls=1), kept=runs)
    opened = gate(before, after, asked)
    assert main(["gate", KIRAN, ASKED, "--runs", RUNS, "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "frame": "Kiran",
        "hash": after.hash,
        "of": {"frame": "Kiran", "hash": before.hash},
        "gate": opened.gate,
        "category": opened.category,
        "climbs": [
            {"text": piece.text, "kind": piece.kind, "sha256": piece.sha256}
            for piece in opened.climbs
        ],
        "changed": list(opened.changed),
        "open": opened.open,
        "runs": 1,
        "firm": True,
        "shares": asked.shares,
    }


def test_gate_reads_a_reframing_against_no_category(tmp_path, capsys):
    observe = load_frame(AMANI).raw["observe"]
    labels = [observe["labels"][0], "boys", "mixed", *observe["labels"][1:]]
    reframed = tmp_path / "amani.json"
    argv = ["successor", AMANI, "--hole", "inside", "--from", ASKED, "--decision", "boy"]
    changed = json.dumps({**observe, "labels": labels})
    assert main([*argv, "--set", "observe", changed, "--out", str(reframed)]) == 0
    capsys.readouterr()
    assert main(["gate", AMANI, str(reframed)]) == 0  # nothing to read: no --runs
    assert told(capsys)[1:] == ["gate: reframing", "changed: observe"]


def test_gate_refuses_a_successor_it_has_no_runs_to_read(tmp_path, capsys):
    assert main(["gate", KIRAN, ASKED]) == 2
    assert told(capsys, "err") == [
        "UsageError: a successor that asks the same question is read from its own runs",
        "name the folder that keeps them with --runs; gadfly firm makes them",
    ]
    assert main(["gate", KIRAN, ASKED, "--runs", str(tmp_path)]) == 2
    assert told(capsys, "err") == [
        f"UsageError: folder {str(tmp_path)!r} keeps no run of the successor",
        "gadfly firm asks it, and keeps each run there",
    ]
    missing = tmp_path / "nope"
    assert main(["gate", KIRAN, ASKED, "--runs", str(missing)]) == 7
    assert told(capsys, "err") == [
        f"FileNotFoundError: folder {str(missing)!r} does not exist",
        "name the folder gadfly firm kept the successor's runs in",
    ]
    assert main(["gate", KIRAN, DECOY, "--runs", DECOY_RUNS, "--most", "4"]) == 2
    assert told(capsys, "err")[0] == (
        f"UsageError: folder {DECOY_RUNS!r} keeps 5 runs, more than --most reads"
    )


def test_firm_says_reasoning_reported_with_no_output_count(thrice, capsys):
    # pass 16 R11: the text line says what --json gives
    frame, runs = thrice
    assert firm(frame, runs, "ReasoningAlone", "--calls", "100") == 0
    assert told(capsys)[-1].endswith(
        "; 24 calls made now, 120 reasoning tokens, 0 of 24 calls unthought"
    )
