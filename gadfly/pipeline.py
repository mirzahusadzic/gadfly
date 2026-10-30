"""The pipeline: situate → plan → run → judge.

    frame = situate(json.load(file))
    trials = plan(frame)
    result = run(frame, battery, Budget(calls=60))
    findings = judge(frame, result.records)

`run` is the only stage that calls out. It never starts a call the budget
cannot cover, stops between calls when the caller says so, and hands each
record to `on_record` as soon as it exists, so the caller keeps what was spent
even if the run stops early.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace

from .frame import Frame, digest, parse
from .interventions import Trial, prompt
from .interventions import plan as plan_trials
from .types import Battery, Budget, Observation, Record
from .verdict import Finding
from .verdict import judge as judge_records

situate = parse
plan = plan_trials

# A raw answer is kept for audit, but only this much of it.
RAW_LIMIT = 2_000


@dataclass(frozen=True)
class RunResult:
    records: tuple[Record, ...]
    planned: int
    stopped: str | None  # None when every planned call was made


def calls_needed(frame: Frame) -> int:
    return len(frame.inputs) * len(plan(frame)) * frame.quorum


def run(
    frame: Frame,
    battery: Battery,
    budget: Budget,
    *,
    cancelled: Callable[[], bool] = lambda: False,
    on_record: Callable[[Record], None] = lambda record: None,
    only: Iterable[str] | None = None,
    kept: Iterable[Record | dict] = (),
) -> RunResult:
    """Every planned trial of every input, `quorum` times each, in a fixed
    order. `only` limits the run to some trial ids (a partial run); the
    verdict then reads what is there. `kept` finishes a run that stopped:
    the calls those records made are not made again (drop a record from it
    to make its call again), and the verdict reads the two runs together."""
    named = frame.battery["kind"]
    if battery.name != named:  # the hash names the battery: no other reads under it
        raise ValueError(f"this frame asks for the {named} battery, not {battery.name}")
    battery.check(frame)
    trials = plan(frame)
    if only is not None:
        wanted = set(only)
        unknown = wanted - {t.id for t in trials}
        if unknown:
            raise ValueError(f"the plan has no trial {sorted(unknown)}")
        trials = [t for t in trials if t.id in wanted]
    done = set()
    for record in kept:
        made = record.as_dict() if isinstance(record, Record) else record
        if made["frame"] != frame.hash:
            raise ValueError("a kept record belongs to another frame")
        done.add((made["input"], made["trial"], made["run"]))
    calls = [
        (x, trial, index)
        for x in frame.inputs
        for trial in trials
        for index in range(frame.quorum)
        if (x["id"], trial.id, index) not in done
    ]
    cap = budget.output_tokens_per_call
    planned = len(calls)
    if planned > budget.calls:
        return RunResult(
            (), planned, f"the plan needs {planned} calls; the budget allows {budget.calls}"
        )
    records: list[Record] = []
    spent = 0
    for x, trial, index in calls:
        if cancelled():
            return RunResult(tuple(records), planned, "cancelled")
        if budget.tokens is not None and spent + cap > budget.tokens:
            return RunResult(
                tuple(records), planned, f"the token budget ({budget.tokens}) is spent"
            )
        text = prompt(frame, trial, x)
        observation = _observe(battery, frame, text, cap)
        # What the battery reports, or the cap when it reports nothing.
        used = observation.usage.get("output_tokens")
        used = cap if not isinstance(used, int) or isinstance(used, bool) else used
        spent += used
        record = _record(frame, battery, x["id"], trial, index, text, observation)
        records.append(record)
        on_record(record)
        if used > cap:  # the budget holds only while every call keeps its cap
            return RunResult(
                tuple(records),
                planned,
                f"the battery reported {used} output tokens for a call capped at {cap}",
            )
    return RunResult(tuple(records), planned, None)


def judge(frame: Frame, records: Iterable[Record | dict]) -> list[Finding]:
    return judge_records(frame, [r.as_dict() if isinstance(r, Record) else r for r in records])


def _observe(battery: Battery, frame: Frame, text: str, cap: int) -> Observation:
    """A battery that fails gives an opening, never a guessed label; what it
    said and spent is kept beside the opening."""
    try:
        observation = battery.observe(frame, text, cap)
    except Exception as error:  # noqa: BLE001 — the failure is the observation
        return Observation(label=None, opening=f"battery failed: {type(error).__name__}")
    if not isinstance(observation, Observation):
        return Observation(label=None, opening="the battery returned no observation")
    if observation.label is not None and observation.label not in frame.labels:
        return replace(
            observation, label=None, opening="the battery returned no label of this frame"
        )
    return observation


def _record(
    frame: Frame, battery: Battery, x: str, trial: Trial, run_index: int, text: str, o: Observation
) -> Record:
    return Record(
        frame=frame.hash,
        input=x,
        trial=trial.id,
        run=run_index,
        body=trial.body_hash,
        prompt=digest(text),
        battery=battery.name,
        observation=o.label,
        opening=o.opening,
        raw=o.raw[:RAW_LIMIT],
        usage=dict(o.usage),
        served=o.served,
    )
