"""Read a frame's kept runs back: the answers each trial got, and each run's
verdict. No model is called; the records are the ones kept under runs/.

    uv run python examples/read.py examples/07-sql-rule.json
    uv run python examples/read.py examples/07-sql-rule.json --verdict 1
    uv run python examples/read.py examples/07-sql-rule.json --frame
    uv run python examples/read.py examples/12-payroll-access.json --verdict 1 --input sam
    uv run python examples/read.py examples/20-incident-cause.json --made 1
"""

from __future__ import annotations

import json
import re
import sys
import textwrap
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


def reader(served: str) -> str:
    """What served a call, in short: the model and its revision cut to 8
    characters, without the provider or endpoint the router reports."""
    return re.sub(r"@(\w{8})\w*", r"@\1", re.sub(r" via [^,]*", "", served))


def table(path: Path) -> str:
    frame = situate(json.loads(path.read_text(encoding="utf-8")))
    kept = runs_of(path)
    records = [r for run in kept for r in load_records(str(run))]
    served = sorted({reader(r["served"]) for r in records if r.get("served")})
    crossed = [re.fullmatch(r"made by (.*), read by (.*)", s) for s in served]
    if served and all(crossed):  # a crossing: who wrote what the reader read
        made_by = sorted({m[1] for m in crossed})
        read_by = sorted({m[2] for m in crossed})
        who = (
            f"made and read by {', '.join(made_by)}"
            if made_by == read_by
            else f"made by {', '.join(made_by)}, read by {', '.join(read_by)}"
        )
    else:
        who = f"read by {', '.join(served) or 'no record'}"
    inputs = [x["id"] for x in frame.raw["inputs"]]
    asked = {r["trial"] for r in records}  # in the plan's order, however the calls ended
    trials = [t.id for t in plan(frame) if t.id in asked]
    lines = [f"{frame.name}: {len(kept)} kept runs, {who}"]
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
    if trial.kind == "input-inversion":
        return "inverts the input's " + ", ".join(f"{a} -> {b}" for a, b in trial.renamed)
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
    maker = frame.battery.get("maker")
    if isinstance(maker, dict) and maker.get("instruction"):  # a crossing: what the reader reads
        lines.append(f"made into: {maker['instruction']}")
    lines += [f"labels: {', '.join(frame.labels)}", "trials:"]
    lines += [f"  {t.id.ljust(12)}  {cut(frame, t)}" for t in trials]
    allowed = "; ".join(
        f"{trial} -> {', '.join(v) if isinstance(v, list) else v}"
        for trial, v in frame.allowed.items()
    )
    lines.append(f"allowed: {allowed}")
    # how the answers are read, when not as every step before rung 16 reads them
    if frame.raw.get("carriage") == "listed":
        lines.append("carriage: listed, so a category is named with its open checks beside it")
    if frame.raw["standing"].get("stable"):
        lines.append("stable: the baseline and the repeat must not split")
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


def made(path: Path, n: int) -> str:
    """What a crossing's maker wrote for each trial in run N, from the first
    call of each, and what the reader answered from it."""
    frame = situate(json.loads(path.read_text(encoding="utf-8")))
    if frame.battery["kind"] != "crossing":
        raise SystemExit(f"{path.name} makes nothing for its reader to read")
    first = {}
    for record in load_records(str(runs_of(path)[n - 1])):
        if record["run"] == 0:
            first.setdefault((record["input"], record["trial"]), record)
    lines = []
    for x in frame.inputs:
        for trial in plan(frame):
            record = first.get((x["id"], trial.id))
            if record is None:
                continue
            name = trial.id if len(frame.inputs) == 1 else f"{x['id']}/{trial.id}"
            lines.append(f"{name}, read as {record['observation'] or 'an opening'}")
            text = json.loads(record["raw"])["made"]["text"]
            lines += textwrap.wrap(
                text, 72, initial_indent="  ", subsequent_indent="  ", break_on_hyphens=False
            )
    return "\n".join(lines)


if __name__ == "__main__":
    frame_path = Path(sys.argv[1])
    if "--frame" in sys.argv:
        print(described(frame_path))
    elif "--made" in sys.argv:
        print(made(frame_path, int(sys.argv[sys.argv.index("--made") + 1])))
    elif "--verdict" in sys.argv:
        only = sys.argv[sys.argv.index("--input") + 1] if "--input" in sys.argv else None
        print(verdict(frame_path, int(sys.argv[sys.argv.index("--verdict") + 1]), only))
    else:
        print(table(frame_path))
