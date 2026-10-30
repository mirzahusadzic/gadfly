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
        (lambda r: r.update(allowed={"ablation": ["maybe"]}), "allowed lists labels"),
        (lambda r: r.update(allowed={"ablation": "lower"}), "needs observe.order"),
        (lambda r: r.update(standing={"quorum": 3, "agree": 4}), "agree is between"),
        (lambda r: r["body"]["spans"].append(dict(r["body"]["spans"][0])), "share an id"),
        (lambda r: r["interventions"].update(bypass=["r9"]), "bypass names a span"),
        (lambda r: r.update(inputs=[{"id": "x1"}]), "inputs are"),
        (lambda r: r["observe"].update(labels=["grant"]), "at least two labels"),
    ],
)
def test_a_frame_that_cannot_be_assessed_is_refused(raw, change, message):
    change(raw)
    with pytest.raises(FrameError, match=message):
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
