"""After the Poem's load-bearing test, replayed through Gadfly.

After the Poem asks whether the level a reader gives a world on one question
rests on the evidence the reading cites (docs/study.md, "The load-bearing
test"). Its scripts/load_bearing.py keeps every trial's sessions in a plan's
findings.json. This is what a user of Gadfly does with such a study:

1. situate the frame, in the study's own coordinates;
2. turn each retained session into a record;
3. judge, and compare with what the study published.

No model is called: the records already exist. Gadfly must reach the category
the study published, case by case. The study's data stays where it is; pass
the directory of one plan that load_bearing.py has run (plan.json and
findings.json):

    uv run python examples/after_the_poem.py <plan directory>

After the Poem: https://github.com/mirzahusadzic/after-the-poem
"""

from __future__ import annotations

import json
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from gadfly.pipeline import judge, plan, situate
from gadfly.types import Record

# The rubric's levels, lowest first.
LEVELS = ["level-0", "level-1", "level-2", "level-3", "level-4"]
# The world's own words, which the study's presentation trial masks.
SEED = "seed vocabulary"
# The study's trial names, and the trial ids Gadfly plans for them.
TRIALS = {
    "baseline": "baseline",
    "repeat": "repeat",
    "presentation": "presentation",
    "ablation": "ablation",
    "sham": "sham-1",
}


def agreement_count(sessions: int, threshold: float) -> int:
    """The fewest agreeing sessions the study accepts: it rounds the agreeing
    share half up to two decimals, the precision its thresholds are written
    in, and compares (scripts/evaluation_contract.py, meets_agreement)."""

    def meets(agreeing: int) -> bool:
        share = (Decimal(agreeing) / Decimal(sessions)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return share >= Decimal(str(threshold))

    return min(k for k in range(1, sessions + 1) if meets(k))


def frame_for(case: dict, study: dict) -> dict:
    """The study's frame, coordinate by coordinate, as its plan pins it. The
    body is described, not copied: the cited ranges and the sham's uncited
    blocks of the same lengths, both in the seed vocabulary its presentation
    trial masks."""
    pinned = study["frame"]
    lines = case.get("ablated_lines") or 0
    return {
        "name": case["id"],
        "relation": "the support the cited evidence gives a reading's level on one question",
        "locus": f"the reading of {case['run_id']} on {case['axis']}",
        "role": "a person reading the page",
        "grain": "one question, one world, one aggregate level",
        "purpose": "the level shown rests on evidence the reader can open",
        "trajectory": "frozen world, evidence the reader sees, independent sessions, quorum, level",
        "crossing": "the page the reader sees",
        "promise": (
            "removing the cited evidence lowers the level; irrelevant changes do not move it"
        ),
        "baseline": {
            "model": pinned["model"],
            "reasoning": pinned["reasoning"],
            "rubric": pinned["rubric_sha256"],
            "prompt": pinned["prompt_version"],
            "plan": study["id"],
        },
        "body": {
            "spans": [
                {
                    "id": "cited",
                    "text": f"the {lines} lines the reference reading cited, in {SEED}",
                    "kind": "lines",
                },
                {
                    "id": "uncited",
                    "text": f"{lines} uncited lines in blocks of the same lengths, in {SEED}",
                    "kind": "lines",
                },
            ]
        },
        "anchors": ["cited"],
        "inputs": [{"id": case["axis"], "text": f"the level on {case['axis']}"}],
        "observe": {
            "labels": LEVELS,
            "order": LEVELS,
            "instruction": "read the world and give the rubric's level for this question",
        },
        "interventions": {
            "repeat": True,
            "ablation": True,
            "presentation": {SEED: "neutral tokens"},
            "sham": {"draws": 1},
        },
        "allowed": {"ablation": "lower"},
        "standing": {
            "quorum": pinned["sessions"],
            "agree": agreement_count(pinned["sessions"], pinned["minimum_agreement"]),
            "stable": study.get("rules", 1) >= 2,
        },
        "battery": {"kind": "after-the-poem-reader", "model": pinned["model"]},
        # The study names the category and lists what is open beside it.
        "carriage": "listed",
    }


def records_for(frame, case: dict) -> list[Record]:
    """Each retained session of each trial, as Gadfly's record of one call."""
    bodies = {trial.id: trial.body_hash for trial in plan(frame)}
    records = []
    for name, trial in case["trials"].items():
        if trial is None:  # the study ran no evaluation: no records, no level
            continue
        for index, sample in enumerate(trial["samples"]):
            label = sample if sample in LEVELS else None
            records.append(
                Record(
                    frame=frame.hash,
                    input=frame.inputs[0]["id"],
                    trial=TRIALS[name],
                    run=index,
                    body=bodies[TRIALS[name]],
                    prompt=trial["evaluation_sha256"],
                    battery=frame.battery["kind"],
                    observation=label,
                    opening=None if label else f"session gave {sample}",
                    raw="",
                    usage={},
                )
            )
    return records


def replay(directory: Path) -> list[tuple[str, str, str, list[str]]]:
    study = json.loads((directory / "plan.json").read_text(encoding="utf-8"))
    published = json.loads((directory / "findings.json").read_text(encoding="utf-8"))
    study.setdefault("rules", published.get("rules", 1))
    rows = []
    for case in published["cases"]:
        frame = situate(frame_for(case, study))
        [finding] = judge(frame, records_for(frame, case))
        rows.append((case["id"], case["category"], finding.category, finding.evidence))
    return rows


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    rows = replay(Path(sys.argv[1]))
    for name, theirs, ours, evidence in rows:
        mark = "same" if theirs == ours else "DIFFERS"
        print(f"{mark:8} {name}: published {theirs}; Gadfly {ours} ({'; '.join(evidence)})")
    same = sum(theirs == ours for _, theirs, ours, _ in rows)
    print(f"{same} of {len(rows)} cases reach the published category")
    return 0 if same == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
