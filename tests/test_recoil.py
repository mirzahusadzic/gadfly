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
import hashlib
import json
import math
import random
import re
import warnings
from dataclasses import replace
from types import SimpleNamespace

import pytest

from midwife.errors import FrameError, RecordsError, StoppedWarning, UsageError
from midwife.frame import parse
from midwife.interventions import plan, prompt
from midwife.pipeline import calls_needed, judge, run
from midwife.recoil import (
    MOST,
    Piece,
    Vectors,
    calls_until_firm,
    decided,
    found,
    gate,
    read_vectors,
    reframes,
    sha256,
    successor,
    until_firm,
    walk,
)
from midwife.stats import stability
from midwife.types import Budget, Observation

RULE = "\n\n---\n\n"
BINDING = "Only a doll's own word says who it is."
SHARED = "The line every frame of a star holds as its own."
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


class Counted:
    """A frame, its hash's readings counted: the walk reads it once a visit."""

    def __init__(self, frame, reads):
        self._frame, self._reads = frame, reads

    def __getattr__(self, name):
        if name == "hash":
            self._reads.append(1)
        return getattr(self._frame, name)


def test_a_text_many_frames_share_is_followed_once():
    # n frames each hold one text and quote it: the walk follows the text
    # once, so its work grows with the frames, not their square (pass 12, P2)
    def star(name, own):
        raw = copy.deepcopy(dolls()[4].raw)
        quoted = {"id": "q", "text": SHARED, "kind": "note", "source": {"sha256": sha256(SHARED)}}
        raw["name"] = name
        raw["body"] = {"spans": [{"id": "own", "text": own, "kind": "note"}, quoted]}
        raw["anchors"] = ["own"]
        raw.pop("holes", None)
        raw["interventions"] = {"ablation": True}
        raw["allowed"] = {"ablation": ["unclear"]}
        return raw

    def reads(n):
        counted = []
        start = Counted(parse(star("start", "the start's own line")), counted)
        frames = [
            Counted(
                parse({**star(f"star-{i}", SHARED), "holes": [{"id": "h", "kind": "note"}]}),
                counted,
            )
            for i in range(n)
        ]
        walked = walk(Piece(SHARED, "note"), start, frames)
        assert len(walked.fits) == n and not walked.passed and walked.complete
        return len(counted)

    assert reads(40) <= 2.2 * reads(20)


def star(name, own, inputs=1, holes=(), quorum=3):
    # a frame holding `own` and quoting the shared line, asked of `inputs`
    # questions, `quorum` calls a trial, with `holes` of kind note
    raw = copy.deepcopy(dolls()[4].raw)
    quoted = {"id": "q", "text": SHARED, "kind": "note", "source": {"sha256": sha256(SHARED)}}
    raw["name"] = name
    raw["body"] = {"spans": [{"id": "own", "text": own, "kind": "note"}, quoted]}
    raw["anchors"] = ["own"]
    raw["inputs"] = [{"id": f"x{i}", "text": f"Question {i}?"} for i in range(inputs)]
    raw["standing"] = {"quorum": quorum, "agree": 2 if quorum > 1 else 1}
    raw.pop("holes", None)
    if holes:
        raw["holes"] = [{"id": hole, "kind": "note"} for hole in holes]
    raw["interventions"] = {"ablation": True}
    raw["allowed"] = {"ablation": ["unclear"]}
    return parse(raw)


def test_a_walks_budget_asks_its_fits_in_order_up_to_the_first_it_cannot_cover():
    start = star("start", "the start's own line")
    wide = star("wide", SHARED, inputs=2, holes=["h"])  # two questions: twice the calls
    narrow = star("narrow", SHARED, holes=["h", "g"])  # two holes: two fits
    piece = Piece(SHARED, "note")
    each = calls_until_firm(parse(successor(narrow, "h", piece)))
    assert each == 2 * 3 * MOST  # baseline and ablation, three calls each, five runs
    walked = walk(piece, start, [wide, narrow])
    assert [(fit.frame.name, fit.hole, fit.calls, fit.asked) for fit in walked.order] == [
        ("wide", "h", None, None),
        ("narrow", "h", None, None),
        ("narrow", "g", None, None),
    ]
    assert walked.budget is None and walked.most is None and walked.unasked == ()
    # enough for the wide fit and one narrow one: the last is listed, not asked
    walked = walk(piece, start, [wide, narrow], calls=3 * each)
    assert [(fit.calls, fit.asked) for fit in walked.order] == [
        (2 * each, True),
        (each, True),
        (each, False),
    ]
    assert [(fit.frame.name, fit.hole) for fit in walked.unasked] == [("narrow", "g")]
    # too little for the wide fit: nothing after it is asked before it, though it fits
    walked = walk(piece, start, [wide, narrow], calls=2 * each - 1)
    assert [fit.asked for fit in walked.order] == [False, False, False]
    # fewer runs a fit, fewer calls each
    walked = walk(piece, start, [wide, narrow], calls=2 * each - 1, most=2)
    assert [(fit.calls, fit.asked) for fit in walked.order] == [(24, True), (12, True), (12, True)]
    lines = walked.lines()
    assert [line["fits"] for line in lines] == [["h"], ["h"], ["g"]]  # a line a hole
    assert lines[0] == {
        "piece": piece.sha256,
        "kind": "note",
        "budget": 2 * each - 1,
        "most": 2,
        "frame": wide.hash,
        "name": "wide",
        "fits": ["h"],
        "calls": 24,
        "asked": True,
    }


def test_a_walks_budget_refuses_what_it_cannot_count():
    start = star("start", "the start's own line")
    piece = Piece(SHARED, "note")
    fitted = star("fitted", SHARED, holes=["h"])
    for calls in (0, -1, True, 1.5):
        with pytest.raises(UsageError, match="a walk's budget is a whole number of calls"):
            walk(piece, start, [fitted], calls=calls)
    with pytest.raises(UsageError, match="most is a whole number of runs, at least 1"):
        walk(piece, start, [fitted], calls=10, most=0)
    # a fit whose successor cannot be asked until firm is named where the walk met it
    once = star("once", SHARED, holes=["h"], quorum=1)
    with pytest.raises(UsageError, match="asks each trial once") as refused:
        walk(piece, start, [fitted, once], calls=10)
    said = "the walk's budget counts the successor of frame 'once' with hole 'h' filled, as drafted"
    assert refused.value.__notes__[-1] == said
    assert walk(piece, start, [fitted, once]).order[1].frame.name == "once"  # no budget, no count


def jsonl(*vectors):
    # vectors as a caller writes them: each (text, space, values), one a line
    lines = (
        json.dumps({"text": sha256(text), "space": space, "values": values})
        for text, space, values in vectors
    )
    return "".join(line + "\n" for line in lines)


def read_for(name, about=None):
    # a frame holding the shared line, with one hole of kind note, read for `about`
    frame = star(name, SHARED, holes=["h"])
    raw = copy.deepcopy(frame.raw)
    raw["holes"] = [{"id": "h", "kind": "note", **({"about": about} if about else {})}]
    return parse(raw)


def test_read_vectors_takes_whole_texts_one_a_space():
    text = jsonl(("a", "s", [1, 0.5]), ("a", "t", [2.0, -1, 3]), ("b", "s", [0, 0]))
    vectors = read_vectors(text.replace("\n", "\r\n", 1))
    assert vectors.spaces == ("s", "t")
    assert vectors.values[sha256("a"), "s"] == (1.0, 0.5)
    assert vectors.values[sha256("a"), "t"] == (2.0, -1.0, 3.0)
    raw = text.encode()
    assert read_vectors(raw).sha256 == hashlib.sha256(raw).hexdigest()  # what was read, whole
    # a value that is not finite is kept, to give no order where it is read
    kept = read_vectors(
        '{"text": "%s", "space": "s", "values": [NaN, 1e999, %s]}' % (sha256("a"), "9" * 400)
    )
    assert [math.isfinite(x) for x in kept.values[sha256("a"), "s"]] == [False, False, False]


@pytest.mark.parametrize(
    "text, message",
    [
        (b"\xff", "the text given is not UTF-8 text"),
        ("{", "the text given cannot be read as JSON at line 1"),
        ("\n[1]", "the text given holds a vector that is not {text, space, values} at line 2"),
        ('{"text": "a", "space": "s", "values": [1], "x": 1}', "is not {text, space, values}"),
        ('{"text": "A%s", "space": "s", "values": [1]}' % ("0" * 63), "keys a vector by 'A0"),
        ('{"text": 5, "space": "s", "values": [1]}', "keys a vector by 5 at line 1"),
        ('{"text": "%s", "space": "", "values": [1]}' % sha256("a"), "names space ''"),
        ('{"text": "%s", "space": "a: b", "values": [1]}' % sha256("a"), "not one plain name"),
        ('{"text": "%s", "space": 7, "values": [1]}' % sha256("a"), "names space 7"),
        ('{"text": "%s", "space": "s", "values": []}' % sha256("a"), "not a list of numbers"),
        ('{"text": "%s", "space": "s", "values": [true]}' % sha256("a"), "not a list of numbers"),
        ('{"text": "%s", "space": "s", "values": "1"}' % sha256("a"), "not a list of numbers"),
        (
            jsonl(("a", "s", [1]), ("b", "s", [1]), ("a", "s", [1])),
            "in space 's' twice, at lines 1 and 3",
        ),
    ],
)
def test_read_vectors_refuses_what_it_cannot_take(text, message):
    with pytest.raises(UsageError, match=re.escape(message)):
        read_vectors(text)


def test_vectors_order_the_fits_and_a_fit_with_no_cosine_keeps_its_place():
    start = star("start", "the start's own line")
    piece = Piece(SHARED, "note")
    a, b, c, d = (
        read_for(n, about) for n, about in [("a", "A"), ("b", "B"), ("c", None), ("d", "D")]
    )
    given = [a, b, c, d]
    vectors = read_vectors(
        jsonl((SHARED, "s", [1, 0]), ("A", "s", [0, 3]), ("B", "s", [1, 1]), ("D", "s", [2, 0]))
    )
    walked = walk(piece, start, given, vectors=vectors)
    # d (1), b (0.71) and a (0) sort among the places they hold; c keeps its own
    assert [fit.frame.name for fit in walked.order] == ["d", "b", "c", "a"]
    assert [fit.cosine for fit in walked.order] == [1.0, pytest.approx(0.5**0.5), None, 0.0]
    assert walked.order[2].unordered == "the hole says nothing under about"
    assert (walked.space, walked.vectors) == ("s", vectors.sha256)
    assert walk(piece, start, given).order == tuple(
        replace(fit, cosine=None, unordered=None)
        for fit in sorted(walked.order, key=lambda fit: given.index(fit.frame))
    )  # without vectors, the walk's own order
    lines = walked.lines()
    assert lines[0]["space"] == "s" and lines[0]["vectors"] == vectors.sha256
    assert lines[0]["cosine"] == 1.0 and "unordered" not in lines[0]
    assert lines[2]["unordered"] == "the hole says nothing under about" and "cosine" not in lines[2]
    # the budget asks in that order: one fit's calls ask the nearest
    each = calls_until_firm(parse(successor(d, "h", piece)))
    walked = walk(piece, start, given, vectors=vectors, calls=each)
    assert [(fit.frame.name, fit.asked) for fit in walked.order][:2] == [("d", True), ("b", False)]


def test_a_cosine_tie_breaks_by_frame_hash():
    start = star("start", "the start's own line")
    piece = Piece(SHARED, "note")
    one, two = read_for("one", "A"), read_for("two", "B")
    vectors = read_vectors(jsonl((SHARED, "s", [1, 0]), ("A", "s", [1, 1]), ("B", "s", [2, 2])))
    for given in ([one, two], [two, one]):
        walked = walk(piece, start, given, vectors=vectors)
        assert [fit.frame.hash for fit in walked.order] == sorted([one.hash, two.hash])


@pytest.mark.parametrize(
    "vectors, why",
    [
        ([("A", "s", [1, 0])], "the piece has no vector in this space"),
        ([(SHARED, "s", [1, 0])], "what the hole is read for has no vector in this space"),
        (
            [(SHARED, "s", [1, 0]), ("A", "s", [1, 0, 0])],
            "its vector has 3 values, and the piece's 2",
        ),
        ([(SHARED, "s", [1, 0]), ("A", "s", [0, 0])], "a vector has no length"),
        ([(SHARED, "s", [1e200, 1e200]), ("A", "s", [1e200, 1])], "its cosine overflows"),
    ],
)
def test_a_fit_geometry_cannot_read_is_said_never_scored(vectors, why):
    start = star("start", "the start's own line")
    piece = Piece(SHARED, "note")
    fit = read_for("a", "A")
    [read] = walk(piece, start, [fit], vectors=read_vectors(jsonl(*vectors))).order
    assert (read.cosine, read.unordered) == (None, why)


def test_a_value_that_is_not_finite_gives_no_order():
    start = star("start", "the start's own line")
    piece = Piece(SHARED, "note")
    text = '{"text": "%s", "space": "s", "values": [1, 0]}\n' % piece.sha256
    text += '{"text": "%s", "space": "s", "values": [NaN, 1]}\n' % sha256("A")
    [read] = walk(piece, start, [read_for("a", "A")], vectors=read_vectors(text)).order
    assert (read.cosine, read.unordered) == (None, "a vector holds a value that is not finite")


def test_a_walk_orders_by_one_space_named_or_alone():
    start = star("start", "the start's own line")
    piece = Piece(SHARED, "note")
    fit = read_for("a", "A")
    two = read_vectors(jsonl((SHARED, "s", [1, 0]), ("A", "s", [1, 0]), (SHARED, "t", [1])))
    with pytest.raises(UsageError, match=r"the vectors hold 2 spaces, 's', 't'"):
        walk(piece, start, [fit], vectors=two)
    assert walk(piece, start, [fit], vectors=two, space="s").order[0].cosine == 1.0
    # in t the piece has a vector and the hole none: never one from another space
    [read] = walk(piece, start, [fit], vectors=two, space="t").order
    assert (read.cosine, read.unordered) == (
        None,
        "what the hole is read for has no vector in this space",
    )
    built = Vectors({(piece.sha256, "s"): (1.0,)}, "0" * 64)  # vectors a caller built
    assert walk(piece, start, [fit], vectors=built).vectors == "0" * 64
    with pytest.raises(UsageError, match="the vectors hold no vector in space 'u'"):
        walk(piece, start, [fit], vectors=two, space="u")
    with pytest.raises(UsageError, match="the vectors hold no vector"):
        walk(piece, start, [fit], vectors=read_vectors(""))
    with pytest.raises(UsageError, match="space is given without vectors"):
        walk(piece, start, [fit], space="s")


CAUSE = "Deploy 42 shrank the connection pool, and requests queued for a connection."


def crossed_run(**fields):
    # the incident's crossing, run whole: a maker writes its cause, a reader decides
    from tests.fixtures.incident import INCIDENT, crossing

    frame = parse({**copy.deepcopy(INCIDENT), **fields})
    return frame, run(frame, crossing, Budget(calls=calls_needed(frame))).records


def review(own="Deploy 43 cut the connection pool again."):
    # the far side: a review that quotes the cause the crossing made, by source
    raw = copy.deepcopy(dolls()[4].raw)
    cited = {"id": "cause", "text": CAUSE, "kind": "cause", "source": {"sha256": sha256(CAUSE)}}
    raw |= {"name": "review", "anchors": ["found"], "interventions": {"ablation": True}}
    raw["body"] = {"spans": [{"id": "found", "text": own, "kind": "metric"}, cited]}
    raw["allowed"] = {"ablation": ["unclear"]}
    raw.pop("holes", None)
    return parse(raw)


def made_cause(records):
    # the trial and input of each record whose maker made the cause, once each
    pairs = [
        (r.trial, r.input) for r in records if json.loads(r.raw)["made"]["sha256"] == sha256(CAUSE)
    ]
    return tuple(dict.fromkeys(pairs))


def test_a_frame_quoting_an_artefact_climbs_to_the_crossing_that_made_it():
    incident, records = crossed_run(holes=[{"id": "m5", "kind": "metric"}])
    start = review()
    piece = found(start, "found")
    # without its records, the cause is a text no frame given holds
    alone = walk(piece, start, [incident])
    assert alone.fits == () and alone.frontier == (sha256(CAUSE),)
    walked = walk(piece, start, [incident], made=[records])
    assert walked.fits == ((incident, ("m5",)),) and walked.complete
    pairs = made_cause(records)
    assert ("baseline", "q1") in pairs and ("ablation", "q1") not in pairs  # its own cause
    assert walked.made == {incident.hash: pairs} and walked.order[0].made == pairs
    assert walked.lines()[0]["made"] == [{"trial": t, "input": x} for t, x in pairs]
    # as dicts too, as a caller keeps them, and a run given twice is two runs
    kept = [record.as_dict() for record in records]
    assert walk(piece, start, [incident], made=[kept, kept]).made == walked.made
    # a crossing with no hole of the piece's kind passes it on, and says how it was reached
    plain, others = crossed_run()
    walked = walk(piece, start, [plain], made=[others])
    assert walked.passed == (plain,)
    assert walked.lines()[0]["made"][0] == {"trial": "baseline", "input": "q1"}


def test_a_crossings_records_are_checked_before_they_are_climbed():
    incident, records = crossed_run(holes=[{"id": "m5", "kind": "metric"}])
    start = review()
    piece = found(start, "found")
    kept = [record.as_dict() for record in records]
    with pytest.raises(RecordsError, match="a made run holds no records"):
        walk(piece, start, [incident], made=[[]])
    with pytest.raises(RecordsError, match=f"a made record names frame {incident.hash!r}, which"):
        walk(piece, start, [], made=[kept])
    with pytest.raises(RecordsError, match="a record is a JSON object"):
        walk(piece, start, [incident], made=[["not a record"]])
    changed = copy.deepcopy(kept)
    changed[0]["body"] = "0" * 64
    with pytest.raises(RecordsError, match="was made on another body"):
        walk(piece, start, [incident], made=[changed])
    unmade = [{**record, "raw": ""} for record in kept]
    with pytest.raises(RecordsError, match="the records of frame 'rollback-from-cause' hold no"):
        walk(piece, start, [incident], made=[unmade])
    # a record that made nothing is no link, beside one that did
    some = [kept[0], *({**record, "raw": "{}"} for record in kept[1:])]
    assert walk(piece, start, [incident], made=[some]).made[incident.hash] == (("baseline", "q1"),)


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


def test_a_piece_placed_after_the_line_it_amends_cuts_back_to_the_frame():
    # a reader that reads each span as a line takes the piece beside the
    # line it amends; cut, the frame is as it was, byte for byte
    second, slip = dolls()[1], found(dolls()[4], "slip")
    draft = successor(second, "says", slip, after="binding", **TRIALS)
    ids = [each["id"] for each in draft["body"]["spans"]]
    assert ids[ids.index("binding") + 1] == "says" and ids[-1] != "says"
    after = parse(draft)
    assert reframes(second, after) == []
    ablation = next(trial for trial in plan(after) if trial.id == "ablation")
    question = second.inputs[0]
    assert prompt(after, ablation, question) == prompt(second, plan(second)[0], question)
    with pytest.raises(UsageError, match="has no span 'nope' to place the piece after"):
        successor(second, "says", slip, after="nope")


def test_a_successor_that_changes_another_hole_reframes():
    # what a frame can take in is part of its question: a successor that
    # adds a hole after the find, changes one, or drops one unfilled asks
    # another question, so a later walk fits nothing nobody predicted
    second = dolls()[1]
    added = with_slip(second, holes=[{"id": "late", "kind": "statement"}])
    assert reframes(second, added) == ["holes"]
    assert (gate(second, added).gate, gate(second, added).changed) == ("reframing", ("holes",))
    two = parse({**second.raw, "holes": [*second.raw["holes"], {"id": "base", "kind": "base"}]})
    filled = parse(successor(two, "says", found(dolls()[4], "slip"), **TRIALS))
    assert filled.raw["holes"] == [{"id": "base", "kind": "base"}]
    assert reframes(two, filled) == []  # the other hole kept as it was
    changed = parse({**filled.raw, "holes": [{"id": "base", "kind": "statement"}]})
    assert reframes(two, changed) == ["holes"]
    dropped = {key: value for key, value in filled.raw.items() if key != "holes"}
    assert reframes(two, parse(dropped)) == ["holes"]
    # a hole closed with no span of its own filled nothing
    emptied = parse({**two.raw, "holes": [{"id": "base", "kind": "base"}]})
    assert reframes(two, emptied) == ["holes"]
    # nor did one closed by a span of another kind: no piece of the hole's
    # kind fits it any more (pass 13, F1)
    slip = found(dolls()[4], "slip")
    body = copy.deepcopy(two.raw["body"])
    body["spans"].append({"id": "says", "text": slip.text, "kind": "note"})
    painted = parse(successor(two, "says", slip, body=body, **TRIALS))
    assert reframes(two, painted) == ["holes"]
    assert gate(two, painted).gate == "reframing"
    # the same holes in another order take in the same (pass 13, F5)
    three = parse({**two.raw, "holes": [*two.raw["holes"], {"id": "note", "kind": "note"}]})
    filled = parse(successor(three, "says", slip, **TRIALS))
    turned = parse({**filled.raw, "holes": filled.raw["holes"][::-1]})
    assert reframes(three, turned) == []


def test_reframes_reads_each_hole_once():
    # closing the last of many holes reads each hole a few times, not once
    # a hole for every hole (pass 13, F3)
    class Holes(list):
        read = 0

        def __getitem__(self, at):
            Holes.read += len(range(*at.indices(len(self)))) if isinstance(at, slice) else 1
            return super().__getitem__(at)

        def __iter__(self):
            for hole in super().__iter__():
                Holes.read += 1
                yield hole

    def close_last(n):
        holes = [{"id": f"h{i}", "kind": "k"} for i in range(n)]
        filled = {"id": f"h{n - 1}", "text": "the last", "kind": "k"}
        before = SimpleNamespace(raw={"holes": Holes(holes)}, spans=())
        after = SimpleNamespace(
            raw={"holes": Holes(holes[:-1]), "body": {"spans": [filled]}},
            spans=(SimpleNamespace(id=filled["id"], kind="k"),),
        )
        Holes.read = 0
        assert reframes(before, after) == []
        return Holes.read

    small, large = close_last(100), close_last(200)
    assert large <= 2.5 * small, (small, large)


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


class Unreachable(DollReader):
    """The doll reader when its service is down: every call an opening."""

    def observe(self, frame, prompt, max_output_tokens):
        return Observation(label=None, opening="the reader could not be reached")


@pytest.mark.parametrize("inputs", [1, 2])
def test_a_firm_unresolved_successor_stops_naming_its_open_check(inputs):
    # unanimous openings are firm, and unresolved: the gate stops and names
    # the open check in the findings' own words, the input's beside it when
    # there are several (pass 12, R1)
    middle = dolls()[1]
    if inputs == 2:
        raw = copy.deepcopy(middle.raw)
        raw["inputs"].append({**raw["inputs"][0], "id": "again"})
        middle = parse(raw)
    after = with_slip(middle)
    asked = until_firm(after, Unreachable(), budget(after))
    assert asked.firm and asked.category == "unresolved"
    recoil = gate(middle, after, asked)
    assert (recoil.gate, recoil.category) == ("stops", "unresolved")
    evidence = asked.findings[0].evidence
    assert evidence and evidence[0].startswith("no agreed level in baseline")
    if inputs == 1:
        assert recoil.open == "; ".join(evidence)
    else:
        assert recoil.open == "; ".join(
            f"in {f.input}, {'; '.join(f.evidence)}" for f in asked.findings
        )


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


def test_the_calls_until_firm_are_counted_before_the_first():
    # a climb's ceiling, known before any call: a whole run's calls for each
    # run most allows beyond the kept ones, and never fewer than it makes
    middle = dolls()[1]
    after = with_slip(middle)
    each = calls_needed(after)
    assert calls_until_firm(after) == MOST * each
    assert calls_until_firm(after, most=3) == 3 * each
    asked = until_firm(after, Shaky(shaky=10**6), budget(after, 3), most=3)
    assert asked.made == calls_until_firm(after, most=3)  # it never settled: every run made
    first = until_firm(after, DollReader(), budget(after))
    assert calls_until_firm(after, kept=first.runs, most=3) == 2 * each
    # refused as until_firm refuses
    with pytest.raises(UsageError, match="most is a whole number of runs, at least 1"):
        calls_until_firm(after, most=0)
    with pytest.raises(UsageError, match="kept holds more runs than most lets"):
        calls_until_firm(after, kept=[*first.runs, *first.runs], most=1)
    with pytest.raises(RecordsError, match="a kept run is not whole"):
        calls_until_firm(after, kept=[first.runs[0][1:]])
    once = parse({**after.raw, "standing": {"quorum": 1, "agree": 1}})
    with pytest.raises(UsageError, match="asks each trial once"):
        calls_until_firm(once)


def test_calls_until_firm_refuses_in_until_firms_order():
    # a frame resting on its holes alone, asked with a bad most: both say
    # what is wrong with most before planning the frame (pass 13, F2)
    waiting = matryoshka()[1]
    waiting["anchors"] = []
    del waiting["interventions"]["repeat"]
    waiting["standing"] = {"quorum": 3, "agree": 2}
    frame = parse(waiting)
    said = "most is a whole number of runs, at least 1"
    with pytest.raises(UsageError, match=said):
        until_firm(frame, None, Budget(calls=1), most=0)
    with pytest.raises(UsageError, match=said):
        calls_until_firm(frame, most=0)


def test_kept_runs_count_as_runs_made_so_a_firm_frame_is_asked_nothing():
    middle = dolls()[1]
    after = with_slip(middle)
    first = until_firm(after, DollReader(), budget(after))
    reader = DollReader()
    again = until_firm(after, reader, budget(after), kept=first.runs)
    assert again.firm and again.made == 0 and reader.calls == 0
    assert again.runs == first.runs and again.category == "carried"


def test_until_firm_reads_each_kept_run_once(monkeypatch):
    # each place's draws are made from its own run, once, not again for every
    # later place: the work grows with the runs, not their square (pass 12, P1)
    from midwife import stats

    middle = dolls()[1]
    after = with_slip(middle)
    runs = [until_firm(after, DollReader(), budget(after)).runs[0] for _ in range(4)]
    checked = []
    real = stats.check_records
    monkeypatch.setattr(stats, "check_records", lambda *a, **k: checked.append(1) or real(*a, **k))
    asked = until_firm(after, None, Budget(calls=1), kept=runs, most=4)
    assert len(checked) == len(runs) == 4
    assert asked.shares == {
        x: shares.get(asked.findings[0].category, 0.0)
        for x, shares in stats.stability(after, runs)[-1].items()
    }


def test_until_firm_never_starts_a_run_the_budget_cannot_cover():
    middle = dolls()[1]
    after = with_slip(middle)
    reader = DollReader()
    # nothing passes in silence: the stop is a StoppedWarning, as a run's is
    with pytest.warns(StoppedWarning, match="^asking stopped after 0 of at most 5 runs, its"):
        asked = until_firm(after, reader, Budget(calls=calls_needed(after) - 1))
    assert not asked.firm and asked.made == 0 and reader.calls == 0
    assert asked.stopped == f"the budget covers no further run of {calls_needed(after)} calls"
    assert gate(middle, after, asked).open == asked.stopped


def test_with_no_battery_until_firm_reads_the_kept_runs_alone():
    # gadfly gate reads a successor's runs so: nothing is asked, and a
    # verdict the kept runs leave unsettled is not firm, with no stop to warn of
    middle = dolls()[1]
    after = with_slip(middle)
    shaky = until_firm(after, Shaky(shaky=calls_needed(after)), budget(after, 1), most=1)
    with warnings.catch_warnings():
        warnings.simplefilter("error", StoppedWarning)
        read = until_firm(after, None, Budget(calls=1), kept=shaky.runs)
    assert not read.firm and read.stopped is None and read.made == 0
    assert gate(middle, after, read).open == "its verdict was not firm after 1 run"
    firm = until_firm(after, DollReader(), budget(after))
    assert until_firm(after, None, Budget(calls=1), kept=firm.runs).firm


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
        ([{"id": "head", "kind": "head", "about": ""}], None, "holes lists"),
        ([{"id": "head", "kind": "head", "about": 5}], None, "holes lists"),
        ([{"id": "head", "kind": "head", "salience": "maybe"}], None, "hole 'head' has salience"),
        ([{"id": "head", "kind": "head", "salience": ""}], None, "holes lists"),
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


def test_a_deferred_hole_is_listed_kept_and_never_asked():
    largest, second, third, fourth, smallest = dolls()
    raw = copy.deepcopy(second.raw)
    raw["holes"] = [{"id": "says", "kind": "statement", "salience": "defer"}]
    held = parse(raw)
    slip = found(smallest, "slip")
    walked = walk(slip, smallest, [largest, held, third, fourth])
    # its fit is kept and not asked: never a fit, never passed, never dropped
    assert walked.fits == () and walked.deferred == ((held, ("says",)),)
    assert held not in walked.passed and walked.complete
    line = {"piece": slip.sha256, "kind": "statement", "frame": held.hash, "name": "second doll"}
    assert {**line, "deferred": ["says"]} in walked.lines()
    # beside a considered hole of the same kind, each is listed where it belongs
    raw["holes"] = [{"id": "said", "kind": "statement"}, *raw["holes"]]
    both = parse(raw)
    walked = walk(slip, smallest, [largest, both, third, fourth])
    assert walked.fits == ((both, ("said",)),) and walked.deferred == ((both, ("says",)),)
    assert both not in walked.passed
    # and the frame's author may still ask it, by drafting its successor
    assert parse(successor(held, "says", slip)).anchors == ("says",)


def test_a_holes_salience_and_what_it_is_read_for_are_hashed():
    middle = matryoshka()[1]
    plain = parse(middle)
    about = "what the second doll says of itself"
    for hole in ({"about": about}, {"salience": "consider"}, {"salience": "defer"}):
        middle["holes"] = [{"id": "says", "kind": "statement", **hole}]
        salient = parse(middle)
        assert salient.hash != plain.hash and salient.holes == tuple(middle["holes"])
    # a successor that changes them on a hole it leaves open reframes
    middle["holes"] = [{"id": "says", "kind": "statement"}, {"id": "else", "kind": "x"}]
    before = parse(middle)
    filled = successor(before, "says", found(dolls()[4], "slip"))
    assert reframes(before, parse(filled)) == []
    filled["holes"] = [{"id": "else", "kind": "x", "salience": "defer"}]
    assert reframes(before, parse(filled)) == ["holes"]
    filled["holes"] = [{"id": "else", "kind": "x", "about": about}]
    assert reframes(before, parse(filled)) == ["holes"]


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
    with pytest.warns(StoppedWarning, match="; the token budget covers no further run of"):
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


def test_a_runs_draws_are_seeded_by_its_place_as_gadfly_stats_reads_them():
    # the same records read at place 0 and at place 1 draw differently; a
    # run is read where it stands, so until_firm agrees with stability over
    # the same runs (pass 11, F3)
    probe = parse(
        {
            "name": "seed probe", "relation": "r", "locus": "l", "role": "ro",
            "grain": "g", "purpose": "p", "trajectory": "t", "crossing": "c",
            "promise": "pr", "baseline": "the frame as is",
            "body": {"spans": [{"id": "a", "text": "The anchor says yes."}]},
            "anchors": ["a"], "inputs": [{"id": "x", "text": "Is it yes?"}],
            "observe": {"labels": ["yes", "no"], "instruction": "Answer yes or no."},
            "interventions": {"ablation": True}, "allowed": {"ablation": ["no"]},
            "standing": {"quorum": 5, "agree": 3}, "carriage": "listed",
            "battery": {"kind": "probe"},
        }
    )  # fmt: skip

    class Probe:
        name = "probe"

        def check(self, frame):
            pass

        def observe(self, frame, prompt, cap):
            return Observation(label="yes" if "anchor" in prompt.split(RULE)[0] else "no")

    clean = [r.as_dict() for r in run(probe, Probe(), Budget(calls_needed(probe))).records]

    def flipped(index, label):
        records = [dict(r) for r in clean]
        records[index]["observation"] = label
        return records

    first = flipped(3, "no")
    for second in (flipped(2, "no"), flipped(9, "yes")):
        asked = until_firm(probe, None, Budget(calls=1), kept=[first, second])
        [finding] = judge(probe, second)
        share = stability(probe, [first, second])[1]["x"][finding.category]
        assert asked.shares == {"x": share}
        assert asked.firm is (share >= 0.95)


def test_a_kept_run_with_a_prompt_its_frame_never_planned_is_refused():
    # a kept record names the prompt its call read: one the frame's plan
    # never makes is another frame's call, refused as run refuses it on
    # resume (pass 11, F4)
    middle = dolls()[1]
    after = with_slip(middle)
    kept = [dict(r) for r in until_firm(after, DollReader(), budget(after)).runs[0]]
    kept[0]["prompt"] = "0" * 64
    with pytest.raises(RecordsError, match="was made from another prompt"):
        until_firm(after, None, Budget(calls=1), kept=[kept])


def test_a_text_the_start_holds_as_its_own_is_no_frontier():
    # a frame may hold a text and quote it too: the text has a maker among
    # the frames given, so the walk is not left incomplete by it (pass 11, F5)
    smallest = matryoshka()[4]
    smallest["body"]["spans"].insert(2, span("held", WORKSHOP, "mark"))
    start = parse(smallest)
    walked = walk(found(start, "slip"), start, [start])
    assert sha256(WORKSHOP) not in walked.frontier
    assert walked.frontier == (sha256(opens(3)),)  # the fourth doll was not given


def test_a_wide_frontier_drains_in_linear_work():
    # a frame quoting many parents: the work of draining the frontier is the
    # frames each pop must shift, which a list makes quadratic (pass 11, F14)
    import inspect
    import sys

    def wide(n):
        base = matryoshka()[1]
        frames = []
        for j in range(1, n):
            parent = copy.deepcopy(base)
            parent.update(name=f"parent {j}", body={"spans": [span("own", f"line {j}", "rule")]})
            parent.update(anchors=["own"])
            frames.append(parse(parent))
        start = copy.deepcopy(base)
        quotes = [span(f"up-{j}", f"line {j}", "rule", quoted=True) for j in range(1, n)]
        start.update(body={"spans": [span("own", "line 0", "rule"), *quotes]}, anchors=["own"])
        return parse(start), frames

    lines, first = inspect.getsourcelines(walk)
    pop = first + next(i for i, line in enumerate(lines) if "climbing.pop" in line)

    def shifted(n):
        start, frames = wide(n)
        total = 0

        def tracer(frame, event, arg):
            nonlocal total
            if event == "line" and frame.f_code is walk.__code__ and frame.f_lineno == pop:
                climbing = frame.f_locals["climbing"]
                if isinstance(climbing, list):
                    total += len(climbing) - 1
            return tracer

        before = sys.gettrace()  # coverage's, when it traces
        sys.settrace(tracer)
        try:
            walk(Piece("x", "none"), start, frames)
        finally:
            sys.settrace(before)
        return total

    assert shifted(80) <= 2 * shifted(40) + 100


def test_a_body_with_no_span_is_refused_beside_holes_too():
    # holes stand in for anchors, not for the evidence: an empty body is
    # refused by the parser as by the schema (pass 11, F6)
    from jsonschema import Draft202012Validator

    from midwife.frame import schema

    empty = matryoshka()[1]
    empty.update(body={"spans": []}, anchors=[])
    assert not Draft202012Validator(schema()).is_valid(empty)
    with pytest.raises(FrameError, match="the body holds no span"):
        parse(empty)


def test_the_stability_docs_name_the_share_until_firm_holds_to():
    # the share a verdict must reach to be firm is one number, in the code
    # and in what the docs say of it (pass 11, F12)
    import inspect

    from midwife.recoil import FIRM

    assert f"{FIRM:.0%} of draws is firm" in inspect.getdoc(stability)


def test_the_troubleshooting_tables_name_what_recoil_refuses():
    # a frame resting on its holes alone is refused when planned, and the
    # tables say so in the words the refusal uses (pass 11, F13)
    from pathlib import Path

    waiting = matryoshka()[1]
    waiting["anchors"] = []
    with pytest.raises(FrameError) as refused:
        plan(parse(waiting))
    tables = (Path(__file__).parent.parent / "docs/troubleshooting.md").read_text()
    said = str(refused.value).replace("'second doll'", "'Kiran'")
    assert f"`FrameError: {said}`" in tables
    assert "`FrameError: the body holds no span`" in tables
