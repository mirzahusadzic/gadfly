"""Recoil through frames (`midwife.recoil`, docs/breadth/recoil.md).

The case is a set of five nesting dolls, after the boy and the girl that
meaning representations have always started with. Each doll is a frame that
quotes the doll it came out of. All five are painted alike, the largest as
girlish as paint gets, and paint says nothing of who a doll is: only a doll's
own word does. The second doll's word is lost, and turns up in the smallest.

No model is called. The doll reader keeps to a doll's own word and never
reads the paint; the superstitious reader guesses from the paint when the
word is missing, and is caught for it.
"""

import copy
import random

import pytest

from midwife.errors import FrameError, RecordsError, UsageError
from midwife.frame import parse
from midwife.interventions import plan, prompt
from midwife.pipeline import calls_needed, judge, run
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
BINDING = "Only a doll's own word says who it is."
WORKSHOP = "The set was painted in one workshop."
SLIP = 'On a slip, in its own hand, the second doll wrote "I am a boy."'
ORDINALS = ("largest", "second", "third", "fourth", "smallest")


def span(id, text, kind, quoted=False):
    return {
        "id": id,
        "text": text,
        "kind": kind,
        **({"source": {"sha256": sha256(text)}} if quoted else {}),
    }


def opens(n):
    # the line a doll's own paint says, and the doll inside it quotes
    return f"The {ORDINALS[n]} doll opens at the waist, and the {ORDINALS[n + 1]} doll sits inside."


def doll(n, paint, question, labels, anchors, extra=(), **fields):
    name = f"{ORDINALS[n]} doll"
    spans = [span("from", opens(n - 1), "inside", quoted=True)] if n else []
    spans += [span(f"paint-{i}", text, "paint") for i, text in enumerate(paint, 1)]
    spans += list(extra)
    if n < 4:
        spans.append(span("opens", opens(n), "inside"))
    return {
        "name": name,
        "relation": f"who the {name} is rests on its own word",
        "locus": f"the {name}'s paint and words",
        "role": "a collector cataloguing a set",
        "grain": "one doll",
        "purpose": "name each doll for the catalogue",
        "trajectory": "the dolls as unpacked, the collector's reading, the catalogue",
        "crossing": "the catalogue entry",
        "promise": "a doll is named by its own word, never by its paint",
        "baseline": "the doll as unpacked; nothing changed",
        "body": {"spans": spans},
        "anchors": anchors,
        "inputs": [{"id": "who", "text": question}],
        "observe": {
            "labels": labels,
            "instruction": "Name the doll by its own word; unclear when it says none.",
        },
        "interventions": {"repeat": True, "ablation": True},
        "allowed": {"ablation": ["unclear"]},
        "standing": {"quorum": 1, "agree": 1},
        "materialized": True,
        "battery": {"kind": "doll-reader"},
        **fields,
    }


GIRLISH = (
    "The largest doll is painted pink from head to hem.",
    "The largest doll wears a red headscarf with white flowers.",
    "The largest doll's apron is painted with roses.",
    "The largest doll holds a basket of painted berries.",
    "The largest doll's cheeks are painted rosy, and its lashes long.",
)
ALIKE = (
    "The {} doll is painted yellow, with a green headscarf.",
    "The {} doll's apron is painted with daisies.",
)
WHO = ["girl", "boy", "unclear"]


def matryoshka():
    # five dolls, each quoting the one it came out of; the smallest also
    # carries the workshop's mark, so it quotes the largest as well
    largest = doll(
        0,
        GIRLISH,
        "Whose set is this?",
        ["girls", "unclear"],
        ["paint-2"],
        extra=[span("workshop", WORKSHOP, "mark")],
        holes=[{"id": "inside", "kind": "role"}],
    )
    second = doll(
        1,
        [line.format("second") for line in ALIKE],
        "Who is the second doll?",
        WHO,
        ["binding"],  # while its word is lost, the note alone names no one
        extra=[span("binding", BINDING, "note")],
        holes=[{"id": "says", "kind": "statement"}],
        offers="role",
    )
    third = doll(
        2,
        [line.format("third") for line in ALIKE],
        "Who is the third doll?",
        WHO,
        ["paint-1"],
        holes=[{"id": "base", "kind": "base"}],  # its base is lost: another kind
    )
    fourth = doll(
        3, [line.format("fourth") for line in ALIKE], "Who is the fourth doll?", WHO, ["paint-1"]
    )
    smallest = doll(
        4,
        [line.format("smallest") for line in ALIKE],
        "What does the smallest doll hold?",
        ["a slip", "nothing", "unclear"],
        ["slip"],
        extra=[span("mark", WORKSHOP, "mark", quoted=True), span("slip", SLIP, "statement")],
    )
    return largest, second, third, fourth, smallest


def dolls():
    return tuple(parse(raw) for raw in matryoshka())


class DollReader:
    """Keeps to a doll's own word while the binding note stands, and never
    reads the paint; a chipped base is chipped whatever the doll says."""

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
        if '"I am a boy."' in body:
            return Observation(label="boy")
        if '"I am a girl."' in body:
            return Observation(label="girl")
        return self.guess(body)

    def guess(self, body):
        return Observation(label="unclear")


class Superstitious(DollReader):
    """The doll reader, which guesses from the paint when a doll says nothing."""

    def guess(self, body):
        girlish = ("headscarf", "apron", "pink", "roses")
        return Observation(label="girl" if any(w in body for w in girlish) else "unclear")


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
TRIALS = {
    "interventions": {
        "repeat": True,
        "ablation": True,
        "sham": {"draws": 2, "kind": {"says": "paint"}},
        "presentation": {"slip": "card"},
        "bypass": ["binding"],
        "control": ["paint-1", "paint-2", "says"],
    },
    "allowed": {"ablation": ["unclear"], "bypass": ["unclear"]},
    "standing": LIGHT,
}


def with_slip(second, **changes):
    return parse(successor(second, "says", found(dolls()[4], "slip"), **{**TRIALS, **changes}))


def budget(frame, runs=5):
    return Budget(calls=runs * calls_needed(frame))


def names(frames):
    return sorted(frame.name for frame in frames)


def test_the_slip_climbs_past_every_doll_it_does_not_fit():
    largest, second, third, fourth, smallest = everything = dolls()
    walked = walk(found(smallest, "slip"), smallest, everything)
    # the fourth and third dolls pass it on (the third's hole wants a base),
    # the second fits it, and the largest passes it on: its hole wants a role
    assert [(frame.name, holes) for frame, holes in walked.fits] == [("second doll", ("says",))]
    assert names(walked.passed) == ["fourth doll", "largest doll", "third doll"]
    assert walked.complete
    assert {
        "piece": sha256(SLIP),
        "kind": "statement",
        "frame": second.hash,
        "name": "second doll",
        "fits": ["says"],
    } in walked.lines()


def test_a_shared_parent_is_visited_once_and_a_missing_one_is_the_frontier():
    largest, second, third, fourth, smallest = dolls()
    slip = found(smallest, "slip")
    # the smallest doll quotes the largest's mark, and the largest is also
    # reached through every doll between: many routes, one visit
    passed = walk(slip, smallest, [largest, second, third, fourth, smallest]).passed
    assert [frame.name for frame in passed].count("largest doll") == 1
    # without the largest, both quotes of it are unanswered, and the walk is
    # not complete; the smallest's quote of the mark never stands in for it
    walked = walk(slip, smallest, [second, third, fourth, smallest])
    assert walked.frontier == tuple(sorted({sha256(WORKSHOP), sha256(opens(0))}))
    assert not walked.complete


def test_the_second_doll_with_its_word_is_a_boy_asked_once_and_carried():
    second = dolls()[1]
    after = with_slip(second)
    assert reframes(second, after) == []  # it filled its hole, and was asked lightly
    reader = DollReader()
    asked = until_firm(after, reader, budget(after))
    # a reader that never wavers is firm after one light run, and disengages
    assert asked.firm and len(asked.runs) == 1 and asked.made == calls_needed(after)
    assert reader.calls == asked.made
    assert asked.category == "carried" and asked.shares == {"who": 1.0}
    recoil = gate(second, after, asked)
    assert (recoil.gate, recoil.category) == ("climbs", "carried")
    assert recoil.climbs == (Piece("second doll reads boy", "role"),)
    # the successor's ablation cuts the slip, which is the doll as it was
    # unpacked, byte for byte: the call its own baseline already made
    ablation = next(trial for trial in plan(after) if trial.id == "ablation")
    question = second.inputs[0]
    assert prompt(after, ablation, question) == prompt(second, plan(second)[0], question)


def test_a_reader_that_guesses_from_the_paint_is_caught():
    second = dolls()[1]
    after = with_slip(second)
    asked = until_firm(after, Superstitious(), budget(after))
    # a boy by his word, a girl by the paint once the word is cut: the
    # answer moved where the frame does not allow
    assert asked.firm and asked.category == "coupled but misaligned"
    assert asked.findings[0].levels["ablation"] == "girl"
    recoil = gate(second, after, asked)
    assert (recoil.gate, recoil.category) == ("climbs", "coupled but misaligned")


def test_a_boy_by_his_own_word_reframes_the_girlish_set():
    largest, second, *_ = dolls()
    after = with_slip(second)
    recoil = gate(second, after, until_firm(after, DollReader(), budget(after)))
    [boy] = recoil.climbs
    walked = walk(boy, after, [largest, after])
    assert [(frame.name, holes) for frame, holes in walked.fits] == [("largest doll", ("inside",))]
    # the set was taken for girls by its paint: a boy inside, by his own
    # word, needs a label the set lacks, so the set asked again asks another
    # question, read against no category and asked nothing
    labels = {"labels": ["girls", "boys", "mixed", "unclear"], "instruction": "Name the set."}
    asked_again = parse(successor(largest, "inside", boy, observe=labels))
    assert gate(largest, asked_again).gate == "reframing"
    assert gate(largest, asked_again).changed == ("observe",)
    assert largest.raw["observe"]["labels"] == ["girls", "unclear"]  # the set as asked stands


def test_a_doll_whose_question_does_not_rest_on_its_word_absorbs_it():
    second = matryoshka()[1]
    based = copy.deepcopy(second)
    based["body"]["spans"].insert(3, span("base", "The second doll's base is chipped.", "base"))
    based["inputs"] = [{"id": "base", "text": "Is the second doll's base whole?"}]
    based["observe"] = {"labels": ["whole", "chipped", "unclear"], "instruction": "Read the base."}
    based = parse(based)
    after = parse(
        successor(
            based,
            "says",
            Piece(SLIP, "statement"),
            interventions={"repeat": True, "ablation": True, "control": ["base", "says"]},
            standing=LIGHT,
        )
    )
    recoil = gate(based, after, until_firm(after, DollReader(), budget(after)))
    # the word fits, is asked again, and changes nothing: nothing climbs
    assert (recoil.gate, recoil.category, recoil.climbs) == ("absorbed", "cooled", ())


def test_a_shaky_reader_is_asked_again_until_its_verdict_is_firm():
    middle = dolls()[1]
    after = with_slip(middle)
    each = calls_needed(after)
    asked = until_firm(after, Shaky(shaky=each), budget(after))
    # the first run wavers, the second is firm and reads as the first did
    # not, the third is firm and reads as the second: then it disengages
    assert asked.firm and asked.category == "carried"
    assert len(asked.runs) == 3 and asked.made == 3 * each


def test_a_reader_that_never_settles_stops_at_the_most_runs_and_the_gate_stops():
    middle = dolls()[1]
    after = with_slip(middle)
    each = calls_needed(after)
    asked = until_firm(after, Shaky(shaky=10**6), budget(after, 3), most=3)
    assert not asked.firm and len(asked.runs) == 3 and asked.made == 3 * each
    recoil = gate(middle, after, asked)
    assert recoil.gate == "stops"
    assert recoil.open == "its verdict was not firm after 3 runs"


def test_kept_runs_count_as_runs_made_so_a_firm_frame_is_asked_nothing():
    middle = dolls()[1]
    after = with_slip(middle)
    first = until_firm(after, DollReader(), budget(after))
    reader = DollReader()
    again = until_firm(after, reader, budget(after), kept=first.runs)
    assert again.firm and again.made == 0 and reader.calls == 0
    assert again.runs == first.runs and again.category == "carried"


def test_until_firm_never_starts_a_run_the_budget_cannot_cover():
    middle = dolls()[1]
    after = with_slip(middle)
    reader = DollReader()
    asked = until_firm(after, reader, Budget(calls=calls_needed(after) - 1))
    assert not asked.firm and asked.made == 0 and reader.calls == 0
    assert asked.stopped == f"the budget covers no further run of {calls_needed(after)} calls"
    assert gate(middle, after, asked).open == asked.stopped


def test_until_firm_refuses_what_it_cannot_read():
    middle = dolls()[1]
    once = with_slip(middle, standing={"quorum": 1, "agree": 1})
    with pytest.raises(UsageError, match="asks each trial once"):
        until_firm(once, DollReader(), budget(once))
    after = with_slip(middle)
    for firm, most in ((0, 5), (1.5, 5), (True, 5), (0.9, 0), (0.9, 2.0)):
        with pytest.raises(UsageError):
            until_firm(after, DollReader(), budget(after), firm=firm, most=most)
    # a successor that asks the same question is read from its own runs
    with pytest.raises(UsageError, match="its own runs"):
        gate(middle, after)


def test_a_piece_fills_only_a_hole_of_its_kind():
    the_set, middle, *_, smallest = dolls()
    with pytest.raises(UsageError, match="hole 'inside' is of kind 'role'"):
        successor(the_set, "inside", found(smallest, "slip"))
    with pytest.raises(UsageError, match="has no hole 'base'"):
        successor(middle, "base", found(smallest, "slip"))
    with pytest.raises(UsageError, match="has no span 'tail'"):
        found(smallest, "tail")
    with pytest.raises(UsageError, match="offers no kind"):
        decided(smallest, "a slip")
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
    middle = matryoshka()[1]
    middle["holes"], middle["offers"] = holes, offers
    if offers is None and holes is not None:
        del middle["offers"]
    with pytest.raises(FrameError, match=message):
        parse(middle)


def test_holes_and_offers_are_hashed_and_change_no_other_frame():
    middle = matryoshka()[1]
    without = {k: v for k, v in middle.items() if k not in ("holes", "offers")}
    assert parse(middle).hash != parse(without).hash
    assert parse(middle).holes == ({"id": "says", "kind": "statement"},)
    assert parse(middle).offers == "role" and parse(without).offers is None
    assert parse(without).holes == ()


class Spending(Shaky):
    """The shaky reader, saying it wrote ten tokens each call."""

    def observe(self, frame, prompt, max_output_tokens):
        seen = super().observe(frame, prompt, max_output_tokens)
        return Observation(label=seen.label, usage={"output_tokens": 10})


def test_until_firm_starts_no_run_the_tokens_cannot_cover_whole():
    middle = dolls()[1]
    after = with_slip(middle)
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
    middle = dolls()[1]
    after = with_slip(middle)
    asked = until_firm(after, Overspending(), budget(after))
    # the run stops after the call that broke its cap, as every run does
    assert not asked.firm and asked.made == 1 and asked.category is None
    assert asked.stopped and gate(middle, after, asked).open == asked.stopped


def test_a_kept_run_with_no_records_is_refused():
    middle = dolls()[1]
    after = with_slip(middle)
    with pytest.raises(RecordsError, match="a kept run holds no records"):
        until_firm(after, DollReader(), budget(after), kept=[[]])


def test_a_run_cut_short_is_not_given_back_as_a_whole_one():
    middle = dolls()[1]
    after = with_slip(middle)
    cut = until_firm(after, Overspending(), budget(after))
    with pytest.raises(RecordsError, match="a kept run is not whole"):
        until_firm(after, DollReader(), budget(after), kept=cut.runs)


def test_a_successor_closes_only_the_hole_it_fills():
    _, middle, *_, smallest = matryoshka()
    middle["holes"].append({"id": "base", "kind": "base"})
    draft = successor(parse(middle), "says", found(parse(smallest), "slip"), **TRIALS)
    assert draft["holes"] == [{"id": "base", "kind": "base"}]
    assert draft["anchors"] == ["says"] and draft["body"]["spans"][-1] == span(
        "says", SLIP, "statement", quoted=True
    )


def test_holes_stand_in_for_anchors_until_a_piece_fills_one():
    from jsonschema import Draft202012Validator

    from midwife.frame import schema

    waiting = matryoshka()[1]
    waiting["anchors"] = []  # its word is lost: the hole is all it rests on
    del waiting["interventions"]["repeat"]
    frame = parse(waiting)
    assert Draft202012Validator(schema()).is_valid(waiting)
    # walked, never asked: nothing to cut until the hole is filled
    with pytest.raises(FrameError, match="rests on its holes alone"):
        plan(frame)
    with pytest.raises(FrameError, match="rests on its holes alone"):
        calls_needed(frame)
    filled = parse(successor(frame, "says", Piece(SLIP, "statement"), **TRIALS))
    assert filled.anchors == ("says",) and calls_needed(filled) == 8 * 3
    # without holes, a frame still rests on at least one anchor
    del waiting["holes"], waiting["offers"]
    assert not Draft202012Validator(schema()).is_valid(waiting)
    with pytest.raises(FrameError, match="rests on at least one anchor"):
        parse(waiting)


def test_a_call_that_reports_no_tokens_is_charged_its_cap_as_run_charges_it():
    # a battery need not report what it wrote: run charges such a call its
    # cap, and so does until_firm, so no run starts past the token budget
    # (pass 11, F1)
    middle = dolls()[1]
    after = with_slip(middle)
    each = calls_needed(after)
    asked = until_firm(after, Shaky(shaky=10**6), Budget(5 * each, 64, 2 * each * 64))
    assert asked.made == 2 * each and not asked.firm
    assert asked.stopped == f"the token budget covers no further run of {each} calls"


def test_the_latest_kept_run_decides_not_an_earlier_firm_one():
    # a firm run kept before one that is not firm does not make the frame
    # firm: only the latest run decides (pass 11, F2)
    middle = dolls()[1]
    after = with_slip(middle)
    each = calls_needed(after)
    steady = until_firm(after, DollReader(), budget(after)).runs[0]
    wavering = tuple(r.as_dict() for r in run(after, Shaky(shaky=10**6), Budget(each)).records)
    asked = until_firm(after, None, Budget(calls=1), kept=[steady, wavering])
    assert not asked.firm and asked.made == 0
    assert asked.findings == tuple(judge(after, list(wavering)))


def test_until_firm_refuses_more_kept_runs_than_it_may_read():
    # most bounds the runs read, kept ones included, so none is returned
    # unread (pass 11, F11)
    middle = dolls()[1]
    after = with_slip(middle)
    kept = until_firm(after, DollReader(), budget(after)).runs * 3
    with pytest.raises(UsageError, match="kept holds more runs than most"):
        until_firm(after, None, Budget(calls=1), kept=kept, most=2)
