"""A run asked to settle skips the calls a trial no longer needs, and one asked
for calls at once makes them only for a battery that takes them; either way
the verdict reads as a whole run's."""

import json
import threading
import time
from collections import Counter
from pathlib import Path

import pytest

from midwife.cli import main
from midwife.pipeline import calls_needed, judge, run, situate
from midwife.types import Budget, Observation
from midwife.verdict import settled

REFUND = Path(__file__).parent / "fixtures" / "refund.json"
LABELS = ("Yes", "No", "open")


@pytest.mark.parametrize(
    "answers, quorum, agree, fixed",
    [
        (["Yes"] * 4, 5, 4, True),  # no other label can reach 4
        (["Yes"] * 3, 5, 4, False),
        (["Yes", "Yes", "No", "No"], 5, 4, True),  # no label can reach 4: no level
        (["Yes", "No"], 5, 4, False),
        ([None, None], 5, 4, True),  # two openings: three calls cannot make four
        ([], 5, 4, False),
        (["Yes"] * 4 + ["No"], 5, 4, True),  # every call made
        (["Yes", "Yes"], 5, 2, False),  # No can still reach 2: no level then
        (["Yes", "Yes", "No", "No"], 5, 2, True),  # two already agree: no level
        (["Yes", "Yes"], 3, 2, True),
    ],
)
def test_settled_says_whether_a_level_can_still_change(answers, quorum, agree, fixed):
    assert settled(answers, quorum, agree, LABELS) is fixed


class Rules:
    """Declines while the receipt rule is in the prompt, grants otherwise;
    `concurrent` as asked, counting how many calls are out at once."""

    name = "rules"

    def __init__(self, concurrent=False, answer=None, pause=0.0):
        self.concurrent, self.answer, self.pause = concurrent, answer, pause
        self.lock, self.out, self.most, self.asked = threading.Lock(), 0, 0, Counter()

    def check(self, frame):
        pass

    def observe(self, frame, prompt, max_output_tokens):
        with self.lock:
            self.out += 1
            self.most = max(self.most, self.out)
            self.asked[prompt] += 1
            n = self.asked[prompt]
        time.sleep(self.pause)
        with self.lock:
            self.out -= 1
        if self.answer:
            return self.answer(prompt, n)
        label = "decline" if "requires a receipt" in prompt else "grant"
        return Observation(label=label, usage={"output_tokens": 1})


@pytest.fixture
def raw(raw):
    raw["battery"] = {"kind": "rules"}
    raw["standing"] = {"quorum": 5, "agree": 4}
    return raw


def whole_and(raw, battery, **asked):
    frame = situate(raw)
    whole = judge(frame, run(frame, Rules(), Budget(calls=calls_needed(frame))).records)
    result = run(frame, battery, Budget(calls=calls_needed(frame)), **asked)
    return frame, whole, result


def same(findings, whole):
    return [f.as_dict() for f in findings] == [f.as_dict() for f in whole]


def test_a_settled_run_reads_as_the_whole_run(raw):
    frame, whole, result = whole_and(raw, Rules(), settle=True)
    trials = len(result.records) // frame.agree
    assert Counter(r.trial for r in result.records) == dict.fromkeys(
        [r.trial for r in result.records], frame.agree
    )
    assert result.settled == trials * (frame.quorum - frame.agree) and result.stopped is None
    assert same(judge(frame, result.records), whole)


def test_under_stable_the_baseline_and_repeat_run_whole(raw):
    raw["standing"]["stable"] = True
    frame, whole, result = whole_and(raw, Rules(), settle=True)
    asked = Counter(r.trial for r in result.records)
    assert asked["baseline"] == asked["repeat"] == 5 and asked["ablation"] == 4
    assert same(judge(frame, result.records), whole)


def test_a_trial_no_label_can_settle_stops_with_no_level(raw):
    def turns(prompt, n):  # grant, decline, grant, decline, grant: never four alike
        return Observation(label="grant" if n % 2 else "decline", usage={"output_tokens": 1})

    frame = situate(raw)
    result = run(frame, Rules(answer=turns), Budget(calls=calls_needed(frame)), settle=True)
    whole = judge(frame, run(frame, Rules(answer=turns), Budget(calls=calls_needed(frame))).records)
    assert Counter(r.trial for r in result.records)["baseline"] == 4
    assert judge(frame, result.records)[0].levels["baseline"] is None
    assert same(judge(frame, result.records), whole)


def test_kept_records_count_toward_a_settled_trial(raw):
    frame = situate(raw)
    first = run(frame, Rules(), Budget(calls=5), only={"baseline"}).records[:4]
    result = run(frame, Rules(), Budget(calls=calls_needed(frame)), kept=first, settle=True)
    assert "baseline" not in {r.trial for r in result.records}
    assert result.settled == 1 + (len(result.records) // 4)  # baseline's fifth, and each other's


def test_calls_at_once_need_a_battery_that_takes_them(raw):
    frame = situate(raw)
    with pytest.raises(ValueError, match="does not take calls at once"):
        run(frame, Rules(), Budget(calls=calls_needed(frame)), parallel=2)
    with pytest.raises(ValueError, match="at least 1"):
        run(frame, Rules(concurrent=True), Budget(calls=calls_needed(frame)), parallel=0)


def test_calls_at_once_read_as_one_at_a_time(raw):
    battery = Rules(concurrent=True, pause=0.01)
    frame, whole, result = whole_and(raw, battery, parallel=3)
    assert len(result.records) == calls_needed(frame) and result.stopped is None
    assert 2 <= battery.most <= 3
    assert same(judge(frame, result.records), whole)


def test_calls_at_once_settle_too(raw):
    battery = Rules(concurrent=True, pause=0.01)
    frame, whole, result = whole_and(raw, battery, parallel=3, settle=True)
    assert result.settled > 0 and len(result.records) + result.settled == calls_needed(frame)
    assert same(judge(frame, result.records), whole)


def test_calls_at_once_keep_the_token_budget(raw):
    def capped(prompt, n):  # every call spends its whole cap
        return Observation(label="grant", usage={"output_tokens": 2})

    frame = situate(raw)
    battery = Rules(concurrent=True, answer=capped, pause=0.01)
    budget = Budget(calls=calls_needed(frame), output_tokens_per_call=2, tokens=11)
    result = run(frame, battery, budget, parallel=4)
    assert result.stopped == "the token budget (11) is spent"
    # no call started that the budget could not cover, though four were out at once
    assert len(result.records) == 5 and battery.most == 4


def test_calls_already_out_are_kept_when_cancelled(raw):
    frame = situate(raw)
    kept = []
    result = run(
        frame,
        Rules(concurrent=True, pause=0.01),
        Budget(calls=calls_needed(frame)),
        parallel=3,
        cancelled=lambda: len(kept) >= 4,
        on_record=kept.append,
    )
    assert result.stopped == "cancelled"
    assert 4 <= len(result.records) == len(kept) < calls_needed(frame)


def test_the_command_line_settles_and_the_report_says_so(tmp_path, capsys):
    frame = json.loads(REFUND.read_text())
    frame["standing"] = {"quorum": 3, "agree": 2}
    path, out = tmp_path / "frame.json", tmp_path / "records.jsonl"
    path.write_text(json.dumps(frame))
    reader = "tests.fixtures.refund:RuleReader"
    argv = ["run", str(path), "--battery", reader, "--calls", "24", "--out", str(out), "--settle"]
    assert main(argv) == 0
    told = capsys.readouterr().out.splitlines()
    assert told[:2] == [
        f"wrote 16/24 calls to {out}",
        "settled: 8 calls not made, their trials' levels already fixed",
    ]
    assert main(["report", str(path), str(out)]) == 0
    report = capsys.readouterr().out.splitlines()
    assert report[1] == "records: 16  planned calls: 24  settled early: 8 calls not made"
    assert report[2] == "overall: carried"


def test_ctrl_c_keeps_every_call_already_out(raw):
    # the calls a battery was already making are spent: each is kept, then
    # the interruption goes on to the caller
    frame = situate(raw)
    battery, kept = Rules(concurrent=True, pause=0.02), []

    def interrupted():
        if len(kept) >= 2:
            raise KeyboardInterrupt
        return False

    with pytest.raises(KeyboardInterrupt):
        run(
            frame,
            battery,
            Budget(calls=calls_needed(frame)),
            parallel=3,
            cancelled=interrupted,
            on_record=kept.append,
        )
    assert len(kept) == sum(battery.asked.values()) >= 3


def test_a_short_trial_has_no_level_until_it_is_settled(raw):
    # with 2 of 5 to agree, two alike decide nothing: three more calls can
    # make a second label agree too (pass 4, R01)
    raw["standing"] = {"quorum": 5, "agree": 2}

    def drift(prompt, n):  # decline, decline, then grant, grant, unclear
        label = ["decline", "decline", "grant", "grant", "unclear"][n - 1]
        return Observation(label=label, usage={"output_tokens": 1})

    frame = situate(raw)
    records = run(frame, Rules(answer=drift), Budget(calls=calls_needed(frame))).records
    short = [r for r in records if r.run < 2]
    [whole], [partial] = judge(frame, records), judge(frame, short)
    assert whole.levels["baseline"] is None  # two labels agree: no level
    assert set(partial.levels.values()) == {None} and partial.category == "unresolved"


def test_a_short_stable_baseline_has_no_level(raw):
    # under stable a fifth call could split the baseline, so four alike are not enough
    raw["standing"]["stable"] = True
    frame = situate(raw)
    records = run(frame, Rules(), Budget(calls=calls_needed(frame))).records
    short = [r for r in records if not (r.trial == "baseline" and r.run == 4)]
    [finding] = judge(frame, short)
    assert finding.levels["baseline"] is None and finding.levels["ablation"] == "grant"
    assert finding.evidence[0] == "no agreed level in: baseline"
