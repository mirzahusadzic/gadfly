"""Statistics beside the verdict: textbook values for each test, and what the
report says of kept runs. No model is called; the readers are rules."""

import json

import pytest

from midwife import stats
from midwife.cli import main
from midwife.errors import UsageError
from midwife.pipeline import calls_needed, run, situate
from midwife.types import Budget, Observation
from tests.fixtures.refund import RuleReader, Unreachable


class Wavering(RuleReader):
    """The rule reader, but every fifth call it answers unclear: a sampled
    reader's noise, made reproducible."""

    def __init__(self):
        self.calls = 0

    def observe(self, frame, prompt, max_output_tokens):
        self.calls += 1
        if self.calls % 5 == 0:
            return Observation(label="unclear")
        return super().observe(frame, prompt, max_output_tokens)


def kept(raw, battery, runs=3):
    raw["battery"] = {"kind": battery.name}
    frame = situate(raw)
    made = []
    for _ in range(runs):
        result = run(frame, battery, Budget(calls=calls_needed(frame)))
        made.append([record.as_dict() for record in result.records])
    return frame, made


def test_wilson_is_honest_at_small_counts():
    low, high = stats.wilson(4, 5)
    assert (round(low, 2), round(high, 2)) == (0.38, 0.96)
    assert round(stats.wilson(15, 15)[0], 2) == 0.80
    assert stats.wilson(0, 0) == (0.0, 1.0)


def test_a_quorum_reaches_a_level_as_often_as_the_binomial_says():
    assert round(stats.at_least(4, 5, 0.88), 3) == 0.888
    assert stats.at_least(4, 5, 1.0) == 1.0 and stats.at_least(4, 5, 0.0) == 0.0


def test_fishers_exact_test_gives_its_textbook_values():
    assert round(stats.fisher(4, 1, 1, 4), 3) == 0.206
    assert round(stats.fisher(5, 0, 0, 5), 4) == 0.0079
    assert stats.fisher(0, 0, 0, 0) == 1.0
    assert stats.fisher(3, 2, 1, 4) == stats.fisher(1, 4, 3, 2)  # either row first


def test_holm_adjusts_each_p_value_among_the_others():
    adjusted = stats.holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert {k: round(v, 3) for k, v in adjusted.items()} == {"a": 0.03, "c": 0.06, "b": 0.06}


def test_power_counts_every_trial_an_input_needs_and_no_one_anchor_trial(raw):
    raw.update(anchors=["r2", "r1"])
    raw["interventions"]["eachAnchor"] = True
    frame = situate(raw)
    power = stats.power(frame, 0.88)
    assert power.trials == 6  # baseline, repeat, ablation, two shams, presentation, bypass
    assert power.trial == stats.at_least(2, 3, 0.88)
    assert power.input == pytest.approx(power.trial**6)
    for wrong in (1.5, -0.1, True, "0.9"):
        with pytest.raises(UsageError, match="agreement is a share"):
            stats.power(frame, wrong)


def test_agreement_is_how_often_a_call_gave_its_trials_most_common_answer(raw):
    _, steady = kept(raw, RuleReader())
    assert stats.agreement(steady) == 1.0
    _, wavering = kept(raw, Wavering(), runs=1)
    assert 0.75 < stats.agreement(wavering) < 1.0  # every fifth call wavered
    _, none = kept(raw, Unreachable(), runs=1)
    assert stats.agreement(none) == 0.0  # an opening never agrees
    assert stats.agreement([]) is None


def test_compare_says_how_far_each_trial_moved_or_held(raw):
    frame, runs = kept(raw, RuleReader())
    rows = {row.trial: row for row in stats.compare(frame, runs)["x1"]}
    base, ablation, sham = rows["baseline"], rows["ablation"], rows["sham-1"]
    assert base.answers == {"decline": 9} and base.moved is None and base.baseline == "decline"
    assert ablation.top == "grant" and ablation.moved == stats.fisher(9, 0, 0, 9)
    assert ablation.adjusted >= ablation.moved and ablation.differ is None
    assert sham.moved == 1.0 and sham.differ == stats.wilson(0, 9)[1]  # held, within 30%
    assert rows["presentation"].differ is not None and rows["bypass"].top == "unclear"


def test_stability_is_seeded_and_firm_for_a_steady_reader(raw):
    frame, runs = kept(raw, RuleReader())
    assert stats.stability(frame, runs, 20) == [{"x1": {"carried": 1.0}}] * 3
    frame, wavering = kept(raw, Wavering(), runs=2)
    first = stats.stability(frame, wavering, 50)
    assert first == stats.stability(frame, wavering, 50)  # the same records, the same shares
    assert all(sum(shares["x1"].values()) == pytest.approx(1.0) for shares in first)
    with pytest.raises(UsageError, match="resamples"):
        stats.stability(frame, wavering, 0)


def test_only_the_same_readers_calls_on_the_same_prompt_are_pooled(raw):
    frame, runs = kept(raw, RuleReader(), runs=1)
    other_raw = json.loads(frame.source)
    other_raw["name"] = "refund-receipt-again"  # another frame, the same calls in all but name
    other = situate(other_raw)
    records = [
        r.as_dict() for r in run(other, RuleReader(), Budget(calls=calls_needed(other))).records
    ]
    pooled = stats.pooled(frame, [(other, records)])
    assert len(pooled) == len(records) and {r["frame"] for r in pooled} == {frame.hash}
    rows = {row.trial: row for row in stats.compare(frame, runs, pooled)["x1"]}
    assert rows["baseline"].calls == 6
    worded = dict(other_raw, observe={**other_raw["observe"], "instruction": "Decide."})
    with pytest.raises(UsageError, match="asks another reader"):
        stats.pooled(frame, [(situate(worded), [])])
    longer = dict(
        other_raw,
        body={"spans": [*other_raw["body"]["spans"], {"id": "r6", "text": "Staff decide."}]},
    )
    longer_frame = situate(longer)
    made = run(longer_frame, RuleReader(), Budget(calls=calls_needed(longer_frame))).records
    assert (
        stats.pooled(frame, [(longer_frame, [r.as_dict() for r in made])]) == []
    )  # no prompt in common


def write(tmp_path, frame, runs):
    (tmp_path / "frame.json").write_text(frame.source)
    paths = []
    for n, records in enumerate(runs, 1):
        path = tmp_path / f"{n}.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in records))
        paths.append(str(path))
    return str(tmp_path / "frame.json"), paths


def test_stats_reports_trials_power_and_stability_on_one_colon_lines(raw, tmp_path, capsys):
    frame, runs = kept(raw, Wavering())
    path, records = write(tmp_path, frame, runs)
    assert main(["stats", path, *records, "--resamples", "20"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[1] == "records: 3 runs, 63 calls" and out[2].startswith("agreement: ")
    assert out[3].startswith("power: at ") and "input x1" in out
    assert any(line.startswith("  run 3, x1  ") for line in out)
    assert [line for line in out if line.count(": ") > 1] == []
    assert main(["stats", path, records[0], "--resamples", "0"]) == 0
    assert "drawn again" not in capsys.readouterr().out
    assert main(["stats", path, *records, "--json", "--resamples", "5"]) == 0
    body = json.loads(capsys.readouterr().out)
    assert body["calls"] == 63 and len(body["stability"]) == 3 and body["pooled"] == 0
    assert [row["trial"] for row in body["inputs"]["x1"]][:3] == ["baseline", "repeat", "ablation"]


def test_stats_refuses_records_of_another_frame_and_a_reader_asked_otherwise(raw, tmp_path, capsys):
    frame, runs = kept(raw, RuleReader(), runs=1)
    path, records = write(tmp_path, frame, runs)
    other = dict(json.loads(frame.source), name="another")
    (tmp_path / "other.json").write_text(json.dumps(other))
    assert main(["stats", str(tmp_path / "other.json"), *records]) == 5  # RecordsError
    worded = dict(other, observe={**other["observe"], "instruction": "Decide."})
    (tmp_path / "worded.json").write_text(json.dumps(worded))
    assert main(["stats", path, *records, "--pool", str(tmp_path / "worded.json"), records[0]]) == 2
    assert "UsageError: frame 'another' asks another reader" in capsys.readouterr().err


def test_plan_shows_the_quorums_power_only_when_asked(raw, tmp_path, capsys):
    path = tmp_path / "frame.json"
    path.write_text(json.dumps(raw))
    assert main(["plan", str(path), "--agreement", "0.88"]) == 0
    second = capsys.readouterr().out.splitlines()[1]
    assert second.startswith("power: at 88% agreement, a trial reaches a level of 2 of 3 ")
    assert main(["plan", str(path)]) == 0 and "power" not in capsys.readouterr().out
    assert main(["plan", str(path), "--agreement", "2"]) == 2
    assert main(["plan", str(path), "--agreement", "0.9", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["power"]["agreement"] == 0.9


def test_a_trial_asked_once_a_run_is_no_measure_of_agreement_or_stability(raw, tmp_path, capsys):
    # one call a trial has nothing to agree with and nothing to draw again:
    # it must not read as a perfectly steady reader or a perfectly firm verdict
    raw["standing"] = {"quorum": 1, "agree": 1}
    frame, runs = kept(raw, RuleReader(), runs=2)
    assert stats.agreement(runs) is None
    assert stats.stability(frame, runs, 20) == [{}, {}]
    path, records = write(tmp_path, frame, runs)
    assert main(["stats", path, *records, "--resamples", "20"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert (
        out[2] == "agreement: no trial was asked twice in a run, so there is no repeat to measure"
    )
    assert not any(line.startswith("power: ") for line in out)
    assert "  run 1, x1  carried; each trial asked once, nothing to draw again" in out
    mixed = [runs[0] + [dict(runs[0][0])]]  # one trial asked twice, alike
    assert stats.agreement(mixed) == 1.0  # the lone calls are left out, not counted as agreeing


def test_a_pooled_call_stays_on_its_own_input_when_two_inputs_ask_alike(raw):
    # two inputs with the same text send the same prompts: a call keeps its
    # own input, and one that names neither could be either's, so it is left out
    text = raw["inputs"][0]["text"]
    raw["inputs"] = [{"id": "x1", "text": text}, {"id": "x2", "text": text}]
    frame, _ = kept(raw, RuleReader(), runs=1)
    other_raw = dict(json.loads(frame.source), name="asked-alike-again")
    other = situate(other_raw)
    records = [
        r.as_dict() for r in run(other, RuleReader(), Budget(calls=calls_needed(other))).records
    ]
    pooled = stats.pooled(frame, [(other, records)])
    assert [r["input"] for r in pooled] == [r["input"] for r in records]
    other_raw["inputs"] = [{"id": "y1", "text": text}, {"id": "y2", "text": text}]
    renamed = situate(other_raw)
    made = run(renamed, RuleReader(), Budget(calls=calls_needed(renamed))).records
    assert stats.pooled(frame, [(renamed, [r.as_dict() for r in made])]) == []


def test_a_label_named_opening_is_counted_apart_from_the_openings(raw, tmp_path, capsys):
    raw["observe"]["labels"] = ["opening", "decline", "unclear"]
    raw["allowed"]["ablation"] = ["opening", "unclear"]

    class Answering(RuleReader):
        def observe(self, frame, prompt, max_output_tokens):
            return Observation(label="opening")

    frame, (labelled,) = kept(raw, Answering(), runs=1)
    _, (unreachable,) = kept(raw, Unreachable(), runs=1)
    row = next(
        r for r in stats.compare(frame, [labelled, unreachable])["x1"] if r.trial == "sham-1"
    )
    assert (row.answers, row.openings, row.calls) == ({"opening": 3}, 3, 6)
    path, records = write(tmp_path, frame, [labelled, unreachable])
    assert main(["stats", path, *records, "--resamples", "0"]) == 0
    assert "  sham-1          6 calls  opening 3, 3 openings  top 50%" in capsys.readouterr().out


def test_the_same_calls_give_the_same_shares_in_whatever_order_they_were_kept(raw):
    frame, wavering = kept(raw, Wavering(), runs=2)
    first = stats.stability(frame, wavering, 200)
    shuffled = [list(reversed(records)) for records in wavering]
    assert stats.stability(frame, shuffled, 200) == first


def test_power_is_a_probability_at_any_quorum_and_says_what_it_counts(raw, tmp_path, capsys):
    assert 0.0 <= stats.at_least(1, 60, 0.99) <= 1.0
    raw["standing"] = {"quorum": 60, "agree": 1}
    power = stats.power(situate(raw), 0.99)
    assert power.trial <= 1.0 and power.input <= 1.0
    path = tmp_path / "frame.json"
    path.write_text(json.dumps(raw))
    assert main(["plan", str(path), "--agreement", "0.9"]) == 0
    assert "and all 7 trials the plan asks of an input " in capsys.readouterr().out


def test_redrawn_shares_add_up_to_the_whole():
    from midwife.cli import _parts

    assert _parts({"carried": 0.695, "unresolved": 0.295, "cooled": 0.01}) == (
        "carried 70%, unresolved 29%, cooled 1%"
    )
    assert _parts({"carried": 0.7, "unresolved": 0.2975, "cooled": 0.0025}) == (
        "carried 70%, unresolved 30%, cooled under 1%"
    )
    assert _parts({"cooled": 1.0}) == "cooled 100%"
