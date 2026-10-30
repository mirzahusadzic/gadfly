"""Code invariant: does the output order rest on line L-2?

One scorer reads the sort-key line in either wording. A full run moves as
the promise allows, but its fallback check stays open, so it is not yet
carried. The same records, read without the sham, presentation and bypass
trials, are unresolved (a record lost is no evidence). The receiving owner's
exclusion, declared alone, is not yet outside scope; declared and checked by
the owner, it is. Deterministic.
"""

from __future__ import annotations

import json
from pathlib import Path

from gadfly.pipeline import calls_needed, judge, run, situate
from gadfly.types import Budget, Observation

HERE = Path(__file__).parent
FULL = ("baseline", "repeat", "ablation", "sham-1", "presentation", "bypass")
# The receiving owner's own check of the exclusion: who, what, from what, when.
SCOPE_CHECK = {
    "owner": "the report's maintainers",
    "statement": "the report re-sorts every table it prints",
    "source": "report spec RS-7",
    "encounter": "the October report review",
}
PARTIAL = ("baseline", "repeat", "ablation")


class KeyReader:
    """Sorted while the sort-key line stands, in either wording."""

    name = "key-reader"

    def check(self, frame):
        if frame.battery["kind"] != self.name:
            raise ValueError(f"this frame asks for the {frame.battery['kind']} battery")

    def observe(self, frame, prompt, max_output_tokens):
        policy, _, _ = prompt.partition("\n\n---\n\n")
        if "sort rows by key k" in policy or "order rows by key k" in policy:
            return Observation(label="sorted")
        return Observation(label="unsorted")


def main() -> list[tuple[str, str, list[str]]]:
    raw = json.loads((HERE / "code_invariant.json").read_text(encoding="utf-8"))
    frame = situate({**raw, "battery": {"kind": "key-reader"}})
    battery = KeyReader()
    result = run(frame, battery, Budget(calls=calls_needed(frame)))
    assert result.stopped is None, result.stopped

    rows = []
    [full] = judge(frame, result.records)
    rows.append(("full run", full.category, full.evidence + full.obligations))
    [partial] = judge(frame, [r for r in result.records if r.trial in PARTIAL])
    rows.append(("records lost", partial.category, partial.evidence + partial.obligations))

    scoped = situate(
        {
            **raw,
            "battery": {"kind": "key-reader"},
            "outsideScope": "the receiving owner excludes formatting-only outputs",
        }
    )
    [outside] = judge(scoped, result.records[:0])
    rows.append(("declared out of scope", outside.category, outside.evidence + outside.obligations))

    checked = situate({**scoped.raw, "scopeCheck": SCOPE_CHECK})
    [outside] = judge(checked, result.records[:0])
    rows.append(("declared and checked", outside.category, outside.evidence + outside.obligations))
    return rows


if __name__ == "__main__":
    for name, category, notes in main():
        print(f"{name}: {category}")
        for note in notes:
            print(f"  {note}")
