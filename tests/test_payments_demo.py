"""The payments demo's kept runs (examples/payments-demo/, copied from the
tendora repository): each reader's records name their frame, the readers
were asked the same prompts, every frame was predicted before its calls, and
the watch page's totals are what the records read."""

import json
import re
from collections import Counter
from pathlib import Path

import pytest

from midwife.cli import load_records
from midwife.frame import digest
from midwife.interventions import plan, prompt
from midwife.pipeline import judge, situate
from midwife.verdict import overall
from tools.watch_data import DEMO, READERS

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = sorted(
    path.stem.removeprefix("tendora-") for path in (DEMO / "frames").glob("tendora-*.json")
)


def read(question):
    for reader, folder, prefix in READERS:
        raw = json.loads((folder / "frames" / f"{prefix}{question}.json").read_text())
        records = load_records(str(folder / "runs" / f"{prefix}{question}.jsonl"))
        yield reader, raw, situate(raw), records


def test_the_demo_holds_31_questions_for_each_reader():
    assert len(QUESTIONS) == 31
    for _, folder, prefix in READERS:
        assert len(list((folder / "frames").glob(f"{prefix}*.json"))) == 31
        assert len(list((folder / "runs").glob(f"{prefix}*.jsonl"))) == 31


@pytest.mark.parametrize("question", QUESTIONS)
def test_each_reader_was_asked_the_same_prompts_by_its_own_frame(question):
    reads = list(read(question))
    _, first, frame, _ = reads[0]
    trials = plan(frame)
    asked = {(x["id"], t.id): digest(prompt(frame, t, x)) for x in frame.inputs for t in trials}
    for _, raw, mine, records in reads:
        assert records and all(r["frame"] == mine.hash for r in records)
        assert {(r["input"], r["trial"]): r["prompt"] for r in records} == asked
        # the readers' frames differ in their battery and answer words alone
        assert {k for k in raw if raw[k] != first[k]} <= {"name", "observe", "battery"}


def test_the_temperature_0_frames_differ_by_their_battery_alone():
    for path in sorted((DEMO / "gemma-temperature-0" / "frames").glob("*.json")):
        cold = json.loads(path.read_text())
        warm = json.loads((DEMO / "frames" / path.name).read_text())
        assert {k for k in cold if cold[k] != warm[k]} == {"battery"}
        assert cold["battery"] == {"kind": "egemma", "temperature": 0}


def test_every_frame_was_predicted_to_carry_before_its_calls():
    for path in (DEMO / "frames").glob("*.json"):
        told = json.loads((DEMO / "predictions" / path.name).read_text())
        assert told["frame"] == path.stem and told["verdict"] == "carried"


def test_the_watch_pages_totals_are_what_the_records_read():
    counted = {reader: Counter() for reader, _, _ in READERS}
    for question in QUESTIONS:
        for reader, _, frame, records in read(question):
            counted[reader][overall(judge(frame, records)).category] += 1
    page = (ROOT / "docs" / "examples" / "watch.md").read_text()
    row = r"^\| (Tendora's engine|Gemma 4 at temperature [0-9.]+) \| (.+) \|$"
    rows = re.findall(row, page, re.M)
    names = {"Tendora's engine": "Tendora", "Gemma 4 at temperature 0.7": "Gemma 4 at 0.7"}
    names["Gemma 4 at temperature 0"] = "Gemma 4 at 0"
    categories = ["carried", "unresolved", "coupled but misaligned", "cooled"]
    shown = {names[name]: [int(n) for n in cells.split(" | ")] for name, cells in rows}
    assert shown == {r: [counted[r][c] for c in categories] for r in counted}
    assert all(sum(n) == 31 for n in shown.values())
