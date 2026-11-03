"""Recoil from the command line: walk, successor, firm and gate, as a person
or an agent runs them. Each `--json` is what `midwife.recoil`'s function of
the same name returns, and each refusal says what to fix, with its status."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from midwife.cli import load_frame, load_records, main
from midwife.pipeline import situate
from midwife.recoil import found, gate, sha256, successor, until_firm, walk
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
            {"frame": frame.name, "hash": frame.hash, "holes": list(holes)}
            for frame, holes in walked.fits
        ],
        "passed": [{"frame": frame.name, "hash": frame.hash} for frame in walked.passed],
        "frontier": list(walked.frontier),
        "complete": walked.complete,
    }


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


def test_successor_writes_a_new_file_and_never_over_one(tmp_path, capsys):
    out = tmp_path / "kiran.json"
    argv = ["successor", KIRAN, "--hole", "paper", "--from", MIRZA, "--span", "says"]
    assert main([*argv, "--out", str(out)]) == 0
    assert told(capsys)[-1] == f"wrote it to {out}"
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
        [sys.executable, "-m", "midwife", *argv], cwd=ROOT, capture_output=True, text=True
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
