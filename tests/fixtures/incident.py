"""An incident chain for the crossing tests: metric lines at the near side,
a cause written from them, and a rollback decided from the cause. The maker
and the reader are rules, so every trial's answer is known before it is
asked; `crossing` is the battery the command line names."""

from midwife.batteries.crossing import Crossing, Function
from midwife.types import Observation

INCIDENT = {
    "name": "rollback-from-cause",
    "relation": "a rollback rests on the change that shrank the pool",
    "locus": "the incident's metric lines",
    "role": "the on-call engineer",
    "grain": "one metric line",
    "purpose": "decide whether to roll a deploy back",
    "trajectory": "metrics, the incident's cause, the rollback decision",
    "crossing": "the cause the engineer reads",
    "promise": "without the pool change, the engineer investigates before rolling back",
    "baseline": "the metric lines as recorded, and one question",
    "body": {
        "spans": [
            {"id": "m1", "text": "p99 latency rose from 120 ms to 900 ms.", "kind": "metric"},
            {"id": "m2", "text": "Deploy 42 shrank the connection pool from 50 to 5.",
             "kind": "metric"},
            {"id": "m3", "text": "The error rate held at 0.1%.", "kind": "metric"},
            {"id": "m4", "text": "CPU use held at 40%.", "kind": "metric"},
            {"id": "n1", "text": "These lines are every signal there is.", "kind": "note"},
        ]
    },
    "anchors": ["m2"],
    "inputs": [{"id": "q1", "text": "Should deploy 42 be rolled back now?"}],
    "observe": {
        "labels": ["rollback", "investigate", "keep"],
        "instruction": "Decide from the incident's cause.",
    },
    "interventions": {
        "repeat": True,
        "ablation": True,
        "sham": {"draws": 2},
        "presentation": {"shrank": "cut"},
        "bypass": ["n1"],
    },
    "allowed": {"ablation": ["investigate", "keep"]},
    "standing": {"quorum": 3, "agree": 2},
    "carriage": "listed",
    "battery": {"kind": "crossing", "maker": {"kind": "cause"}, "reader": {"kind": "cause-reader"}},
}  # fmt: skip


def cause(body):
    """Writes the incident's cause from the metric lines it is given."""
    if "These lines are every signal there is." not in body:
        return "Cause unknown; other signals were not looked at."
    if "connection pool" in body and ("shrank" in body or " cut " in body):
        return "Deploy 42 shrank the connection pool, and requests queued for a connection."
    if "latency rose" in body:
        return "Cause unknown; latency rose after deploy 42."
    return "No incident."


def headline(body):
    """A lossy maker: the headline is all it keeps, whatever the lines say."""
    return "Latency rose after deploy 42; the team is looking into it."


class CauseReader:
    """Decides from the cause: roll back a known cause, look into an unknown
    one, keep the deploy when there was no incident."""

    name = "cause-reader"
    concurrent = True

    def __init__(self):
        self.prompts = []

    def check(self, frame):
        if frame.battery["kind"] != self.name:
            raise ValueError("not my line")

    def observe(self, frame, prompt, max_output_tokens):
        self.prompts.append((prompt, max_output_tokens))
        made, _, _question = prompt.partition("\n\n---\n\n")
        if "connection pool" in made:
            label = "rollback"
        elif "unknown" in made or "looking into" in made:
            label = "investigate"
        else:
            label = "keep"
        return Observation(label=label, usage={"output_tokens": 3}, served="cause-reader 1")


crossing = Crossing(Function("cause", cause), CauseReader())
