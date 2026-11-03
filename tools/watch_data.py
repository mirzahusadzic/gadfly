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

import hashlib
import json
import re
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
# Each teaching page plays the frames it reads back, in its "Watch a run"
# section; a test holds this list to those sections.
FRAMES = [
    "upgrade",
    "07-sql-rule",
    "08-clock-rule",
    "09-sync-sms",
    "10a-incident-fast",
    "10b-incident-slow",
    "10c2-incident-both",
    "10d-incident-metrics",
    "10c-incident-both",
    "11-eu-clause",
    "12-payroll-access",
    "13-drop-table-section",
    "13b-drop-table-reads",
    "14-orders-latency",
    "15-invoice-export",
    "16-restore-inversion",
    "17-clock-asked",
    "18c-restore-cited",
    "18-notify-chain",
    "18b-access-logs",
    "18b2-access-logs-both",
    "20-incident-cause",
    "20b-incident-status",
    "22c-mirza-not-mine",
    "22-kiran-paper",
    "22b-kiran-paper-decoy",
]
# The doll stage stands over rung 22's frames: the order it plays them, with
# the climb of the paper's words and the gate between.
DOLLS = "dolls"
DOLL_ORDER = ["22c-mirza-not-mine", "climb", "22-kiran-paper", "22b-kiran-paper-decoy", "gate"]
# The reader each example names: Gemma through eGemma, unless its battery asks
# for another model by name.
NAMED = {"openrouter/meta/muse-spark-1.3-contributor": "Muse"}
# The model each example's records say served it, as the view says who read it
MODELS = {
    "google/gemma-4-26B-A4B-it-qat-q4_0-gguf": "Gemma 4 26B-A4B, instruction-tuned, through "
    "eGemma on one machine",
    "meta/muse-spark-1.3-contributor": "Muse Spark 1.3 Contributor, Meta's model, through "
    "unified-model-router",
}


def watched(stem: str) -> dict:
    path = ROOT / "examples" / f"{stem}.json"
    frame = situate(json.loads(path.read_text(encoding="utf-8")))
    trials = plan(frame)
    prompts = {(x["id"], t.id): prompt(frame, t, x) for x in frame.inputs for t in trials}
    digests = {key: digest(text) for key, text in prompts.items()}  # each prompt's, once
    # a crossing's reader reads what its maker wrote from the trial's body
    crossing = frame.battery["kind"] == "crossing"
    runs, served = [], set()
    for kept in runs_of(path):
        records = load_records(str(kept))
        served |= {_model(stem, r.get("served")) for r in records}
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
                        **(_made(r["raw"]) if crossing else {"raw": r["raw"]}),
                    }
                    for r in records
                ],
                "findings": [f.as_dict() for f in findings],
                "overall": overall(findings).category,
            }
        )
    line = frame.battery["reader"] if crossing else frame.battery
    reader = NAMED.get(line.get("model", ""), "Gemma")
    models = {model for sides in served for model in sides}
    if len(served) > 1 or not models <= MODELS.keys():
        raise SystemExit(f"{stem}: its runs name {sorted(served)}, not one model the view knows")
    data = {**watched_frame(frame, trials, prompts, f"examples/{stem}.json"), "reader": reader}
    for sides in served:  # none without runs
        # who read it in words, and the model's own id apart, as the records name it
        data["readBy"], data["model"] = MODELS[sides[-1]], sides[-1]
        if crossing:
            maker = frame.battery["maker"]
            data["maker"] = NAMED.get(maker.get("model", ""), maker["kind"])
            data["madeBy"], data["makerModel"] = MODELS[sides[0]], sides[0]
            data["makerInstruction"] = maker["instruction"]
    return {**data, "runs": runs}


def _model(stem: str, served: object) -> tuple[str, ...]:
    # the model a record says served it: "model", "model@revision", or the
    # unified battery's "model via endpoint"; a crossing's "made by M, read
    # by R" names the maker's, then the reader's
    if not isinstance(served, str) or not served:
        raise SystemExit(f"{stem}: a record does not say what served it")
    crossed = re.fullmatch(r"made by (.*), read by (.*)", served)
    sides = crossed.groups() if crossed else (served,)
    return tuple(side.partition(" via ")[0].partition("@")[0] for side in sides)


def _made(raw: str) -> dict:
    # what a crossing's maker wrote, from the record's raw answer, and the
    # reader's answer apart; "made" is null when the maker made nothing, and
    # "cut" says the record kept only the start of the artefact
    try:
        kept = json.loads(raw)
        made = kept["made"]
        text, sha = made["text"], made["sha256"]
    except (ValueError, TypeError, KeyError):
        return {"raw": raw, "made": None}
    whole = hashlib.sha256(text.encode("utf-8")).hexdigest() == sha
    return {"raw": kept.get("read", ""), "made": text, **({} if whole else {"cut": True})}


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


def dolls() -> dict:
    """The doll stage's data, read from the frames and kept runs with no
    model: each doll's own lines and the design they name, the frames that
    ask it, where the paper's words climb and fit (`midwife.recoil.walk`), and
    the gate Kiran's kept runs set, with what it does to the largest doll."""
    from examples.matryoshka import THEMES
    from midwife.frame import load, parse
    from midwife.recoil import found, gate, successor, until_firm, walk
    from midwife.types import Budget

    unpacked = [load(p) for p in sorted((ROOT / "examples/dolls").glob("*.json"))]
    asked = [stem for stem in DOLL_ORDER if stem not in ("climb", "gate")]
    frames = {stem: load(ROOT / "examples" / f"{stem}.json") for stem in asked}
    largest, smallest = unpacked[0], unpacked[-1]
    [paper] = [span for span in smallest.spans if span.kind.endswith("-paper")]
    walked = walk(found(smallest, paper.id), smallest, unpacked)
    [(fits, holes)] = walked.fits
    place = {frame.hash: n for n, frame in enumerate(unpacked)}
    # the dolls between where the words were found and where they fit, from the bottom up
    climbed = sorted(walked.passed, key=lambda frame: -place[frame.hash])
    passes = [f.name for f in climbed if place[f.hash] > place[fits.hash]]

    # the gate Kiran's plain frame sets, read from its kept runs as until_firm reads them
    plain = frames[asked[1]]
    runs = [load_records(str(kept)) for kept in runs_of(ROOT / "examples" / f"{asked[1]}.json")]
    recoil = gate(fits, plain, until_firm(plain, None, Budget(calls=1), kept=runs))
    [decision] = recoil.climbs
    [(above, room)] = walk(decision, plain, [largest, plain]).fits
    labels = ["girls", "boys", "mixed", "unknown"]
    again = parse(
        successor(above, room[0], decision, observe={**above.raw["observe"], "labels": labels})
    )
    reframed = gate(above, again)

    entries = []
    for n, doll in enumerate(unpacked):
        own = [{"id": s.id, "text": s.text, "kind": s.kind} for s in doll.spans]
        mine = [stem for stem in asked if frames[stem].name == doll.name]
        seen = {s["id"] for s in own}
        extra = []
        for stem in mine:
            for span in frames[stem].spans:
                if span.id not in seen:
                    seen.add(span.id)
                    extra.append({"id": span.id, "text": span.text, "kind": span.kind})
        design = {
            k: THEMES[n][k]
            for k in ("body", "scarf", "trim", "dots", "hair", "eyes", "hem", "motif", "flower")
        }
        entries.append(
            {"name": doll.name, "design": design, "lines": own, "extra": extra, "frames": mine}
        )
    decoy = next(span.text for span in frames[asked[2]].spans if span.kind == "decoy")
    return {
        "dolls": entries,
        "frames": {
            asked[0]: {
                "doll": smallest.name,
                "variant": None,
                "caption": f"{smallest.name} holds a paper whose words say {fits.name} is a boy, "
                f"and says the paper is not {smallest.name}'s. What is {smallest.name}?",
            },
            asked[1]: {
                "doll": fits.name,
                "variant": "With the paper",
                "caption": f"{fits.name} asked again, with the paper's words in the hole they "
                f"fit. What is {fits.name}?",
            },
            asked[2]: {
                "doll": fits.name,
                "variant": "With a decoy too",
                "caption": f'{fits.name} again, with the paper\'s words, and beside them "{decoy}"',
            },
        },
        "piece": {
            "from": smallest.name,
            "text": paper.text,
            "fits": fits.name,
            "hole": holes[0],
            "passes": passes,
        },
        "gate": {
            "frame": asked[1],
            "category": recoil.category,
            "climbs": decision.text,
            "fits": above.name,
            "changed": list(reframed.changed),
            "caption": f"{fits.name}'s run is {recoil.category}, so "
            f'"{decision.text}" climbs to {above.name}, whose hole waits for who is inside. '
            f"Asked again, {above.name} would need labels it lacks, so it asks another "
            f"question, and {above.name} as it was asked stands.",
        },
        "order": DOLL_ORDER,
    }


def encoded(stem: str) -> str:
    """The file's text, as it is kept."""
    if stem == DOLLS:
        return json.dumps(dolls(), ensure_ascii=False, separators=(",", ":")) + "\n"
    if stem in FEATURED:
        data = demo_watched(stem)
    elif stem == INDEX:
        data = titled()
    else:
        data = watched(stem)
        if not data["runs"]:  # the view plays a run; an example keeps three
            raise SystemExit(f"{stem}: no kept run to play")
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"


# every file the watch view reads
FILES = [*FRAMES, *FEATURED, INDEX, DOLLS]


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
