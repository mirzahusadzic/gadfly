"""The incident chain read from the other side, for the branch tests: what a
rollback would have to rest on is written from the question alone, and the
decision is then read from that, the metric lines and the question. The
maker and the reader are rules, so every trial's answer is known before it
is asked; `branch` is the battery the command line names."""

import copy

from midwife.batteries.branch import Branch
from midwife.batteries.crossing import Function
from midwife.types import Observation
from tests.fixtures.incident import INCIDENT, cause

PARTS = "\n\n---\n\n"
NEEDS = {
    **copy.deepcopy(INCIDENT),
    "name": "rollback-from-needs",
    "trajectory": "the question, what an answer needs, the metrics, the rollback decision",
    "crossing": "what the engineer wrote down before reading the metrics",
    "observe": {
        "labels": ["rollback", "investigate", "keep"],
        "instruction": "Decide from the metric lines, against what is needed.",
    },
    "battery": {"kind": "branch", "maker": {"kind": "needs"}, "reader": {"kind": "needs-reader"}},
}


def needs(question):
    """Writes what an answer would have to rest on, from the question alone."""
    return f"To answer {question!r}, the lines must name a change that explains the incident."


class NeedsReader:
    """Decides from the metric lines against what was written down: roll back
    when they name the change, look into it when they do not, keep the
    deploy when there was no incident. Without the three parts it was
    promised, it keeps."""

    name = "needs-reader"
    concurrent = True

    def __init__(self):
        self.prompts = []

    def check(self, frame):
        if frame.battery["kind"] != self.name:
            raise ValueError("not my line")

    def observe(self, frame, prompt, max_output_tokens):
        self.prompts.append((prompt, max_output_tokens))
        parts = prompt.split(PARTS)
        if len(parts) != 3 or parts[0] != needs(parts[2]):
            return Observation(label="keep", usage={"output_tokens": 3}, served="needs-reader 1")
        found = cause(parts[1])
        if "connection pool" in found:
            label = "rollback"
        elif "unknown" in found:
            label = "investigate"
        else:
            label = "keep"
        return Observation(label=label, usage={"output_tokens": 3}, served="needs-reader 1")


branch = Branch(Function("needs", needs), NeedsReader())
