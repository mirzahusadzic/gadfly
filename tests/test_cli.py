"""The command line, as a person runs it: plan, run, report, portfolio."""

import io
import json
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from midwife.cli import main

ROOT = Path(__file__).parent.parent
REFUND = str(ROOT / "tests/fixtures/refund.json")


@pytest.fixture(autouse=True)
def at_root(monkeypatch):
    monkeypatch.chdir(ROOT)  # the battery is imported from here


def test_plan_says_what_each_trial_changes(capsys):
    # cuts, renames and moves, so predictions can be written from the command line
    assert main(["plan", str(ROOT / "examples/upgrade.json")]) == 0
    lines = {line.split()[0]: line for line in capsys.readouterr().out.splitlines()[1:]}
    assert lines["baseline"].endswith("  nothing")
    assert lines["repeat"].endswith("  nothing, asked again")
    assert lines["ablation"].endswith("  cuts removed")
    assert lines["presentation"].endswith(
        "renames backoff to pause, quill to heron, retry_after to wait_hint"
    )
    assert lines["control"].endswith("  cuts removed, use")
    assert main(["plan", REFUND, "--json"]) == 0
    changes = {t["id"]: t["change"] for t in json.loads(capsys.readouterr().out)["trials"]}
    assert changes["ablation"].startswith("cuts ")


def test_plan_says_when_a_control_empties_the_body(tmp_path, capsys):
    raw = json.loads(Path(REFUND).read_text())
    raw["interventions"]["control"] = [span["id"] for span in raw["body"]["spans"]]
    frame = tmp_path / "every.json"
    frame.write_text(json.dumps(raw))
    assert main(["plan", str(frame)]) == 0
    assert capsys.readouterr().out.rstrip().endswith("  cuts every span")


def test_plan_shows_the_trials_and_the_calls_without_spending(capsys):
    assert main(["plan", REFUND]) == 0
    out = capsys.readouterr().out
    assert out.startswith("refund-receipt (") and ": 8 calls" in out.splitlines()[0]
    assert main(["plan", REFUND, "--json"]) == 0
    planned = json.loads(capsys.readouterr().out)
    assert planned["calls"] == 8 and [t["id"] for t in planned["trials"]][:3] == [
        "baseline",
        "repeat",
        "ablation",
    ]


def test_plan_names_what_no_answers_can_give(capsys):
    # found before a call: frame 07 declares no bypass, so it is never carried
    assert main(["plan", str(ROOT / "examples/07-sql-rule.json")]) == 0
    assert capsys.readouterr().out.splitlines()[-2:] == [
        "never carried, whatever the answers: these stay open",
        "  no hidden fallback (no bypass trial was declared)",
    ]
    assert main(["plan", str(ROOT / "examples/upgrade.json")]) == 0
    assert "never" not in capsys.readouterr().out
    assert main(["plan", str(ROOT / "examples/07-sql-rule.json"), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["unreachable"] == {
        "carried": ["no hidden fallback (no bypass trial was declared)"]
    }


def test_plan_says_an_excluded_frame_is_never_carried_or_cooled(tmp_path, capsys):
    frame = json.loads(Path(REFUND).read_text())
    frame["outsideScope"] = "refunds above the agent's limit"
    path = tmp_path / "frame.json"
    path.write_text(json.dumps(frame))
    assert main(["plan", str(path)]) == 0
    assert capsys.readouterr().out.splitlines()[-4:] == [
        "never carried, whatever the answers",
        "  declared outside scope (refunds above the agent's limit)",
        "never cooled, whatever the answers",
        "  declared outside scope (refunds above the agent's limit)",
    ]


def test_plan_says_when_the_answers_are_too_many_to_read(tmp_path, capsys):
    raw = json.loads(Path(REFUND).read_text())
    raw["observe"]["labels"] += [f"other-{n}" for n in range(9)]
    frame = tmp_path / "many.json"
    frame.write_text(json.dumps(raw))
    assert main(["plan", str(frame)]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == (
        "too many answers to read which categories it can reach"
    )


def run_refund(tmp_path, *more):
    out = tmp_path / "records.jsonl"
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:RuleReader", "--calls", "8"]
    return main([*argv, "--out", str(out), *more]), out


def test_run_keeps_each_record_and_report_reads_them_back(tmp_path, capsys):
    status, out = run_refund(tmp_path)
    assert status == 0 and capsys.readouterr().out == (
        f"wrote 8/8 calls to {out}\nto read the verdict: gadfly report {REFUND} {out}\n"
    )
    assert len(out.read_text().splitlines()) == 8
    assert main(["report", REFUND, str(out)]) == 0
    report = capsys.readouterr().out.splitlines()
    assert report[2] == "overall: carried"
    assert (
        "  evidence: ablation moved it decline -> grant; held under presentation, 2 shams" in report
    )
    assert not [line for line in report if "obligation:" in line]  # every check passed
    assert main(["report", REFUND, str(out), "--json"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["overall"]["category"] == "carried"
    assert document["findings"][0]["levels"]["ablation"] == "grant"


def test_out_dash_streams_the_records_and_report_reads_them_back(capsys, monkeypatch):
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:RuleReader", "--calls", "8"]
    assert main([*argv, "--out", "-"]) == 0
    told = capsys.readouterr()
    assert [json.loads(line)["trial"] for line in told.out.splitlines()][:2] == [
        "baseline",
        "repeat",
    ]
    assert told.err == (  # the records own standard output: the rest is a message
        "wrote 8/8 calls to standard output\n"
        f"to read the verdict: pipe them to gadfly report {REFUND} -\n"
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(told.out))
    assert main(["report", REFUND, "-"]) == 0
    assert "overall: carried" in capsys.readouterr().out


class Terminal(io.StringIO):
    """Standard input that is a terminal: nothing piped in."""

    def isatty(self):
        return True


def test_dash_at_a_terminal_is_refused_not_waited_on(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", Terminal())
    assert main(["report", REFUND, "-"]) == 2
    assert "standard input, which is a terminal" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("command", "name", "text", "said", "status"),
    [
        (
            "plan",
            "frame.json",
            '{"name":\n',
            "FrameError: file 'frame.json' is not JSON at line 2",
            4,
        ),
        (
            "check-frame",
            "frame.json",
            "[1,",
            "FrameError: file 'frame.json' is not JSON at line 1",
            4,
        ),
        ("report", "records.jsonl", "{}\nnot json\n", "RecordsError: file 'records.jsonl' is", 5),
        (
            "portfolio",
            "report.json",
            "{",
            "RecordsError: file 'report.json' is not JSON at line 1",
            5,
        ),
    ],
)
def test_a_file_that_is_not_json_is_named_with_its_line(
    tmp_path, capsys, monkeypatch, command, name, text, said, status
):
    monkeypatch.chdir(tmp_path)  # so the message names the file as given
    Path(name).write_text(text)
    argv = [command, REFUND, name] if command == "report" else [command, name]
    assert main(argv) == status
    assert capsys.readouterr().err.startswith(said)


@pytest.mark.parametrize("command", ["check-frame", "plan"])
def test_a_frame_may_come_from_standard_input(capsys, monkeypatch, command):
    monkeypatch.setattr("sys.stdin", io.StringIO(Path(REFUND).read_text()))
    assert main([command, "-"]) == 0
    assert "refund-receipt" in capsys.readouterr().out


def test_standard_input_is_read_once(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(Path(REFUND).read_text()))
    assert main(["report", "-", "-"]) == 2
    assert "standard input is read once" in capsys.readouterr().err


def test_out_dash_and_json_are_refused_together(capsys):
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:RuleReader", "--calls", "8"]
    assert main([*argv, "--out", "-", "--json"]) == 2
    told = capsys.readouterr()
    assert told.out == "" and "both print to standard output" in told.err


def test_run_never_writes_over_kept_records(tmp_path, capsys):
    (tmp_path / "records.jsonl").write_text("")
    status, _ = run_refund(tmp_path)
    assert status == 7 and capsys.readouterr().err.startswith("FileExistsError: ")


def test_run_says_when_its_calls_came_back_as_openings(tmp_path, capsys):
    # a service that is down answers every call with an opening; the run says
    # so, instead of only counting the calls it wrote
    out = tmp_path / "records.jsonl"
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:Unreachable", "--calls", "8"]
    assert main([*argv, "--out", str(out)]) == 1  # every call opened: nothing was read
    assert capsys.readouterr().err.splitlines() == [
        "OpeningWarning: 8 of 8 calls came back as openings, most often "
        "'the reader could not be reached (ConnectionRefused)' (8 times)",
        "nothing was read; run again into a new file once it answers",
    ]
    assert main([*argv, "--out", str(tmp_path / "again.jsonl"), "--json"]) == 1
    told = capsys.readouterr()
    assert json.loads(told.out)["openings"] == {
        "the reader could not be reached (ConnectionRefused)": 8
    }
    warning = json.loads(told.err)["warning"]
    assert (warning["type"], warning["exit"]) == ("OpeningWarning", 1)
    assert warning["help"].endswith("troubleshooting#openingwarning")
    (tmp_path / "fine").mkdir()
    status, _ = run_refund(tmp_path / "fine")
    assert status == 0 and "openings" not in capsys.readouterr().out


def test_a_budget_below_the_plan_is_a_refusal(tmp_path, capsys):
    # nothing was spent and no file made: a refusal, not a run
    out = tmp_path / "records.jsonl"
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:RuleReader", "--calls", "3"]
    assert main([*argv, "--out", str(out)]) == 2
    captured = capsys.readouterr()
    assert captured.err.splitlines() == [
        "UsageError: the plan needs 8 calls; the budget allows 3",
        "gadfly plan shows the calls a whole run needs",
    ]
    assert captured.out == "" and not out.exists()


def test_a_run_its_budget_cuts_short_exits_with_3(tmp_path, capsys):
    out = tmp_path / "records.jsonl"
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:RuleReader", "--calls", "8"]
    budget = ["--output-tokens", "10", "--token-budget", "30"]
    assert main([*argv, *budget, "--out", str(out)]) == 3  # the records are partial
    told = capsys.readouterr()
    assert "wrote 3/8 calls" in told.out and told.err.splitlines() == [
        "StoppedWarning: the run stopped after 3 of 8 calls; the token budget (30) is spent",
        f"finish with --kept {str(out)!r} and a new --out",
    ]
    assert len(out.read_text().splitlines()) == 3


@pytest.mark.parametrize("name", ["-o", "--output"])
def test_the_records_file_takes_the_usual_names_too(tmp_path, capsys, name):
    out = tmp_path / "records.jsonl"
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:RuleReader", "--calls", "8"]
    assert main([*argv, name, str(out)]) == 0
    assert len(out.read_text().splitlines()) == 8


def test_a_flag_is_named_in_full(tmp_path, capsys):
    # a shortened flag would change meaning the day a longer one is added
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:RuleReader", "--calls", "8"]
    assert main([*argv, "--out", str(tmp_path / "records.jsonl"), "--stop"]) == 2
    assert capsys.readouterr().err.splitlines() == [
        "UsageError: unrecognized arguments --stop",
        "gadfly run --help shows its arguments",
    ]


def test_a_stopped_run_is_finished_from_its_records(tmp_path, capsys):
    status, first = run_refund(tmp_path, "--only", "baseline")
    rest = tmp_path / "rest.jsonl"
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:RuleReader", "--calls", "7"]
    assert main([*argv, "--out", str(rest), "--kept", str(first)]) == 0
    assert f"wrote 7/7 calls to {rest}, after 1 kept record\n" in capsys.readouterr().out
    # the new file is the whole run, so it reports as one
    assert main(["report", REFUND, str(rest)]) == 0
    report = capsys.readouterr().out.splitlines()
    assert report[1:3] == ["records: 8 of 8 planned calls", "overall: carried"]


@pytest.mark.parametrize(
    "argv, said, status",
    [
        (["--battery", "tests.fixtures.refund:NoSuchReader"], "BatteryError: ", 6),
        (["--out", "{tmp}/missing-dir/records.jsonl"], "FileNotFoundError: ", 7),
    ],
)
def test_run_refuses_a_bad_battery_or_folder_before_any_call(tmp_path, capsys, argv, said, status):
    # a refusal is its class and its status, before a call is spent
    out = str(tmp_path / "r.jsonl")
    argv = [a.replace("{tmp}", str(tmp_path)) for a in argv]
    argv = ["--battery", "tests.fixtures.refund:Unreachable", "--out", out, *argv]
    assert main(["run", REFUND, "--calls", "8", *argv]) == status
    err = capsys.readouterr().err
    assert err.startswith(said) and "Traceback" not in err


@pytest.mark.parametrize(
    "document",
    [
        "[]",
        '{"overall": null}',
        '{"frame": "x"}',
        '{"frame": "a", "overall": {"category": "carried", "inputs": []}}',
        '{"frame": "a", "overall": {"category": "carried", "evidence": "x"}}',
        '{"frame": "a", "overall": {"category": "carried", "obligations": [3]}}',
        '{"frame": 3, "overall": {"category": "carried"}}',
        '{"frame": "a", "overall": {"category": "great"}}',
        '{"frame": "a", "overall": {"category": "carried", "inputs": {"x": "excellent"}}}',
    ],
)
def test_portfolio_refuses_a_report_that_is_not_one(tmp_path, capsys, document):
    report = tmp_path / "report.json"
    report.write_text(document)
    assert main(["portfolio", str(report)]) == 5
    assert capsys.readouterr().err.startswith("RecordsError: ")


def test_portfolio_counts_categories_and_never_names_one(tmp_path, capsys):
    _, out = run_refund(tmp_path)
    capsys.readouterr()
    reports = []
    for name in ("a", "b"):
        assert main(["report", REFUND, str(out), "--json"]) == 0
        document = json.loads(capsys.readouterr().out)
        document["frame"] = name
        reports.append(tmp_path / f"{name}.json")
        reports[-1].write_text(json.dumps(document))
    assert main(["portfolio", *map(str, reports)]) == 0
    assert capsys.readouterr().out.splitlines()[:2] == ["2 frames", "carried: a, b"]
    assert main(["portfolio", *map(str, reports), "--json"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["categories"] == {"carried": 2} and "category" not in summary
    assert summary["by_category"] == {"carried": ["a", "b"]}


@pytest.mark.parametrize(
    "argv, said, status",
    [
        (["run", REFUND, "--battery", "RuleReader", "--calls", "7", "--out", "x"], "UsageError", 2),
        (["plan", str(ROOT / "pyproject.toml")], "FrameError", 4),
        (
            ["plan", "no-such-frame.json"],
            "FileNotFoundError: file 'no-such-frame.json' does not exist",
            7,
        ),
    ],
)
def test_a_refusal_is_its_class_its_message_and_its_status(argv, said, status, capsys):
    assert main(argv) == status and capsys.readouterr().err.startswith(said)


def test_with_json_a_refusal_is_one_object_on_standard_error(capsys):
    assert main(["plan", "no-such-frame.json", "--json"]) == 7
    told = capsys.readouterr()
    assert told.out == "" and json.loads(told.err) == {
        "error": {
            "type": "FileNotFoundError",
            "exit": 7,
            "message": "file 'no-such-frame.json' does not exist",
            "notes": [],
            "help": "https://mirzahusadzic.github.io/gadfly/troubleshooting#file-errors",
        }
    }


def test_a_bug_prints_its_traceback_and_exits_with_70(capsys, monkeypatch):
    def broken(args):
        return 1 / 0

    monkeypatch.setattr("midwife.cli.command_plan", broken)
    assert main(["plan", REFUND]) == 70
    assert "Traceback" in capsys.readouterr().err


def test_python_m_midwife_is_the_command_line():
    done = subprocess.run(
        [sys.executable, "-m", "midwife", "plan", REFUND],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=60,
    )
    assert done.returncode == 0 and ": 8 calls" in done.stdout


def test_a_portfolio_refuses_no_frames_and_twice_named_ones_and_shows_disagreements():
    from midwife.portfolio import Entry, summarize

    with pytest.raises(ValueError, match="at least one frame"):
        summarize([])
    one = Entry("a", "h", "carried", {"x1": "carried"})
    with pytest.raises(ValueError, match="unique"):
        summarize([one, one])
    split = Entry("b", "h2", "unresolved", {"x1": "carried", "x2": "cooled"}, [], ["open: f"])
    other = Entry("c", "h3", "unresolved", {"x1": "unresolved"}, [], ["open: f", "open: g"])
    summary = summarize([one, split, other])
    assert summary["input_disagreements"] == {"b": split.inputs}
    assert summary["shared_obligations"] == {"open: f": ["b", "c"]}  # g is c's alone


def test_a_refused_run_writes_no_records_file(tmp_path, capsys):
    # the frame names the rule reader: another battery is refused before a call
    out = tmp_path / "records.jsonl"
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:PhraseMatcher", "--calls", "7"]
    assert main([*argv, "--out", str(out)]) == 6
    assert "BatteryError: this frame asks for battery 'rule-reader'" in capsys.readouterr().err
    assert not out.exists()


def test_the_command_line_says_what_it_is_and_how_to_use_it(capsys):
    # clig.dev: a version, help when there is no command, examples and the docs
    with pytest.raises(SystemExit) as shown:
        main(["--version"])
    assert shown.value.code == 0 and capsys.readouterr().out.startswith("gadfly 0.")
    assert main([]) == 0
    usage = capsys.readouterr().out
    assert "examples:" in usage and "https://mirzahusadzic.github.io/gadfly/" in usage


def test_ctrl_c_keeps_what_was_made_and_says_how_to_finish(tmp_path, capsys):
    out = tmp_path / "records.jsonl"
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:Interrupted", "--calls", "8"]
    assert main([*argv, "--out", str(out)]) == 130
    err = capsys.readouterr().err
    assert err.startswith("KeyboardInterrupt: stopped by Ctrl-C after 2 calls")
    assert f"finish with --kept '{out}'" in err
    assert "Traceback" not in err and len(out.read_text().splitlines()) == 2


def test_ctrl_c_with_out_dash_says_where_the_records_went(capsys):
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:Interrupted", "--calls", "8"]
    assert main([*argv, "--out", "-"]) == 130
    told = capsys.readouterr()
    assert len(told.out.splitlines()) == 2 and "they went to standard output" in told.err


def test_a_garbled_reply_still_writes_every_record(tmp_path):
    out = tmp_path / "records.jsonl"
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:Garbled", "--calls", "8"]
    assert main([*argv, "--out", str(out)]) == 0
    assert len(out.read_text(encoding="utf-8").splitlines()) == 8


def test_a_resume_with_nothing_left_still_writes_the_whole_run(tmp_path, capsys):
    status, first = run_refund(tmp_path)
    rest = tmp_path / "rest.jsonl"
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:RuleReader", "--calls", "8"]
    assert main([*argv, "--out", str(rest), "--kept", str(first)]) == 0
    assert "after 8 kept records" in capsys.readouterr().out
    assert rest.read_text() == first.read_text()


def test_an_unwritable_folder_is_refused_before_any_call(tmp_path, capsys):
    from tests.fixtures.refund import Counted

    folder = tmp_path / "read-only"
    folder.mkdir()
    folder.chmod(0o555)
    try:
        Counted.calls = 0
        argv = ["run", REFUND, "--battery", "tests.fixtures.refund:Counted", "--calls", "8"]
        assert main([*argv, "--out", str(folder / "records.jsonl")]) == 7
    finally:
        folder.chmod(0o755)
    assert Counted.calls == 0 and "read-only" in capsys.readouterr().err


def test_a_battery_that_is_not_one_is_refused(tmp_path, capsys):
    argv = ["run", REFUND, "--battery", "midwife.frame:parse", "--calls", "8"]
    assert main([*argv, "--out", str(tmp_path / "r.jsonl")]) == 6
    assert "is not a battery" in capsys.readouterr().err


def test_a_kept_record_no_file_can_hold_is_refused_before_a_call(tmp_path, capsys):
    # valid JSON, but its escaped lone surrogate cannot be written back: found
    # out before the first new call, not after it is spent (pass 4, R08)
    status, first = run_refund(tmp_path, "--only", "baseline")
    assert status == 0
    row = json.loads(first.read_text().splitlines()[0])
    row["raw"] = "\ud800"
    kept = tmp_path / "kept.jsonl"
    kept.write_text(json.dumps(row) + "\n")  # ascii: the surrogate stays escaped
    out = tmp_path / "rest.jsonl"
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:RuleReader", "--calls", "8"]
    capsys.readouterr()
    assert main([*argv, "--kept", str(kept), "--out", str(out)]) == 5
    assert "holds a lone surrogate" in capsys.readouterr().err
    assert not out.exists()


def test_report_and_plan_print_one_colon_to_a_line(capsys):
    # the label's colon, and no other: over every kept example run
    seen = 0
    for path in sorted((ROOT / "examples").glob("*.json")):
        for records in sorted((ROOT / "examples/runs" / path.stem).glob("*.jsonl")):
            for argv in (["report", str(path), str(records)], ["plan", str(path)]):
                assert main(argv) == 0
                lines = capsys.readouterr().out.splitlines()
                seen += len(lines)
                assert [line for line in lines if line.count(": ") > 1] == [], argv
    assert seen > 1000


@pytest.mark.parametrize(
    ("command", "text", "said", "status"),
    [
        ("plan", '{"n": ' + "9" * 5000 + "}", "FrameError: file 'in.json' holds a number", 4),
        ("plan", "[" * 100_000 + "]" * 100_000, "FrameError: file 'in.json' nests", 4),
        ("report", '{"n": ' + "9" * 5000 + "}\n", "RecordsError: file 'in.json' holds a number", 5),
        ("portfolio", "[" * 100_000 + "]" * 100_000, "RecordsError: file 'in.json' nests", 5),
    ],
)
def test_json_python_cannot_read_is_a_refusal_not_a_bug(
    tmp_path, capsys, monkeypatch, command, text, said, status
):
    monkeypatch.chdir(tmp_path)
    Path("in.json").write_text(text)
    argv = [command, REFUND, "in.json"] if command == "report" else [command, "in.json"]
    assert main(argv) == status
    err = capsys.readouterr().err
    assert err.startswith(said) and "Traceback" not in err


def test_a_link_where_the_records_would_go_is_refused_before_a_call(tmp_path, capsys):
    from tests.fixtures.refund import Counted

    out = tmp_path / "records.jsonl"
    out.symlink_to(tmp_path / "nowhere.jsonl")  # a link to nothing: exists() says no
    Counted.calls = 0
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:Counted", "--calls", "8"]
    assert main([*argv, "--out", str(out)]) == 7
    assert Counted.calls == 0 and capsys.readouterr().err.startswith("FileExistsError: ")


@pytest.mark.parametrize(
    "source",
    [
        "raise ValueError('no setting for the evaluator')\n",
        "class Reader:\n    def __init__(self):\n"
        "        raise ValueError('no setting for the evaluator')\n",
    ],
)
def test_a_battery_that_refuses_to_be_made_is_a_battery_error(
    tmp_path, capsys, monkeypatch, source
):
    # the protocol's refusal is a ValueError: on import and when made, as in check
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    Path("refusing_battery.py").write_text(source)
    argv = [
        "run",
        REFUND,
        "--battery",
        "refusing_battery:Reader",
        "--calls",
        "8",
        "--out",
        "r.jsonl",
    ]
    assert main(argv) == 6
    assert capsys.readouterr().err.splitlines() == [
        "BatteryError: battery 'refusing_battery:Reader' could not be made",
        "it said 'no setting for the evaluator'",
    ]
    sys.modules.pop("refusing_battery", None)


def test_a_file_named_json_after_the_options_is_a_file(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)  # no file named --json here
    assert main(["plan", "--", "--json"]) == 7
    assert capsys.readouterr().err.startswith("FileNotFoundError: file '--json' does not exist")


def test_standard_input_that_is_not_utf8_says_so(capsys, monkeypatch):
    # as a terminal's or a pipe's stdin is opened: bad bytes would pass as surrogates
    piped = io.TextIOWrapper(io.BytesIO(b'{"name": "\xff"}'), "utf-8", "surrogateescape")
    monkeypatch.setattr("sys.stdin", piped)
    assert main(["plan", "-"]) == 4
    assert capsys.readouterr().err == "FrameError: standard input is not UTF-8 text\n"


def test_a_second_ctrl_c_stops_at_once_though_a_call_hangs(tmp_path):
    # a call hung in its thread cannot be stopped; the command does not wait for it
    out = tmp_path / "records.jsonl"
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:Stuck", "--calls", "8"]
    child = subprocess.Popen(
        [sys.executable, "-m", "midwife", *argv, "--parallel", "2", "--out", str(out)],
        cwd=ROOT,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 10
        while (
            time.monotonic() < deadline
            and len(out.read_text().splitlines() if out.exists() else []) < 2
        ):
            time.sleep(0.05)  # the two calls that answer are kept; the next two hang
        time.sleep(0.3)
        child.send_signal(signal.SIGINT)
        time.sleep(0.3)
        child.send_signal(signal.SIGINT)
        status = child.wait(timeout=3)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
    assert status == 130
    assert child.stderr.read().startswith("KeyboardInterrupt: stopped by Ctrl-C after 2 calls")
    assert len(out.read_text().splitlines()) == 2


def test_a_reader_that_stops_reading_ends_the_command_quietly():
    # as `gadfly run ... --out - | head -1`: as Unix tools do, SIGPIPE ends it
    # at once, with no message, rather than a Python warning and status 120
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:Slow", "--calls", "8"]
    child = subprocess.Popen(
        [sys.executable, "-m", "midwife", *argv, "--out", "-"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        assert json.loads(child.stdout.readline())["trial"] == "baseline"
        child.stdout.close()  # the reader is gone; the next record has nowhere to go
        status = child.wait(timeout=10)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
    assert status == -signal.SIGPIPE and child.stderr.read() == b""


def test_a_battery_s_own_ctrl_c_at_once_ends_the_command_as_one(tmp_path, capsys, monkeypatch):
    # its call has ended, so nothing is left running: no exit past the caller
    import os

    monkeypatch.setattr(os, "_exit", lambda status: pytest.fail(f"os._exit({status})"))
    out = tmp_path / "records.jsonl"
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:InterruptingAtOnce", "--calls", "8"]
    assert main([*argv, "--parallel", "2", "--out", str(out)]) == 130
    err = capsys.readouterr().err
    assert err.startswith("KeyboardInterrupt: stopped by Ctrl-C") and "unanswered" not in err


def test_text_standard_input_holding_surrogates_is_not_utf8(capsys, monkeypatch):
    # a caller's own text stream, no bytes beneath it, read as standard input is
    bad = b'{"name": "\xff"}'.decode("utf-8", "surrogateescape")
    monkeypatch.setattr("sys.stdin", io.StringIO(bad))
    assert main(["plan", "-"]) == 4
    assert capsys.readouterr().err == "FrameError: standard input is not UTF-8 text\n"


@pytest.mark.parametrize(
    ("place", "said"),
    [
        ("blocker/records.jsonl", "NotADirectoryError: path 'blocker/records.jsonl' runs through"),
        ("folder", "IsADirectoryError: 'folder' is a folder, not a file"),
    ],
)
def test_out_through_a_file_or_at_a_folder_says_which(tmp_path, capsys, monkeypatch, place, said):
    monkeypatch.chdir(tmp_path)
    Path("blocker").write_text("")
    Path("folder").mkdir()
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:RuleReader", "--calls", "8"]
    assert main([*argv, "--out", place]) == 7
    assert capsys.readouterr().err.startswith(said)


@pytest.mark.parametrize(
    ("source", "said"),
    [
        ("import no_such_module_anywhere\n", "BatteryError: module 'refusing_import' could not"),
        (
            "class Reader:\n    def __init__(self):\n        import no_such_module_anywhere\n",
            "BatteryError: battery 'refusing_import:Reader' could not be made",
        ),
    ],
)
def test_a_battery_that_lacks_a_module_is_a_battery_error(
    tmp_path, capsys, monkeypatch, source, said
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    Path("refusing_import.py").write_text(source)
    argv = [
        "run",
        REFUND,
        "--battery",
        "refusing_import:Reader",
        "--calls",
        "8",
        "--out",
        "r.jsonl",
    ]
    assert main(argv) == 6
    lines = capsys.readouterr().err.splitlines()
    assert (
        lines[0].startswith(said)
        and lines[1] == "it said \"No module named 'no_such_module_anywhere'\""
    )
    sys.modules.pop("refusing_import", None)


def test_a_battery_that_exits_is_a_bug_not_a_success(tmp_path, capsys):
    out = tmp_path / "records.jsonl"
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:Exiting", "--calls", "8"]
    assert main([*argv, "--out", str(out)]) == 70
    assert "SystemExit" in capsys.readouterr().err


def test_records_holding_line_separators_are_read_back(tmp_path, capsys):
    out = tmp_path / "records.jsonl"
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:Separated", "--calls", "8"]
    assert main([*argv, "--out", str(out)]) == 0
    assert main(["report", REFUND, str(out)]) == 0
    assert "records: 8 of 8 planned calls" in capsys.readouterr().out
