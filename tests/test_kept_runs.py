"""Every example's kept runs: each is its frame's whole plan, and each reads to
the verdict the docs report. No model is called; the records are the ones
Gemma gave through eGemma, kept under examples/runs/."""

import json
import re
from collections import Counter
from pathlib import Path

import pytest

from examples.read import runs_of, verdict
from midwife.cli import load_records
from midwife.pipeline import calls_needed, judge, situate
from midwife.verdict import CARRIED as CAR
from midwife.verdict import COOLED as COO
from midwife.verdict import MISALIGNED as MIS
from midwife.verdict import UNRESOLVED as UNR

EXAMPLES = Path(__file__).parent.parent / "examples"
FRAMES = sorted(EXAMPLES.glob("*.json"))

# Each kept run's category for each input, in the frame's order of inputs, as
# examples/RESULTS.md and docs/examples/ report them: a frame edited after its
# runs refuses them, and a change to the rules that reads them otherwise fails here.
REPORTED: dict[str, list[list[str]]] = {
    "07-sql-rule": [[COO]] * 5,
    "08-clock-rule": [[UNR]] * 5,
    "09-sync-sms": [[COO], [UNR], [COO]],
    "10a-incident-fast": [[UNR, UNR, UNR, UNR], [UNR, COO, MIS, UNR], [UNR, MIS, UNR, UNR]],
    "10b-incident-slow": [[MIS, UNR, MIS, MIS], [MIS, MIS, MIS, MIS], [UNR, MIS, MIS, MIS]],
    "10c-incident-both": [[UNR, UNR, UNR, UNR]] * 3,
    "10c2-incident-both": [[UNR, UNR, COO, COO], [COO, UNR, COO, COO], [COO, COO, COO, UNR]],
    "10d-incident-metrics": [[UNR, UNR, COO, COO], [UNR, COO, COO, UNR], [UNR, COO, COO, MIS]],
    "11-eu-clause": [[UNR]] * 3,
    "12-payroll-access": [[CAR, UNR, COO]] * 3,
    "13-drop-table-section": [[UNR]] * 3,
    "13b-drop-table-reads": [[COO], [UNR], [COO]],
    "14-orders-latency": [
        [CAR, CAR, UNR, CAR, UNR],
        [CAR, UNR, CAR, CAR, UNR],
        [CAR, CAR, UNR, CAR, UNR],
    ],
    "15-invoice-export": [[UNR, UNR, UNR, UNR]] * 3,
    "16-restore-inversion": [[UNR, UNR]] * 3,
    "rung1": [[UNR]] * 5,
    "rung2": [[UNR]] * 5,
    "rung3": [[UNR]] * 5,
    "rung4": [[UNR]] * 5,
    "rung5": [[CAR]] * 5,
    "rung6": [[CAR]] * 5,
    "upgrade": [[CAR]] * 5,
}


@pytest.mark.parametrize("path", FRAMES, ids=lambda p: p.stem)
def test_every_kept_run_is_its_frames_whole_plan(path):
    frame = situate(json.loads(path.read_text(encoding="utf-8")))
    kept = runs_of(path)
    assert len(kept) >= 3, "an example keeps at least three runs"
    for run in kept:
        records = load_records(str(run))
        assert len(records) == calls_needed(frame)
        judge(frame, records)  # refuses a record of another frame or another plan
        assert {r["battery"] for r in records} == {"egemma"}
        assert all(r["served"] for r in records), "every record names what served it"


@pytest.mark.parametrize("stem", sorted(REPORTED))
def test_each_kept_run_reads_as_reported(stem):
    path = EXAMPLES / f"{stem}.json"
    frame = situate(json.loads(path.read_text(encoding="utf-8")))
    read = [[f.category for f in judge(frame, load_records(str(run)))] for run in runs_of(path)]
    assert read == REPORTED[stem]


def test_only_the_restore_rules_approved_case_raises_monotonicity():
    # as docs/reading-a-verdict.md says it, in every run
    raised = Counter()
    for path in FRAMES:
        frame = situate(json.loads(path.read_text(encoding="utf-8")))
        for run in runs_of(path):
            for f in judge(frame, load_records(str(run))):
                if any(o.startswith("monotonicity") for o in f.obligations):
                    raised[path.stem, f.input] += 1
    assert raised == {("16-restore-inversion", "approved"): 3}


def test_every_frame_has_its_reported_verdicts():
    assert sorted(REPORTED) == [p.stem for p in FRAMES]


def test_reading_one_input_back_refuses_an_input_the_frame_lacks():
    # an empty reading would look like an input with nothing to say
    with pytest.raises(SystemExit, match="has no input 'nobody'"):
        verdict(EXAMPLES / "12-payroll-access.json", 1, "nobody")
    assert verdict(EXAMPLES / "12-payroll-access.json", 1, "sam").startswith("sam: unresolved")


def _calls(stem, trials, task=None):
    # every answer given in those trials over all of a frame's kept runs
    counts = Counter()
    for path in sorted((EXAMPLES / "runs" / stem).glob("*.jsonl")):
        for record in load_records(str(path)):
            if record["trial"] in trials and task in (None, record["input"]):
                counts[record["observation"]] += 1
    return counts


def test_the_counts_the_results_quote_are_the_kept_runs():
    # RESULTS and FINDINGS are hand-written claims about kept evidence:
    # each count here is recounted from the records it describes
    results = (EXAMPLES / "RESULTS.md").read_text(encoding="utf-8")
    prose = " ".join(results.split())
    findings = " ".join((EXAMPLES / "FINDINGS.md").read_text(encoding="utf-8").split())
    steady = _calls("09-sync-sms", {"baseline", "repeat", "sham-1", "sham-2", "presentation"})
    assert list(steady) == ["revise"]
    assert f"| baseline, repeat, shams, presentation | revise, all {steady['revise']} |" in results
    both = ("10c-incident-both", "10c2-incident-both", "10d-incident-metrics")
    for task in ("debug", "fix", "optimize", "alert"):
        baseline = sum((_calls(stem, {"baseline"}, task) for stem in both), Counter())
        assert list(baseline) == ["database"]
        assert re.search(rf"^\| {task} \|.*\| database {baseline['database']} \|$", results, re.M)
    cooled = sum(row.count(COO) for row in REPORTED["10c2-incident-both"])
    assert f"cooled on {cooled} of 12 task-runs" in results
    assert f"{cooled} of its 12 task-runs did" in findings
    ordinal = ["first", "second", "third"]
    runs = REPORTED["10d-incident-metrics"]
    fix_odd = next(i for i, run in enumerate(runs) if run[1] != COO)
    alert_cooled = next(i for i, run in enumerate(runs) if run[3] == COO)
    assert f"fix cooled (two runs; the {ordinal[fix_odd]} had no agreed cumulative)" in prose
    assert f"though its {ordinal[alert_cooled]} run agreed on database and read cooled" in prose


def test_the_rung_generator_never_changes_a_kept_frame(tmp_path, monkeypatch):
    # a rung frame with kept runs is never written over; the same frame is left as it is
    from examples import climb

    (tmp_path / "upgrade.json").write_text((EXAMPLES / "upgrade.json").read_text())
    monkeypatch.setattr(climb, "HERE", tmp_path)
    first = climb.rung_frame(1).read_text()
    assert climb.rung_frame(1).read_text() == first  # the same frame: left alone
    (tmp_path / "rung1.json").write_text(first.replace("quill-upgrade-rung-1", "edited"))
    with pytest.raises(SystemExit, match="never changed"):
        climb.rung_frame(1)
    assert "edited" in (tmp_path / "rung1.json").read_text()
