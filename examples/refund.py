"""A refund policy, its receipt rule, and two scorers: the whole pipeline,
with the records kept where the caller chooses (here, a JSON Lines file).

Both scorers decline the request while the rule is in the policy, and grant it
once the rule is removed. Only one of them reads the rule; the other reads a
phrase. The presentation trial, which renames "receipt" consistently, tells
them apart. The rule reader also applies the rules only while the policy says
they decide (its binding line): with that line cut, it cannot decide, which
is the opening the frame's bypass must expose.

    python examples/refund.py records.jsonl
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from gadfly.pipeline import calls_needed, judge, run, situate
from gadfly.types import Budget, Observation

FRAME = Path(__file__).with_name("refund.json")


# --8<-- [start:battery]
class PhraseMatcher:
    """Declines when the policy contains one of its phrases."""

    name = "phrase-matcher"
    phrases: tuple[str, ...] = ("requires a receipt",)

    def check(self, frame):
        if frame.battery["kind"] != self.name:
            raise ValueError(f"this frame asks for the {frame.battery['kind']} battery")

    def observe(self, frame, prompt, max_output_tokens):
        policy, _, _request = prompt.partition("\n\n---\n\n")
        return Observation(label="decline" if any(p in policy for p in self.phrases) else "grant")


# --8<-- [end:battery]


class RuleReader(PhraseMatcher):
    """Reads the rule in either of its wordings, while the rules bind."""

    name = "rule-reader"
    phrases = ("requires a receipt", "requires a proof of purchase")

    def observe(self, frame, prompt, max_output_tokens):
        policy, _, _request = prompt.partition("\n\n---\n\n")
        if "These rules decide every request." not in policy:
            return Observation(label="unclear")  # no rule binds: nothing to decide by
        return super().observe(frame, prompt, max_output_tokens)


def main(path: Path) -> list[tuple[str, str, list[str]]]:
    raw = json.loads(FRAME.read_text(encoding="utf-8"))
    rows = []
    with path.open("x", encoding="utf-8") as kept:  # a new file: never another run's
        for battery in (PhraseMatcher(), RuleReader()):
            # Another battery is another coordinate, so another frame.
            frame = situate({**raw, "battery": {"kind": battery.name}})
            result = run(
                frame,
                battery,
                Budget(calls=calls_needed(frame)),
                on_record=lambda r: kept.write(json.dumps(r.as_dict()) + "\n"),
            )
            assert result.stopped is None, result.stopped
            rows.append((battery.name, frame.hash))
    # The verdict is read back from the caller's own records, nothing else.
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    findings = []
    for name, frame_hash in rows:
        frame = situate({**raw, "battery": {"kind": name}})
        [finding] = judge(frame, [r for r in records if r["frame"] == frame_hash])
        findings.append((name, finding.category, finding.evidence + finding.obligations))
    return findings


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    for name, category, notes in main(Path(sys.argv[1])):
        print(f"{name}: {category}")
        for note in notes:
            print(f"  {note}")
