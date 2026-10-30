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
4. cooled: ablation leaves it as it was, unless a control trial (spans whose
   removal must move any scorer that reads) left it too: then unresolved, as
   the scorer cannot tell;
5. unresolved: a sham moves it (the change is not specific to the relation);
6. carried: otherwise.
Outside scope only when the frame declares the exclusion; never inferred.

What the trials do not settle is recorded as an open obligation beside the
category. Carried: no hidden fallback (a bypass trial), presentation
invariance and specificity when their trials were not run, and
materialization (whether the observation is the form the recipient
receives, which the frame must say). Cooled: discrimination, unless a
control moved it. Outside scope: the independent scope check, which only
the receiving owner can make. Traceability rests on the records: each
names its frame, battery, body, prompt and what served it.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from .frame import Frame

CARRIED, COOLED = "carried", "cooled"
# What a record must say to be read: the call it was, and what it saw.
RECORD_KEYS = {"frame", "input", "trial", "run", "body", "battery", "observation", "opening"}
MISALIGNED, UNRESOLVED, OUTSIDE = "coupled but misaligned", "unresolved", "outside scope"


@dataclass
class Finding:
    """One input's verdict: its category, each trial's agreed level (None
    where the quorum did not agree), the evidence for the category, and the
    obligations it leaves open."""

    input: str
    category: str
    levels: dict[str, str | None]
    evidence: list[str] = field(default_factory=list)
    obligations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        """The finding as a plain dict."""
        return self.__dict__.copy()


@dataclass
class Overall:
    """The frame's one category over its test domain: every input's."""

    category: str
    inputs: dict[str, str]
    evidence: list[str] = field(default_factory=list)
    obligations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        """The verdict as a plain dict."""
        return self.__dict__.copy()


def overall(findings: list[Finding]) -> Overall:
    """One category over the frame's inputs: outside scope when declared;
    otherwise coupled but misaligned if any input is; unresolved if any is,
    or if the relation carried on some inputs and cooled on others; carried
    or cooled only when every input is. Each input's evidence is kept; what
    every input leaves open is said once, the rest names its input."""
    if not findings:
        raise ValueError("there is no finding to read")
    inputs = {f.input: f.category for f in findings}
    found = set(inputs.values())
    evidence = [f"{f.input}: {line}" for f in findings for line in f.evidence]
    if found == {CARRIED, COOLED}:
        carried = ", ".join(x for x, c in inputs.items() if c == CARRIED)
        cooled = ", ".join(x for x, c in inputs.items() if c == COOLED)
        evidence.insert(
            0, f"carried on {carried}, cooled on {cooled}: the relation holds on some inputs only"
        )
    category = next(
        (c for c in (OUTSIDE, MISALIGNED, UNRESOLVED) if c in found),
        UNRESOLVED if len(found) > 1 else found.pop(),
    )
    shared = set.intersection(*(set(f.obligations) for f in findings))
    obligations = [o for o in findings[0].obligations if o in shared]
    obligations += [f"{f.input}: {o}" for f in findings for o in f.obligations if o not in shared]
    return Overall(category, inputs, evidence, obligations)


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
    check_records(frame, records, {trial.id: trial.body_hash for trial in trials})
    planned = [trial.id for trial in trials]
    seen: dict[tuple[str, str], list[str | None]] = defaultdict(list)
    for record in records:  # one pass, in record order
        seen[record["input"], record["trial"]].append(record["observation"])
    findings = []
    for x in frame.inputs:
        samples = {t: seen.get((x["id"], t), []) for t in planned}
        levels = {t: level(s, frame.agree) for t, s in samples.items()}
        findings.append(_finding(frame, x["id"], levels, samples))
    return findings


def check_records(
    frame: Frame, records: list[dict[str, Any]], bodies: dict[str, str] | None = None
) -> None:
    """Records are read only as the plan and the frame's battery made them:
    this frame, its battery, its inputs and trials, each trial's own body,
    runs within the quorum, each run once, and each a label of the frame or
    an opening. A record copied twice can never make a quorum. `run` reads the
    records it is given to keep by the same checks."""
    if bodies is None:
        from .interventions import plan

        bodies = {trial.id: trial.body_hash for trial in plan(frame)}
    inputs = {x["id"] for x in frame.inputs}
    battery = frame.battery["kind"]
    seen: set[tuple[str, str, int]] = set()
    for record in records:
        lacking = RECORD_KEYS - set(record)
        if lacking:
            raise ValueError(f"a record lacks {sorted(lacking)}")
        if record["frame"] != frame.hash:
            raise ValueError("a record belongs to another frame")
        if record["battery"] != battery:
            raise ValueError(
                f"a record was made by {record['battery']}, not the {battery} battery "
                "the frame names"
            )
        observation, opening = record["observation"], record["opening"]
        if (observation is None) == (opening is None):
            raise ValueError("a record holds a label or an opening: not both, not neither")
        if observation is not None and observation not in frame.labels:
            raise ValueError(f"{observation!r} is not one of this frame's labels")
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


def allowed_for(frame: Frame, base: str, trial: str = "ablation") -> list[str]:
    """What a trial may produce (ablation; bypass, its designated opening):
    the labels listed, or, for ordered labels, those below (or above) the
    baseline."""
    rule = frame.allowed[trial]
    if isinstance(rule, list):
        return rule
    order = list(frame.raw["observe"]["order"])
    at = order.index(base)
    return order[:at] if rule == "lower" else order[at + 1 :]


def _finding(
    frame: Frame, x: str, levels: dict[str, str | None], samples: dict[str, list[str | None]]
) -> Finding:
    finding = Finding(input=x, category=UNRESOLVED, levels=levels)
    if frame.outside_scope:
        finding.category = OUTSIDE
        finding.evidence.append(f"declared outside scope: {frame.outside_scope}")
        finding.obligations.append("independent scope check: the exclusion is declared, not tested")
        return finding
    _read(frame, finding, levels, samples)
    # What the trials did not settle is listed whatever the category: a
    # category never hides an open check.
    base = levels.get("baseline")
    finding.obligations[:0] = _open_checks(frame, levels, base)
    return finding


def _read(
    frame: Frame,
    finding: Finding,
    levels: dict[str, str | None],
    samples: dict[str, list[str | None]],
) -> None:
    """The rules, in order: the first that matches names the category."""
    say = finding.evidence.append
    missing = [t for t, v in levels.items() if v is None]
    if missing:
        say(f"no agreed level in: {', '.join(missing)}")
        return
    base = levels["baseline"]
    if frame.raw["standing"].get("stable") and "repeat" in samples:
        pooled = samples["baseline"] + samples["repeat"]
        if len(set(pooled)) > 1:
            say(f"the baseline and repeat sessions split ({', '.join(map(str, pooled))})")
            return
    if "repeat" in levels and levels["repeat"] != base:
        say(f"repeat gave {levels['repeat']}, baseline {base}: this grain cannot tell")
        return
    if "presentation" in levels and levels["presentation"] != base:
        finding.category = MISALIGNED
        say(f"presentation moved it {base} -> {levels['presentation']}")
        return
    ablated = levels["ablation"]
    if ablated != base and ablated not in allowed_for(frame, base):
        finding.category = MISALIGNED
        say(f"ablation moved it {base} -> {ablated}, which the frame does not allow")
        return
    if ablated == base:
        if levels.get("control") == base:
            say(f"ablation left it at {base}, and so did the control: the scorer cannot tell")
            finding.obligations.append(f"discrimination: the control left it at {base} too")
            return
        finding.category = COOLED
        say(f"ablation left it at {base}")
        if "control" in levels:
            say(f"the control moved it {base} -> {levels['control']}: the scorer can tell")
        else:
            finding.obligations.append("discrimination: no control trial shows the scorer can move")
        if levels.get("cumulative") not in (None, base):
            say(
                f"the cumulative ablation moved it to {levels['cumulative']}: carried elsewhere too"
            )
        return
    moved = [t for t, v in levels.items() if t.startswith("sham-") and v != base]
    if moved:
        say(f"a sham moved it too ({', '.join(moved)}); the change is not specific")
        return
    finding.category = CARRIED
    shams = sum(t.startswith("sham-") for t in levels)
    held = (["presentation"] if "presentation" in levels else []) + (
        [f"{shams} sham{'s' if shams > 1 else ''}"] if shams else []
    )
    say(
        f"ablation moved it {base} -> {ablated}"
        + (f"; held under {', '.join(held)}" if held else "")
    )


def _open_checks(frame: Frame, levels: dict[str, str | None], base: str | None) -> list[str]:
    """The carriage checks the trials did not settle: no hidden fallback,
    presentation invariance, specificity and materialization."""
    open_ = []
    bypass = levels.get("bypass")
    if "bypass" not in levels:
        open_.append("no hidden fallback: no bypass trial was declared")
    elif bypass is None or base is None:
        open_.append("no hidden fallback: the bypass has no agreed level to read against baseline")
    elif "bypass" in frame.allowed:
        opening = allowed_for(frame, base, "bypass")
        if bypass not in opening:
            open_.append(
                f"no hidden fallback: bypass gave {bypass}, "
                f"not the designated opening ({', '.join(opening)})"
            )
    elif bypass == base:
        open_.append(f"no hidden fallback: bypass left it at {base}")
    if "presentation" not in levels:
        open_.append("presentation invariance: no presentation trial was declared")
    shams = sum(t.startswith("sham-") for t in levels)
    declared = frame.interventions.get("sham")
    wanted = 0 if not declared else 1 if declared is True else declared["draws"]
    if shams < max(wanted, 1):
        open_.append(
            f"specificity: {shams} sham trial(s), {wanted} declared"
            + (
                "; the body has no unanchored span of the anchors' kind left"
                if wanted > shams
                else ""
            )
        )
    if not frame.raw.get("materialized"):
        open_.append(
            "materialization: the frame does not say the observation is "
            "the form the recipient receives"
        )
    return open_
