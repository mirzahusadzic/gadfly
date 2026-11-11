"""The pipeline: situate → plan → run → judge (→ overall, over the inputs).

    frame = situate(json.load(file))
    trials = plan(frame)
    result = run(frame, battery, Budget(calls=60))
    findings = judge(frame, result.records)
    verdict = overall(findings)

`overall` names one category over all the inputs. `run` is the only stage
that calls out. It never starts a call the budget cannot cover, stops
between calls when the caller says so, and hands each record to `on_record`
as soon as it exists, so the caller keeps what was spent even if the run
stops early. Asked to, it skips the calls a settled trial no longer needs,
stops an input once it reads unresolved whatever its other trials give, and
makes several calls at once for a battery that takes them.
"""

from __future__ import annotations

import itertools
import re
import signal
import threading
import warnings
from collections import Counter, defaultdict, deque
from collections.abc import Callable, Iterable, Mapping
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, replace
from typing import Any

from .errors import (
    BatteryError,
    GadflyError,
    OpeningWarning,
    RecordsError,
    StoppedWarning,
    StopRun,
    UsageError,
    quoted,
)
from .frame import Frame, digest, parse
from .interventions import Trial, prompt, trial_ids
from .interventions import plan as plan_trials
from .types import Battery, Budget, Observation, Record
from .verdict import (
    CARRIED,
    COOLED,
    Finding,
    _check_shape,
    _fixed,
    check_records,
    out_of_reach,
    unneeded,
)
from .verdict import judge as judge_records
from .verdict import overall as overall_of
from .withhold import Withhold, refuse_withheld, trains

situate = parse
plan = plan_trials
overall = overall_of

# A raw answer is kept for audit, but only this much of it.
RAW_LIMIT = 2_000


# Asked to stop an input once it reads unresolved, a run asks these first,
# as they most often fix a verdict, then the rest in the plan's order.
DECISIVE = ("baseline", "repeat", "ablation", "control", "presentation", "placement")


# Asked to stop once a category is out of reach, a run asks these first, as
# they most often rule it out, then the rest in the plan's order; with calls
# at once, the rest wait until these have answered.
RULING = {
    CARRIED: ("baseline", "repeat", "inversion", "input-inversion"),
    COOLED: ("baseline", "repeat", "ablation"),
}


@dataclass(frozen=True)
class RunResult:
    """What a run made: its records, the calls it planned, why it stopped
    early (None when it reached the end of its plan), and how many planned
    calls it skipped because their trial had settled, their input could read
    nothing but unresolved, or the category it was asked for was out of
    reach."""

    records: tuple[Record, ...]
    planned: int
    stopped: str | None  # None when it reached the end of its plan
    settled: int = 0  # calls not made: their trial's level could no longer change
    unasked: int = 0  # calls not made: their input reads unresolved whatever they give
    short: int = 0  # calls not made: no answer left could make the frame read `short_of`


def calls_needed(frame: Frame) -> int:
    """The calls a whole run makes: every trial of every input, `quorum`
    times each. A budget of this many calls covers it."""
    return len(frame.inputs) * len(trial_ids(frame)) * frame.quorum


def summed_usage(records: Iterable[Record | dict[str, Any]]) -> dict[str, int]:
    """Each whole count the records' calls reported, summed by name, as
    `run --json`, `firm --json` and `report --json` give it under `usage`; a
    count no call reported is absent, never a zero."""
    summed: dict[str, int] = {}
    for record in records:
        for name, count in _counts(record).items():
            summed[name] = summed.get(name, 0) + count
    return summed


def unthought(records: Iterable[Record | dict[str, Any]]) -> dict[str, Any]:
    """The calls whose provider reported no reasoning: of the `calls` that
    reported `reasoning_tokens`, how many reported 0 (`unthought`), and
    those by trial, as `run --json`, `firm --json` and `report --json` give
    it. Read it against the reasoning the frame asked for; nothing is resent
    and no answer is set aside, so a reflex answer counts as any other."""
    calls, none, trials = 0, 0, {}
    for record in records:
        counts = _counts(record)
        if "reasoning_tokens" not in counts:
            continue
        calls += 1
        if counts["reasoning_tokens"] == 0:
            none += 1
            trial = record.get("trial") if isinstance(record, dict) else record.trial
            trials[str(trial)] = trials.get(str(trial), 0) + 1
    return {"calls": calls, "unthought": none, "trials": trials}


def _counts(record: Record | dict[str, Any]) -> dict[str, int]:
    # a record's whole usage counts by name, whatever else it holds
    usage = record.get("usage") if isinstance(record, dict) else record.usage
    return {
        name: count
        for name, count in (usage if isinstance(usage, dict) else {}).items()
        if isinstance(count, int) and not isinstance(count, bool)
    }


def _check_parallel(parallel: int, battery: Battery | None) -> None:
    """Refuse calls at once that are not a whole number from 1, or that a
    battery does not take (one that says `concurrent = True` does)."""
    if not isinstance(parallel, int) or isinstance(parallel, bool) or parallel < 1:
        raise UsageError("parallel is a whole number of calls, at least 1")
    if parallel > 1 and battery is not None and getattr(battery, "concurrent", False) is not True:
        raise UsageError(f"battery {battery.name!r} does not take calls at once")


def run(
    frame: Frame,
    battery: Battery,
    budget: Budget,
    *,
    cancelled: Callable[[], bool] = lambda: False,
    on_record: Callable[[Record], None] = lambda record: None,
    only: Iterable[str] | None = None,
    kept: Iterable[Record | dict] = (),
    settle: bool = False,
    stop_unresolved: bool = False,
    parallel: int = 1,
    withhold: Withhold | None = None,
    short_of: str | None = None,
) -> RunResult:
    """Every planned trial of every input, `quorum` times each, in a fixed
    order. `only` limits the run to some trial ids (a partial run); the
    verdict then reads what is there. `kept` finishes a run that stopped:
    the calls those records made are not made again (drop a record from it
    to make its call again), and the verdict reads the two runs together.

    `settle` makes no more calls for a trial whose level can no longer
    change (`settled`); the verdict reads it as it would read every call.
    With `parallel`, a trial has out only the calls that could fix its level.
    Under `standing.stable` the baseline and repeat always run whole, as
    their split is read across all their calls. `stop_unresolved` asks the
    `DECISIVE` trials first and asks an input nothing more once every answer
    its other trials could give reads unresolved (`unneeded`); the verdict
    reads the category a whole run would, and names the trials not asked.
    `short_of`, carried or cooled, is for a caller who needs only to know
    whether the frame reads that category: the trials that most often rule
    it out are asked first (`RULING`), and once no answer left could make an
    input read it (`out_of_reach`), and so the frame, no further call starts.
    With `parallel`, the other trials' calls wait until those first trials
    have answered, so calls at once spare what one at a time spares.
    Such a run is cut short (`short` counts the calls it left): it says the
    frame does not read that category, and not which other it reads.
    `parallel` makes up to that many calls at once, for a battery that says
    it takes them (a `concurrent` attribute that is true); records are
    handed on as each call ends, and a call already started is always kept:
    a first Ctrl-C starts no more calls, keeps those already out, then goes
    on as KeyboardInterrupt, and a second stops at once. `withhold` refuses,
    before any call, a frame whose prompts hold text the set withholds
    (`midwife.withhold`), its `training` part only when the battery says its
    calls may train."""
    return _run(
        frame,
        battery,
        budget,
        cancelled=cancelled,
        on_record=on_record,
        only=only,
        kept=kept,
        settle=settle,
        stop_unresolved=stop_unresolved,
        parallel=parallel,
        withhold=withhold,
        short_of=short_of,
        depth=1,
    )


def _run(
    frame: Frame,
    battery: Battery,
    budget: Budget,
    *,
    cancelled: Callable[[], bool] = lambda: False,
    on_record: Callable[[Record], None] = lambda record: None,
    only: Iterable[str] | None = None,
    kept: Iterable[Record | dict] = (),
    settle: bool = False,
    stop_unresolved: bool = False,
    parallel: int = 1,
    withhold: Withhold | None = None,
    short_of: str | None = None,
    reads: Mapping[str, str] | None = None,
    depth: int = 0,
) -> RunResult:
    # run, and for until_firm also `reads`, a category for each input by its
    # id: the run is cut short once some input can no longer read its own, as
    # `short_of` cuts it once one cannot read that category; `depth` counts
    # the calls between run's caller and here, for the warnings' stack level
    named = frame.battery["kind"]
    if battery.name != named:  # the hash names the battery: no other reads under it
        raise BatteryError(f"this frame asks for battery {named!r}, not {battery.name!r}")
    _check_parallel(parallel, battery)
    if short_of is not None and short_of not in RULING:
        raise UsageError(f"short_of is carried or cooled, not {short_of!r}")
    if short_of is not None:
        reads = dict.fromkeys((x["id"] for x in frame.inputs), short_of)
    if withhold is not None:
        refuse_withheld(frame, withhold, training=trains(battery, frame))
    try:
        battery.check(frame)
        fits = getattr(battery, "check_cap", None)  # optional: a cap it cannot answer within
        if callable(fits):
            fits(frame, budget.output_tokens_per_call)
    except ValueError as error:  # a battery refuses as the protocol says, with a ValueError
        if isinstance(error, GadflyError) and type(battery).__module__.startswith("midwife."):
            raise  # a shipped battery's refusal, in Gadfly's own words
        said = f"it said {str(error)!r}"  # its words quoted: a battery's are not Gadfly's
        raise BatteryError(f"battery {battery.name!r} refused this frame", said) from error
    ids = trial_ids(frame)
    wanted = set(ids) if only is None else set(only)
    unknown = wanted - set(ids)
    if unknown:
        raise UsageError(
            f"the plan has no trial {quoted(sorted(unknown))}", "gadfly plan lists its trials"
        )
    made = [record.as_dict() if isinstance(record, Record) else record for record in kept]
    for record in made:  # a row that is no record is refused before anything is counted
        _check_shape(record)
    # Counted, not built: a plan the budget refuses is never made.
    done = {
        (r["input"], r["trial"], r["run"])
        for r in made
        if isinstance(r, dict)
        and all(isinstance(r.get(k), str) for k in ("input", "trial"))
        and isinstance(r.get("run"), int)
    }  # a malformed row counts for nothing here; check_records refuses it below
    planned = len(frame.inputs) * len(wanted) * frame.quorum - sum(t in wanted for _, t, _ in done)
    if planned > budget.calls:
        return _warned(
            RunResult(
                (), planned, f"the plan needs {planned} calls; the budget allows {budget.calls}"
            ),
            level=3 + depth,
        )
    everything = plan(frame)
    trials = [trial for trial in everything if trial.id in wanted]
    # asked to keep each input's category in reach, the trials that rule out the
    # one category asked go first, or those that most often fix a verdict
    wanted_reads = set(reads.values()) if reads else set()
    first = (
        RULING[next(iter(wanted_reads))]
        if len(wanted_reads) == 1 and next(iter(wanted_reads)) in RULING
        else DECISIVE
        if reads or stop_unresolved
        else ()
    )
    if first:  # stable: the rest keep the plan's order
        trials.sort(key=lambda t: first.index(t.id) if t.id in first else len(first))
    # Kept records stand for calls, so they are read as judge will read them,
    # and, being this run's own, each must name the prompt its call was planned with.
    check_records(frame, made, {trial.id: trial.body_hash for trial in everything})
    by_trial = {trial.id: trial for trial in everything}
    by_input = {x["id"]: x for x in frame.inputs}
    for record in made:
        planned_prompt = prompt(frame, by_trial[record["trial"]], by_input[record["input"]])
        if record["prompt"] != digest(planned_prompt):
            raise RecordsError(
                f"a kept record of trial {record['trial']!r} was made from another prompt"
            )
    calls = [
        (x, trial, index)
        for x in frame.inputs
        for trial in trials
        for index in range(frame.quorum)
        if (x["id"], trial.id, index) not in done
    ]
    # each trial's answers so far, kept ones included, counted as they come,
    # so a trial can settle without counting them again
    tally: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    answered: Counter[tuple[str, str]] = Counter()
    whole = {"baseline", "repeat"} if frame.raw["standing"].get("stable") else set()
    # asked to stop: each input's trials whose level is fixed, with their answers
    # as they come, and how often those changed, which names the input's state
    known: dict[str, dict[str, list[str | None]]] = defaultdict(dict)
    revision: Counter[str] = Counter()
    spared: dict[str, tuple[int, frozenset[str]]] = {}  # each input's unneeded trials, by state

    def fixed(key: tuple[str, str]) -> bool:
        # a trial whose level can no longer change, whatever its other calls give
        n = answered[key]
        return n >= frame.quorum or (
            key[1] not in whole and _fixed(tally[key], n, frame.quorum, frame.agree, frame.labels)
        )

    def count(x: str, trial: str, observation: str | None) -> None:
        answered[x, trial] += 1
        if observation is not None:
            tally[x, trial][observation] += 1
        if (stop_unresolved or reads) and (trial in known[x] or fixed((x, trial))):
            known[x].setdefault(trial, []).append(observation)
            if len(known[x][trial]) == 1:  # fixed now: its earlier answers too
                known[x][trial] = [*tally[x, trial].elements()] + [None] * (
                    answered[x, trial] - tally[x, trial].total()
                )
            revision[x] += 1

    for record in made:
        count(record["input"], record["trial"], record["observation"])
    cap = budget.output_tokens_per_call
    records: list[Record] = []
    spent = skipped = unasked = short = 0
    lost: list[str] = []  # the first input found unable to read its category in `reads`
    looked: dict[str, int] = {}  # each input's state when it was last looked at

    def needless(x: dict[str, str], trial: Trial) -> bool:
        # asked to settle, a trial whose level can no longer change asks no more
        key = (x["id"], trial.id)
        return settle and trial.id not in whole and fixed(key)

    def done_with(x: dict[str, str], trial: Trial) -> bool:
        # asked to stop, an input that reads unresolved whatever comes asks no more;
        # read from its fixed trials alone, once each time their answers change
        if not stop_unresolved:
            return False
        state = revision[x["id"]]
        if spared.get(x["id"], (None,))[0] != state:
            spared[x["id"]] = state, unneeded(frame, x["id"], known[x["id"]])
        return trial.id in spared[x["id"]][1]

    def beyond(x: dict[str, str]) -> bool:
        # asked for each input's category, a frame an input can no longer read its own
        # on asks no more; read from the input's fixed trials, once each time their
        # answers change
        if not reads or lost:
            return bool(lost)
        state = revision[x["id"]]
        if looked.get(x["id"]) != state:
            looked[x["id"]] = state
            if out_of_reach(frame, x["id"], known[x["id"]], reads[x["id"]]):
                lost.append(x["id"])
        return bool(lost)

    def blocked(running: int) -> str | None:
        # why no further call may start while `running` calls are still out
        if cancelled():
            return "cancelled"
        if budget.tokens is not None and spent + (running + 1) * cap > budget.tokens:
            return f"the token budget ({budget.tokens}) is spent"
        return None

    def keep(x: dict[str, str], trial: Trial, index: int, text: str, o: Observation) -> str | None:
        # one call's record, handed on; why the run must stop after it, if it must
        nonlocal spent
        # What the battery reports, or the cap when it reports nothing.
        used = o.usage.get("output_tokens")
        used = cap if not isinstance(used, int) or isinstance(used, bool) else used
        spent += used
        record = _record(frame, battery, x["id"], trial, index, text, o)
        records.append(record)
        count(x["id"], trial.id, record.observation)
        on_record(record)
        if used > cap:  # the budget holds only while every call keeps its cap
            return f"the battery reported {used} output tokens for a call capped at {cap}"
        if used < 0:  # a negative report would buy back budget it never had
            return f"the battery reported {used} output tokens, which no call spends"
        return None

    def ended(stopped: str | None = None) -> RunResult:
        result = RunResult(tuple(records), planned, stopped, skipped, unasked, short)
        return _warned(result, level=4 + depth)

    if parallel == 1:
        try:
            for x, trial, index in calls:
                if needless(x, trial):
                    skipped += 1
                    continue
                if done_with(x, trial):
                    unasked += 1
                    continue
                if beyond(x):
                    short += 1
                    continue
                stopped = blocked(0)
                if stopped:
                    return ended(stopped)
                text = prompt(frame, trial, x)
                try:
                    observation = _observe(battery, frame, text, cap)
                except StopRun as stop:
                    return ended(_halted(stop))
                stopped = keep(x, trial, index, text, observation)
                if stopped:
                    return ended(stopped)
        except (KeyboardInterrupt, SystemExit) as interrupt:
            interrupt.running = 0  # the one call out was this thread's, and it ended with it
            raise
        return ended()

    # At once: each trial's first calls before any trial's next, so a trial
    # can settle before its later calls start; made in that order, not sorted.
    # Asked to stop short of a category, the trials that rule it out go whole first.
    ruling = set(first) if reads else set()
    queue = deque(
        (x, trial, index)
        for late in (False, True)
        for index in range(frame.quorum)
        for x in frame.inputs
        for trial in trials
        if (x["id"], trial.id, index) not in done
        and (bool(ruling) and trial.id not in ruling) is late
    )
    order = itertools.count()
    out: Counter[tuple[str, str]] = Counter()  # each trial's calls out now
    started: dict[int, tuple[dict[str, str], Trial, int, str]] = {}  # each call made, until kept
    ended_at: dict[int, Observation] = {}  # each call's observation, set by its worker
    running: dict[Future[None], int] = {}

    def waiting(x: dict[str, str], trial: Trial) -> bool:
        # asked to settle, a trial has out no more calls than could fix it, so calls at
        # once spare what one at a time spares; which call goes when never touches a level
        key = (x["id"], trial.id)
        if ruling and trial.id not in ruling:
            # asked to stop short, it waits for every ruling call to answer: one may end the run
            if any(c[1].id in ruling for c in queue) or any(
                n and t in ruling for (_, t), n in out.items()
            ):
                return True
        if not settle or trial.id in whole or needless(x, trial):
            return False
        return out[key] >= max(1, frame.agree - max(tally[key].values(), default=0))

    def ask(seq: int, text: str) -> None:
        try:
            ended_at[seq] = _observe(battery, frame, text, cap)
        except StopRun as stop:
            ended_at[seq] = stop  # read when kept: no record, and no call after

    def keep_call(seq: int) -> str | None:
        x, trial, index, text = started.pop(seq)
        out[x["id"], trial.id] -= 1
        observed = ended_at.pop(seq)
        if isinstance(observed, StopRun):
            return _halted(observed)
        return keep(x, trial, index, text, observed)

    # A first Ctrl-C lets the calls already out end and keeps them, then goes
    # on as KeyboardInterrupt; a second stops at once.
    interrupted: list[int] = []
    held = threading.current_thread() is threading.main_thread()
    previous = (signal.getsignal(signal.SIGINT) if held else None) or signal.default_int_handler

    def hold(signum: int, _frame: object) -> None:
        interrupted.append(signum)
        signal.signal(signal.SIGINT, previous)

    if held:
        signal.signal(signal.SIGINT, hold)
    stopped = None
    pool = ThreadPoolExecutor(max_workers=parallel)
    try:
        while queue or running:
            while stopped is None and queue and len(running) < parallel:
                chosen = next((c for c in queue if not waiting(c[0], c[1])), None)
                if chosen is None:  # all held: an answer now out decides what goes next
                    break
                x, trial, index = chosen
                if needless(x, trial):
                    queue.remove(chosen)
                    skipped += 1
                    continue
                if done_with(x, trial):
                    queue.remove(chosen)
                    unasked += 1
                    continue
                if beyond(x):
                    queue.remove(chosen)
                    short += 1
                    continue
                stopped = "cancelled" if interrupted else blocked(len(running))
                if stopped:
                    break
                queue.remove(chosen)
                seq, text = next(order), prompt(frame, trial, x)
                started[seq] = (x, trial, index, text)
                out[x["id"], trial.id] += 1
                running[pool.submit(ask, seq, text)] = seq
            if not running:
                break
            finished, _ = wait(running, return_when=FIRST_COMPLETED)
            raised = None  # what a worker raised past _observe, once the rest are kept
            for seq, call in sorted((running.pop(call), call) for call in finished):
                if call.exception() is not None:
                    raised = raised or call.exception()
                    continue
                stopped = keep_call(seq) or stopped
            if raised is not None:
                raise raised
    except (KeyboardInterrupt, SystemExit) as interrupt:
        # raised here, not held: every call made is spent, so keep each
        # one that ended; after a second Ctrl-C, wait for none still out,
        # as a call hung in its thread cannot be stopped
        if not interrupted:
            pool.shutdown(wait=True)  # every call handed to a worker, tracked or not
        for seq in sorted(set(started) & set(ended_at)):
            keep_call(seq)
        interrupt.running = sum(not call.done() for call in running)  # still out
        raise
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
        if held and signal.getsignal(signal.SIGINT) is hold:
            signal.signal(signal.SIGINT, previous)
    if interrupted:  # every call made has ended and is kept: none left running
        interrupt = KeyboardInterrupt()
        interrupt.running = 0
        raise interrupt
    return ended(stopped)


def _warned(result: RunResult, level: int = 3) -> RunResult:
    """The result, once what the run did not do as asked is raised as a
    warning (PEP 230): calls that came back with no answer, and a stop before
    the plan's end. Nothing passes in silence; a caller may make either an
    error with Python's own warning filters. `level` points the warning at
    run's caller."""
    openings = Counter(r.opening for r in result.records if r.opening is not None)
    if openings:
        reason, times = openings.most_common(1)[0]
        many, often = sum(openings.values()), "once" if times == 1 else f"({times} times)"
        warnings.warn(
            OpeningWarning(
                f"{many} of {len(result.records)} calls came back as openings, "
                f"most often {reason!r} {often}"
            ),
            stacklevel=level,
        )
    if result.stopped:
        made, stopped = len(result.records), result.stopped
        warnings.warn(
            StoppedWarning(f"the run stopped after {made} of {result.planned} calls; {stopped}"),
            stacklevel=level,
        )
    return result


def judge(frame: Frame, records: Iterable[Record | dict]) -> list[Finding]:
    """One finding per input, read from the records alone: the Records of a
    run, or the dicts a caller kept of them. A record the plan and the
    frame's battery could not have made is refused."""
    return judge_records(frame, [r.as_dict() if isinstance(r, Record) else r for r in records])


_SURROGATE = re.compile("[\ud800-\udfff]")


def _text(text: str) -> str:
    """Text a file can hold: each lone surrogate becomes U+FFFD."""
    return _SURROGATE.sub("\ufffd", text)


def _halted(stop: StopRun) -> str:
    """Why a run a battery stopped ended, its reason quoted."""
    return f"the battery stopped the run ({stop.reason!r})"


def _observe(battery: Battery, frame: Frame, text: str, cap: int) -> Observation:
    """A battery that fails gives an opening, never a guessed label; what it
    said and spent is kept beside the opening."""
    try:
        observation = battery.observe(frame, text, cap)
    except StopRun:
        raise  # the harness, not the call, failed: the run stops, with no record
    except Exception as error:  # noqa: BLE001 — the failure is the observation
        return Observation(label=None, opening=f"the battery failed ({type(error).__name__})")
    return _checked(frame, observation)


def _checked(frame: Frame, observation: object) -> Observation:
    """What a battery returned, held to the protocol: an observation of the
    right types, text a file can hold, and a label of this frame; anything
    else is an opening that names what was wrong."""
    if not isinstance(observation, Observation):
        return Observation(label=None, opening="the battery returned no observation")
    kinds = {"label": (str, type(None)), "opening": (str, type(None)), "raw": str,
             "usage": dict, "served": str}  # fmt: skip
    wrong = [
        name for name, kind in kinds.items() if not isinstance(getattr(observation, name), kind)
    ]
    if "usage" not in wrong and not all(
        isinstance(key, str) and isinstance(value, int) and not isinstance(value, bool)
        for key, value in observation.usage.items()
    ):
        wrong.append("usage")  # counts are whole numbers, or nothing can be spent by them
    if wrong:  # the call was spent: keep it, as an opening that names what was wrong
        raw = _text(observation.raw) if isinstance(observation.raw, str) else ""
        opening = f"the battery returned a malformed observation ({', '.join(wrong)})"
        return Observation(label=None, opening=opening, raw=raw)
    # a lone surrogate is valid JSON but no text a file can hold: keep the rest of it
    observation = replace(
        observation,
        raw=_text(observation.raw),
        served=_text(observation.served),
        opening=None if observation.opening is None else _text(observation.opening),
    )
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
