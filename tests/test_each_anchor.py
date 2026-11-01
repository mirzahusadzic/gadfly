"""Each anchor cut alone, on the statements of Tendora's bundled demo
(Apache-2.0), asked as the demo's own checks ask: a chain of two rules, two
routes to one answer, and a citation that carries nothing, declared on purpose
(the demo's restore check rests on s15 alone). Read by an engine of rules
that answers from the anchors it still sees. No engine is called."""

import copy
import json
from pathlib import Path

import pytest

from midwife.cli import main
from midwife.frame import FrameError, parse
from midwife.interventions import plan, prompt, trial_ids
from midwife.pipeline import calls_needed, judge, run, situate
from midwife.types import Budget, Observation
from midwife.verdict import CARRIED, COOLED

DEMO = json.loads((Path(__file__).parent / "fixtures" / "restore-inversion.json").read_text())
TEXT = {span["id"]: span["text"] for span in DEMO["body"]["spans"]}


class Present:
    """Answers from the anchors still in the body: `rule` takes their ids and
    gives a label, or None for an opening."""

    name = "rules"

    def __init__(self, rule):
        self.rule = rule

    def check(self, frame):
        pass

    def observe(self, frame, prompt, max_output_tokens):
        body, _, _ = prompt.rpartition("\n\n---\n\n")
        seen = {anchor for anchor in frame.anchors if TEXT[anchor] in body}
        label = self.rule(seen)
        return Observation(label=label, opening=None if label else "no answer")


def framed(anchors, text, each=True, **interventions):
    raw = copy.deepcopy(DEMO)
    raw.update(name="each-anchor", anchors=anchors, inputs=[{"id": "x", "text": text}])
    if text == NOTIFY:  # asked who, it is answered with a name
        raw["observe"] = WHO
    raw["interventions"] = {"repeat": True, "ablation": True, **interventions}
    if each:
        raw["interventions"]["eachAnchor"] = True
    raw["allowed"] = {"ablation": ["open"]}
    return raw


def read(raw, rule):
    frame = situate(raw)
    result = run(frame, Present(rule), Budget(calls=calls_needed(frame)))
    return judge(frame, result.records)[0]


NOTIFY = "Case: A certificate expires.\nQuestion: Who notifies the customers?"
WHO = {
    "labels": ["Maya", "Alex", "Morgan", "Sam", "Jordan", "Priya", "another answer", "open"],
    "instruction": (
        "Answer the question for the case from the statements above and nothing else: "
        "the one person they make the answer, 'another answer' for several people or any "
        "other answer, or 'open' if they do not settle it."
    ),
}
LOGS = "Question: Are access logs reviewed?"
RESTORE = (
    "Case: The incident commander has approved the restore.\n"
    "Question: May Jordan, the database administrator, restore the database from a backup?"
)
# The three reference frames: the anchors, what is asked, how the engine
# answers, and the line the predictions, written first, expected.
REFERENCE = {
    "a chain": (
        ["s22", "s23"],
        NOTIFY,
        lambda seen: "Sam" if seen == {"s22", "s23"} else "open",
        "each anchor carries it",
    ),
    "two routes": (
        ["s16", "s24"],
        LOGS,
        lambda seen: "conditional" if seen else "open",
        "the anchors carry it independently; either suffices",
    ),
    "an idle citation": (
        ["s15", "s14"],
        RESTORE,
        lambda seen: "Yes" if "s15" in seen else "open",
        "s15 carries it; s14 adds nothing alone",
    ),
}


@pytest.mark.parametrize("case", REFERENCE)
def test_each_anchor_alone_says_how_the_anchors_carry_it(case):
    anchors, text, rule, line = REFERENCE[case]
    finding = read(framed(anchors, text), rule)
    assert finding.category == CARRIED
    assert finding.evidence[-1] == line


@pytest.mark.parametrize("case", REFERENCE)
def test_each_anchor_alone_never_changes_the_category(case):
    anchors, text, rule, line = REFERENCE[case]
    each, once = read(framed(anchors, text), rule), read(framed(anchors, text, each=False), rule)
    assert (each.category, each.obligations) == (once.category, once.obligations)
    assert each.evidence == [*once.evidence, line]


def test_each_anchor_is_cut_alone_after_the_ablation():
    frame = parse(framed(["s22", "s23"], NOTIFY, sham=True))
    trials = plan(frame)
    assert [t.id for t in trials] == trial_ids(frame)
    assert trial_ids(frame)[:5] == [
        "baseline",
        "repeat",
        "ablation",
        "ablation-s22",
        "ablation-s23",
    ]
    alone = {t.id: t for t in trials if t.kind == "each-anchor"}
    assert {t.removed for t in alone.values()} == {("s22",), ("s23",)}
    # the battery reads the body less one anchor and the input as it is
    asked = prompt(frame, alone["ablation-s22"], frame.inputs[0])
    assert TEXT["s22"] not in asked and TEXT["s23"] in asked and asked.endswith(NOTIFY)
    assert calls_needed(frame) == len(trial_ids(frame)) * frame.quorum


def test_an_anchor_alone_with_no_agreed_level_is_said_and_read_no_further():
    finding = read(
        framed(["s22", "s23"], NOTIFY),
        lambda seen: "Sam" if seen == {"s22", "s23"} else None if seen else "open",
    )
    assert finding.category == CARRIED
    assert finding.levels["ablation-s22"] is None
    assert finding.evidence[-2:] == [
        "s22 alone has no agreed level",
        "s23 alone has no agreed level",
    ]


def test_an_anchor_that_moves_it_alone_where_the_ablation_did_not_is_said():
    finding = read(framed(["s22", "s23"], NOTIFY), lambda seen: "open" if len(seen) == 1 else "Sam")
    assert finding.category == COOLED
    assert finding.evidence[-2:] == [
        "s22 alone moved it Sam -> open, though cutting every anchor did not",
        "s23 alone moved it Sam -> open, though cutting every anchor did not",
    ]


@pytest.mark.parametrize(
    "rule, line",
    [
        (
            lambda seen: "conditional" if seen else "open",
            "no anchor alone is needed: the others carry it without it",
        ),
        (
            lambda seen: "conditional" if {"s16", "s24"} <= seen else "open",
            "s16, s24 carry it; s29 adds nothing alone",
        ),
        (
            lambda seen: "conditional" if "s16" in seen else "open",
            "s16 carries it; s24, s29 add nothing alone",
        ),
    ],
)
def test_three_anchors_read_alone(rule, line):
    finding = read(framed(["s16", "s24", "s29"], LOGS), rule)
    assert finding.evidence[-1] == line


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda r: r.update(anchors=["s22"]), "one is the ablation again"),
        (lambda r: r["interventions"].update(eachAnchor="yes"), "true or false"),
        (lambda r: r["interventions"].update(eachAnchor=None), "null"),
    ],
)
def test_each_anchor_is_refused_where_it_would_test_nothing_new(change, message):
    raw = framed(["s22", "s23"], NOTIFY)
    change(raw)
    with pytest.raises(FrameError, match=message):
        parse(raw)


def test_a_bypass_of_one_anchor_is_asked_beside_that_anchors_trial():
    # the same body, two questions: the bypass settles no hidden fallback,
    # the anchor's trial is evidence
    raw = framed(["s22", "s23"], NOTIFY, bypass=["s23"])
    raw["allowed"]["bypass"] = ["open"]
    finding = read(raw, lambda seen: "Sam" if seen == {"s22", "s23"} else "open")
    bodies = {t.id: t.body_hash for t in plan(parse(raw))}
    assert bodies["bypass"] == bodies["ablation-s23"]
    assert finding.category == CARRIED
    assert finding.evidence[-2:] == [
        "bypass moved it Sam -> open: no hidden fallback",
        "each anchor carries it",
    ]


def test_the_plan_says_which_anchor_each_trial_cuts(tmp_path, capsys):
    path = tmp_path / "frame.json"
    path.write_text(json.dumps(framed(["s22", "s23"], NOTIFY)))
    assert main(["plan", str(path), "--json"]) == 0
    trials = {t["id"]: t for t in json.loads(capsys.readouterr().out)["trials"]}
    assert (trials["ablation-s23"]["kind"], trials["ablation-s23"]["change"]) == (
        "each-anchor",
        "cuts s23",
    )
