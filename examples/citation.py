"""Cited source: does the answer's crate count rest on source S-2?

Two scorers read the same frame. Both give the count while S-2 is cited and
drop it when S-2 is removed. Only one of them reads the source; the other
reads the word "cobalt". The presentation trial, which renames cobalt
consistently, tells them apart. Deterministic: no model is called.
"""

from __future__ import annotations

import json
from pathlib import Path

from gadfly.pipeline import calls_needed, judge, run, situate
from gadfly.types import Budget, Observation

HERE = Path(__file__).parent


class WordMatcher:
    """Grounded when the policy contains its word."""

    name = "word-matcher"
    words = ("cobalt",)

    def check(self, frame):
        if frame.battery["kind"] != self.name:
            raise ValueError(f"this frame asks for the {frame.battery['kind']} battery")

    def observe(self, frame, prompt, max_output_tokens):
        policy, _, _ = prompt.partition("\n\n---\n\n")
        return Observation(
            label="grounded" if any(w in policy for w in self.words) else "ungrounded"
        )


class CitationReader(WordMatcher):
    """Reads the source in either of its wordings."""

    name = "citation-reader"
    words = ("cobalt manifest records", "verdigris manifest records")


def assess(raw: dict, battery) -> tuple[str, list[str]]:
    frame = situate({**raw, "battery": {"kind": battery.name}})
    result = run(frame, battery, Budget(calls=calls_needed(frame)))
    assert result.stopped is None, result.stopped
    [finding] = judge(frame, result.records)
    return finding.category, finding.evidence + finding.obligations


def main() -> list[tuple[str, str, list[str]]]:
    raw = json.loads((HERE / "citation.json").read_text(encoding="utf-8"))
    return [(b.name, *assess(raw, b)) for b in (WordMatcher(), CitationReader())]


if __name__ == "__main__":
    for name, category, notes in main():
        print(f"{name}: {category}")
        for note in notes:
            print(f"  {note}")
