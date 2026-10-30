"""The verdict, read from the trial records by fixed rules and nothing else.

For each input, each trial's observations are reduced to one level when the
frame's quorum agrees, or to none. The rules, in this order (the order of the
reference implementation, After the Poem's `finding` with `rules: 2`, in
scripts/load_bearing.py, https://github.com/mirzahusadzic/after-the-poem):

1. unresolved: a planned trial has no agreed level; with `standing.stable`,
   the baseline and repeat sessions do not all agree (a split level cannot show
   a one-level change); or repeat differs from baseline;
2. coupled but misaligned: presentation moves it;
3. coupled but misaligned: ablation moves it to an observation the frame does
   not allow (for ordered labels, the wrong way);
4. cooled: ablation leaves it as it was;
5. unresolved: a sham moves it (the change is not specific to the relation);
6. carried: otherwise.
Outside scope only when the frame declares the exclusion; never inferred.

Two carriage checks are recorded as open obligations unless the trials settle
them: no hidden fallback (a bypass trial) and materialization (whether the
observation is the form the recipient receives, which the frame must say).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .frame import Frame

CARRIED, COOLED = "carried", "cooled"
MISALIGNED, UNRESOLVED, OUTSIDE = "coupled but misaligned", "unresolved", "outside scope"


@dataclass
class Finding:
    input: str
    category: str
    levels: dict[str, str | None]
    evidence: list[str] = field(default_factory=list)
    obligations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def level(observations: list[str | None], agree: int) -> str | None:
    """The observation at least `agree` runs gave, if exactly one did."""
    counts = Counter(o for o in observations if o is not None)
    winners = [label for label, n in counts.items() if n >= agree]
    return winners[0] if len(winners) == 1 else None


def judge(frame: Frame, records: list[dict[str, Any]]) -> list[Finding]:
    """One finding per input, from the records of one run of one frame.
    Every planned trial is read; one without records has no level."""
    from .interventions import plan

    trials = plan(frame)
    _check_records(frame, records, {trial.id: trial.body_hash for trial in trials})
    planned = [trial.id for trial in trials]
    findings = []
    for x in frame.inputs:
        mine = [r for r in records if r["input"] == x["id"]]
        samples = {t: [r["observation"] for r in mine if r["trial"] == t] for t in planned}
        levels = {t: level(s, frame.agree) for t, s in samples.items()}
        findings.append(_finding(frame, x["id"], levels, samples))
    return findings


def _check_records(frame: Frame, records: list[dict[str, Any]], bodies: dict[str, str]) -> None:
    """Records are read only as the plan made them: this frame, its inputs and
    trials, each trial's own body, runs within the quorum, each run once. A
    record copied twice can never make a quorum."""
    inputs = {x["id"] for x in frame.inputs}
    seen: set[tuple[str, str, int]] = set()
    for record in records:
        if record["frame"] != frame.hash:
            raise ValueError("a record belongs to another frame")
        if record["input"] not in inputs or record["trial"] not in bodies:
            raise ValueError(
                f"a record names an input or trial the plan does not have: "
                f"{record['input']}/{record['trial']}"
            )
        if record["body"] != bodies[record["trial"]]:
            raise ValueError(f"a {record['trial']} record was made on another body")
        run = record["run"]
        if not isinstance(run, int) or isinstance(run, bool) or not 0 <= run < frame.quorum:
            raise ValueError(f"run {run!r} is outside the quorum of {frame.quorum}")
        key = (record["input"], record["trial"], run)
        if key in seen:
            raise ValueError(f"two records for {key[0]}/{key[1]} run {run}")
        seen.add(key)


def allowed_for(frame: Frame, base: str) -> list[str]:
    """What ablation may produce: the labels listed, or, for ordered labels,
    those below (or above) the baseline."""
    rule = frame.allowed["ablation"]
    if isinstance(rule, list):
        return rule
    order = list(frame.raw["observe"]["order"])
    at = order.index(base)
    return order[:at] if rule == "lower" else order[at + 1 :]


def _finding(
    frame: Frame, x: str, levels: dict[str, str | None], samples: dict[str, list[str | None]]
) -> Finding:
    finding = Finding(input=x, category=UNRESOLVED, levels=levels)
    say = finding.evidence.append
    if frame.outside_scope:
        finding.category = OUTSIDE
        say(f"declared outside scope: {frame.outside_scope}")
        return finding
    missing = [t for t, v in levels.items() if v is None]
    if missing:
        say(f"no agreed level in: {', '.join(missing)}")
        return finding
    base = levels["baseline"]
    if frame.raw["standing"].get("stable") and "repeat" in samples:
        pooled = samples["baseline"] + samples["repeat"]
        if len(set(pooled)) > 1:
            say(f"the baseline and repeat sessions split ({', '.join(map(str, pooled))})")
            return finding
    if "repeat" in levels and levels["repeat"] != base:
        say(f"repeat gave {levels['repeat']}, baseline {base}: this grain cannot tell")
        return finding
    if "presentation" in levels and levels["presentation"] != base:
        finding.category = MISALIGNED
        say(f"presentation moved it {base} -> {levels['presentation']}")
        return finding
    ablated = levels["ablation"]
    if ablated != base and ablated not in allowed_for(frame, base):
        finding.category = MISALIGNED
        say(f"ablation moved it {base} -> {ablated}, which the frame does not allow")
        return finding
    if ablated == base:
        finding.category = COOLED
        say(f"ablation left it at {base}")
        if levels.get("cumulative") not in (None, base):
            say(
                f"the cumulative ablation moved it to {levels['cumulative']}: carried elsewhere too"
            )
        return finding
    moved = [t for t, v in levels.items() if t.startswith("sham-") and v != base]
    if moved:
        say(f"a sham moved it too ({', '.join(moved)}); the change is not specific")
        return finding
    finding.category = CARRIED
    shams = sum(t.startswith("sham-") for t in levels)
    held = (["presentation"] if "presentation" in levels else []) + (
        [f"{shams} sham{'s' if shams > 1 else ''}"] if shams else []
    )
    say(
        f"ablation moved it {base} -> {ablated}"
        + (f"; held under {', '.join(held)}" if held else "")
    )
    _obligations(frame, finding, levels, base)
    return finding


def _obligations(frame: Frame, finding: Finding, levels: dict[str, str | None], base: str) -> None:
    if "bypass" not in levels:
        finding.obligations.append("no hidden fallback: no bypass trial was declared")
    elif levels["bypass"] in (None, base):
        finding.obligations.append(f"no hidden fallback: bypass left it at {levels['bypass']}")
    if "presentation" not in levels:
        finding.obligations.append("presentation invariance: no presentation trial was declared")
    shams = sum(t.startswith("sham-") for t in levels)
    declared = frame.interventions.get("sham")
    wanted = 0 if not declared else 1 if declared is True else declared["draws"]
    if shams < max(wanted, 1):
        finding.obligations.append(
            f"specificity: {shams} sham trial(s), {wanted} declared"
            + (
                "; the body has no unanchored span of the anchors' kind left"
                if wanted > shams
                else ""
            )
        )
    if not frame.raw.get("materialized"):
        finding.obligations.append(
            "materialization: the frame does not say the observation is "
            "the form the recipient receives"
        )
