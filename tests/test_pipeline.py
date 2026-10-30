"""The run: what it spends, when it stops, and what a failing battery leaves."""

import pytest

from gadfly.pipeline import calls_needed, judge, run, situate
from gadfly.types import Budget, Observation
from gadfly.verdict import CARRIED, MISALIGNED


@pytest.fixture
def raw(raw):
    raw["battery"] = {"kind": "rules"}
    return raw


class Rules:
    """A deterministic battery: declines while the receipt rule is in the
    prompt, grants otherwise. It is what a frame's promise says should happen."""

    name = "rules"

    def __init__(self, answer=None, words=("requires a receipt", "requires a proof of purchase")):
        self.calls, self.caps, self.answer, self.words = [], [], answer, words

    def check(self, frame):
        if frame.battery.get("refuse"):
            raise ValueError("this battery refuses the frame")

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


def test_a_cancelled_run_is_finished_from_what_it_kept(raw):
    raw["inputs"].append({"id": "x2", "text": "Another customer without a receipt asks."})
    frame, battery = situate(raw), Rules()
    first = run(frame, battery, Budget(calls=42), cancelled=lambda: len(battery.calls) == 30)
    kept = [r.as_dict() for r in first.records]
    rest = run(frame, battery, Budget(calls=12), kept=kept)
    assert rest.stopped is None and rest.planned == len(rest.records) == 12
    made = [(r.input, r.trial, r.run) for r in (*first.records, *rest.records)]
    assert len(made) == len(set(made)) == calls_needed(frame)
    [one, two] = judge(frame, [*first.records, *rest.records])
    assert one.category == two.category == CARRIED
    with pytest.raises(ValueError, match="another frame"):
        run(frame, battery, Budget(calls=42), kept=[{**kept[0], "frame": "other"}])


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


def test_an_answer_outside_the_frame_keeps_what_the_battery_said(raw):
    said = Observation(label="refund", raw='{"label": "refund"}', usage={"output_tokens": 3})
    [record, *_] = run(situate(raw), Rules(answer=lambda p: said), Budget(calls=21)).records
    assert record.opening == "the battery returned no label of this frame"
    assert record.raw == '{"label": "refund"}' and record.usage == {"output_tokens": 3}


def test_a_battery_that_returns_no_observation_gives_an_opening(raw):
    result = run(situate(raw), Rules(answer=lambda p: None), Budget(calls=21))
    assert {r.opening for r in result.records} == {"the battery returned no observation"}


def test_a_battery_that_breaks_its_cap_stops_the_run(raw):
    # the budget's promise rests on each call keeping to its cap
    over = Observation(label="decline", usage={"output_tokens": 40})
    budget = Budget(calls=21, output_tokens_per_call=4)
    result = run(situate(raw), Rules(answer=lambda p: over), budget)
    assert len(result.records) == 1
    assert result.stopped == "the battery reported 40 output tokens for a call capped at 4"


def test_a_record_says_what_served(raw):
    served = Observation(label="decline", served="rules@2")
    result = run(situate(raw), Rules(answer=lambda p: served), Budget(calls=21))
    assert {r.served for r in result.records} == {"rules@2"}


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
    raw["battery"]["refuse"] = True
    battery = Rules()
    with pytest.raises(ValueError, match="refuses the frame"):
        run(situate(raw), battery, Budget(calls=21))
    assert battery.calls == []


def test_only_the_battery_the_frame_names_reads_it(raw):
    # the frame's hash names its battery: another one reading it would be
    # recorded under a frame that says something else read it
    raw["battery"] = {"kind": "unified", "model": "anthropic/claude-sonnet-5-5"}
    battery = Rules()
    with pytest.raises(ValueError, match="asks for the unified battery, not rules"):
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


def test_nothing_read_from_a_frame_changes_it(raw):
    frame = situate(raw)
    frame.raw["materialized"] = True
    frame.battery["model"] = "other"
    frame.inputs[0]["text"] = "changed"
    frame.interventions.pop("presentation")
    assert frame == situate(raw) and frame.hash == situate(raw).hash
    assert "materialized" not in frame.raw and frame.battery == raw["battery"]


def test_a_battery_cannot_change_the_frame_it_reads(raw):
    class Sneaky(Rules):
        def observe(self, frame, prompt, max_output_tokens):
            frame.raw["materialized"] = True  # would clear materialization unearned
            return super().observe(frame, prompt, max_output_tokens)

    frame = situate(raw)
    [finding] = judge(frame, run(frame, Sneaky(), Budget(calls=21)).records)
    assert any(o.startswith("materialization") for o in finding.obligations)
