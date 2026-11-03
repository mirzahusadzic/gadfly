"""Recoil through frames (`midwife.recoil`, docs/breadth/recoil.md).

The case is a matryoshka, after the boy and the girl that meaning
representations have always started with: a set of three dolls, the middle
one missing its head, and the smallest holding a painted head with a beard.
Each doll is a frame that quotes the doll it came out of. No model is called:
a doll reader reads the paint by fixed rules.
"""

import copy
import random

import pytest

from midwife.errors import FrameError, RecordsError, UsageError
from midwife.frame import parse
from midwife.interventions import plan, prompt
from midwife.pipeline import calls_needed
from midwife.recoil import (
    Piece,
    decided,
    found,
    gate,
    reframes,
    sha256,
    successor,
    until_firm,
    walk,
)
from midwife.types import Budget, Observation

RULE = "\n\n---\n\n"
BINDING = "The painted head decides who a doll is."
WORKSHOP = "The set was painted in one workshop."
OPENS = "The largest doll opens at the waist, and the middle doll sits inside."
INSIDE = "The middle doll opens at the waist, and the smallest doll sits inside."
HEAD = "A painted head with a beard."


def span(id, text, kind, quoted=False):
    return {
        "id": id,
        "text": text,
        "kind": kind,
        **({"source": {"sha256": sha256(text)}} if quoted else {}),
    }


def doll(name, spans, question, labels, anchors, **fields):
    return {
        "name": name,
        "relation": f"who the {name} is rests on its paint",
        "locus": f"the {name}'s paint",
        "role": "a collector cataloguing a set",
        "grain": "one doll",
        "purpose": "name each doll for the catalogue",
        "trajectory": "the dolls as unpacked, the collector's reading, the catalogue",
        "crossing": "the catalogue entry",
        "promise": "a doll without its head is not named",
        "baseline": "the doll as unpacked; nothing changed",
        "body": {"spans": spans},
        "anchors": anchors,
        "inputs": [{"id": "who", "text": question}],
        "observe": {"labels": labels, "instruction": "Name the doll from its paint."},
        "interventions": {"repeat": True, "ablation": True},
        "allowed": {"ablation": ["unclear"]},
        "standing": {"quorum": 1, "agree": 1},
        "materialized": True,
        "battery": {"kind": "doll-reader"},
        **fields,
    }


def matryoshka():
    # each doll quotes the doll it came out of; the smallest also carries the
    # workshop's mark, so it quotes the set as well as the middle doll
    the_set = doll(
        "set",
        [
            span("aprons", "The set's dolls wear painted aprons.", "paint"),
            span("workshop", WORKSHOP, "mark"),
            span("opens", OPENS, "inside"),
        ],
        "Whose set is this?",
        ["girls", "unclear"],
        ["aprons"],
        holes=[{"id": "inside", "kind": "role"}],
    )
    middle = doll(
        "middle doll",
        [
            span("from", OPENS, "inside", quoted=True),
            span("body", "The middle doll is painted blue.", "paint"),
            span("spoon", "The middle doll holds a painted spoon.", "paint"),
            span("belt", "The middle doll wears a painted belt.", "paint"),
            span("binding", BINDING, "note"),
            span("opens", INSIDE, "inside"),
        ],
        "Who is the middle doll?",
        ["girl", "boy", "unclear"],
        ["binding"],  # while its head is missing, the note alone names no one
        holes=[{"id": "head", "kind": "head"}],
        offers="role",
    )
    smallest = doll(
        "smallest doll",
        [
            span("from", INSIDE, "inside", quoted=True),
            span("mark", WORKSHOP, "mark", quoted=True),
            span("head", HEAD, "head"),
        ],
        "What does the smallest doll hold?",
        ["a head", "nothing", "unclear"],
        ["head"],
    )
    return the_set, middle, smallest


def dolls():
    return tuple(parse(raw) for raw in matryoshka())


class DollReader:
    """Reads a doll's paint by fixed rules. The painted head names a doll
    while the binding note stands; a chipped base is chipped whatever the
    head says."""

    name = "doll-reader"

    def __init__(self):
        self.calls = 0

    def check(self, frame):
        pass

    def observe(self, frame, prompt, max_output_tokens):
        self.calls += 1
        body, _, question = prompt.partition(RULE)
        if "base" in question:
            return Observation(label="chipped" if "base is chipped" in body else "unclear")
        if BINDING not in body:
            return Observation(label="unclear")
        if "beard" in body or "moustache" in body:
            return Observation(label="boy")
        if "headscarf" in body:
            return Observation(label="girl")
        return Observation(label="unclear")


class Shaky(DollReader):
    """The doll reader, which for its first `shaky` calls answers at random."""

    def __init__(self, shaky, seed=7):
        super().__init__()
        self.shaky, self.rng = shaky, random.Random(seed)

    def observe(self, frame, prompt, max_output_tokens):
        if self.calls < self.shaky:
            self.calls += 1
            return Observation(label=self.rng.choice(frame.labels))
        return super().observe(frame, prompt, max_output_tokens)


LIGHT = {"quorum": 3, "agree": 2}  # a successor is asked lightly, and again only if it must be
WHO = {
    "interventions": {
        "repeat": True,
        "ablation": True,
        "sham": {"draws": 2, "kind": {"head": "paint"}},
        "presentation": {"beard": "moustache"},
        "bypass": ["binding"],
        "control": ["body", "spoon", "belt", "head"],
    },
    "allowed": {"ablation": ["unclear"], "bypass": ["unclear"]},
    "standing": LIGHT,
}


def with_head(middle, **changes):
    return parse(successor(middle, "head", found(dolls()[2], "head"), **{**WHO, **changes}))


def budget(frame, runs=5):
    return Budget(calls=runs * calls_needed(frame))


def test_the_head_climbs_past_every_frame_it_does_not_fit():
    the_set, middle, smallest = dolls()
    walked = walk(found(smallest, "head"), smallest, [the_set, middle, smallest])
    # it fits the middle doll, and climbs on to the set, which passes it on:
    # the set's hole wants a role, not a head
    assert [(frame.name, holes) for frame, holes in walked.fits] == [("middle doll", ("head",))]
    assert [frame.name for frame in walked.passed] == ["set"]
    assert walked.complete
    assert walked.lines() == [
        {"piece": sha256(HEAD), "kind": "head", "frame": middle.hash} | {"name": "middle doll"}
        | {"fits": ["head"]},
        {"piece": sha256(HEAD), "kind": "head", "frame": the_set.hash, "name": "set"}
        | {"passed": True},
    ]  # fmt: skip


def test_a_shared_parent_is_visited_once_and_a_missing_one_is_the_frontier():
    the_set, middle, smallest = dolls()
    head = found(smallest, "head")
    # the smallest doll quotes the set and the middle doll, which quotes the
    # set again: two routes, one visit
    assert len(walk(head, smallest, [the_set, middle, smallest]).passed) == 1
    # without the set, both quotes of it are unanswered, and the walk is not
    # complete; a frame quoting a text is not its maker, so the middle doll's
    # quote of the set never stands in for the set
    walked = walk(head, smallest, [middle, smallest])
    assert walked.frontier == tuple(sorted({sha256(WORKSHOP), sha256(OPENS)}))
    assert not walked.complete
    assert {"piece": sha256(HEAD), "kind": "head", "frontier": sha256(OPENS)} in walked.lines()


def test_the_middle_doll_with_its_head_is_a_boy_asked_once_and_carried():
    _, middle, _ = dolls()
    after = with_head(middle)
    assert reframes(middle, after) == []  # it filled its hole, and was asked lightly
    reader = DollReader()
    asked = until_firm(after, reader, budget(after))
    # a reader that never wavers is firm after one light run, and disengages
    assert asked.firm and len(asked.runs) == 1 and asked.made == calls_needed(after)
    assert reader.calls == asked.made
    assert asked.category == "carried" and asked.shares == {"who": 1.0}
    recoil = gate(middle, after, asked)
    assert (recoil.gate, recoil.category) == ("climbs", "carried")
    assert recoil.climbs == (Piece("middle doll reads boy", "role"),)
    # the successor's ablation cuts the head, which is the doll as it was
    # unpacked, byte for byte: the call its own baseline already made
    ablation = next(trial for trial in plan(after) if trial.id == "ablation")
    unpacked = plan(middle)[0]
    question = middle.inputs[0]
    assert prompt(after, ablation, question) == prompt(middle, unpacked, question)


def test_a_boy_inside_reframes_the_girls_set():
    the_set, middle, _ = dolls()
    after = with_head(middle)
    recoil = gate(middle, after, until_firm(after, DollReader(), budget(after)))
    [boy] = recoil.climbs
    walked = walk(boy, after, [the_set, after])
    assert [(frame.name, holes) for frame, holes in walked.fits] == [("set", ("inside",))]
    # the set was asked girls or unclear: a boy inside needs a label it
    # lacks, so the set asked again asks another question, read against no
    # category and asked nothing
    labels = {"labels": ["girls", "boys", "mixed", "unclear"], "instruction": "Name the set."}
    asked_again = parse(successor(the_set, "inside", boy, observe=labels))
    assert gate(the_set, asked_again).gate == "reframing"
    assert gate(the_set, asked_again).changed == ("observe",)
    assert the_set.raw["observe"]["labels"] == ["girls", "unclear"]  # the set as asked stands


def test_a_doll_whose_question_does_not_rest_on_its_head_absorbs_it():
    _, middle, _ = matryoshka()
    based = copy.deepcopy(middle)
    based["body"]["spans"].insert(4, span("base", "The middle doll's base is chipped.", "base"))
    based["inputs"] = [{"id": "base", "text": "Is the middle doll's base whole?"}]
    based["observe"] = {"labels": ["whole", "chipped", "unclear"], "instruction": "Read the base."}
    based = parse(based)
    after = parse(
        successor(
            based,
            "head",
            Piece(HEAD, "head"),
            interventions={"repeat": True, "ablation": True, "control": ["base", "head"]},
            standing=LIGHT,
        )
    )
    recoil = gate(based, after, until_firm(after, DollReader(), budget(after)))
    # the head fits, is asked again, and changes nothing: nothing climbs
    assert (recoil.gate, recoil.category, recoil.climbs) == ("absorbed", "cooled", ())


def test_a_shaky_reader_is_asked_again_until_its_verdict_is_firm():
    _, middle, _ = dolls()
    after = with_head(middle)
    each = calls_needed(after)
    asked = until_firm(after, Shaky(shaky=each), budget(after))
    # the first run wavers, the second is firm and reads as the first did
    # not, the third is firm and reads as the second: then it disengages
    assert asked.firm and asked.category == "carried"
    assert len(asked.runs) == 3 and asked.made == 3 * each


def test_a_reader_that_never_settles_stops_at_the_most_runs_and_the_gate_stops():
    _, middle, _ = dolls()
    after = with_head(middle)
    each = calls_needed(after)
    asked = until_firm(after, Shaky(shaky=10**6), budget(after, 3), most=3)
    assert not asked.firm and len(asked.runs) == 3 and asked.made == 3 * each
    recoil = gate(middle, after, asked)
    assert recoil.gate == "stops"
    assert recoil.open == "its verdict was not firm after 3 runs"


def test_kept_runs_count_as_runs_made_so_a_firm_frame_is_asked_nothing():
    _, middle, _ = dolls()
    after = with_head(middle)
    first = until_firm(after, DollReader(), budget(after))
    reader = DollReader()
    again = until_firm(after, reader, budget(after), kept=first.runs)
    assert again.firm and again.made == 0 and reader.calls == 0
    assert again.runs == first.runs and again.category == "carried"


def test_until_firm_never_starts_a_run_the_budget_cannot_cover():
    _, middle, _ = dolls()
    after = with_head(middle)
    reader = DollReader()
    asked = until_firm(after, reader, Budget(calls=calls_needed(after) - 1))
    assert not asked.firm and asked.made == 0 and reader.calls == 0
    assert asked.stopped == f"the budget covers no further run of {calls_needed(after)} calls"
    assert gate(middle, after, asked).open == asked.stopped


def test_until_firm_refuses_what_it_cannot_read():
    _, middle, _ = dolls()
    once = with_head(middle, standing={"quorum": 1, "agree": 1})
    with pytest.raises(UsageError, match="asks each trial once"):
        until_firm(once, DollReader(), budget(once))
    after = with_head(middle)
    for firm, most in ((0, 5), (1.5, 5), (True, 5), (0.9, 0), (0.9, 2.0)):
        with pytest.raises(UsageError):
            until_firm(after, DollReader(), budget(after), firm=firm, most=most)
    # a successor that asks the same question is read from its own runs
    with pytest.raises(UsageError, match="its own runs"):
        gate(middle, after)


def test_a_piece_fills_only_a_hole_of_its_kind():
    the_set, middle, smallest = dolls()
    with pytest.raises(UsageError, match="hole 'inside' is of kind 'role'"):
        successor(the_set, "inside", found(smallest, "head"))
    with pytest.raises(UsageError, match="has no hole 'base'"):
        successor(middle, "base", found(smallest, "head"))
    with pytest.raises(UsageError, match="has no span 'tail'"):
        found(smallest, "tail")
    with pytest.raises(UsageError, match="offers no kind"):
        decided(smallest, "a head")
    with pytest.raises(UsageError, match="has no label 'man'"):
        decided(middle, "man")


@pytest.mark.parametrize(
    "holes, offers, message",
    [
        ([], None, "holes lists what the body is missing"),
        ([{"id": "head"}], None, "holes lists what the body is missing"),
        ([{"id": "head", "kind": "head", "x": "y"}], None, "holes lists"),
        ([{"id": "head", "kind": ""}], None, "holes lists"),
        ([{"id": "binding", "kind": "note"}], None, "holes name span 'binding', which the body"),
        ([{"id": "a", "kind": "x"}, {"id": "a", "kind": "y"}], None, "two holes share an id"),
        ([{"id": "a: b", "kind": "x"}], None, "hole id 'a: b' is not one plain name"),
        ([{"id": "head", "kind": "head"}], "", "offers names the kind"),
        ([{"id": "head", "kind": "head"}], 5, "offers names the kind"),
        (None, None, "key 'holes' is null"),
    ],
)
def test_the_parser_refuses_holes_it_cannot_read(holes, offers, message):
    _, middle, _ = matryoshka()
    middle["holes"], middle["offers"] = holes, offers
    if offers is None and holes is not None:
        del middle["offers"]
    with pytest.raises(FrameError, match=message):
        parse(middle)


def test_holes_and_offers_are_hashed_and_change_no_other_frame():
    _, middle, _ = matryoshka()
    without = {k: v for k, v in middle.items() if k not in ("holes", "offers")}
    assert parse(middle).hash != parse(without).hash
    assert parse(middle).holes == ({"id": "head", "kind": "head"},)
    assert parse(middle).offers == "role" and parse(without).offers is None
    assert parse(without).holes == ()


class Spending(Shaky):
    """The shaky reader, saying it wrote ten tokens each call."""

    def observe(self, frame, prompt, max_output_tokens):
        seen = super().observe(frame, prompt, max_output_tokens)
        return Observation(label=seen.label, usage={"output_tokens": 10})


def test_until_firm_starts_no_run_the_tokens_cannot_cover_whole():
    _, middle, _ = dolls()
    after = with_head(middle)
    each = calls_needed(after)
    # one run at each call's cap, and nearly a second: the reader says it
    # wrote ten tokens a call, but a run is covered only at the cap
    asked = until_firm(after, Spending(shaky=10**6), Budget(5 * each, 64, 64 * each + 63))
    assert not asked.firm and len(asked.runs) == 1 and asked.made == each
    assert asked.stopped == f"the token budget covers no further run of {each} calls"


class Overspending(DollReader):
    """The doll reader, saying it wrote past the cap it was given."""

    def observe(self, frame, prompt, max_output_tokens):
        seen = super().observe(frame, prompt, max_output_tokens)
        return Observation(label=seen.label, usage={"output_tokens": max_output_tokens + 1})


def test_a_run_cut_short_is_never_read_as_firm():
    _, middle, _ = dolls()
    after = with_head(middle)
    asked = until_firm(after, Overspending(), budget(after))
    # the run stops after the call that broke its cap, as every run does
    assert not asked.firm and asked.made == 1 and asked.category is None
    assert asked.stopped and gate(middle, after, asked).open == asked.stopped


def test_a_kept_run_with_no_records_is_refused():
    _, middle, _ = dolls()
    after = with_head(middle)
    with pytest.raises(RecordsError, match="a kept run holds no records"):
        until_firm(after, DollReader(), budget(after), kept=[[]])


def test_a_run_cut_short_is_not_given_back_as_a_whole_one():
    _, middle, _ = dolls()
    after = with_head(middle)
    cut = until_firm(after, Overspending(), budget(after))
    with pytest.raises(RecordsError, match="a kept run is not whole"):
        until_firm(after, DollReader(), budget(after), kept=cut.runs)


def test_a_successor_closes_only_the_hole_it_fills():
    _, middle, smallest = matryoshka()
    middle["holes"].append({"id": "base", "kind": "base"})
    draft = successor(parse(middle), "head", found(parse(smallest), "head"), **WHO)
    assert draft["holes"] == [{"id": "base", "kind": "base"}]
    assert draft["anchors"] == ["head"] and draft["body"]["spans"][-1] == span(
        "head", HEAD, "head", quoted=True
    )
