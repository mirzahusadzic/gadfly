"""Each verdict path, from records alone, in the order the rules are read."""

import copy

import pytest

from midwife.pipeline import judge, plan, situate
from midwife.types import Record
from midwife.verdict import CARRIED, COOLED, MISALIGNED, OUTSIDE, UNRESOLVED, level
from tests.conftest import REFUND


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


def test_a_bypass_that_holds_at_baseline_settles_nothing(raw):
    # naming the baseline answer as the opening cannot make a bypass that
    # never moved read as one that did
    raw["allowed"]["bypass"] = ["decline"]
    held = verdict(situate(raw), ablation="grant", bypass="decline")
    assert "no hidden fallback: bypass left it at decline" in held.obligations
    assert not [line for line in held.evidence if "bypass moved it" in line]


def test_a_stable_split_names_an_opening_not_none(raw):
    # a call that opened is not a level of None: the split says it opened
    raw["interventions"]["repeat"] = True
    raw["standing"]["stable"] = True
    frame = situate(raw)
    baseline = ["decline"] * (frame.quorum - 1) + [None]
    finding = verdict(frame, baseline=baseline, ablation="grant")
    [split] = [line for line in finding.evidence if "sessions split" in line]
    assert "None" not in split and "an opening" in split


def test_cooled_when_ablation_leaves_it(raw):
    assert verdict(situate(raw)).category == COOLED


def test_cooled_needs_a_scorer_that_can_move(raw):
    # every trial declines: a blind scorer and an idle relation look the same
    blind = verdict(situate(raw))
    assert blind.category == COOLED
    assert blind.obligations[-1] == "discrimination: no control trial shows the scorer can move"
    raw["interventions"]["control"] = ["r1", "r2", "r3", "r4"]
    blind = verdict(situate(raw))
    assert blind.category == UNRESOLVED
    assert blind.evidence == [
        "ablation left it at decline, and so did the control: the scorer cannot tell"
    ]
    seeing = verdict(situate(raw), control="grant")
    assert seeing.category == COOLED
    assert not any(o.startswith("discrimination") for o in seeing.obligations)
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


def test_a_cumulative_that_moved_it_is_said_when_the_control_did_not(raw):
    # the levels showed it, but the evidence did not: a reader of an unresolved
    # finding lost the one trial that says the decision rests elsewhere too
    raw["interventions"]["cumulative"] = ["r1"]
    raw["interventions"]["control"] = ["r1", "r2", "r3", "r4"]
    finding = verdict(situate(raw), cumulative="grant")
    assert finding.category == UNRESOLVED
    assert "discrimination: the control left it at decline too" in finding.obligations
    assert (
        finding.evidence[-1] == "the cumulative ablation moved it to grant: carried elsewhere too"
    )


def test_carried_without_a_sham_keeps_specificity_open(raw):
    del raw["interventions"]["sham"]
    finding = verdict(situate(raw), ablation="grant")
    assert finding.category == CARRIED
    # said as the other undeclared checks are, not as "0 sham trial(s), 0 declared"
    assert "specificity: no sham trial was declared" in finding.obligations
    # the evidence names only the trials that ran
    assert "sham" not in finding.evidence[0] and "presentation" in finding.evidence[0]


def test_carried_evidence_names_the_bypass_and_the_control_that_settled_it(raw):
    # without them, a run with a bypass and a control read the same as one without
    raw["interventions"]["control"] = ["r1", "r2", "r3", "r4"]
    finding = verdict(situate(raw), ablation="grant", bypass="grant", control="grant")
    assert finding.category == CARRIED
    assert finding.evidence == [
        "ablation moved it decline -> grant; held under presentation, 2 shams",
        "bypass moved it decline -> grant: no hidden fallback",
        "the control moved it decline -> grant",
    ]


def test_a_sham_that_moved_it_is_listed_under_every_category(raw):
    # misaligned and cooled are read before the shams; the moved sham stays visible
    raw["allowed"] = {"ablation": ["unclear"]}
    misaligned = verdict(situate(raw), ablation="grant", sham_2="grant")
    assert misaligned.category == MISALIGNED
    assert "specificity: sham-2 moved it too; the change is not specific" in misaligned.obligations
    cooled = verdict(situate(raw), sham_1="grant")
    assert cooled.category == COOLED
    assert "specificity: sham-1 moved it too; the change is not specific" in cooled.obligations
    held = verdict(situate(raw), ablation="unclear")
    assert not any("moved it too" in o for o in held.obligations)


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
    from midwife.pipeline import overall
    from midwife.verdict import Finding

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


def test_every_category_keeps_its_open_checks_visible(raw):
    # misaligned by direction, with no bypass, presentation, sham or
    # materialization: the open checks are listed, not dropped by the category
    raw["allowed"] = {"ablation": ["unclear"]}
    for key in ("repeat", "sham", "presentation", "bypass"):
        raw["interventions"].pop(key)
    misaligned = verdict(situate(raw), ablation="grant")
    assert misaligned.category == MISALIGNED
    assert [o.split(":")[0] for o in misaligned.obligations] == [
        "no hidden fallback",
        "presentation invariance",
        "specificity",
        "materialization",
    ]
    # cooled and unresolved list theirs too
    assert any(o.startswith("no hidden fallback") for o in verdict(situate(raw)).obligations)
    unresolved = verdict(situate(raw), ablation=["grant", "decline", "unclear"])
    assert unresolved.category == UNRESOLVED
    assert any(o.startswith("materialization") for o in unresolved.obligations)


def test_carried_and_cooled_need_their_checks_under_the_default_policy(raw):
    # the essay: a candidate earns carriage only when every check establishes
    # it, and cooled needs adequate discriminating trials
    raw.pop("carriage")
    raw["materialized"] = True
    open_fallback = verdict(situate(raw), ablation="grant")
    assert open_fallback.category == UNRESOLVED
    assert open_fallback.evidence[-1] == "not carried while 1 carriage check is open"
    assert open_fallback.obligations == ["no hidden fallback: bypass left it at decline"]
    assert verdict(situate(raw), ablation="grant", bypass="grant").category == CARRIED
    blind = verdict(situate(raw))
    assert blind.category == UNRESOLVED
    assert blind.evidence[-1] == "not cooled until a control shows the scorer can move"
    raw["interventions"]["control"] = ["r1", "r2", "r3", "r4"]
    assert verdict(situate(raw), control="grant").category == COOLED


def test_the_listed_policy_names_the_category_and_lists_what_is_open(raw):
    # After the Poem's rule: the category stands, its open checks beside it
    assert raw["carriage"] == "listed"
    assert verdict(situate(raw), ablation="grant").category == CARRIED
    assert verdict(situate(raw)).category == COOLED


CHECKED = {
    "owner": "the refunds team",
    "statement": "replies never quote the refund rule",
    "source": "scope review SR-4",
    "encounter": "the March policy review",
}


def test_outside_scope_needs_the_owners_scope_check(raw):
    # the essay: the declared exclusion AND an independent scope check
    raw.pop("carriage")
    raw["outsideScope"] = "the recipient never reads refunds"
    declared = verdict(situate(raw), ablation="grant")
    assert declared.category == UNRESOLVED
    assert declared.obligations == [
        "independent scope check: the exclusion is declared, not tested"
    ]
    raw["scopeCheck"] = CHECKED
    checked = verdict(situate(raw), ablation="grant")
    assert checked.category == OUTSIDE and checked.obligations == []
    assert checked.evidence[-1] == (
        "the refunds team checked the scope at the March policy review: "
        "replies never quote the refund rule (scope review SR-4)"
    )


def test_a_move_under_placement_is_misaligned(raw):
    # structure, not wording, drove the observation
    raw["interventions"]["placement"] = {"span": "r2", "after": "r4"}
    finding = verdict(situate(raw), ablation="grant", placement="grant")
    assert finding.category == MISALIGNED
    assert finding.evidence == ["placement moved it decline -> grant"]
    held = verdict(situate(raw), ablation="grant")
    assert held.evidence == [
        "ablation moved it decline -> grant; held under presentation, placement, 2 shams"
    ]


def superset_control(carriage="all-checks", control=("r1", "r2", "r3", "r4")):
    # the anchor r2 and more; every other check settled
    raw = copy.deepcopy(REFUND)
    raw["interventions"]["sham"] = {"draws": 1}
    raw["interventions"]["control"] = list(control)
    raw["standing"] = {"quorum": 3, "agree": 2, "stable": True}
    raw["materialized"] = True
    raw["carriage"] = carriage
    return situate(raw)


MONOTONE = "monotonicity: the control removes the anchors and more, yet left it at decline"
MOVED = {"*": "decline", "ablation": "grant", "bypass": "unclear"}


def test_a_control_that_cuts_more_yet_holds_keeps_carried_from_being_named():
    finding = verdict(superset_control(), **MOVED)
    assert finding.category == UNRESOLVED and finding.obligations == [MONOTONE]
    assert "not carried while 1 carriage check is open" in finding.evidence


def test_listed_names_carried_with_the_monotonicity_check_beside_it():
    finding = verdict(superset_control("listed"), **MOVED)
    assert finding.category == CARRIED and finding.obligations == [MONOTONE]


def test_a_misaligned_finding_lists_it_too():
    finding = verdict(superset_control(), **{**MOVED, "presentation": "grant"})
    assert finding.category == MISALIGNED and MONOTONE in finding.obligations


@pytest.mark.parametrize(
    "control, levels",
    [
        (("r1", "r2", "r3", "r4"), {**MOVED, "control": "grant"}),  # the control moved too
        (("r1", "r3", "r4"), MOVED),  # it does not cut the anchor
    ],
)
def test_no_monotonicity_check_when_the_control_moved_or_spares_the_anchors(control, levels):
    finding = verdict(superset_control(control=control), **levels)
    assert finding.category == CARRIED and finding.obligations == []


def inverting(**allowed):
    raw = copy.deepcopy(REFUND)
    raw["interventions"]["inversion"] = {"requires a receipt": "needs no receipt"}
    raw["allowed"]["inversion"] = allowed.get("reach", ["grant", "unclear"])
    raw["materialized"] = True
    raw["carriage"] = "listed"
    return situate(raw)


CARRIES = {"*": "decline", "ablation": "grant", "bypass": "unclear"}


def test_an_inversion_that_reaches_what_the_frame_allows_carries_it():
    finding = verdict(inverting(), **CARRIES, inversion="grant")
    assert finding.category == CARRIED
    assert "inversion moved it decline -> grant: the answer follows the relation's sense" in (
        finding.evidence
    )


def test_an_inversion_that_leaves_the_answer_is_misaligned():
    finding = verdict(inverting(), **CARRIES, inversion="decline")
    assert finding.category == MISALIGNED
    assert finding.evidence[-1] == (
        "inversion left it at decline: the answer does not follow the relation's sense"
    )


def test_an_inversion_that_moves_it_where_the_frame_does_not_allow_is_misaligned():
    finding = verdict(inverting(reach=["unclear"]), **CARRIES, inversion="grant")
    assert finding.category == MISALIGNED
    assert (
        finding.evidence[-1]
        == "inversion moved it decline -> grant, which the frame does not allow"
    )


def test_an_inversion_with_no_agreed_level_leaves_direction_open():
    finding = verdict(inverting(), **CARRIES, inversion=["grant", "unclear", "decline"])
    assert finding.category == UNRESOLVED
    assert "direction: the inversion has no agreed level" in finding.obligations


def test_on_the_cooled_side_an_inversion_is_evidence_only():
    raw = copy.deepcopy(REFUND)
    raw["interventions"]["inversion"] = {"requires a receipt": "needs no receipt"}
    raw["interventions"]["control"] = ["r1", "r2", "r3", "r4"]
    raw["allowed"]["inversion"] = ["grant"]
    raw["carriage"] = "listed"
    finding = verdict(situate(raw), **{"*": "decline", "control": "grant", "inversion": "grant"})
    assert finding.category == COOLED
    assert "the inversion moved it decline -> grant, though the ablation did not" in (
        finding.evidence
    )
