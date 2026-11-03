"""The nesting dolls' recoil, read back from the kept files: no model is called.

    uv run python examples/dolls.py [--gate] [--rung 21]

The dolls as unpacked, and the walk that carries the piece found in the
smallest up to the doll whose hole it fits; with `--gate`, the frame that
doll is asked again in, read from its kept runs as `until_firm` reads them,
the gate it sets, and what its decision does when it climbs to the largest
doll. Rung 22's painted dolls by default; rung 21's first, coarser set with
`--rung 21`.
"""

from __future__ import annotations

import sys
from pathlib import Path

from midwife.cli import load_records
from midwife.frame import Frame, load, parse
from midwife.recoil import Piece, found, gate, successor, until_firm, walk
from midwife.types import Budget

HERE = Path(__file__).parent
# each set: where its dolls are, and the frame the fitted doll is asked again in
SETS = {"22": ("dolls", "22-kiran-paper"), "21": ("matryoshka", "21-second-doll-word")}


def unpacked(rung: str) -> list[Frame]:
    return [load(path) for path in sorted((HERE / SETS[rung][0]).glob("*.json"))]


def piece(dolls: list[Frame]) -> tuple[Frame, Piece]:
    """The smallest doll, and what it holds that some doll's hole is for."""
    kinds = {hole["kind"] for doll in dolls for hole in doll.holes}
    smallest = dolls[-1]
    [span] = [s for s in smallest.spans if s.kind in kinds]
    return smallest, found(smallest, span.id)


def walked(rung: str) -> None:
    dolls = unpacked(rung)
    for doll in dolls:
        holes = ", ".join(f"{h['id']} ({h['kind']})" for h in doll.holes) or "none"
        print(f"{doll.name}: {len(doll.spans)} lines, holes {holes}")
    smallest, held = piece(dolls)
    climbed = walk(held, smallest, dolls)
    inward = {doll.hash: n for n, doll in enumerate(dolls)}
    print(f"\nfound in {smallest.name}: {held.text}")
    for frame in sorted(climbed.passed, key=lambda frame: -inward[frame.hash]):
        print(f"  passed on by {frame.name}")
    for frame, holes in climbed.fits:
        print(f"  fits {frame.name}, hole {', '.join(holes)}")
    print(f"  complete: {'yes' if climbed.complete else 'no'}")


def gated(rung: str) -> None:
    dolls = unpacked(rung)
    smallest, held = piece(dolls)
    [(fitted, _)] = walk(held, smallest, dolls).fits
    path = HERE / f"{SETS[rung][1]}.json"
    rung_frame = load(path)
    runs = [load_records(str(p)) for p in sorted((HERE / "runs" / path.stem).glob("*.jsonl"))]
    asked = until_firm(rung_frame, None, Budget(calls=1), kept=runs)
    runs_made = f"{len(asked.runs)} run{'s' if len(asked.runs) != 1 else ''}"
    print(f"{path.stem}, {fitted.name} asked again: {asked.category}")
    shares = ", ".join(f"{share:.0%}" for share in asked.shares.values())
    state = "firm" if asked.firm else "not firm"
    print(f"  {state} after {runs_made}, read alike in {shares} of draws")
    recoil = gate(fitted, rung_frame, asked)
    print(f"  the gate: {recoil.gate}")
    largest = dolls[0]
    for decision in recoil.climbs:
        for frame, holes in walk(decision, rung_frame, [largest, rung_frame]).fits:
            print(f"  {decision.text!r} fits {frame.name}, hole {', '.join(holes)}")
            labels = list(frame.labels)
            observe = {**frame.raw["observe"], "labels": [labels[0], "boys", "mixed", *labels[1:]]}
            again = parse(successor(frame, holes[0], decision, observe=observe))
            changed = ", ".join(gate(frame, again).changed)
            print(f"  {frame.name} asked again: reframing, it changed {changed}")
            print(f"  {frame.name} as it was asked stands: {', '.join(labels)}")


if __name__ == "__main__":
    args = sys.argv[1:]
    rung = args[args.index("--rung") + 1] if "--rung" in args else "22"
    (gated if "--gate" in args else walked)(rung)
