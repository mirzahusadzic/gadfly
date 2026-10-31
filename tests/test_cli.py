"""The command line, as a person runs it: plan, run, report, portfolio."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from midwife.cli import main

ROOT = Path(__file__).parent.parent
REFUND = str(ROOT / "tests/fixtures/refund.json")


@pytest.fixture(autouse=True)
def at_root(monkeypatch):
    monkeypatch.chdir(ROOT)  # the battery is imported from here


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


def run_refund(tmp_path, *more):
    out = tmp_path / "records.jsonl"
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:RuleReader", "--calls", "8"]
    return main([*argv, "--out", str(out), *more]), out


def test_run_keeps_each_record_and_report_reads_them_back(tmp_path, capsys):
    status, out = run_refund(tmp_path)
    assert status == 0 and capsys.readouterr().out == f"wrote 8/8 calls to {out}\n"
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


def test_run_never_writes_over_kept_records(tmp_path, capsys):
    (tmp_path / "records.jsonl").write_text("")
    status, _ = run_refund(tmp_path)
    assert status == 2 and "never written over" in capsys.readouterr().err


def test_run_says_when_its_calls_came_back_as_openings(tmp_path, capsys):
    # a service that is down answers every call with an opening; the run says
    # so, instead of only counting the calls it wrote
    out = tmp_path / "records.jsonl"
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:Unreachable", "--calls", "8"]
    assert main([*argv, "--out", str(out)]) == 0
    assert capsys.readouterr().out.splitlines()[1] == (
        "openings: 8 of 8 calls, most often "
        '"the reader could not be reached: ConnectionRefused" (8)'
    )
    assert main([*argv, "--out", str(tmp_path / "again.jsonl"), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["openings"] == {
        "the reader could not be reached: ConnectionRefused": 8
    }
    (tmp_path / "fine").mkdir()
    status, _ = run_refund(tmp_path / "fine")
    assert status == 0 and "openings" not in capsys.readouterr().out


def test_run_says_when_the_budget_stopped_it(tmp_path, capsys):
    out = tmp_path / "records.jsonl"
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:RuleReader", "--calls", "3"]
    assert main([*argv, "--out", str(out)]) == 0
    assert capsys.readouterr().out.splitlines()[1] == (
        "stopped: the plan needs 8 calls; the budget allows 3"
    )


def test_a_stopped_run_is_finished_from_its_records(tmp_path, capsys):
    status, first = run_refund(tmp_path, "--only", "baseline")
    rest = tmp_path / "rest.jsonl"
    argv = ["run", REFUND, "--battery", "tests.fixtures.refund:RuleReader", "--calls", "7"]
    assert main([*argv, "--out", str(rest), "--kept", str(first)]) == 0
    assert capsys.readouterr().out.endswith(f"wrote 7/7 calls to {rest}, after 1 kept record\n")
    # the new file is the whole run, so it reports as one
    assert main(["report", REFUND, str(rest)]) == 0
    report = capsys.readouterr().out.splitlines()
    assert report[1:3] == ["records: 8  planned calls: 8", "overall: carried"]


@pytest.mark.parametrize(
    "argv, message",
    [
        (["--battery", "tests.fixtures.refund:NoSuchReader"], "has no NoSuchReader"),
        (["--out", "{tmp}/missing-dir/records.jsonl"], "missing-dir"),
    ],
)
def test_run_refuses_a_bad_battery_or_folder_before_any_call(tmp_path, capsys, argv, message):
    # a refusal is a message and exit 2, before a call is spent
    out = str(tmp_path / "r.jsonl")
    argv = [a.replace("{tmp}", str(tmp_path)) for a in argv]
    argv = ["--battery", "tests.fixtures.refund:Unreachable", "--out", out, *argv]
    assert main(["run", REFUND, "--calls", "8", *argv]) == 2
    err = capsys.readouterr().err
    assert err.startswith("gadfly: ") and message in err and "Traceback" not in err


@pytest.mark.parametrize("document", ["[]", '{"overall": null}', '{"frame": "x"}'])
def test_portfolio_refuses_a_report_that_is_not_one(tmp_path, capsys, document):
    report = tmp_path / "report.json"
    report.write_text(document)
    assert main(["portfolio", str(report)]) == 2
    assert capsys.readouterr().err.startswith("gadfly: ")


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
    summary = json.loads(capsys.readouterr().out)
    assert summary["categories"] == {"carried": 2} and "category" not in summary
    assert summary["by_category"] == {"carried": ["a", "b"]}


@pytest.mark.parametrize(
    "argv, message",
    [
        (["run", REFUND, "--battery", "RuleReader", "--calls", "7", "--out", "x"], "module:Class"),
        (["plan", str(ROOT / "pyproject.toml")], "gadfly: "),
    ],
)
def test_a_refusal_is_a_message_and_status_two(argv, message, capsys):
    assert main(argv) == 2 and message in capsys.readouterr().err


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
    assert main([*argv, "--out", str(out)]) == 2
    assert "asks for the rule-reader battery" in capsys.readouterr().err
    assert not out.exists()
