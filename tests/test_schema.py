"""The frame's JSON Schema agrees with the parser on every shipped frame, and
refuses the shapes the parser refuses."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from midwife.cli import main
from midwife.frame import FrameError, parse, schema
from tests.conftest import REFUND
from tests.fixtures.after_the_poem import frame_for

ROOT = Path(__file__).parent.parent
VALIDATOR = Draft202012Validator(schema())
STUDY = {
    "id": "s",
    "frame": {
        "model": "m",
        "reasoning": "low",
        "rubric_sha256": "h",
        "prompt_version": "p",
        "sessions": 3,
        "minimum_agreement": 0.67,
    },
}
SHIPPED = {
    **{path.name: json.loads(path.read_text()) for path in sorted(ROOT.glob("examples/*.json"))},
    "the test fixture": REFUND,
    "the study replay": frame_for(
        {"id": "c", "run_id": "r", "axis": "a", "ablated_lines": 3}, STUDY
    ),
}


def test_the_schema_is_a_draft_2020_12_schema():
    Draft202012Validator.check_schema(schema())
    assert schema()["$id"] == "https://mirzahusadzic.github.io/gadfly/frame.schema.json"


@pytest.mark.parametrize("name", SHIPPED)
def test_every_shipped_frame_meets_the_schema_and_the_parser(name):
    assert [error.message for error in VALIDATOR.iter_errors(SHIPPED[name])] == []
    parse(SHIPPED[name])


@pytest.mark.parametrize(
    "change",
    [
        lambda r: r.update(materialised=True),
        lambda r: r.pop("baseline"),
        lambda r: r["interventions"].update(ablation=False),
        lambda r: r["interventions"].update(sham={"draws": 0}),
        lambda r: r["interventions"].update(sham={"draws": 1, "kind": {}}),
        lambda r: r["interventions"].update(sham={"draws": 1, "kind": {"": "rule"}}),
        lambda r: r["interventions"].update(eachAnchor="yes"),
        lambda r: r["interventions"].update(placement={"span": "r2"}),
        lambda r: r["observe"].update(labels=["grant"]),
        lambda r: r["standing"].update(stable="yes"),
        lambda r: r.update(carriage="lenient"),
        lambda r: r.update(scopeCheck={"owner": "o", "statement": "s", "source": "x"}),
        lambda r: r.update(
            scopeCheck={"owner": "o", "statement": "s", "source": "x", "encounter": "e"}
        ),  # a check of no declared exclusion
        lambda r: r["allowed"].update(ablation=[]),
        lambda r: r["body"]["spans"][1].update(source={"sha256": "XYZ"}),
        lambda r: r["body"]["spans"][1].update(source={"from": "elsewhere"}),
        lambda r: r["body"]["spans"][1].update(source={"sha256": "0" * 64, "from": ""}),
        lambda r: r["body"]["spans"][1].update(source={"sha256": "0" * 64, "when": "now"}),
        lambda r: r["body"]["spans"][1].update(source="0" * 64),
    ],
)
def test_the_schema_refuses_what_the_parser_refuses(change):
    raw = copy.deepcopy(REFUND)
    change(raw)
    assert not VALIDATOR.is_valid(raw)
    with pytest.raises(FrameError):
        parse(raw)


def test_check_frame_says_ok_or_where_the_frame_is_wrong(tmp_path, capsys):
    assert main(["check-frame", str(ROOT / "tests/fixtures/refund.json")]) == 0
    assert capsys.readouterr().out.startswith("ok (schema and parser): refund-receipt (")
    raw = copy.deepcopy(REFUND)
    raw["anchors"] = ["r9"]  # only the parser can see this one
    raw["interventions"]["sham"] = {"draws": 0}
    path = tmp_path / "frame.json"
    path.write_text(json.dumps(raw))
    # with --json, one FrameError on standard error, as every refusal is, listing them
    assert main(["check-frame", str(path), "--json"]) == 4
    told = capsys.readouterr()
    error = json.loads(told.err)["error"]
    assert told.out == "" and (error["type"], error["exit"]) == ("FrameError", 4)
    assert error["checked"] == "schema and parser"
    assert [p["at"] for p in error["problems"]] == ["/interventions/sham", "/"]
    assert error["problems"][1] == {
        "at": "/",
        "problem": "the body has no span 'r9'",
        "notes": ["anchors name spans of the body"],
    }
    # in words, each problem is a FrameError, gathered rather than raised at the
    # first, with its notes
    assert main(["check-frame", str(path)]) == 4
    told = capsys.readouterr()
    assert told.out == "" and told.err.splitlines()[-2:] == [
        "FrameError: the body has no span 'r9'",
        "anchors name spans of the body",
    ]
    assert told.err.startswith("FrameError: ") and " at /interventions/sham" in told.err


def _drift(change):
    raw = copy.deepcopy(REFUND)
    change(raw)
    return raw


@pytest.mark.parametrize(
    "shape, raw",
    [
        ("an empty name", _drift(lambda r: r.update(name=""))),
        ("an empty battery kind", _drift(lambda r: r["battery"].update(kind=""))),
        ("a body key besides spans", _drift(lambda r: r["body"].update(notes="x"))),
        ("an input key besides id and text", _drift(lambda r: r["inputs"][0].update(note="x"))),
        ("an anchor named twice", _drift(lambda r: r.update(anchors=r["anchors"] * 2))),
        (
            "a bypass span named twice",
            _drift(lambda r: r["interventions"].update(bypass=["r5", "r5"])),
        ),
        (
            "an allowed label named twice",
            _drift(lambda r: r["allowed"].update(ablation=["grant", "grant"])),
        ),
    ],
)
def test_the_parser_refuses_what_the_schema_refuses(shape, raw):
    # a Python caller cannot run a frame the published schema calls invalid
    assert list(VALIDATOR.iter_errors(raw)), shape
    with pytest.raises(FrameError):
        parse(raw)


OPTIONAL = [
    ("materialized",), ("carriage",), ("outsideScope",), ("scopeCheck",),
    ("observe", "order"), ("standing", "stable"), ("allowed", "bypass"),
    *(("interventions", key) for key in
      ("repeat", "eachAnchor", "cumulative", "sham", "presentation", "placement", "bypass",
       "control")),
]  # fmt: skip


@pytest.mark.parametrize("path", OPTIONAL, ids=".".join)
def test_an_optional_key_set_to_null_is_refused_like_the_schema_does(path):
    # null is not "left out": it hashes differently, so the parser refuses it
    raw = copy.deepcopy(REFUND)
    (raw if len(path) == 1 else raw[path[0]])[path[-1]] = None
    assert list(VALIDATOR.iter_errors(raw)), path
    with pytest.raises(FrameError, match="null"):
        parse(raw)


@pytest.mark.parametrize("depth", [200, 600, 1000])
def test_check_frame_refuses_a_deep_frame_as_a_frame_error(tmp_path, capsys, depth):
    path = tmp_path / "deep.json"
    path.write_text('{"a": ' + "[" * depth + "]" * depth + "}")
    assert main(["check-frame", str(path)]) == 4
    err = capsys.readouterr().err
    assert err.startswith("FrameError: ") and "Traceback" not in err
