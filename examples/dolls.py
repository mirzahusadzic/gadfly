"""Rung 21's recoil, read back from the kept files: no model is called.

    uv run python examples/dolls.py [--gate]

The five dolls of examples/matryoshka/ as unpacked, and the walk that
carries the second doll's word up from the smallest; with `--gate`, rung
21's verdict read from its kept runs as `until_firm` reads them, the gate it
sets, and what its decision does when it climbs to the largest doll.
"""

from __future__ import annotations

import sys
from pathlib import Path

from midwife.cli import load_records
from midwife.frame import load, parse
from midwife.recoil import found, gate, successor, until_firm, walk
from midwife.types import Budget

HERE = Path(__file__).parent
LABELS = ["girls", "boys", "mixed", "unclear"]


def main(gated: bool) -> None:
    dolls = [load(path) for path in sorted((HERE / "matryoshka").glob("*.json"))]
    largest, second, smallest = dolls[0], dolls[1], dolls[-1]
    if gated:
        return gate_of(largest, second)
    for doll in dolls:
        holes = ", ".join(f"{h['id']} ({h['kind']})" for h in doll.holes) or "none"
        print(f"{doll.name}: {len(doll.spans)} lines, holes {holes}")
    slip = found(smallest, "slip")
    walked = walk(slip, smallest, dolls)
    print(f"\nthe slip, found in the {smallest.name}: {slip.text}")
    inward = {doll.hash: n for n, doll in enumerate(dolls)}
    climbed = sorted(walked.passed, key=lambda frame: -inward[frame.hash])
    print(f"  passed on by the {', the '.join(frame.name for frame in climbed)}")
    for frame, holes in walked.fits:
        print(f"  fits the {frame.name}, hole {', '.join(holes)}")
    print(f"  complete: {'yes' if walked.complete else 'no'}")


def gate_of(largest, second) -> None:
    path = HERE / "21-second-doll-word.json"
    rung = load(path)
    runs = [load_records(str(p)) for p in sorted((HERE / "runs" / path.stem).glob("*.jsonl"))]
    asked = until_firm(rung, None, Budget(calls=1), kept=runs)
    state = "firm" if asked.firm else "not firm"
    print(f"rung 21, the {rung.name} asked again with its word: {asked.category}")
    runs_made = f"{len(asked.runs)} run{'s' if len(asked.runs) != 1 else ''}"
    print(f"  {state} after {runs_made}, read alike in {asked.shares['who']:.0%} of draws")
    recoil = gate(second, rung, asked)
    print(f"  the gate: {recoil.gate}")
    for piece in recoil.climbs:
        climbed = walk(piece, rung, [largest, rung])
        for frame, holes in climbed.fits:
            print(f"  {piece.text!r} fits the {frame.name}, hole {', '.join(holes)}")
            observe = {**frame.raw["observe"], "labels": LABELS}
            again = parse(successor(frame, holes[0], piece, observe=observe))
            reframed = gate(frame, again)
            changed = ", ".join(reframed.changed)
            print(f"  the {frame.name} asked again: {reframed.gate}, it changed {changed}")
            labels = ", ".join(frame.labels)
            print(f"  the {frame.name} as it was asked stands: {labels}")


if __name__ == "__main__":
    main("--gate" in sys.argv[1:])
