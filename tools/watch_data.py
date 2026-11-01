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
from collections import Counter
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
    "17-clock-asked",
    "18c-restore-cited",
    "07-sql-rule",
    "09-sync-sms",
    "10c2-incident-both",
    "11-eu-clause",
    "12-payroll-access",
]


def watched(stem: str) -> dict:
    path = ROOT / "examples" / f"{stem}.json"
    frame = situate(json.loads(path.read_text(encoding="utf-8")))
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
    return {**watched_frame(frame, trials, prompts, f"examples/{stem}.json"), "runs": runs}


def watched_frame(frame, trials, prompts, file: str) -> dict:
    """What the watch view shows of a frame before any run: the evidence,
    the questions, each trial as planned, and the prompt of every input and
    trial."""
    texts = {span.id: span.text for span in frame.spans}  # each span's own words, by id
    return {
        "name": frame.name,
        "file": file,
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
    }


def _placed(frame, trial, key: str) -> str | None:
    return frame.interventions["placement"][key] if trial.kind == "placement" else None


# The payments demo: each question read once by each reader, its records kept
# in examples/payments-demo/ as the tendora repository published them
DEMO = ROOT / "examples" / "payments-demo"
READERS = [
    ("Tendora", DEMO, "tendora-"),
    ("Gemma 4 at 0.7", DEMO, "gemma-"),
    ("Gemma 4 at 0", DEMO / "gemma-temperature-0", "gemma-"),
]
# every demo question, played with its three readers in place of runs
QUESTIONS = sorted(
    path.stem.removeprefix("tendora-") for path in (DEMO / "frames").glob("tendora-*.json")
)
FEATURED = {f"payments-{question}": question for question in QUESTIONS}
INDEX = "payments-demo"  # the demo's questions, for the widget's picker
# answers that are not a decision: no answer, or one no saved check gives
NEUTRAL = ["open", "another answer"]


def reads(question: str) -> list[tuple[str, object, list[dict]]]:
    """Each reader's frame of one demo question and its records, every
    record checked against its frame's hash."""
    out = []
    for reader, folder, prefix in READERS:
        path = folder / "frames" / f"{prefix}{question}.json"
        frame = situate(json.loads(path.read_text(encoding="utf-8")))
        records = load_records(str(folder / "runs" / f"{prefix}{question}.jsonl"))
        if any(r["frame"] != frame.hash for r in records):
            raise SystemExit(f"{path.name}: a record names another frame")
        out.append((reader, frame, records))
    return out


def _answers(read: list[tuple[str, object, list[dict]]]) -> list[str]:
    # the decisions given, in the order the readers first gave them, then the
    # answers that decide nothing: each keeps one colour across the readers
    seen = [r["observation"] for _, _, records in read for r in records if r["observation"]]
    decided = [a for a in dict.fromkeys(seen) if a not in NEUTRAL]
    return decided + NEUTRAL


def demo_watched(name: str) -> dict:
    """One demo question for the watch view: the evidence and trials as the
    first reader's frame plans them, and each reader's run of it. The readers
    read the same prompts, each checked against the digest its records
    carry."""
    read = reads(FEATURED[name])
    _, frame, _ = read[0]
    trials = plan(frame)
    prompts = {(x["id"], t.id): prompt(frame, t, x) for x in frame.inputs for t in trials}
    digests = {key: digest(text) for key, text in prompts.items()}
    source = (DEMO / "frames" / f"tendora-{FEATURED[name]}.json").relative_to(ROOT)
    data = watched_frame(frame, trials, prompts, str(source))
    data["labels"] = _answers(read)
    data["neutral"] = NEUTRAL
    data["runs"] = []
    for reader, mine, records in read:
        for r in records:
            if digests.get((r["input"], r["trial"])) != r["prompt"]:
                raise SystemExit(f"{reader}: {r['input']}/{r['trial']} was asked another prompt")
        findings = judge(mine, records)
        engine = mine.battery["kind"] == "tendora"
        data["runs"].append(
            {
                "reader": reader,
                # what the reader was told to answer: Gemma reads the
                # frame's instruction, the engine answers by its own rules
                "instruction": None if engine else mine.instruction,
                "calls": [
                    {
                        "input": r["input"],
                        "trial": r["trial"],
                        "n": r["run"],
                        "answer": r["observation"],
                        # the engine's answer line, never the reply after it
                        "raw": r["raw"].split("\n", 1)[0] if engine else r["raw"],
                    }
                    for r in records
                ],
                "findings": [f.as_dict() for f in findings],
                "overall": overall(findings).category,
            }
        )
    return data


def titled() -> dict:
    """The demo's questions as the widget's picker lists them, in one group:
    each question with its case, and, for a question asked twice, the
    statements it was asked over."""
    rows = []
    for question in QUESTIONS:
        _, frame, _ = reads(question)[0]
        [x] = frame.inputs
        lines = x["text"].split("\n")
        case = lines[0].removeprefix("Case: ") if len(lines) > 1 else None
        kinds = sorted({span.kind for span in frame.spans})
        rows.append([question, lines[-1].removeprefix("Question: "), case, len(frame.spans), kinds])
    asked = Counter((q, case) for _, q, case, _, _ in rows)
    corpus = max(n for *_, n, _ in rows)
    listed = []
    for question, text, case, n, kinds in rows:
        said = [case] if case else []
        if asked[text, case] > 1:
            if n == corpus:
                said.append(f"all {n} statements")
            elif len(kinds) == 1:
                said.append(f"the {kinds[0].replace('-', ' ')}'s {n} statements")
            else:
                said.append(f"{n} statements")
        title = f"{text} ({'; '.join(said)})" if said else text
        listed.append({"stem": f"payments-{question}", "title": title})
    listed.sort(key=lambda q: q["title"])
    return {"group": "Payments demo, Tendora and Gemma", "examples": listed}


def encoded(stem: str) -> str:
    """The file's text, as it is kept."""
    if stem in FEATURED:
        data = demo_watched(stem)
    elif stem == INDEX:
        data = titled()
    else:
        data = watched(stem)
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"


# every file the watch view reads
FILES = [*FRAMES, *FEATURED, INDEX]


def main(write: bool) -> int:
    differ = 0
    for stem in FILES:
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
