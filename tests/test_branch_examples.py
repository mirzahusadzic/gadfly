"""The branch battery's examples (examples/branch/): three public examples said
as claims, read in one turn and twice through the branch. They are kept runs,
so they never change; these tests hold them to their frames, to the
predictions hashed before them, and to what the README and the batteries page
say of them."""

import hashlib
import json
import re
from pathlib import Path

import pytest

from midwife.cli import load_records
from midwife.pipeline import calls_needed, judge, overall, situate, steps

ROOT = Path(__file__).parent.parent
HERE = ROOT / "examples" / "branch"
READ = {"19": "carried", "22": "carried", "22c": "cooled"}
RUNS = {"one-turn": ("one-turn",), "branch": ("branch-a", "branch-b")}


def frame_of(example, side):
    return situate(json.loads((HERE / f"{example}-{side}.json").read_text(encoding="utf-8")))


def records_of(example, run):
    return load_records(str(HERE / "runs" / f"{example}-{run}.jsonl"))


def seconds_of(example, run):
    said = (HERE / "runs" / f"{example}-{run}.time").read_text(encoding="utf-8")
    return int(re.search(r"exit 0, (\d+) s", said).group(1))


def test_the_predictions_and_frames_are_as_they_were_hashed_before_the_runs():
    for line in (HERE / "PREDICTIONS.sha256").read_text(encoding="utf-8").splitlines():
        sha, name = line.split()
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == sha, name


@pytest.mark.parametrize("example", sorted(READ))
@pytest.mark.parametrize("side", sorted(RUNS))
def test_every_run_is_its_frames_whole_plan_and_reads_as_reported(example, side):
    frame = frame_of(example, side)
    for run in RUNS[side]:
        records = records_of(example, run)
        assert len(records) == calls_needed(frame)
        assert {r["battery"] for r in records} == {frame.battery["kind"]}
        assert overall(judge(frame, records)).category == READ[example]


@pytest.mark.parametrize("example", sorted(READ))
def test_each_branch_run_made_its_own_step_and_read_every_trial_through_one(example):
    made = []
    for run in RUNS["branch"]:
        read = steps(records_of(example, run))
        assert all(entry["remade"] == [] for entry in read.values())
        made.append({sha for entry in read.values() for sha in entry["steps"]})
    assert made[0].isdisjoint(made[1])  # remade each run, as the method asks
    for run in RUNS["branch"]:
        assert all("thinking off" in r["served"] for r in records_of(example, run))


def test_the_readme_and_the_batteries_page_quote_these_runs():
    readme = (HERE / "README.md").read_text(encoding="utf-8")
    page = (ROOT / "docs" / "batteries.md").read_text(encoding="utf-8")
    for example in READ:
        one = records_of(example, "one-turn")
        branch = [records_of(example, run) for run in RUNS["branch"]]
        out = [sum(r["usage"]["output_tokens"] for r in records) for records in branch]
        own = sum(r["usage"]["output_tokens"] for r in one)
        times = [seconds_of(example, run) for run in RUNS["branch"]]
        for run, tokens, seconds in zip("AB", out, times, strict=True):
            row = f"| {example} | branch, run {run} | {READ[example]} | {tokens:,} | {seconds} s |"
            assert row in readme
        assert f"| {example} | one turn | {READ[example]} | {own:,} | " in readme
        mean = int(sum(out) / len(out) + 0.5)
        fewer = round(100 * (1 - mean / own))
        assert f"{own:,} → **{mean:,}, {fewer}% fewer**" in page
        inputs = [r["usage"]["input_tokens"] for records in branch for r in records]
        alone = [r["usage"]["input_tokens"] for r in one]
        quoted = (
            f"{int(sum(alone) / len(alone) + 0.5)} → **{int(sum(inputs) / len(inputs) + 0.5):,}**"
        )
        assert quoted in page
        took = [seconds_of(example, run) for run in RUNS["branch"]]
        alone_took, mean_took = seconds_of(example, "one-turn"), sum(took) / len(took)
        said = f"{alone_took} s → **{int(mean_took + 0.5)} s"
        assert said in page
        if mean_took < alone_took:
            assert f"{said}, {round(100 * (1 - mean_took / alone_took))}% less**" in page
