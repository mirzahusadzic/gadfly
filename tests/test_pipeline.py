"""The run: what it spends, when it stops, and what a failing battery leaves."""

import pytest

from gadfly.pipeline import calls_needed, judge, run, situate
from gadfly.types import Budget, Observation
from gadfly.verdict import CARRIED, MISALIGNED


class Rules:
    """A deterministic battery: declines while the receipt rule is in the
    prompt, grants otherwise. It is what a frame's promise says should happen."""

    name = "rules"

    def __init__(self, answer=None, words=("requires a receipt", "requires a proof of purchase")):
        self.calls, self.caps, self.answer, self.words = [], [], answer, words

    def check(self, frame):
        if frame.battery["kind"] != "unified":
            raise ValueError("wrong battery")

    def observe(self, frame, prompt, max_output_tokens):
        self.calls.append(prompt)
        self.caps.append(max_output_tokens)
        if self.answer:
            return self.answer(prompt)
        label = "decline" if any(w in prompt for w in self.words) else "grant"
        return Observation(label=label, raw=label, usage={"output_tokens": 1})


def test_a_full_run_is_judged_from_its_records_alone(raw):
    frame = situate(raw)
    battery, kept = Rules(), []
    result = run(frame, battery, Budget(calls=calls_needed(frame)), on_record=kept.append)
    assert result.stopped is None and len(result.records) == result.planned == 21
    assert list(result.records) == kept
    assert set(battery.caps) == {64}
    # bypass cuts "These rules decide every request."; a battery that reads the
    # rule's words regardless still declines, so the fallback check stays open
    [finding] = judge(frame, [r.as_dict() for r in kept])
    assert finding.category == CARRIED
    assert "no hidden fallback: bypass left it at decline" in finding.obligations


def test_a_scorer_that_reads_a_word_not_the_rule_is_caught_by_presentation(raw):
    frame = situate(raw)
    result = run(frame, Rules(words=("requires a receipt",)), Budget(calls=21))
    [finding] = judge(frame, result.records)
    assert finding.category == MISALIGNED
    assert finding.evidence == ["presentation moved it decline -> grant"]


def test_no_call_is_made_when_the_plan_exceeds_the_budget(raw):
    battery = Rules()
    result = run(situate(raw), battery, Budget(calls=20))
    assert result.records == () and battery.calls == []
    assert result.stopped == "the plan needs 21 calls; the budget allows 20"


def test_the_token_budget_stops_before_a_call_that_could_pass_it(raw):
    battery = Rules()
    result = run(situate(raw), battery, Budget(calls=21, output_tokens_per_call=4, tokens=10))
    # each call reports 1 token but may spend 4: after 6, a seventh could pass 10
    assert len(battery.calls) == 7 and result.stopped == "the token budget (10) is spent"


def test_a_call_that_reports_no_usage_counts_as_its_cap(raw):
    battery = Rules(answer=lambda prompt: Observation(label="decline"))
    result = run(situate(raw), battery, Budget(calls=21, output_tokens_per_call=4, tokens=10))
    assert len(result.records) == 2


def test_cancel_stops_between_calls_and_keeps_what_was_made(raw):
    battery = Rules()
    result = run(situate(raw), battery, Budget(calls=21), cancelled=lambda: len(battery.calls) == 5)
    assert result.stopped == "cancelled" and len(result.records) == 5


def test_a_failing_battery_gives_an_opening_never_a_label(raw):
    def fail(prompt):
        raise TimeoutError("slow")

    result = run(situate(raw), Rules(answer=fail), Budget(calls=21))
    assert {r.opening for r in result.records} == {"battery failed: TimeoutError"}
    assert {r.observation for r in result.records} == {None}


def test_a_label_outside_the_frame_is_an_opening(raw):
    result = run(
        situate(raw), Rules(answer=lambda p: Observation(label="refund")), Budget(calls=21)
    )
    assert {r.opening for r in result.records} == {"the battery returned no label of this frame"}


def test_the_raw_answer_is_kept_only_up_to_its_limit(raw):
    long = Observation(label="decline", raw="x" * 5000)
    result = run(situate(raw), Rules(answer=lambda p: long), Budget(calls=21))
    assert {len(r.raw) for r in result.records} == {2000}


def test_a_partial_run_names_trials_the_plan_has(raw):
    frame = situate(raw)
    battery = Rules()
    result = run(frame, battery, Budget(calls=6), only=(t for t in ["baseline", "ablation"]))
    assert [r.trial for r in result.records] == ["baseline"] * 3 + ["ablation"] * 3
    with pytest.raises(ValueError, match="no trial"):
        run(frame, battery, Budget(calls=6), only=["baselin"])


def test_the_battery_refuses_before_any_call(raw):
    raw["battery"]["kind"] = "other"
    battery = Rules()
    with pytest.raises(ValueError, match="wrong battery"):
        run(situate(raw), battery, Budget(calls=21))
    assert battery.calls == []


def test_an_observation_is_a_label_or_an_opening():
    with pytest.raises(ValueError):
        Observation(label=None)
    with pytest.raises(ValueError):
        Observation(label="grant", opening="also")
    with pytest.raises(ValueError):
        Budget(calls=0)


def test_the_frame_keeps_its_own_copy(raw):
    frame = situate(raw)
    raw["anchors"].append("r1")
    raw["promise"] = "changed"
    assert frame.anchors == ("r2",) and frame.raw["promise"] != "changed"
