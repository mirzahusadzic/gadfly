"""Recoil, the design in docs/breadth/recoil.md, held by a model of its walk.

Not built: `walk`, `reframes` and `GATE` below are the design's rules written
small, so the test can hold the design to a case. The successors are real
frames, and their runs and verdicts, which gate the recoil, are Gadfly's own.

The case is a matryoshka, after the boy and the girl that meaning
representations have always started with: a set of three dolls, the middle
one missing its head, and the smallest holding a painted head with a beard.
"""

import copy
import hashlib

from midwife.frame import digest, parse
from midwife.interventions import plan, prompt
from midwife.pipeline import calls_needed, judge, run
from midwife.types import Budget, Observation

RULE = "\n\n---\n\n"
BINDING = "The painted head decides who a doll is."
WORKSHOP = "The set was painted in one workshop."
OPENS = "The largest doll opens at the waist, and the middle doll sits inside."
INSIDE = "The middle doll opens at the waist, and the smallest doll sits inside."
HEAD = "A painted head with a beard."

# what a successor may change while it fills a declared hole: its evidence.
# Anything else asks another question (docs/breadth/recoil.md, Reframing).
QUESTION = (
    "relation", "role", "locus", "grain", "purpose", "trajectory", "crossing",
    "promise", "inputs", "observe", "standing", "battery",
)  # fmt: skip
# the successor's category, read as the gate
GATE = {
    "carried": "climbs",
    "coupled but misaligned": "climbs",
    "cooled": "absorbed",
    "outside scope": "absorbed",
    "unresolved": "stops",
}


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def span(id, text, kind, quoted=False):
    return {
        "id": id,
        "text": text,
        "kind": kind,
        **({"source": {"sha256": sha(text)}} if quoted else {}),
    }


def doll(name, spans, question, labels, **fields):
    raw = {
        "name": name,
        "relation": f"who the {name} is rests on its painted head",
        "locus": f"the {name}'s paint",
        "role": "a collector cataloguing a set",
        "grain": "one doll",
        "purpose": "name each doll for the catalogue",
        "trajectory": "the dolls as unpacked, the collector's reading, the catalogue",
        "crossing": "the catalogue entry",
        "promise": "a doll without its head is not named",
        "baseline": "the doll as unpacked; nothing changed",
        "body": {"spans": spans},
        "anchors": [],
        "inputs": [{"id": "who", "text": question}],
        "observe": {"labels": labels, "instruction": "Name the doll from its paint."},
        "interventions": {"repeat": True, "ablation": True},
        "allowed": {"ablation": ["unclear"]},
        "standing": {"quorum": 1, "agree": 1},
        "materialized": True,
        "battery": {"kind": "doll-reader"},
    }
    return {**raw, **fields}


def matryoshka():
    # each doll quotes the doll it came out of; the smallest also carries the
    # workshop's mark, so it names the set as well as the middle doll
    the_set = doll(
        "set",
        [
            span("aprons", "The set's dolls wear painted aprons.", "paint"),
            span("workshop", WORKSHOP, "mark"),
            span("opens", OPENS, "inside"),
        ],
        "Whose set is this?",
        ["girls", "unclear"],
        anchors=["aprons"],
        holes=[{"id": "inside", "kind": "role"}],
        offers="set",
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
        anchors=["head"],
    )
    return the_set, middle, smallest


def parents(frame, frames):
    """The frames whose text this frame's spans quote by `source`, and each
    source no given frame holds."""
    named = {s["source"]["sha256"] for s in frame["body"]["spans"] if "source" in s}
    found, held = {}, set()
    for other in frames:
        if other is frame:
            continue
        texts = {sha(s["text"]) for s in other["body"]["spans"]}
        held |= texts
        if named & texts:
            found[digest(other)] = other
    return list(found.values()), named - held


def walk(piece, start, frames):
    """Climb from the frame a piece was found in to every frame above it,
    each once by its hash. A frame with a hole of the piece's kind is a fit,
    and the piece climbs on past it; any other passes it on. No call is made:
    the walk reads frames, and is given no battery."""
    seen, fits, passed, frontier = set(), {}, [], set()
    climbing = [start]
    while climbing:
        above, unfound = parents(climbing.pop(0), frames)
        frontier |= unfound
        for parent in above:
            if digest(parent) in seen:
                continue
            seen.add(digest(parent))
            holes = [h["id"] for h in parent.get("holes", []) if h["kind"] == piece["kind"]]
            if holes:
                fits[parent["name"]] = holes
            else:
                passed.append(parent["name"])
            climbing.append(parent)
    return {"fits": fits, "passed": passed, "frontier": frontier, "complete": not frontier}


def fill(frame, hole, piece, **evidence):
    """The successor an author would write for a fit: the piece a span of
    the hole's id, quoting the text it was found as, and the frame's anchor;
    the hole closed. Only its evidence changes, unless `evidence` says more."""
    successor = copy.deepcopy(frame)
    successor["body"]["spans"].append(span(hole, piece["text"], piece["kind"], quoted=True))
    successor["anchors"] = [hole]
    successor["holes"] = [h for h in frame["holes"] if h["id"] != hole]
    for key, value in evidence.items():
        successor[key] = value
    if not successor["holes"]:
        del successor["holes"]
    return successor


def reframes(before, after):
    """The parts of the question a successor changed: none when it only
    filled a declared hole."""
    return [key for key in QUESTION if before.get(key) != after.get(key)]


def recoil(before, after, read=None):
    """What a fit does: a reframing opening when the successor asks another
    question, read against no category; otherwise the gate its category
    sets."""
    changed = reframes(before, after)
    if changed:
        return {"reframing": (digest(before), digest(after)), "changed": changed}
    return {"gate": GATE[read]}


def runnable(raw):
    # today's parser knows neither key; the design adds them
    return parse({k: v for k, v in raw.items() if k not in ("holes", "offers")})


class DollReader:
    """Reads a doll's paint by fixed rules: no model. The painted head names
    a doll while the binding note stands; a chipped base is chipped whatever
    the head says."""

    name = "doll-reader"

    def check(self, frame):
        pass

    def observe(self, frame, prompt, max_output_tokens):
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


def category(raw):
    frame = runnable(raw)
    records = run(frame, DollReader(), Budget(calls=calls_needed(frame))).records
    [finding] = judge(frame, records)
    return frame, finding.category


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
}


def test_the_head_climbs_past_nothing_it_does_not_fit():
    the_set, middle, smallest = matryoshka()
    head = {"text": HEAD, "kind": "head"}
    walked = walk(head, smallest, [the_set, middle, smallest])
    # it fits the middle doll, and climbs on to the set, which passes it on:
    # the set's hole wants a role, not a head
    assert walked == {"fits": {"middle doll": ["head"]}, "passed": ["set"]} | {
        "frontier": set(),
        "complete": True,
    }


def test_a_shared_parent_is_visited_once_and_a_missing_one_is_the_frontier():
    the_set, middle, smallest = matryoshka()
    head = {"text": HEAD, "kind": "head"}
    # the smallest doll quotes the set and the middle doll, which quotes the
    # set again: two routes, one visit
    assert walk(head, smallest, [the_set, middle, smallest])["passed"].count("set") == 1
    # without the set, both quotes of it are unanswered: never complete
    walked = walk(head, smallest, [middle, smallest])
    assert walked["frontier"] == {sha(WORKSHOP), sha(OPENS)}
    assert walked["complete"] is False


def test_the_middle_doll_with_its_head_is_a_boy_and_carried():
    _, middle, _ = matryoshka()
    head = {"text": HEAD, "kind": "head"}
    successor = fill(middle, "head", head, **WHO)
    frame, read = category(successor)
    assert read == "carried"
    assert recoil(middle, successor, read) == {"gate": "climbs"}  # it only filled its hole
    # the successor's ablation cuts the head, which is the doll as it was
    # unpacked, byte for byte: the call its kept baseline already made
    ablation = next(trial for trial in plan(frame) if trial.id == "ablation")
    as_unpacked = "\n".join(s["text"] for s in middle["body"]["spans"])
    asked = as_unpacked + RULE + "Who is the middle doll?"
    assert prompt(frame, ablation, frame.inputs[0]) == asked


def test_a_boy_inside_reframes_the_girls_set():
    the_set, middle, _ = matryoshka()
    as_catalogued = copy.deepcopy(the_set)
    successor = fill(middle, "head", {"text": HEAD, "kind": "head"}, **WHO)
    _, read = category(successor)
    assert read == "carried"
    # the gate is open: the middle doll's decision climbs as a piece of the
    # kind it offers, and its parent is the set
    decision = {"text": f"{successor['name']} reads boy", "kind": successor["offers"]}
    walked = walk(decision, successor, [the_set, successor])
    assert walked["fits"] == {"set": ["inside"]}
    # the set was asked girls or unclear: a boy inside needs a label it lacks,
    # so its successor asks another question, and is read against no category
    labels = {"labels": ["girls", "boys", "mixed", "unclear"], "instruction": "Name the set."}
    asked_again = fill(the_set, "inside", decision, observe=labels)
    assert recoil(the_set, asked_again) == {
        "reframing": (digest(the_set), digest(asked_again)),
        "changed": ["observe"],
    }
    assert the_set == as_catalogued  # the set as it was asked stands, unchanged


def test_a_doll_whose_question_does_not_rest_on_its_head_absorbs_it():
    _, middle, _ = matryoshka()
    based = copy.deepcopy(middle)
    based["body"]["spans"].insert(4, span("base", "The middle doll's base is chipped.", "base"))
    based["inputs"] = [{"id": "base", "text": "Is the middle doll's base whole?"}]
    based["observe"] = {"labels": ["whole", "chipped", "unclear"], "instruction": "Read the base."}
    successor = fill(
        based,
        "head",
        {"text": HEAD, "kind": "head"},
        interventions={"repeat": True, "ablation": True, "control": ["base", "head"]},
    )
    _, read = category(successor)
    # the head fits, is asked again, and changes nothing: nothing climbs
    assert read == "cooled"
    assert recoil(based, successor, read) == {"gate": "absorbed"}
