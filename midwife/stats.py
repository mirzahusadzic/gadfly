"""Statistics beside the verdict: how firm each trial's answers are, how
likely a quorum is to reach a level at all, whether a trial moved the answer
or held it, and how often a run's verdict comes out the same when its calls
are drawn again.

Nothing here changes a verdict. The fixed rules in `midwife.verdict` read
every category from the records; this module only says how much the calls
behind a category support it, so a run of five calls is not read as if it
were five hundred. Every number is computed from kept records, and the draws
are seeded by the frame's hash, so the same records always give the same
report.
"""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from .errors import RecordsError, UsageError
from .frame import Frame, canonical, digest
from .interventions import plan, prompt, trial_ids
from .verdict import check_records
from .verdict import judge as _judge

Z = 1.959963984540054  # two-sided 95%
HELD = ("repeat", "presentation", "placement")  # trials that should leave the answer
RESAMPLES = 200  # draws a stability report makes of each run, by default


def wilson(hits: int, n: int, z: float = Z) -> tuple[float, float]:
    """The Wilson score interval for `hits` of `n`: where the true share most
    likely lies (95% by default). Unlike hits/n it stays honest at small n:
    4 of 5 is anywhere from 38% to 96%."""
    if n == 0:
        return 0.0, 1.0
    share = hits / n
    scale = 1 + z * z / n
    centre = (share + z * z / (2 * n)) / scale
    margin = z * math.sqrt(share * (1 - share) / n + z * z / (4 * n * n)) / scale
    return max(0.0, centre - margin), min(1.0, centre + margin)


def at_least(k: int, n: int, p: float) -> float:
    """The chance that at least `k` of `n` calls give the reader's usual
    answer, when each gives it with chance `p`: a probability, kept within
    0 and 1 however the sum's rounding falls."""
    total = sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))
    return min(1.0, max(0.0, total))


def fisher(a: int, b: int, c: int, d: int) -> float:
    """Fisher's exact test, two-sided, for the table [[a, b], [c, d]]: the
    chance of a split at least this uneven if the two rows read alike."""
    row, total, column = a + b, a + b + c + d, a + c
    if total == 0:
        return 1.0

    def chance(x: int) -> float:
        return math.comb(row, x) * math.comb(total - row, column - x) / math.comb(total, column)

    seen = chance(a)
    low, high = max(0, column - (total - row)), min(row, column)
    return min(1.0, sum(p for p in map(chance, range(low, high + 1)) if p <= seen * (1 + 1e-9)))


def holm(pvalues: Mapping[str, float]) -> dict[str, float]:
    """Holm's adjustment: each p-value as it stands among the others, so that
    of many trials tested at once, chance alone passes 5% only 5% of the
    time."""
    ranked = sorted(pvalues.items(), key=lambda item: item[1])
    adjusted, running = {}, 0.0
    for rank, (key, p) in enumerate(ranked):
        running = max(running, min(1.0, (len(ranked) - rank) * p))
        adjusted[key] = running
    return adjusted


@dataclass(frozen=True)
class Power:
    """How likely a quorum is to reach a level, before a call is made."""

    agreement: float  # how often the reader gives its usual answer
    quorum: int
    agree: int
    trial: float  # one trial reaches a level of `agree` of `quorum`
    trials: int  # the trials the plan asks of an input, the one-anchor ones aside
    input: float  # every one of them reaches one

    def as_dict(self) -> dict[str, Any]:
        """The fields as a plain dict, as `--json` prints them."""
        return asdict(self)


def power(frame: Frame, agreement: float) -> Power:
    """The chance that a trial, and every trial the plan asks of an input,
    reaches a level, for a reader that gives its usual answer with chance
    `agreement`. A trial with no level leaves its input unresolved, so this
    is the most a run can resolve, whatever the evidence. The count is
    every planned trial but the one-anchor ones, which are evidence only;
    an input that no input inversion turns needs that trial's level no
    more, so for it the figure is a floor."""
    if isinstance(agreement, bool) or not isinstance(agreement, int | float):
        raise UsageError("agreement is a share between 0 and 1")
    if not 0 <= agreement <= 1:
        raise UsageError("agreement is a share between 0 and 1")
    needed = [t for t in trial_ids(frame) if not t.startswith("ablation-")]
    trial = at_least(frame.agree, frame.quorum, agreement)
    return Power(
        float(agreement), frame.quorum, frame.agree, trial, len(needed), trial ** len(needed)
    )


def _runs(frame: Frame, runs: Sequence[Iterable[dict]]) -> list[list[dict]]:
    # each kept run as the plan made it, refused as report refuses it otherwise
    checked = []
    for records in runs:
        records = list(records)
        check_records(frame, records)
        checked.append(records)
    return checked


def agreement(runs: Sequence[Iterable[dict]]) -> float | None:
    """The share of calls that gave their trial's most common answer in their
    own run: how steadily the reader answers when nothing changes between
    its calls. An opening never agrees, and a call its trial asked alone in
    its run has nothing to agree with, so it is not counted. None when no
    trial was asked twice in a run: there is no repeat to measure."""
    agreed = calls = 0
    for records in runs:
        groups: dict[tuple[str, str], list[str | None]] = defaultdict(list)
        for record in records:
            groups[record["input"], record["trial"]].append(record["observation"])
        for answers in groups.values():
            if len(answers) < 2:
                continue
            labels = Counter(a for a in answers if a is not None)
            agreed += labels.most_common(1)[0][1] if labels else 0
            calls += len(answers)
    return agreed / calls if calls else None


def pooled(frame: Frame, others: Sequence[tuple[Frame, Iterable[dict]]]) -> list[dict]:
    """Calls made under other frames that are this frame's calls in all but
    name: the same battery line, instruction and labels, and the same prompt.
    Each comes back as a call of this frame's trial with that prompt (its
    own input and trial when they have it), for counting, never for a
    verdict, since its frame's plan is not this one's. A call whose prompt
    is two of this frame's inputs' at once, and whose own input is neither,
    could be either's, and is left out."""
    same = (canonical(frame.battery), frame.instruction, frame.labels)
    by_prompt: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for trial in plan(frame):
        for x in frame.inputs:
            by_prompt[digest(prompt(frame, trial, x))].append((x["id"], trial.id))
    kept = []
    for other, records in others:
        if (canonical(other.battery), other.instruction, other.labels) != same:
            raise UsageError(
                f"frame {other.name!r} asks another reader, or asks it otherwise",
                "pool only calls made with the same battery line, instruction and labels",
            )
        for record in _runs(other, [records])[0]:
            places = by_prompt.get(record["prompt"])
            if not places:
                continue
            own = [place for place in places if place == (record["input"], record["trial"])]
            same = own or [place for place in places if place[1] == record["trial"]] or places
            if len({x for x, _ in same}) > 1:  # it says not whose call it is
                continue
            x, trial = same[0]
            kept.append({**record, "frame": frame.hash, "input": x, "trial": trial})
    return kept


@dataclass(frozen=True)
class TrialStats:
    """One trial's calls for one input, pooled over runs, against the
    baseline's most common answer."""

    trial: str
    calls: int
    answers: dict[str, int]  # each label given, by count
    openings: int  # calls that gave no label, apart: a label may itself be named "opening"
    top: str | None  # the most common label
    share: float  # of calls that gave it
    low: float  # its 95% interval
    high: float
    baseline: str | None  # the baseline's most common label
    moved: float | None  # Fisher's p against the baseline, or None for the baseline
    adjusted: float | None  # Holm's, among this input's trials
    differ: float | None  # for a trial that should hold: at most this share differs (95%)

    def as_dict(self) -> dict[str, Any]:
        """The fields as a plain dict, as `--json` prints them."""
        return asdict(self)


def compare(
    frame: Frame, runs: Sequence[Iterable[dict]], extra: Iterable[dict] = ()
) -> dict[str, list[TrialStats]]:
    """Each input's trials over all the runs given, and `extra` calls pooled
    in (see `pooled`): how many gave each answer, how firm the most common
    is, whether the trial moved the baseline's answer (Fisher's exact test,
    Holm-adjusted across the input's trials), and, for a repeat,
    presentation, placement or sham, at most how many of its answers could
    differ from the baseline's (the upper end of a 95% interval): "held" with
    15 calls means less than with 150."""
    calls: dict[tuple[str, str], list[str | None]] = defaultdict(list)
    for records in [*_runs(frame, runs), list(extra)]:
        for record in records:
            calls[record["input"], record["trial"]].append(record["observation"])
    report: dict[str, list[TrialStats]] = {}
    for x in frame.inputs:
        rows = []
        base_calls = calls.get((x["id"], "baseline"), [])
        base_labels = Counter(a for a in base_calls if a is not None)
        base = base_labels.most_common(1)[0][0] if base_labels else None
        hits = base_labels[base] if base else 0
        tests = {}
        for trial in trial_ids(frame):
            answers = calls.get((x["id"], trial))
            if not answers:
                continue
            labels = Counter(a for a in answers if a is not None)
            top, top_n = labels.most_common(1)[0] if labels else (None, 0)
            low, high = wilson(top_n, len(answers))
            same = sum(1 for a in answers if a is not None and a == base)
            moved = differ = None
            if trial != "baseline" and base is not None:
                moved = fisher(hits, len(base_calls) - hits, same, len(answers) - same)
                tests[trial] = moved
                if trial in HELD or trial.startswith("sham-"):
                    differ = wilson(len(answers) - same, len(answers))[1]
            rows.append(
                TrialStats(
                    trial=trial,
                    calls=len(answers),
                    answers=dict(labels.most_common()),
                    openings=len(answers) - labels.total(),
                    top=top,
                    share=top_n / len(answers),
                    low=low,
                    high=high,
                    baseline=base,
                    moved=moved,
                    adjusted=None,
                    differ=differ,
                )
            )
        adjusted = holm(tests)
        report[x["id"]] = [
            TrialStats(**{**row.as_dict(), "adjusted": adjusted.get(row.trial)}) for row in rows
        ]
    return report


def stability(
    frame: Frame, runs: Sequence[Iterable[dict]], resamples: int = RESAMPLES
) -> list[dict[str, dict[str, float]]]:
    """For each run, how often each input's verdict comes out each way when
    every trial's calls are drawn again, with replacement, as many as it had:
    the fixed rules read every draw, so no model judges anything. A verdict
    that comes out the same in 95% of draws is firm; one at 55% rests on a
    call or two. The draws are seeded by the frame's hash and the run's
    place, and made in the plan's order, so the same records always give
    the same shares, in whatever order they were kept. An input whose
    trials were each asked once in a run has nothing to draw again, and gets
    no shares for that run."""
    if isinstance(resamples, bool) or not isinstance(resamples, int) or resamples < 1:
        raise UsageError("resamples is a whole number of draws, at least 1")
    shares = []
    inputs = {x["id"]: n for n, x in enumerate(frame.inputs)}
    trials = {trial: n for n, trial in enumerate(trial_ids(frame))}
    for place, records in enumerate(_runs(frame, runs)):
        rng = random.Random(int(frame.hash[:16], 16) + place)
        groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
        # in the order a run one call at a time asks them, however they were
        # kept: calls made at once are kept as they end
        for record in sorted(
            records, key=lambda r: (inputs[r["input"]], trials[r["trial"]], r["run"])
        ):
            groups[record["input"], record["trial"]].append(record)
        tally: dict[str, Counter] = defaultdict(Counter)
        for _ in range(resamples):
            drawn = [
                {**rng.choice(group), "run": index}
                for group in groups.values()
                for index in range(len(group))
            ]
            for finding in _judge(frame, drawn):
                tally[finding.input][finding.category] += 1
        repeated = {x for (x, _), group in groups.items() if len(group) > 1}
        shares.append(
            {
                x: {category: count / resamples for category, count in counts.most_common()}
                for x, counts in tally.items()
                if x in repeated
            }
        )
    return shares


def observed(frame: Frame, runs: Sequence[Iterable[dict]]) -> list[dict[str, str]]:
    """Each run's verdict for each input, as the fixed rules read it."""
    return [
        {finding.input: finding.category for finding in _judge(frame, records)}
        for records in _runs(frame, runs)
    ]


def require_runs(runs: Sequence[Sequence[dict]]) -> None:
    """Refuse a report with no calls to count."""
    if not any(runs):
        raise RecordsError("no records to count", "give the kept runs of this frame")
