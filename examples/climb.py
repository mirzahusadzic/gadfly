"""Run an example frame against eGemma, keep every run, and tally.

    EGEMMA_API_KEY=... uv run python examples/climb.py rung N [RUNS]
    EGEMMA_API_KEY=... uv run python examples/climb.py FRAME.json [RUNS]
    uv run python examples/climb.py FRAME.json --firm module:Class

`rung N` (1-6) builds rungN.json from upgrade.json: rung 1 declares only the
ablation, and each later rung adds one trial. Each run is a new records file
under examples/runs/<frame>/; a kept file is never written over. With
`--firm`, the frame is asked one light run at a time through the battery
named, until its verdict is firm (`midwife.recoil.until_firm`), and the runs
already kept count as runs made.
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

from midwife.cli import load_battery, load_records
from midwife.cli import main as gadfly
from midwife.pipeline import calls_needed, judge, situate
from midwife.verdict import overall

HERE = Path(__file__).parent
STEPS = ["ablation", "repeat", "sham", "presentation", "bypass", "control"]


def rung_frame(rung: int) -> Path:
    full = json.loads((HERE / "upgrade.json").read_text(encoding="utf-8"))
    keep = STEPS[:rung]
    full["interventions"] = {k: v for k, v in full["interventions"].items() if k in keep}
    full["name"] = f"quill-upgrade-rung-{rung}"
    path = HERE / f"rung{rung}.json"
    text = json.dumps(full, indent=2, ensure_ascii=False) + "\n"
    if path.exists():  # a frame with kept runs is never changed: a new idea is a new frame
        if path.read_text(encoding="utf-8") != text:
            raise SystemExit(f"{path.name} exists and differs: a kept frame is never changed")
        return path
    path.write_text(text, encoding="utf-8")
    return path


def climb(path: Path, runs: int) -> None:
    frame = situate(json.loads(path.read_text(encoding="utf-8")))
    out_dir = HERE / "runs" / path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    tally: dict[str, Counter] = {}
    multi = len(frame.raw["inputs"]) > 1
    for _ in range(runs):
        began = time.monotonic()
        n = len(list(out_dir.glob("*.jsonl"))) + 1
        out = out_dir / f"{n}.jsonl"
        argv = ["run", str(path), "--battery", "midwife.batteries.egemma:EGemma"]
        if gadfly([*argv, "--calls", str(calls_needed(frame)), "--out", str(out)]) != 0:
            raise SystemExit(f"run {n} failed")
        records = load_records(str(out))
        for r in records:
            key = f"{r['input']}/{r['trial']}" if multi else r["trial"]
            tally.setdefault(key, Counter())[r["observation"] or "opening"] += 1
        findings = judge(frame, records)
        took = f"({time.monotonic() - began:.0f} s)"
        if multi:
            print(f"run {n}: overall {overall(findings).category} {took}")
        for finding in findings:
            levels = " ".join(f"{t}={v}" for t, v in finding.levels.items())
            head = f"  {finding.input}:" if multi else f"run {n}:"
            if not multi:
                head += f" {took}"
            print(f"{head} {finding.category} | {levels}")
            for line in finding.evidence:
                print(f"    evidence: {line}")
            for line in finding.obligations:
                print(f"    open: {line}")
    print("calls per trial, all runs of this frame so far:" if runs else "")
    for trial, counts in tally.items():
        print(f"    {trial:24} {dict(counts.most_common())}")


def firm(path: Path, battery: str) -> None:
    from midwife.recoil import MOST, until_firm
    from midwife.types import Budget

    frame = situate(json.loads(path.read_text(encoding="utf-8")))
    out_dir = HERE / "runs" / path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    made = sorted(out_dir.glob("*.jsonl"), key=lambda p: int(p.stem))
    kept = [load_records(str(p)) for p in made]
    each = calls_needed(frame)
    writing = {"file": None, "count": 0, "n": len(kept)}

    def keep(record) -> None:  # each run a file of its own, each record as it exists
        if writing["count"] % each == 0:
            if writing["file"]:
                writing["file"].close()
            writing["n"] += 1
            writing["file"] = (out_dir / f"{writing['n']}.jsonl").open("x", encoding="utf-8")
        writing["file"].write(json.dumps(record.as_dict(), ensure_ascii=False) + "\n")
        writing["file"].flush()
        writing["count"] += 1

    began = time.monotonic()
    try:
        asked = until_firm(
            frame, load_battery(battery), Budget(MOST * each, 8000), kept=kept, on_record=keep
        )
    finally:
        if writing["file"]:
            writing["file"].close()
    for n, records in enumerate(asked.runs, 1):
        for finding in judge(frame, list(records)):
            levels = " ".join(f"{t}={v}" for t, v in finding.levels.items())
            print(f"run {n}: {finding.category} | {levels}")
    state = "firm" if asked.firm else f"not firm ({asked.stopped or 'at the most runs'})"
    took = f"{time.monotonic() - began:.0f} s"
    print(f"{state}: {asked.category}, shares {asked.shares}, {asked.made} calls made ({took})")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--firm" in args:
        firm(Path(args[0]), args[args.index("--firm") + 1])
        raise SystemExit(0)
    if args[0] == "rung":
        path, rest = rung_frame(int(args[1])), args[2:]
    else:
        path, rest = Path(args[0]), args[1:]
    climb(path, int(rest[0]) if rest else 5)
