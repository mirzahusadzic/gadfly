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
