"""Read a frame's kept runs back: the answers each trial got, and each run's
verdict. No model is called; the records are the ones kept under runs/.

    uv run python examples/read.py examples/07-sql-rule.json
    uv run python examples/read.py examples/07-sql-rule.json --verdict 1
    uv run python examples/read.py examples/07-sql-rule.json --frame
    uv run python examples/read.py examples/12-payroll-access.json --verdict 1 --input sam
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from midwife.cli import load_records
from midwife.pipeline import calls_needed, judge, plan, situate
from midwife.verdict import overall

HERE = Path(__file__).parent


def runs_of(path: Path) -> list[Path]:
    """The kept records files of a frame, in the order they were made."""
    return sorted((HERE / "runs" / path.stem).glob("*.jsonl"), key=lambda p: int(p.stem))


def answers(records: list[dict], x: str, trial: str) -> str:
    """How the calls of one trial answered, most common first."""
    return said(
        Counter(
            r["observation"] or "opening" for r in records if (r["input"], r["trial"]) == (x, trial)
        )
    )


def said(counts: Counter) -> str:
    """The answers counted, most common first."""
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
    cells: dict[tuple[str, str], Counter] = defaultdict(Counter)  # one pass over the records
    for r in records:
        cells[r["input"], r["trial"]][r["observation"] or "opening"] += 1
    rows = [["trial", *inputs]] + [[t, *(said(cells[x, t]) for x in inputs)] for t in trials]
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    lines += [
        "  ".join(cell.ljust(w) for cell, w in zip(row, widths, strict=True)).rstrip()
        for row in rows
    ]
    lines += [f"run {n}: {reading(frame, run)}" for n, run in enumerate(kept, 1)]
    return "\n".join(lines)


def cut(frame, trial) -> str:
    """What one trial does to the evidence, in a few words."""
    if trial.kind == "inversion":
        return "inverts " + ", ".join(f"{a} -> {b}" for a, b in trial.renamed)
    if trial.renamed:
        return "renames " + ", ".join(f"{a} -> {b}" for a, b in trial.renamed)
    if trial.kind == "placement":
        move = frame.interventions["placement"]
        return f"moves {move['span']} after {move['after']}"
    if trial.removed:
        return "cuts " + ", ".join(trial.removed) if trial.spans else "cuts every span"
    return "asks it again" if trial.kind == "repeat" else "asks the evidence as it is"


def described(path: Path) -> str:
    """The frame as Gadfly plans it: the evidence, the anchors, the question,
    and what each trial cuts, renames, inverts or moves."""
    frame = situate(json.loads(path.read_text(encoding="utf-8")))
    trials = plan(frame)
    lines = [
        f"{frame.name}: {len(frame.inputs)} input{'s' * (len(frame.inputs) > 1)}"
        f" x {len(trials)} trials x {frame.quorum} calls = {calls_needed(frame)} calls,"
        f" {frame.agree} of {frame.quorum} to agree",
        f"relation: {frame.raw['relation']}",
        f"grain: {frame.raw['grain']}",
        "evidence, the anchors marked *:",
    ]
    width = max(len(span.id) for span in frame.spans)
    kinds = max(len(span.kind) for span in frame.spans)
    lines += [
        f"  {'*' if span.id in frame.anchors else ' '} {span.id.ljust(width)}"
        f"  {span.kind.ljust(kinds)}  {span.text}"
        for span in frame.spans
    ]
    ids = max(len(x["id"]) for x in frame.inputs)
    # an input of several lines, such as a case and its question, keeps its column
    gap = "\n" + " " * (ids + 4)
    lines += ["asked:"] + [
        f"  {x['id'].ljust(ids)}  {x['text'].replace(chr(10), gap)}" for x in frame.inputs
    ]
    lines += [f"labels: {', '.join(frame.labels)}", "trials:"]
    lines += [f"  {t.id.ljust(12)}  {cut(frame, t)}" for t in trials]
    allowed = "; ".join(
        f"{trial} -> {', '.join(v) if isinstance(v, list) else v}"
        for trial, v in frame.allowed.items()
    )
    lines.append(f"allowed: {allowed}")
    return "\n".join(lines)


def verdict(path: Path, n: int, only: str | None = None) -> str:
    """One run's findings in full: levels, evidence and what stays open; one
    input's alone when `only` names it."""
    frame = situate(json.loads(path.read_text(encoding="utf-8")))
    lines = []
    for finding in judge(frame, load_records(str(runs_of(path)[n - 1]))):
        if only and finding.input != only:
            continue
        levels = ", ".join(f"{t} {v}" for t, v in finding.levels.items())
        lines += [f"{finding.input}: {finding.category}", f"  levels: {levels}"]
        lines += [f"  evidence: {line}" for line in finding.evidence]
        lines += [f"  open: {line}" for line in finding.obligations]
    if only and not lines:
        raise SystemExit(f"{path.name} has no input {only!r}")
    return "\n".join(lines)


if __name__ == "__main__":
    frame_path = Path(sys.argv[1])
    if "--frame" in sys.argv:
        print(described(frame_path))
    elif "--verdict" in sys.argv:
        only = sys.argv[sys.argv.index("--input") + 1] if "--input" in sys.argv else None
        print(verdict(frame_path, int(sys.argv[sys.argv.index("--verdict") + 1]), only))
    else:
        print(table(frame_path))
