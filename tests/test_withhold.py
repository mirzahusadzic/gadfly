"""Withheld text: refused before any call, by name, line or pattern, the
training part only where a battery says its calls may train."""

import json
import re
from pathlib import Path

import pytest

from midwife.batteries.crossing import Crossing, Function
from midwife.batteries.egemma import EGemma
from midwife.batteries.unified import Unified
from midwife.cli import main
from midwife.errors import FrameError, UsageError
from midwife.pipeline import run, situate
from midwife.recoil import until_firm
from midwife.types import Budget, Observation
from midwife.withhold import Withhold, line_sha256, read_withhold, refuse_withheld, withheld

ROOT = Path(__file__).parent.parent
REFUND = ROOT / "tests/fixtures/refund.json"
SECRET = "sk-" + "a" * 24


class Counting:
    """The rule reader's name, counting calls, saying nothing of training."""

    name = "rule-reader"

    def __init__(self, trains=None):
        self.calls = 0
        if trains is not None:
            self.trains = lambda frame: trains

    def check(self, frame):
        pass

    def observe(self, frame, prompt, max_output_tokens):
        self.calls += 1
        return Observation(label="grant")


def withhold(**parts):
    return read_withhold(json.dumps(parts))


def planted(raw, text):
    raw["battery"] = {"kind": "rule-reader"}
    raw["body"]["spans"][1]["text"] = text
    return situate(raw)


def test_a_name_is_matched_as_a_whole_word_in_any_case(raw):
    held = withhold(training={"names": ["Kestrel"]})
    assert withheld(planted(raw, "Kestrel-lab notes say a receipt is needed."), held)
    assert withheld(planted(raw, "the kestrel rule requires a receipt."), held)
    assert not withheld(planted(raw, "Kestrels require a receipt."), held)


def test_a_line_copied_into_a_diff_still_matches_its_source(raw):
    # its words joined by single spaces, and read again without a diff marker
    source = "def private_rule(receipt):    return receipt is not None"
    held = withhold(training={"lines": [line_sha256(source)]})
    frame = planted(raw, "+    def private_rule(receipt):  return receipt is not None")
    assert [h.kind for h in withheld(frame, held)][:1] == ["a line"]
    assert not withheld(planted(raw, "A refund requires a receipt."), held)


def test_the_training_part_binds_only_a_battery_that_may_train(raw):
    frame = planted(raw, "Kestrel says a refund requires a receipt.")
    held = withhold(training={"names": ["Kestrel"]})
    assert withheld(frame, held, training=False) == []
    keeps = Counting(trains=False)
    run(frame, keeps, Budget(calls=100), withhold=held)  # no refusal: it keeps no data
    assert keeps.calls > 0
    for reader in (Counting(), Counting(trains=True)):  # silent is read as may
        with pytest.raises(FrameError, match="^frame 'refund-receipt' would send withheld text"):
            run(frame, reader, Budget(calls=100), withhold=held)
        assert reader.calls == 0


def test_the_always_part_binds_every_battery_and_never_says_the_text(raw):
    frame = planted(raw, f"A refund requires a receipt; key {SECRET}.")
    held = withhold(always={"patterns": [r"sk-[a-z0-9]{20,}"]})
    reader = Counting(trains=False)
    with pytest.raises(FrameError) as refused:
        run(frame, reader, Budget(calls=100), withhold=held)
    assert reader.calls == 0
    said = " ".join([str(refused.value), *refused.value.__notes__])
    assert "a pattern" in said and "no call may carry it" in said and SECRET not in said


def test_until_firm_refuses_before_its_first_run(raw):
    raw["standing"] = {"quorum": 3, "agree": 2}
    frame = planted(raw, "Kestrel says a refund requires a receipt.")
    reader = Counting()
    with pytest.raises(FrameError):
        until_firm(
            frame, reader, Budget(calls=1000), withhold=withhold(training={"names": ["kestrel"]})
        )
    assert reader.calls == 0


def test_each_battery_says_whether_its_calls_may_train(raw):
    line = {"kind": "unified", "model": "openrouter/meta/muse-spark-1.3-contributor"}
    raw["battery"] = dict(line)
    assert Unified().trains(situate(raw)) is False  # without consent: the deny policy
    raw["battery"]["trainsOnInputs"] = [line["model"]]
    assert Unified().trains(situate(raw)) is True
    raw["battery"] = {"kind": "egemma"}
    assert EGemma().trains(situate(raw)) is False
    # a crossing's own maker, a function that says nothing, is read as one that may
    raw["battery"] = {"kind": "crossing", "maker": {"kind": "echo"}, "reader": line}
    assert Crossing(Function("echo", str), Unified()).trains(situate(raw)) is True


@pytest.mark.parametrize(
    ("text", "said"),
    [
        (b"\xff", "file 'w.json' is not UTF-8 text"),
        (b"{", "file 'w.json' cannot be read as JSON"),
        (b'{"secret": {}}', "file 'w.json' is not a withhold set"),
        (b'{"training": {"names": [""]}}', "file 'w.json' is not a withhold set"),
        (b'{"training": {"lines": ["abc"]}}', "file 'w.json' lists a line that is no SHA-256"),
        (
            b'{"always": {"patterns": ["("]}}',
            "file 'w.json' holds a pattern that is no regular expression",
        ),
    ],
)
def test_a_set_that_is_not_one_is_refused_and_named(text, said):
    with pytest.raises(UsageError, match=f"^{re.escape(said)}"):
        read_withhold(text, path="w.json")


def test_refuse_withheld_counts_every_prompt_that_holds_some(raw):
    frame = planted(raw, "Kestrel says a refund requires a receipt.")
    with pytest.raises(FrameError) as refused:
        refuse_withheld(frame, withhold(training={"names": ["Kestrel"]}))
    assert any(
        note.endswith("prompts in all hold withheld text") for note in refused.value.__notes__
    )
    assert Withhold() == read_withhold("{}")


def test_the_command_line_refuses_before_a_call_and_makes_no_file(tmp_path, capsys):
    raw = json.loads(REFUND.read_text(encoding="utf-8"))
    raw["body"]["spans"][1]["text"] = "Kestrel says a refund requires a receipt."
    raw["standing"] = {"quorum": 3, "agree": 2}
    frame = tmp_path / "frame.json"
    frame.write_text(json.dumps(raw), encoding="utf-8")
    sets = tmp_path / "w.json"
    sets.write_text(json.dumps({"training": {"names": ["Kestrel"]}}), encoding="utf-8")
    out = tmp_path / "records.jsonl"
    battery = "tests.fixtures.refund:RuleReader"
    argv = ["run", str(frame), "--battery", battery, "--calls", "8", "--out", str(out)]
    assert main([*argv, "--withhold", str(sets)]) == 4
    assert not out.exists()
    said = capsys.readouterr().err
    assert "would send withheld text, a name, in trial 'baseline'" in said
    assert "Kestrel" not in said.replace(str(tmp_path), "")
    assert main(["check-frame", str(frame), "--withhold", str(sets)]) == 4
    assert "withheld text" in capsys.readouterr().err
    (tmp_path / "runs").mkdir()
    firm = ["firm", str(frame), "--battery", battery, "--runs", str(tmp_path / "runs")]
    assert main([*firm, "--calls", "100", "--withhold", str(sets)]) == 4
    assert list((tmp_path / "runs").iterdir()) == []
    assert main(["check-frame", str(REFUND), "--withhold", str(sets)]) == 0
    capsys.readouterr()
    # --json lists every place, as withheld() returns them
    assert main(["check-frame", str(frame), "--withhold", str(sets), "--json"]) == 4
    places = json.loads(capsys.readouterr().err)["error"]["withheld"]
    expected = [h.as_dict() for h in withheld(situate(raw), read_withhold(sets.read_bytes()))]
    assert places == expected and len(places) > 1
    assert main(["check-frame", str(REFUND), "--withhold", str(sets), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["withheld"] == []


def test_a_name_is_held_in_every_case_folding(raw):
    # pass 16 R1: full case folding, so Straße holds STRASSE back too
    held = withhold(always={"names": ["Straße"]})
    assert withheld(planted(raw, "STRASSE requires a receipt."), held)
    assert withheld(planted(raw, "strasse requires a receipt."), held)
    assert not withheld(planted(raw, "Strassen require a receipt."), held)


def test_a_refusal_names_a_withheld_id_by_its_place(raw, tmp_path, capsys):
    # pass 16 R2: an id the set withholds is never said, in text or JSON
    raw = json.loads(REFUND.read_text(encoding="utf-8"))
    raw["name"], raw["inputs"][0]["id"] = "Kestrel", "Kestrel"
    raw["body"]["spans"][1]["text"] = "Kestrel requires a receipt."
    frame = tmp_path / "frame.json"
    frame.write_text(json.dumps(raw), encoding="utf-8")
    sets = tmp_path / "w.json"
    sets.write_text(json.dumps({"always": {"names": ["kestrel"]}}), encoding="utf-8")
    assert main(["check-frame", str(frame), "--withhold", str(sets), "--json"]) == 4
    said = capsys.readouterr().err
    assert "kestrel" not in said.casefold().replace(str(tmp_path).casefold(), "")
    error = json.loads(said)["error"]
    assert error["message"].startswith("the frame would send withheld text, a name")
    assert {place["input"] for place in error["withheld"]} == {"input 1"}
    assert main(["check-frame", str(frame), "--withhold", str(sets)]) == 4
    assert "kestrel" not in capsys.readouterr().err.casefold().replace(str(tmp_path).casefold(), "")


@pytest.mark.parametrize("answer", [None, 0, "", "no"])
def test_only_an_answer_of_false_keeps_the_training_part_off(raw, answer):
    # pass 16 R3: a trains() that does not answer False is read as one that may
    frame = planted(raw, "Kestrel says a refund requires a receipt.")
    reader = Counting(trains=answer)
    with pytest.raises(FrameError):
        run(frame, reader, Budget(calls=100), withhold=withhold(training={"names": ["Kestrel"]}))
    assert reader.calls == 0
    quiet = type("Quiet", (), {"name": "echo", "trains": lambda self, line: None})()
    raw["battery"] = {"kind": "crossing", "maker": {"kind": "echo"}, "reader": {"kind": "egemma"}}
    assert Crossing(quiet, EGemma()).trains(situate(raw)) is True


def test_an_oversized_pattern_is_refused_as_no_regular_expression(tmp_path, capsys):
    # pass 16 R4: OverflowError while compiling is a caller's mistake, never a bug
    huge = {"always": {"patterns": ["(?:a){999999999999999999999999999999}"]}}
    with pytest.raises(UsageError, match="holds a pattern that is no regular expression"):
        read_withhold(json.dumps(huge))
    sets = tmp_path / "w.json"
    sets.write_text(json.dumps(huge), encoding="utf-8")
    assert main(["check-frame", str(REFUND), "--withhold", str(sets)]) == 2
