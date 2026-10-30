"""System-prompt line: does the refusal rest on system line S-2?

Two scorers refuse while S-2 stands and are read under ablation (S-2
removed) and a control (the request quote removed). One refuses because of
the request text, so ablation leaves it refusing but the control moves it:
cooled, with discrimination shown. The other refuses everything, so the
control leaves it too: unresolved, the scorer cannot tell. Deterministic.
"""

from __future__ import annotations

import json
from pathlib import Path

from gadfly.pipeline import calls_needed, judge, run, situate
from gadfly.types import Budget, Observation

HERE = Path(__file__).parent


class AlwaysRefuse:
    """Refuses every trial body, whatever was removed."""

    name = "always-refuse"

    def check(self, frame):
        if frame.battery["kind"] != self.name:
            raise ValueError(f"this frame asks for the {frame.battery['kind']} battery")

    def observe(self, frame, prompt, max_output_tokens):
        return Observation(label="refuse")


class RequestAlarm(AlwaysRefuse):
    """Refuses when the request quote is present; complies without it."""

    name = "request-alarm"

    def observe(self, frame, prompt, max_output_tokens):
        policy, _, _ = prompt.partition("\n\n---\n\n")
        return Observation(label="refuse" if "production API key" in policy else "comply")


def assess(raw: dict, battery) -> tuple[str, list[str]]:
    frame = situate({**raw, "battery": {"kind": battery.name}})
    result = run(frame, battery, Budget(calls=calls_needed(frame)))
    assert result.stopped is None, result.stopped
    [finding] = judge(frame, result.records)
    return finding.category, finding.evidence + finding.obligations


def main() -> list[tuple[str, str, list[str]]]:
    raw = json.loads((HERE / "system_prompt.json").read_text(encoding="utf-8"))
    return [(b.name, *assess(raw, b)) for b in (RequestAlarm(), AlwaysRefuse())]


if __name__ == "__main__":
    for name, category, notes in main():
        print(f"{name}: {category}")
        for note in notes:
            print(f"  {note}")
