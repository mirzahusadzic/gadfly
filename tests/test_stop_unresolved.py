"""A run asked to stop an input once it reads unresolved, whatever its other
trials give, asks the decisive trials first and none it no longer needs; the
verdict reads the same category as a whole run's, and says what it did not
ask."""

import json
import random
from collections import Counter
from pathlib import Path

import pytest

from midwife.cli import main
from midwife.pipeline import calls_needed, judge, overall, run, situate
from midwife.types import Budget, Observation
from midwife.verdict import UNRESOLVED

REFUND = Path(__file__).parent / "fixtures" / "refund.json"


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


@pytest.fixture
def raw(raw):
    raw["battery"] = {"kind": "rules"}
    raw["interventions"]["control"] = ["r1", "r2", "r3", "r4"]
    raw["carriage"] = "all-checks"
    return raw


def both(frame, answer, **asked):
    whole = run(frame, Reader(answer), Budget(calls=calls_needed(frame)))
    stopped = run(frame, Reader(answer), Budget(calls=calls_needed(frame)), stop_unresolved=True)
    return whole, stopped


def test_a_reader_that_never_moves_stops_once_the_control_holds(raw):
    frame = situate(raw)
    whole, stopped = both(frame, lambda prompt, n: "decline")
    asked = [t for t in dict.fromkeys(r.trial for r in stopped.records)]
    # decisive trials first; once the ablation and the control hold and the
    # presentation cannot make it misaligned, nothing else is asked
    assert asked == ["baseline", "repeat", "ablation", "control", "presentation"]
    assert stopped.unasked == 3 * frame.quorum and stopped.stopped is None
    assert len(stopped.records) + stopped.unasked == calls_needed(frame)
    [finding] = judge(frame, stopped.records)
    [read] = judge(frame, whole.records)
    assert finding.category == read.category == UNRESOLVED
    assert "ablation left it at decline, and so did the control: the scorer cannot tell" in (
        finding.evidence
    )
    assert finding.evidence[-1] == (
        "not asked: sham-1, sham-2, bypass; whatever they gave, it reads unresolved"
    )


def test_a_reader_that_reads_is_asked_everything(raw):
    def reads(prompt, n):
        return "decline" if "requires a receipt" in prompt else "grant"

    frame = situate(raw)
    whole, stopped = both(frame, reads)
    assert stopped.unasked == 0
    assert judge(frame, stopped.records)[0].as_dict() == judge(frame, whole.records)[0].as_dict()


@pytest.mark.parametrize("seed", range(60))
def test_a_stopped_run_reads_the_whole_runs_category(raw, seed):
    # random answers, splits included: a run stops only when no answer could
    # read otherwise, so every input reads as it would have
    raw["inputs"].append({"id": "x2", "text": "A customer with a receipt asks on day 40."})
    raw["interventions"]["eachAnchor"] = True
    raw["anchors"] = ["r2", "r4"]
    weights = random.Random(seed).choice([(8, 1, 1), (1, 8, 1), (3, 3, 1), (1, 1, 0)])

    def answer(prompt, n):
        pick = random.Random(f"{seed}/{prompt}/{n}")
        return pick.choices(("grant", "decline", "unclear"), weights=weights)[0]

    frame = situate(raw)
    whole, stopped = both(frame, answer)
    read = [f.category for f in judge(frame, whole.records)]
    assert [f.category for f in judge(frame, stopped.records)] == read
    assert (
        overall(judge(frame, stopped.records)).category
        == overall(judge(frame, whole.records)).category
    )


def test_some_random_runs_stop_early_and_some_read_otherwise(raw):
    # the property above is not vacuous: over its seeds, inputs stop early
    # and categories other than unresolved are read
    raw["anchors"] = ["r2", "r4"]
    raw["interventions"]["eachAnchor"] = True
    frame = situate(raw)
    saved, categories = 0, Counter()
    for seed in range(60):
        weights = random.Random(seed).choice([(8, 1, 1), (1, 8, 1), (3, 3, 1), (1, 1, 0)])

        def answer(prompt, n, seed=seed, weights=weights):
            pick = random.Random(f"{seed}/{prompt}/{n}")
            return pick.choices(("grant", "decline", "unclear"), weights=weights)[0]

        whole, stopped = both(frame, answer)
        saved += stopped.unasked
        categories.update(f.category for f in judge(frame, stopped.records))
    assert saved > 0 and len(categories) > 1


def test_judge_reads_a_missing_trial_as_unasked_only_when_no_answer_could_matter(raw):
    frame = situate(raw)
    records = run(frame, Reader(lambda p, n: "decline"), Budget(calls=calls_needed(frame))).records
    without = [r for r in records if r.trial not in ("sham-1", "bypass")]
    [finding] = judge(frame, without)
    assert finding.evidence[-1] == (
        "not asked: sham-1, bypass; whatever they gave, it reads unresolved"
    )
    # with the control unasked as well, it could move and read cooled
    [finding] = judge(frame, [r for r in without if r.trial != "control"])
    assert finding.evidence == ["no agreed level in: sham-1, bypass, control"]


def test_the_command_line_stops_and_says_so(tmp_path, capsys):
    frame = json.loads(REFUND.read_text())  # one call a trial, a control declared
    frame["battery"] = {"kind": "rules"}
    path, out = tmp_path / "frame.json", tmp_path / "records.jsonl"
    path.write_text(json.dumps(frame))
    reader = "tests.test_stop_unresolved:Never"
    argv = ["run", str(path), "--battery", reader, "--calls", "8", "--out", str(out)]
    assert main([*argv, "--stop-unresolved"]) == 0
    told = capsys.readouterr().out.splitlines()
    assert told[:2] == [
        f"wrote 5/8 calls to {out}",
        "unasked: 3 calls not made, their input unresolved whatever they gave",
    ]
    assert main(["report", str(path), str(out)]) == 0
    report = capsys.readouterr().out
    assert "overall: unresolved" in report
    assert "not asked: sham-1, sham-2, bypass; whatever they gave, it reads unresolved" in report


def test_a_run_with_nothing_to_ask_still_makes_its_file(tmp_path, capsys):
    # no control and no bypass under all-checks: unresolved before a call
    frame = json.loads(REFUND.read_text())
    frame["battery"] = {"kind": "rules"}
    frame["interventions"] = {"ablation": True}
    frame["allowed"] = {"ablation": ["grant", "decline", "unclear"]}
    path, out = tmp_path / "frame.json", tmp_path / "records.jsonl"
    path.write_text(json.dumps(frame))
    reader = "tests.test_stop_unresolved:Never"
    argv = ["run", str(path), "--battery", reader, "--calls", "2", "--out", str(out)]
    assert main([*argv, "--stop-unresolved"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        f"wrote 0/2 calls to {out}",
        "unasked: 2 calls not made, their input unresolved whatever they gave",
        f"to read the verdict: gadfly report {path} {out}",
    ]
    assert out.read_text() == ""  # the whole run, with nothing in it
    assert main(["report", str(path), str(out)]) == 0
    assert "not asked: baseline, ablation; whatever" in capsys.readouterr().out


class Never(Reader):
    """A reader that declines whatever it is shown."""

    def __init__(self):
        super().__init__(lambda prompt, n: "decline")


def test_calls_at_once_stop_too(raw):
    class AtOnce(Reader):
        concurrent = True

    frame = situate(raw)
    stopped = run(
        frame,
        AtOnce(lambda prompt, n: "decline"),
        Budget(calls=calls_needed(frame)),
        stop_unresolved=True,
        parallel=3,
    )
    assert stopped.unasked > 0
    assert len(stopped.records) + stopped.unasked == calls_needed(frame)
    # calls made at once leave some trials part asked: read as left, not as split
    said = judge(frame, stopped.records)[0].evidence[-1]
    assert said.startswith("not asked") and said.endswith("whatever they gave, it reads unresolved")
