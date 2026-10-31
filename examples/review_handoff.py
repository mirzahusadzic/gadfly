"""The worked example of "When meaning is load-bearing": from failed check to
review handoff (docs/load-bearing.md, "Worked example").

A failed test challenges one claim; a reviewer may inspect and propose, not
apply. Three review systems turn the same material into a handoff; two
frames ask whether the failure's relation to the claim, and the grant's
scope, survive into it.

    uv run python examples/review_handoff.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from gadfly.pipeline import calls_needed, judge, run, situate
from gadfly.types import Budget, Observation

HERE = Path(__file__).parent
FRAMES = ("review_finding.json", "review_authority.json")


def operations(body: str) -> list[str]:
    """What the grant permits, and only while the state says it is granted."""
    grant = re.search(r"Grant (G-\d+): (.+)", body)
    if grant is None or f"State: {grant.group(1)} is granted to" not in body:
        return []  # an unbound grant permits nothing: the opening a bypass exposes
    ops = [
        op
        for op, phrase in (("inspect", "may inspect"), ("propose", "propose a repair"))
        if phrase in grant.group(2)
    ]
    return ops + (["apply"] if "may apply" in grant.group(2) else [])


def projection(body: str) -> dict:
    """The handoff generated from the review state; what it lacks, it says."""
    handoff = {
        "claim": None,
        "status": None,
        "evidence": None,
        "limits": None,
        "openings": [],
        "operations": operations(body),
    }
    capture = re.search(r"Capture (T-\d+): ([^;]+); (.+)", body)
    link = re.search(r"State: (T-\d+) challenges (C-\d+)\.", body)
    if capture is None:
        handoff["openings"].append("no captured result")
    elif link is None or link.group(1) != capture.group(1):
        handoff["openings"].append(f"missing connection: {capture.group(1)} reaches no claim")
    elif "a captured failure is a reason to reconsider" not in body:
        handoff["openings"].append(f"no rule makes {capture.group(1)} a reason")
    else:
        handoff.update(
            claim=link.group(2),
            status="reconsider",
            evidence=f"{capture.group(1)}: {capture.group(2)}",
            limits=capture.group(3),
        )
    return handoff


def summary(body: str) -> dict:
    """ "Review complete; fix ready": the source link kept, the distinctions lost."""
    source = re.search(r"Capture (T-\d+)", body)
    return {
        "status": "complete",
        "note": "review complete; fix ready",
        "source": source and source.group(1),
        "operations": ["apply", "inspect", "propose"],
    }


def drops_openings(body: str) -> dict:
    """The projection, but what it lacks it leaves out instead of saying."""
    handoff = projection(body)
    return {**handoff, "openings": []} if handoff["openings"] else handoff


SYSTEMS = {
    "state projection": projection,
    "summary: fix ready": summary,
    "drops its openings": drops_openings,
}


def observe_finding(handoff: dict) -> str:
    """o_p for the finding: claim, status, evidence and limits, openings."""
    if handoff.get("openings"):
        return "opening"
    if handoff.get("status") == "reconsider" and handoff.get("evidence") and handoff.get("limits"):
        return "reconsider"
    return "complete" if handoff.get("status") == "complete" else "silent"


def observe_operations(handoff: dict) -> str:
    return "+".join(sorted(handoff.get("operations") or [])) or "none"


class ReviewSystem:
    """A battery that runs a review system and reads its handoff through o_p."""

    def __init__(self, name: str):
        self.name, self.system = name, SYSTEMS[name]

    def check(self, frame):
        if frame.battery["kind"] != self.name:
            raise ValueError(f"this frame asks for the {frame.battery['kind']} battery")

    def observe(self, frame, prompt, max_output_tokens):
        handoff = self.system(prompt.partition("\n\n---\n\n")[0])
        field = frame.raw["observe"]["field"]
        label = observe_finding(handoff) if field == "finding" else observe_operations(handoff)
        return Observation(label=label, raw=json.dumps(handoff))


def assess(file: str, name: str, only=None):
    raw = json.loads((HERE / file).read_text(encoding="utf-8"))
    frame = situate({**raw, "battery": {"kind": name}})
    battery = ReviewSystem(name)
    result = run(frame, battery, Budget(calls=calls_needed(frame)), only=only)
    [finding] = judge(frame, result.records)
    return finding


def main() -> list[tuple[str, str, str]]:
    rows = [(name, *(assess(file, name).category for file in FRAMES)) for name in SYSTEMS]
    # An unavailable trial record is insufficient evidence.
    planned = ("baseline", "repeat", "ablation", "sham-1", "sham-2", "bypass")
    rows.append(
        ("projection, a record lost", assess(FRAMES[0], "state projection", planned).category, "-")
    )
    return rows


if __name__ == "__main__":
    print(f"{'system':28} {'finding':24} authority")
    for name, finding, authority in main():
        print(f"{name:28} {finding:24} {authority}")
