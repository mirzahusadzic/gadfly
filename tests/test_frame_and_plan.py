import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from gadfly.frame import FrameError, parse
from gadfly.interventions import plan, prompt, rename


def test_a_frame_is_hashed_whole_and_any_coordinate_changes_it(raw):
    first = parse(raw).hash
    assert parse(raw).hash == first
    raw["grain"] = "one sentence"
    assert parse(raw).hash != first


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda r: r.pop("promise"), "promise"),
        (lambda r: r.update(anchors=["r9"]), "anchors not in the body"),
        (lambda r: r.update(anchors=[]), "at least one anchor"),
        (lambda r: r["interventions"].pop("ablation"), "ablation"),
        (lambda r: r["interventions"].update(teleport=True), "unknown interventions"),
        (lambda r: r.update(allowed={"ablation": ["maybe"]}), "allowed lists one or more"),
        (lambda r: r.update(allowed={"ablation": "lower"}), "needs observe.order"),
        (lambda r: r.update(standing={"quorum": 3, "agree": 4}), "agree is between"),
        (lambda r: r["body"]["spans"].append(dict(r["body"]["spans"][0])), "share an id"),
        (lambda r: r["interventions"].update(bypass=["r9"]), "bypass names a span"),
        (lambda r: r.update(inputs=[{"id": "x1"}]), "inputs are"),
        (lambda r: r["observe"].update(labels=["grant"]), "at least two labels"),
        # a frame that would run, spend its calls, and only then be refused
        (lambda r: r.update(inputs=[{"id": "x", "text": "a"}, {"id": "x", "text": "b"}]), "share"),
        (lambda r: r.update(inputs=[{"id": 1, "text": "a"}]), "inputs are"),
        # a declaration that would be read as something else, or not at all
        (lambda r: (r["standing"].update(stable=True), r["interventions"].pop("repeat")), "repeat"),
        (lambda r: r["standing"].update(stable="no"), "stable is true or false"),
        (lambda r: r["standing"].update(stabel=True), "standing says"),
        (lambda r: r.pop("baseline"), "baseline"),
        (lambda r: r.update(materialised=True), "unknown keys"),
        (lambda r: r.update(materialized="yes"), "materialized is true or false"),
        (lambda r: r.update(outsideScope=True), "outsideScope"),
        (lambda r: r["observe"].update(instruction=" "), "instruction"),
        # a wrong type is a FrameError, not a TypeError
        (lambda r: r.update(allowed={"ablation": [{"a": 1}]}), "allowed lists"),
        (lambda r: r.update(allowed={"ablation": []}), "allowed lists"),
        (lambda r: r["observe"].update(order=5), "observe.order orders"),
        (lambda r: r["allowed"].update(bypass=["maybe"]), "allowed lists one or more"),
        (lambda r: r["allowed"].update(sham=["grant"]), "allowed says"),
        (
            lambda r: (r["allowed"].update(bypass=["grant"]), r["interventions"].pop("bypass")),
            "allowed.bypass needs a bypass trial",
        ),
        # a trial that cannot change anything would clear its check unearned
        (lambda r: r["interventions"].update(presentation={"reciept": "slip"}), "renames nothing"),
        (lambda r: r["interventions"].update(presentation={"a": "x", "A": "y"}), "twice"),
        (lambda r: r["interventions"].update(bypass=["r2"]), "the ablation again"),
        (lambda r: r["interventions"].update(cumulative=["r2"]), "adds no span"),
        (lambda r: r["interventions"].update(control=["r2"]), "the ablation again"),
        (lambda r: r["interventions"].update(control=["r9"]), "control names a span"),
        (lambda r: r.update(carriage="lenient"), "carriage is all-checks or listed"),
        (lambda r: r.update(scopeCheck={"owner": "o"}), "scopeCheck checks an outsideScope"),
        (
            lambda r: r.update(outsideScope="x", scopeCheck={"owner": "o", "statement": "s"}),
            "scopeCheck says who checked",
        ),
    ],
)
def test_a_frame_that_cannot_be_assessed_is_refused(raw, change, message):
    change(raw)
    with pytest.raises(FrameError, match=message):
        parse(raw)


def test_presentation_must_reach_every_input(raw):
    # "day" is only in x1's text; x2's presentation prompt would be its baseline's
    raw["interventions"]["presentation"] = {"day": "date"}
    raw["inputs"].append({"id": "x2", "text": "A customer asks for a refund."})
    with pytest.raises(FrameError, match="renames nothing x2 reads"):
        parse(raw)


def test_the_plan_is_fixed_by_the_frame_alone(raw):
    frame = parse(raw)
    trials = plan(frame)
    assert [t.id for t in trials] == [
        "baseline",
        "repeat",
        "ablation",
        "sham-1",
        "sham-2",
        "presentation",
        "bypass",
    ]
    assert [t.id for t in plan(parse(raw))] == [t.id for t in trials]
    assert [t.removed for t in plan(parse(raw))] == [t.removed for t in trials]


def test_the_control_removes_what_it_names_last(raw):
    raw["interventions"]["control"] = ["r1", "r2", "r3", "r4"]
    *_, control = plan(parse(raw))
    assert control.id == "control" and control.removed == ("r1", "r2", "r3", "r4")
    assert control.text == "These rules decide every request."


def test_ablation_removes_the_anchors_and_nothing_else(raw):
    ablation = next(t for t in plan(parse(raw)) if t.id == "ablation")
    assert ablation.removed == ("r2",)
    assert "receipt" not in ablation.text and "30 days" in ablation.text


def test_shams_remove_as_much_of_the_same_kind_closest_in_length_and_never_twice(raw):
    shams = [t for t in plan(parse(raw)) if t.kind == "sham"]
    # r2 is 28 characters: r3 (30) is closest, then r4 (40); r1 (48) is left
    assert [t.removed for t in shams] == [("r3",), ("r4",)]
    raw["interventions"]["sham"] = {"draws": 4}
    assert [t.id for t in plan(parse(raw)) if t.kind == "sham"] == ["sham-1", "sham-2", "sham-3"]


def test_a_sham_that_cannot_be_matched_is_left_out(raw):
    for span in raw["body"]["spans"]:
        if span["id"] != "r2":
            span["kind"] = "note"
    assert not [t for t in plan(parse(raw)) if t.kind == "sham"]


def test_presentation_renames_whole_words_in_body_and_input(raw):
    frame = parse(raw)
    presentation = next(t for t in plan(frame) if t.id == "presentation")
    assert "proof of purchase" in presentation.text
    assert "proof of purchase" in prompt(frame, presentation, frame.inputs[0])
    assert rename("Receipts and a Receipt", (("receipt", "slip"),)) == "Receipts and a Slip"


def test_presentation_renames_each_word_once_and_the_longest_phrase_first():
    swap = (("cat", "dog"), ("dog", "cat"))
    assert rename("The cat chased the dog", swap) == "The dog chased the cat"
    assert rename("a then b", (("a", "b"), ("b", "c"))) == "b then c"
    longer = (("refund", "credit"), ("refund policy", "terms"))
    assert rename("the refund policy, a refund", longer) == "the terms, a credit"
    assert rename("RECEIPT, Receipt, receipt", (("receipt", "slip"),)) == "SLIP, Slip, slip"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), {1, 2}, "\ud800", {1: "a"}])
def test_a_frame_is_plain_json_or_refused(raw, value):
    # NaN would be hashed and could not be read back by a strict JSON reader;
    # the rest escaped as TypeError or UnicodeEncodeError
    raw["baseline"] = {"pinned": value}
    with pytest.raises(FrameError, match="plain JSON"):
        parse(raw)


class CountingRandom:
    """A seeded random source that counts its draws (and always ties)."""

    calls = 0

    def __init__(self, seed):
        self.seed = seed

    def random(self):
        type(self).calls += 1
        return 0.5


def draws_to_plan(raw, anchors):
    spans = [{"id": f"a{i}", "text": "anchor " + "x" * i, "kind": "rule"} for i in range(anchors)]
    free = range(4 * anchors)
    spans += [{"id": f"f{i}", "text": "free " + "y" * i, "kind": "rule"} for i in free]
    raw.update(body={"spans": spans}, anchors=[f"a{i}" for i in range(anchors)])
    raw["interventions"] = {"ablation": True, "sham": {"draws": 4}}
    raw["inputs"] = [{"id": "x", "text": "a request"}]
    CountingRandom.calls = 0
    with patch("gadfly.interventions.random.Random", CountingRandom):
        assert len([t for t in plan(parse(raw)) if t.kind == "sham"]) == 4
    return CountingRandom.calls


def test_sham_draws_grow_with_the_spans_not_their_square(raw):
    small, large = draws_to_plan(copy.deepcopy(raw), 5), draws_to_plan(copy.deepcopy(raw), 10)
    assert large <= 2.5 * max(small, 1), (small, large)


def mapping_bytes_to_parse(raw, words):
    # a map that renames only the input still had to be rebuilt for every span
    raw["body"] = {
        "spans": [
            *[{"id": f"s{i}", "text": f"policy line {i}", "kind": "rule"} for i in range(words)],
            {"id": "anchor", "text": "the rule under test", "kind": "rule"},
        ]
    }
    raw["anchors"] = ["anchor"]
    mapping = {f"absent{i}": f"replacement{i}" for i in range(words)}
    raw["interventions"] = {"ablation": True, "presentation": mapping}
    raw["inputs"] = [{"id": "x", "text": " ".join(mapping)}]
    touched = [0]

    def counting(text, pairs):
        touched[0] += len(text) + sum(len(a) + len(b) for a, b in pairs)
        return rename(text, pairs)

    with patch("gadfly.interventions.rename", counting):
        parse(raw)
    return touched[0]


def test_the_presentation_map_is_built_once_per_frame(raw):
    small = mapping_bytes_to_parse(copy.deepcopy(raw), 20)
    large = mapping_bytes_to_parse(copy.deepcopy(raw), 40)
    assert large <= 2.5 * max(small, 1), (small, large)


def test_placement_moves_one_span_after_another_and_nothing_else(raw):
    raw["interventions"]["placement"] = {"span": "r2", "after": "r4"}
    frame = parse(raw)
    trials = {t.id: t for t in plan(frame)}
    ids = [t.id for t in plan(frame)]
    assert ids.index("presentation") < ids.index("placement") < ids.index("bypass")
    assert [s.id for s in trials["placement"].spans] == ["r1", "r3", "r4", "r2", "r5"]
    assert sorted(trials["placement"].text.split("\n")) == sorted(
        trials["baseline"].text.split("\n")
    )
    assert trials["placement"].body_hash != trials["baseline"].body_hash


@pytest.mark.parametrize(
    "placement, message",
    [
        ({"span": "r2", "after": "r1"}, "leaves the order as it is"),  # r2 already follows r1
        ({"span": "r2", "after": "r2"}, "after another span"),
        ({"span": "r9", "after": "r1"}, "placement names a span not in the body"),
        ({"span": "r2"}, "placement moves one span"),
    ],
)
def test_a_placement_that_cannot_move_anything_is_refused(raw, placement, message):
    raw["interventions"]["placement"] = placement
    with pytest.raises(FrameError, match=message):
        parse(raw)


def test_a_frame_without_placement_keeps_its_hash():
    # placement is additive: a frame that does not use it is the frame it was
    refund = json.loads((Path(__file__).parent.parent / "examples/refund.json").read_text())
    assert parse(refund).hash == "6a788e8843504c0828dc1dc8c236c349e8f9750c0cd2d52b2d124d2bb9580e9e"
