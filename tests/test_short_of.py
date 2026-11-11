"""Asked for one category only, a run stops once no answer left could make
the frame read it, and asking until firm ends once no firm reading of it is
left to reach; a run that goes on reads as a whole run does, and one cut
short was never going to read the category."""

import json
import random
from collections import Counter
from pathlib import Path

import pytest

from midwife.cli import main
from midwife.errors import UsageError
from midwife.pipeline import calls_needed, judge, overall, run, situate
from midwife.recoil import ANY, until_firm
from midwife.types import Budget, Observation
from midwife.verdict import CARRIED, COOLED, out_of_reach

ROOT = Path(__file__).parent.parent
REFUND = ROOT / "tests" / "fixtures" / "refund.json"


class Reader:
    """Answers each prompt from `answer(prompt, n)`, n counting that prompt's
    calls, so two runs asking the same calls get the same answers."""

    name = "rules"

    def __init__(self, answer):
        self.answer, self.asked = answer, Counter()

    def check(self, frame):
        pass

    def observe(self, frame, prompt, max_output_tokens):
        self.asked[prompt] += 1
        return Observation(label=self.answer(prompt, self.asked[prompt]), usage={})


def reads(prompt, n):
    """The rule read in either wording, and its reversal read as a grant."""
    if "never requires a receipt" in prompt:
        return "grant"
    return "decline" if "requires a receipt" in prompt or "proof of purchase" in prompt else "grant"


def never(prompt, n):
    return "decline"


def wavers(prompt, n):
    """Declines, but for each prompt's third call: no trial moves, and no run is firm."""
    return "grant" if n == 3 else "decline"


class Never(Reader):
    """A reader that declines whatever it is shown, under the fixture's name."""

    name = "rule-reader"

    def __init__(self):
        super().__init__(never)


@pytest.fixture
def raw(raw):
    raw["battery"] = {"kind": "rules"}
    raw["interventions"]["inversion"] = {"requires a receipt": "never requires a receipt"}
    raw["allowed"]["inversion"] = ["grant"]
    return raw


def both(frame, answer, category=CARRIED, **asked):
    budget = Budget(calls=calls_needed(frame))
    whole = run(frame, Reader(answer), budget)
    short = run(frame, Reader(answer), budget, short_of=category, **asked)
    return whole, short


def noisy(seed):
    # mostly the reader that reads, with answers of any label mixed in, splits included
    noise = random.Random(seed).choice([0.0, 0.05, 0.15, 0.4, 1.0])

    def answer(prompt, n):
        pick = random.Random(f"{seed}/{prompt}/{n}")
        if pick.random() < noise:
            return pick.choice(("grant", "decline", "unclear"))
        return reads(prompt, n)

    return answer


def test_a_reader_that_never_moves_is_asked_no_more_once_carried_is_out_of_reach(raw):
    frame = situate(raw)
    whole, short = both(frame, never)
    # the inversion is asked first, and its second answer fixes it where it may not
    # stay: its third call and every trial after it are left
    assert list(dict.fromkeys(r.trial for r in short.records)) == [
        "baseline",
        "repeat",
        "inversion",
    ]
    assert short.stopped is None and len(short.records) == 2 * frame.quorum + frame.agree
    assert len(short.records) + short.short == len(whole.records)
    assert overall(judge(frame, whole.records)).category != CARRIED


def test_a_reader_that_reads_is_asked_everything_and_reads_as_a_whole_run(raw):
    frame = situate(raw)
    whole, short = both(frame, reads)
    assert short.short == 0 and len(short.records) == calls_needed(frame)
    [finding], [read] = judge(frame, short.records), judge(frame, whole.records)
    assert finding.as_dict() == read.as_dict() and read.category == CARRIED


@pytest.mark.parametrize("carriage", ["listed", "all-checks"])
@pytest.mark.parametrize("category", [CARRIED, COOLED])
@pytest.mark.parametrize("seed", range(80))
def test_a_run_cut_short_was_never_going_to_read_the_category(raw, seed, category, carriage):
    # random answers, splits included, on two inputs and two anchors: a run is cut
    # short only when the whole run does not read the category, and one that goes on
    # reads every input as the whole run does
    raw["carriage"] = carriage
    raw["inputs"].append({"id": "x2", "text": "A customer with a receipt asks on day 40."})
    if seed % 2:
        raw["interventions"]["control"] = ["r1", "r2", "r3", "r4"]
    frame = situate(raw)
    whole, short = both(frame, noisy(seed), category)
    read = judge(frame, whole.records)
    if short.short:
        assert overall(read).category != category
        assert len(short.records) + short.short == len(whole.records)
    else:
        assert [f.as_dict() for f in judge(frame, short.records)] == [f.as_dict() for f in read]


def test_some_random_runs_are_cut_short_and_some_read_the_category(raw):
    # the property above is not vacuous: over its seeds runs are cut short, and
    # others go on and read carried
    frame = situate(raw)
    cut = carried = 0
    for seed in range(80):
        whole, short = both(frame, noisy(seed))
        cut += bool(short.short)
        carried += overall(judge(frame, whole.records)).category == CARRIED
    assert cut > 10 and carried > 10


def test_calls_at_once_are_cut_short_too(raw):
    class AtOnce(Reader):
        concurrent = True

    frame = situate(raw)
    budget = Budget(calls=calls_needed(frame))
    for parallel in (2, 4, 7, 24):
        short = run(frame, AtOnce(never), budget, short_of=CARRIED, parallel=parallel)
        # the trials after the ruling ones wait for them, however many calls go at once
        assert {r.trial for r in short.records} == {"baseline", "repeat", "inversion"}, parallel
        assert len(short.records) + short.short == calls_needed(frame)
    whole = run(frame, AtOnce(reads), budget, parallel=7)
    short = run(frame, AtOnce(reads), budget, short_of=CARRIED, parallel=7)
    assert short.short == 0 and len(short.records) == calls_needed(frame)
    assert judge(frame, short.records)[0].as_dict() == judge(frame, whole.records)[0].as_dict()


def test_out_of_reach_reads_only_what_is_fixed(raw):
    frame = situate(raw)
    x = frame.inputs[0]["id"]
    assert not out_of_reach(frame, x, {}, CARRIED)
    held = {"baseline": ["decline"] * 3, "repeat": ["decline"] * 3, "inversion": ["decline"] * 3}
    assert out_of_reach(frame, x, held, CARRIED)
    assert not out_of_reach(frame, x, {**held, "inversion": ["grant"] * 3}, CARRIED)


def test_a_category_that_cannot_be_stopped_short_of_is_refused(raw):
    frame = situate(raw)
    budget = Budget(calls=calls_needed(frame))
    for short_of in ("unresolved", ANY):  # a single run has no run before it to read as
        with pytest.raises(UsageError, match="short_of is carried or cooled, not"):
            run(frame, Reader(reads), budget, short_of=short_of)
    with pytest.raises(UsageError, match="short_of is carried, cooled or any, not 'unresolved'"):
        until_firm(frame, Reader(reads), budget, short_of="unresolved")


# ---- asked until firm


def firmly(frame, answer, runs=1, **asked):
    each = calls_needed(frame)
    return until_firm(frame, Reader(answer), Budget(calls=each * runs), **asked), each


def test_until_firm_ends_with_the_run_that_cannot_read_the_category(raw):
    frame = situate(raw)
    asked, each = firmly(frame, never, most=1, short_of=CARRIED)
    assert not asked.firm and asked.short == CARRIED and asked.stopped is None
    assert asked.made == 2 * frame.quorum + frame.agree < each
    assert asked.findings == () and asked.category is None  # a run cut short is never read


def test_until_firm_reads_a_frame_that_carries_as_it_does_unasked(raw):
    frame = situate(raw)
    plain, each = firmly(frame, reads, most=1)
    asked, _ = firmly(frame, reads, most=1, short_of=CARRIED)
    assert asked.firm and asked.short is None and asked.made == each
    assert (asked.category, asked.shares, asked.findings) == (
        plain.category,
        plain.shares,
        plain.findings,
    )


def test_until_firm_cuts_no_run_short_while_a_firm_reading_is_two_runs_away(raw):
    # three runs allowed: after a first run that does not carry, two that do are firm,
    # so the first is asked whole; the second then leaves none, and is cut short
    frame = situate(raw)
    asked, each = firmly(frame, wavers, runs=3, most=3, short_of=CARRIED)
    assert [len(records) for records in asked.runs] == [each, 2 * frame.quorum + frame.agree]
    assert not asked.firm and asked.short == CARRIED
    assert asked.findings and asked.category != CARRIED  # the whole run's, the first


def test_a_whole_run_that_is_firm_on_another_category_is_still_read_so(raw):
    # three runs allowed, so the first is whole: firm where it is, it is the verdict
    frame = situate(raw)
    asked, each = firmly(frame, never, runs=3, most=3, short_of=CARRIED)
    assert asked.firm and asked.short is None and asked.made == each
    assert asked.category not in (None, CARRIED)


def test_until_firm_asks_nothing_after_a_kept_run_that_leaves_no_firm_reading(raw):
    frame = situate(raw)
    each = calls_needed(frame)
    kept = [r.as_dict() for r in run(frame, Reader(wavers), Budget(calls=each)).records]
    asked = until_firm(
        frame, Reader(wavers), Budget(calls=each), kept=[kept], most=2, short_of=CARRIED
    )
    assert asked.made == 0 and asked.short == CARRIED and not asked.firm
    again = until_firm(frame, Reader(wavers), Budget(calls=each), kept=[kept], most=2)
    assert again.made == each and again.short is None


# ---- asked until firm, whatever its category


def then(first, after):
    """Answers as `first` in a prompt's first run of three calls, then as `after`."""
    return lambda prompt, n: first(prompt, n) if n <= 3 else after(prompt, n)


def test_a_firm_reading_of_another_category_is_never_cut_short_of_any(raw):
    # the firm miss: the second run reads as the first, firmly, but not carried;
    # stopping short of carried cuts it, stopping short of any reads it whole
    frame = situate(raw)
    whole, each = firmly(frame, wavers, runs=2, most=2)
    asked, _ = firmly(frame, wavers, runs=2, most=2, short_of=ANY)
    carried, _ = firmly(frame, wavers, runs=2, most=2, short_of=CARRIED)
    assert whole.firm and whole.category != CARRIED and whole.made == 2 * each
    assert asked.firm and asked.short is None
    assert (asked.runs, asked.findings, asked.shares) == (whole.runs, whole.findings, whole.shares)
    assert not carried.firm and carried.short == CARRIED


def test_the_last_run_is_cut_once_it_cannot_read_as_the_run_before(raw):
    frame = situate(raw)
    whole, each = firmly(frame, then(wavers, reads), runs=2, most=2)
    asked, _ = firmly(frame, then(wavers, reads), runs=2, most=2, short_of=ANY)
    assert not whole.firm and whole.made == 2 * each
    assert asked.short == ANY and not asked.firm and asked.stopped is None
    assert [len(r) for r in asked.runs][0] == each and each < asked.made < 2 * each
    assert asked.findings == tuple(judge(frame, asked.runs[0]))  # the whole run's, the first


def test_no_run_but_the_last_is_cut_short_of_any(raw):
    # each run before the last is read against by the next, so it is asked whole,
    # and a single run has none before it to read as
    frame = situate(raw)
    one, each = firmly(frame, then(wavers, reads), most=1, short_of=ANY)
    assert one.short is None and one.made == each
    three, _ = firmly(frame, then(wavers, reads), runs=3, most=3, short_of=ANY)
    assert [len(r) for r in three.runs][:2] == [each, each]


@pytest.mark.parametrize("carriage", ["listed", "all-checks"])
@pytest.mark.parametrize("most", [2, 3])
@pytest.mark.parametrize("seed", range(60))
def test_a_reading_cut_short_of_any_was_never_going_to_be_firm(raw, seed, most, carriage):
    # random answers, splits included, on two inputs: asking cut short of any would
    # not have been firm whole, and asking that goes on reads as asking whole does
    raw["carriage"] = carriage
    raw["inputs"].append({"id": "x2", "text": "A customer with a receipt asks on day 40."})
    if seed % 2:
        raw["interventions"]["control"] = ["r1", "r2", "r3", "r4"]
    frame = situate(raw)
    whole, _ = firmly(frame, noisy(seed), runs=most, most=most)
    asked, _ = firmly(frame, noisy(seed), runs=most, most=most, short_of=ANY)
    if asked.short:
        assert asked.short == ANY and not whole.firm and not asked.firm
        assert asked.runs[:-1] == whole.runs[:-1] and len(asked.runs) == most
        assert asked.findings == tuple(judge(frame, whole.runs[-2]))
    else:  # the same calls, the deciding trials first in the last run
        assert [sorted(map(calls, r)) for r in asked.runs] == [
            sorted(map(calls, r)) for r in whole.runs
        ]
        assert (asked.firm, asked.findings, asked.shares) == (
            whole.firm,
            whole.findings,
            whole.shares,
        )


def calls(record):
    return json.dumps(record, sort_keys=True)


def test_some_random_readings_are_cut_short_of_any_and_some_are_firm(raw):
    # the property above is not vacuous
    frame = situate(raw)
    cut = firm = 0
    for seed in range(60):
        asked, _ = firmly(frame, noisy(seed), runs=2, most=2, short_of=ANY)
        cut += asked.short == ANY
        firm += asked.firm
    assert cut > 5 and firm > 5, (cut, firm)


# ---- the command line


def test_the_command_line_stops_short_and_says_so(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(ROOT)  # the battery is imported from here
    raw = json.loads(REFUND.read_text(encoding="utf-8"))
    raw["standing"] = {"quorum": 3, "agree": 2, "most": 1}
    path, runs = tmp_path / "frame.json", tmp_path / "runs"
    path.write_text(json.dumps(raw), encoding="utf-8")
    runs.mkdir()
    argv = ["firm", str(path), "--battery", "tests.test_short_of:Never", "--runs", str(runs)]
    argv += ["--calls", "auto", "--short-of", "carried"]
    assert main([*argv, "--json"]) == 0
    said = json.loads(capsys.readouterr().out)
    assert (said["firm"], said["short"], said["stopped"], said["category"]) == (
        False,
        "carried",
        None,
        None,
    )
    assert said["runs"] == [
        {"file": str(runs / "1.jsonl"), "kept": False, "category": None, "short": True}
    ]
    assert 0 < said["made"] < calls_needed(situate(raw))
    (runs / "1.jsonl").unlink()
    assert main(argv) == 0
    told = capsys.readouterr().out.splitlines()
    assert told[1] == "run 1: no category, asked now, cut short: it cannot read carried"
    assert told[2].startswith(
        "firm: no, no category after 1 run, and no firm reading of carried is left to reach; "
    )


def test_run_on_the_command_line_stops_short_too_and_counts_it(tmp_path, capsys, monkeypatch):
    """Parity: `run(short_of=)` has its command, and its count is in `--json`."""
    monkeypatch.chdir(ROOT)  # the battery is imported from here
    frame = situate(json.loads(REFUND.read_text(encoding="utf-8")))
    argv = ["run", str(REFUND), "--battery", "tests.test_short_of:Never", "--calls", "auto"]
    argv += ["--short-of", "carried"]
    assert main([*argv, "--out", str(tmp_path / "a.jsonl"), "--json"]) == 0
    said = json.loads(capsys.readouterr().out)
    assert said["short"] > 0 and said["stopped"] is None
    assert said["made"] + said["short"] == calls_needed(frame)
    assert main([*argv, "--out", str(tmp_path / "b.jsonl")]) == 0
    told = capsys.readouterr().out.splitlines()
    assert f"short: {said['short']} calls not made, no answer left could make it read carried" in (
        told
    )
    assert main(argv[:-2] + ["--out", str(tmp_path / "c.jsonl"), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["short"] == 0


def test_the_command_line_stops_short_of_any_and_says_so(raw, tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(ROOT)  # the battery is imported from here
    raw["standing"] = {**raw["standing"], "most": 2}
    path, runs = tmp_path / "frame.json", tmp_path / "runs"
    path.write_text(json.dumps(raw), encoding="utf-8")
    runs.mkdir()
    argv = ["firm", str(path), "--battery", "tests.test_short_of:Turns", "--runs", str(runs)]
    argv += ["--calls", "auto", "--short-of", "any"]
    assert main([*argv, "--json"]) == 0
    said = json.loads(capsys.readouterr().out)
    assert (said["firm"], said["short"], said["stopped"]) == (False, "any", None)
    assert [run.get("short", False) for run in said["runs"]] == [False, True]
    each = calls_needed(situate(raw))
    assert each < said["made"] < 2 * each
    for name in ("1.jsonl", "2.jsonl"):  # asked again from the start, in words
        (runs / name).unlink()
    assert main(argv) == 0
    told = capsys.readouterr().out.splitlines()
    assert told[2] == "run 2: no category, asked now, cut short: it cannot read as run 1 did"
    assert ", and no firm reading is left to reach; " in told[3]


class Turns(Reader):
    """Wavers in a prompt's first run, then reads the rule: the second run cannot
    read as the first."""

    def __init__(self):
        super().__init__(then(wavers, reads))
