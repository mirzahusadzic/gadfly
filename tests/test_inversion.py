"""The inversion trial on Tendora's reference frame: may Jordan restore the
database? Built from what Tendora printed for its bundled demo (Apache-2.0),
read here by two engines of rules, one that follows the approval rule's sense
and one that, as a negation bug would, does not. No engine is called."""

import json
from pathlib import Path

import pytest

from midwife.pipeline import calls_needed, judge, run, situate
from midwife.types import Budget, Observation
from midwife.verdict import CARRIED, MISALIGNED

FRAME = Path(__file__).parent / "fixtures" / "restore-inversion.json"
RULE = "only after the incident commander approves the restore."
INVERTED = "only after the incident commander does not approve the restore."


class Rules:
    """Yes when the approval rule is met, No when it is not, open without it."""

    name = "rules"

    def __init__(self, follows_sense=True):
        self.follows_sense = follows_sense

    def check(self, frame):
        pass

    def observe(self, frame, prompt, max_output_tokens):
        body, _, asked = prompt.rpartition("\n\n---\n\n")
        approved = "has approved" in asked
        if RULE in body:
            permitted = approved
        elif INVERTED in body:  # the bug: the negation is not read
            permitted = (not approved) if self.follows_sense else approved
        else:
            return Observation(label="open")
        return Observation(label="Yes" if permitted else "No")


@pytest.fixture
def frame():
    return situate(json.loads(FRAME.read_text(encoding="utf-8")))


def read(frame, engine):
    result = run(frame, engine, Budget(calls=calls_needed(frame)))
    return judge(frame, result.records)


def test_the_inversion_turns_each_answer_on_an_engine_that_reads_the_rule(frame):
    # the predictions written first: Yes with approval and No without; turned
    # by the inversion; open where the rule is cut; carried on both
    findings = {f.input: f for f in read(frame, Rules())}
    assert findings["approved"].levels == {
        "baseline": "Yes",
        "repeat": "Yes",
        "ablation": "open",
        "inversion": "No",
        "control": "open",
    }
    assert findings["not-approved"].levels["baseline"] == "No"
    assert findings["not-approved"].levels["inversion"] == "Yes"
    assert {f.category for f in findings.values()} == {CARRIED}


def test_the_inversion_tells_an_engine_that_drops_the_negation(frame):
    findings = read(frame, Rules(follows_sense=False))
    assert {f.category for f in findings} == {MISALIGNED}
    assert findings[0].evidence[-1] == (
        "inversion left it at Yes: the answer does not follow the relation's sense"
    )
