"""Read a frame's kept runs back: the answers each trial got, and each run's
verdict. No model is called; the records are the ones kept under runs/.

    uv run python examples/read.py examples/07-sql-rule.json
    uv run python examples/read.py examples/07-sql-rule.json --verdict 1
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from gadfly.cli import load_records
from gadfly.pipeline import judge, situate
from gadfly.verdict import overall

HERE = Path(__file__).parent


def runs_of(path: Path) -> list[Path]:
    """The kept records files of a frame, in the order they were made."""
    return sorted((HERE / "runs" / path.stem).glob("*.jsonl"), key=lambda p: int(p.stem))


def answers(records: list[dict], x: str, trial: str) -> str:
    """How the calls of one trial answered, most common first."""
    counts = Counter(
        r["observation"] or "opening" for r in records if (r["input"], r["trial"]) == (x, trial)
    )
    return ", ".join(f"{label} {n}" for label, n in counts.most_common())


def reading(frame, run: Path) -> str:
    """One run's verdict in a line: its category, and each input's when there
    are several."""
    findings = judge(frame, load_records(str(run)))
    if len(findings) == 1:
        return findings[0].category
    each = ", ".join(f"{f.input} {f.category}" for f in findings)
    return f"{overall(findings).category} ({each})"


def table(path: Path) -> str:
    frame = situate(json.loads(path.read_text(encoding="utf-8")))
    kept = runs_of(path)
    records = [r for run in kept for r in load_records(str(run))]
    # the model and its revision, the revision cut to 8 characters
    served = sorted({r["served"][: r["served"].find("@") + 9] for r in records if r.get("served")})
    inputs = [x["id"] for x in frame.raw["inputs"]]
    trials = list(dict.fromkeys(r["trial"] for r in records))
    lines = [f"{frame.name}: {len(kept)} kept runs, read by {', '.join(served) or 'no record'}"]
    rows = [["trial", *inputs]] + [[t, *(answers(records, x, t) for x in inputs)] for t in trials]
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    lines += [
        "  ".join(cell.ljust(w) for cell, w in zip(row, widths, strict=True)).rstrip()
        for row in rows
    ]
    lines += [f"run {n}: {reading(frame, run)}" for n, run in enumerate(kept, 1)]
    return "\n".join(lines)


def verdict(path: Path, n: int) -> str:
    """One run's findings in full: levels, evidence and what stays open."""
    frame = situate(json.loads(path.read_text(encoding="utf-8")))
    lines = []
    for finding in judge(frame, load_records(str(runs_of(path)[n - 1]))):
        levels = ", ".join(f"{t} {v}" for t, v in finding.levels.items())
        lines += [f"{finding.input}: {finding.category}", f"  levels: {levels}"]
        lines += [f"  evidence: {line}" for line in finding.evidence]
        lines += [f"  open: {line}" for line in finding.obligations]
    return "\n".join(lines)


if __name__ == "__main__":
    frame_path = Path(sys.argv[1])
    if "--verdict" in sys.argv:
        print(verdict(frame_path, int(sys.argv[sys.argv.index("--verdict") + 1])))
    else:
        print(table(frame_path))
