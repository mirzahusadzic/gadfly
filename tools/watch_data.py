"""The kept runs the docs play, as the data the watch view draws.

For each frame named below, one JSON file under docs/public/assets/watch/: the
evidence, the questions, each trial as Gadfly plans it, the exact prompt of
every input and trial, and every kept run's calls and verdict, in the words
`gadfly report` uses. Each prompt is checked against the digest its records
carry, so the page shows what the reader was asked, not a reconstruction.

    uv run python -m tools.watch_data          # report each file that differs
    uv run python -m tools.watch_data --write  # rewrite them from the kept runs
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from examples.read import cut, runs_of
from midwife.cli import load_records
from midwife.frame import digest
from midwife.interventions import plan, prompt
from midwife.pipeline import judge, situate
from midwife.verdict import overall

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/public/assets/watch"
FRAMES = [
    "upgrade",
    "16-restore-inversion",
    "07-sql-rule",
    "09-sync-sms",
    "10c2-incident-both",
    "11-eu-clause",
    "12-payroll-access",
]


def watched(stem: str) -> dict:
    path = ROOT / "examples" / f"{stem}.json"
    frame = situate(json.loads(path.read_text(encoding="utf-8")))
    texts = {span.id: span.text for span in frame.spans}  # each span's own words, by id
    trials = plan(frame)
    prompts = {(x["id"], t.id): prompt(frame, t, x) for x in frame.inputs for t in trials}
    digests = {key: digest(text) for key, text in prompts.items()}  # each prompt's, once
    runs = []
    for kept in runs_of(path):
        records = load_records(str(kept))
        for r in records:
            if digests[r["input"], r["trial"]] != r["prompt"]:
                raise SystemExit(f"{kept}: {r['input']}/{r['trial']} was asked another prompt")
        findings = judge(frame, records)
        runs.append(
            {
                "calls": [
                    {
                        "input": r["input"],
                        "trial": r["trial"],
                        "n": r["run"],
                        "answer": r["observation"],
                        "raw": r["raw"],
                    }
                    for r in records
                ],
                "findings": [f.as_dict() for f in findings],
                "overall": overall(findings).category,
            }
        )
    return {
        "name": frame.name,
        "file": f"examples/{stem}.json",
        "relation": frame.raw["relation"],
        "grain": frame.raw["grain"],
        "instruction": frame.instruction,
        "labels": list(frame.labels),
        "quorum": frame.quorum,
        "agree": frame.agree,
        "allowed": frame.allowed,
        "spans": [
            {"id": s.id, "kind": s.kind, "text": s.text, "anchor": s.id in frame.anchors}
            for s in frame.spans
        ],
        "inputs": [{"id": x["id"], "text": x["text"]} for x in frame.inputs],
        "trials": [
            {
                "id": t.id,
                "kind": t.kind,
                "does": cut(frame, t),
                "removed": list(t.removed),
                "order": [s.id for s in t.spans],
                "renamed": [s.id for s in t.spans if t.renamed and s.text != texts[s.id]],
                "renames": [list(pair) for pair in t.renamed],
                "moved": _placed(frame, t, "span"),
                "after": _placed(frame, t, "after"),
            }
            for t in trials
        ],
        "prompts": {f"{x}/{t}": text for (x, t), text in prompts.items()},
        "runs": runs,
    }


def _placed(frame, trial, key: str) -> str | None:
    return frame.interventions["placement"][key] if trial.kind == "placement" else None


def encoded(stem: str) -> str:
    """The file's text, as it is kept."""
    return json.dumps(watched(stem), ensure_ascii=False, separators=(",", ":")) + "\n"


def main(write: bool) -> int:
    differ = 0
    for stem in FRAMES:
        target = OUT / f"{stem}.json"
        data = encoded(stem)
        if not target.exists() or target.read_text(encoding="utf-8") != data:
            differ += 1
            print(f"{target.relative_to(ROOT)} differs")
            if write:
                OUT.mkdir(parents=True, exist_ok=True)
                target.write_text(data, encoding="utf-8")
    print(f"{differ} file(s) {'rewritten' if write else 'differ'}")
    return 0 if write or not differ else 1


if __name__ == "__main__":
    raise SystemExit(main("--write" in sys.argv))
