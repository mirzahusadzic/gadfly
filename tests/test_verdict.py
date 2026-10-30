"""Each verdict path, from records alone, in the order the rules are read."""

import copy

import pytest

from gadfly.pipeline import judge, plan, situate
from gadfly.types import Record
from gadfly.verdict import CARRIED, COOLED, MISALIGNED, OUTSIDE, UNRESOLVED, level


def records(frame, levels, runs=None):
    """Records giving each trial the level named (default: the baseline's
    `decline`); a list gives each run its own observation."""
    out = []
    for x, trial in ((x, trial) for x in frame.inputs for trial in plan(frame)):
        given = levels.get(trial.id, levels.get("*", "decline"))
        for run in range(frame.quorum if runs is None else runs):
            label = given[run] if isinstance(given, list) else given
            out.append(
                Record(
                    frame=frame.hash,
                    input=x["id"],
                    trial=trial.id,
                    run=run,
                    body=trial.body_hash,
                    prompt="p",
                    battery=frame.battery["kind"],
                    observation=label,
                    opening=None if label else "no reading",
                    raw="",
                    usage={},
                )
            )
    return out


def verdict(frame, **levels):
    [finding] = judge(frame, records(frame, {k.replace("_", "-"): v for k, v in levels.items()}))
    return finding


def test_the_quorum_reads_one_agreed_level_or_none():
    assert level(["a", "a", "b"], 2) == "a"
    assert level(["a", "b", None], 2) is None
    assert level(["a", "b"], 1) is None  # two winners: no level


def test_carried_when_ablation_moves_it_as_allowed_and_nothing_else_does(raw):
    finding = verdict(situate(raw), ablation="grant")
    assert finding.category == CARRIED
    assert any("bypass left it at decline" in o for o in finding.obligations)
    assert any(o.startswith("materialization") for o in finding.obligations)


def test_bypass_clears_the_fallback_check_only_at_its_designated_opening(raw):
    # the method: removing the connection exposes the designated opening
    raw["observe"]["labels"].append("opening")
    raw["allowed"]["bypass"] = ["opening"]
    missed = verdict(situate(raw), ablation="grant", bypass="unclear")
    assert missed.category == CARRIED
    assert (
        "no hidden fallback: bypass gave unclear, not the designated opening (opening)"
        in missed.obligations
    )
    reached = verdict(situate(raw), ablation="grant", bypass="opening")
    assert not any(o.startswith("no hidden fallback") for o in reached.obligations)


def test_cooled_when_ablation_leaves_it(raw):
    assert verdict(situate(raw)).category == COOLED


def test_cooled_needs_a_scorer_that_can_move(raw):
    # every trial declines: a blind scorer and an idle relation look the same
    blind = verdict(situate(raw))
    assert blind.category == COOLED
    assert blind.obligations == ["discrimination: no control trial shows the scorer can move"]
    raw["interventions"]["control"] = ["r1", "r2", "r3", "r4"]
    blind = verdict(situate(raw))
    assert blind.category == UNRESOLVED
    assert blind.evidence == [
        "ablation left it at decline, and so did the control: the scorer cannot tell"
    ]
    seeing = verdict(situate(raw), control="grant")
    assert seeing.category == COOLED and seeing.obligations == []
    assert seeing.evidence == [
        "ablation left it at decline",
        "the control moved it decline -> grant: the scorer can tell",
    ]


def test_outside_scope_keeps_its_scope_check_open(raw):
    raw["outsideScope"] = "the recipient never reads refunds"
    finding = verdict(situate(raw), ablation="grant")
    assert finding.obligations == ["independent scope check: the exclusion is declared, not tested"]


def test_misaligned_when_ablation_moves_it_where_the_frame_does_not_allow(raw):
    raw["allowed"] = {"ablation": ["unclear"]}
    finding = verdict(situate(raw), ablation="grant")
    assert finding.category == MISALIGNED and "does not allow" in finding.evidence[0]


def test_misaligned_when_presentation_moves_it(raw):
    assert verdict(situate(raw), ablation="grant", presentation="grant").category == MISALIGNED


def test_unresolved_when_a_sham_moves_it(raw):
    finding = verdict(situate(raw), ablation="grant", sham_2="grant")
    assert finding.category == UNRESOLVED and "sham-2" in finding.evidence[0]


def test_unresolved_when_repeat_differs(raw):
    assert verdict(situate(raw), ablation="grant", repeat="grant").category == UNRESOLVED


def test_unresolved_when_a_trial_has_no_agreed_level(raw):
    finding = verdict(situate(raw), ablation=["grant", "decline", "unclear"])
    assert finding.category == UNRESOLVED and finding.evidence == ["no agreed level in: ablation"]


def test_a_trial_without_records_has_no_level(raw):
    frame = situate(raw)
    kept = [r for r in records(frame, {"ablation": "grant"}) if r.trial != "bypass"]
    [finding] = judge(frame, kept)
    assert finding.category == UNRESOLVED and "bypass" in finding.evidence[0]


def test_stable_standing_reads_a_split_baseline_as_unresolved(raw):
    raw["standing"]["stable"] = True
    split = ["decline", "decline", "unclear"]
    finding = verdict(situate(raw), baseline=split, ablation="grant")
    assert finding.category == UNRESOLVED and "split" in finding.evidence[0]
    raw["standing"]["stable"] = False
    assert verdict(situate(raw), baseline=split, ablation="grant").category == CARRIED


def test_ordered_labels_allow_only_the_declared_direction(raw):
    raw["observe"]["labels"] = raw["observe"]["order"] = ["low", "mid", "high"]
    raw["allowed"] = {"ablation": "lower"}
    frame = situate(raw)
    assert verdict(frame, **{"*": "mid", "ablation": "low"}).category == CARRIED
    assert verdict(frame, **{"*": "mid", "ablation": "high"}).category == MISALIGNED
    assert verdict(frame, **{"*": "low", "ablation": "mid"}).category == MISALIGNED


def test_outside_scope_only_when_declared(raw):
    raw["outsideScope"] = "the recipient never reads refunds"
    assert verdict(situate(raw), ablation="grant").category == OUTSIDE


def test_cooled_notes_a_cumulative_ablation_that_moved_it(raw):
    raw["interventions"]["cumulative"] = ["r1"]
    finding = verdict(situate(raw), cumulative="grant")
    assert finding.category == COOLED and "carried elsewhere" in finding.evidence[1]


def test_carried_without_a_sham_keeps_specificity_open(raw):
    del raw["interventions"]["sham"]
    finding = verdict(situate(raw), ablation="grant")
    assert finding.category == CARRIED
    assert any(o.startswith("specificity: 0 sham") for o in finding.obligations)
    # the evidence names only the trials that ran
    assert "sham" not in finding.evidence[0] and "presentation" in finding.evidence[0]


def test_carried_evidence_counts_the_shams_that_held(raw):
    finding = verdict(situate(raw), ablation="grant")
    assert finding.evidence == [
        "ablation moved it decline -> grant; held under presentation, 2 shams"
    ]
    del raw["interventions"]["presentation"]
    raw["interventions"]["sham"] = {"draws": 1}
    finding = verdict(situate(raw), ablation="grant")
    assert finding.evidence == ["ablation moved it decline -> grant; held under 1 sham"]


@pytest.mark.parametrize(
    "tamper, message",
    [
        (lambda r: r.__class__(**{**r.as_dict(), "frame": "other"}), "another frame"),
        (lambda r: r.__class__(**{**r.as_dict(), "trial": "sham-9"}), "does not have"),
        (lambda r: r.__class__(**{**r.as_dict(), "input": "x9"}), "does not have"),
        (lambda r: r.__class__(**{**r.as_dict(), "body": "other"}), "another body"),
        (lambda r: r.__class__(**{**r.as_dict(), "run": 3}), "outside the quorum"),
        (lambda r: r.__class__(**{**r.as_dict(), "battery": "other"}), "made by other"),
        (lambda r: r.__class__(**{**r.as_dict(), "observation": "approved"}), "not one of"),
        (lambda r: r.__class__(**{**r.as_dict(), "opening": "also"}), "a label or an opening"),
        (
            lambda r: r.__class__(**{**r.as_dict(), "observation": None, "opening": None}),
            "a label or an opening",
        ),
    ],
)
def test_records_the_plan_did_not_make_are_refused(raw, tamper, message):
    frame = situate(raw)
    made = records(frame, {"ablation": "grant"})
    with pytest.raises(ValueError, match=message):
        judge(frame, [*made[:-1], tamper(made[-1])])


def test_a_record_copied_twice_cannot_make_a_quorum(raw):
    frame = situate(raw)
    made = [
        r for r in records(frame, {"ablation": "grant"}) if not (r.trial == "ablation" and r.run)
    ]
    ablation = next(r for r in made if r.trial == "ablation")
    with pytest.raises(ValueError, match="two records"):
        judge(frame, [*made, ablation])


def test_one_category_over_the_frames_inputs(raw):
    from gadfly.pipeline import overall
    from gadfly.verdict import Finding

    def found(x, category, obligations=()):
        return Finding(x, category, {}, [f"{x} read {category}"], list(obligations))

    assert overall([found("x1", CARRIED), found("x2", CARRIED)]).category == CARRIED
    assert overall([found("x1", COOLED), found("x2", COOLED)]).category == COOLED
    assert overall([found("x1", UNRESOLVED), found("x2", MISALIGNED)]).category == MISALIGNED
    assert overall([found("x1", CARRIED), found("x2", UNRESOLVED)]).category == UNRESOLVED
    split = overall([found("x1", CARRIED), found("x2", COOLED)])
    assert split.category == UNRESOLVED and split.inputs == {"x1": CARRIED, "x2": COOLED}
    assert (
        split.as_dict()["inputs"] == split.inputs and found("x", COOLED).as_dict()["input"] == "x"
    )
    with pytest.raises(ValueError, match="no finding"):
        overall([])
    assert split.evidence == [
        "carried on x1, cooled on x2: the relation holds on some inputs only",
        "x1: x1 read carried",
        "x2: x2 read cooled",
    ]
    # what every input leaves open is said once; the rest names its input
    both = overall(
        [
            found("x1", CARRIED, ["materialization: m", "no hidden fallback: f"]),
            found("x2", CARRIED, ["materialization: m"]),
        ]
    )
    assert both.obligations == ["materialization: m", "x1: no hidden fallback: f"]
    # from a run: two inputs, one frame
    raw["inputs"].append({"id": "x2", "text": "Another customer without a receipt asks."})
    frame = situate(raw)
    assert overall(judge(frame, records(frame, {"ablation": "grant"}))).category == CARRIED


class CountingRecord(dict):
    """A stored record that counts how often judge reads it."""

    reads = 0

    def __getitem__(self, key):
        type(self).reads += 1
        return super().__getitem__(key)


def reads_to_judge(raw, inputs):
    raw["inputs"] = [{"id": f"x{i}", "text": f"request {i}"} for i in range(inputs)]
    raw["interventions"] = {"ablation": True}
    frame = situate(raw)
    stored = [CountingRecord(r.as_dict()) for r in records(frame, {"ablation": "grant"})]
    CountingRecord.reads = 0
    judge(frame, stored)
    return CountingRecord.reads


def test_judge_reads_each_record_a_fixed_number_of_times(raw):
    # twice the inputs and records: twice the reads, not four times
    small, large = reads_to_judge(copy.deepcopy(raw), 20), reads_to_judge(copy.deepcopy(raw), 40)
    assert large <= 2.2 * small, (small, large)
