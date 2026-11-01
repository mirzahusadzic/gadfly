"""The verdict, read from the trial records by fixed rules and nothing else.

For each input, each trial's observations are reduced to one level when the
frame's quorum agrees, or to none. The rules, in this order (the order of the
reference implementation, After the Poem's `finding` with `rules: 2`, in
scripts/load_bearing.py, https://github.com/mirzahusadzic/after-the-poem):

1. unresolved: a planned trial has no agreed level; with `standing.stable`,
   the baseline and repeat sessions do not all agree (a split level cannot show
   a one-level change); or repeat differs from baseline;
2. coupled but misaligned: presentation moves it, or placement does (the
   structure, not the wording, drove it);
3. coupled but misaligned: ablation moves it to an observation the frame does
   not allow (for ordered labels, the wrong way);
4. cooled: ablation leaves it as it was, unless a control trial (spans whose
   removal must move any scorer that reads) left it too: then unresolved, as
   the scorer cannot tell;
5. unresolved: a sham moves it (the change is not specific to the relation);
6. carried: otherwise.

Outside scope only when the frame declares the exclusion; never inferred.

With `eachAnchor`, each anchor is also cut alone. Those trials are evidence
only and never change a category: after the ablation moved it, they say
whether each anchor carries it, either suffices, or one adds nothing alone;
where the ablation left it, they name any anchor that moved it alone.

What the trials do not settle is recorded as an open obligation beside the
category:

- carried: no hidden fallback (a bypass trial), presentation invariance and
  specificity when their trials were not run, and materialization (whether
  the observation is the form the recipient receives, which the frame must
  say);
- cooled: discrimination, unless a control moved it;
- outside scope: the independent scope check, which only the receiving
  owner can make.

Traceability rests on the records: each names its frame, battery, body,
prompt and what served it.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from .frame import Frame, _read_once

CARRIED, COOLED = "carried", "cooled"
# What a record must say to be read: the call it was, and what it saw.
# `served` is not required: records older than it lack it.
RECORD_KEYS = {
    "frame", "input", "trial", "run", "body", "prompt", "battery",
    "observation", "opening", "raw", "usage",
}  # fmt: skip
MISALIGNED, UNRESOLVED, OUTSIDE = "coupled but misaligned", "unresolved", "outside scope"
# The trials that turn a sense, the allowed key each answers to, and what the
# answer must follow when it turns
TURNS = (
    ("inversion", "inversion", "the relation's sense"),
    ("input-inversion", "inputInversion", "what is asked"),
)


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


def settled(observations: list[str | None], quorum: int, agree: int, labels: Iterable[str]) -> bool:
    """Whether a trial's level can no longer change: whatever its remaining
    calls answer, `level` gives what it gives now. One label at `agree` that
    no other can still reach settles it; so does no label able to reach it."""
    remaining = quorum - len(observations)
    if remaining <= 0:
        return True
    counts = Counter(o for o in observations if o is not None)
    reach = {label: counts[label] + remaining for label in labels}
    leaders = [label for label in reach if counts[label] >= agree]
    if len(leaders) > 1:  # two already agree: no level, whatever comes
        return True
    return all(n < agree for label, n in reach.items() if label not in leaders)


def judge(frame: Frame, records: list[dict[str, Any]]) -> list[Finding]:
    """One finding per input, from the records of one run of one frame.
    Every planned trial is read; one without records has no level, and one
    with fewer than `quorum` has a level only once it is settled, so a
    stopped run never reads a level its missing calls could change."""
    from .interventions import plan

    trials = plan(frame)
    check_records(frame, records, {trial.id: trial.body_hash for trial in trials})
    planned = [trial.id for trial in trials]
    seen: dict[tuple[str, str], list[str | None]] = defaultdict(list)
    for record in records:  # one pass, in record order
        seen[record["input"], record["trial"]].append(record["observation"])
    # under `stable` a split is read across every baseline and repeat call,
    # so those two settle only when whole
    whole = {"baseline", "repeat"} if _read_once(frame)["standing"].get("stable") else set()
    findings = []
    for x in frame.inputs:
        samples = {t: seen.get((x["id"], t), []) for t in planned}
        levels = {t: _level_of(frame, s, t in whole) for t, s in samples.items()}
        findings.append(_finding(frame, x["id"], levels, samples))
    return findings


def _level_of(frame: Frame, samples: list[str | None], whole: bool) -> str | None:
    """A trial's level, read only when its missing calls could not change it."""
    if len(samples) < frame.quorum and (
        whole or not settled(samples, frame.quorum, frame.agree, frame.labels)
    ):
        return None
    return level(samples, frame.agree)


def _check_shape(record: Any) -> None:
    """A record's shape, before anything is read from it: an object with every
    key, each of its kind."""
    if not isinstance(record, dict):
        raise ValueError("a record is a JSON object")
    lacking = RECORD_KEYS - set(record)
    if lacking:
        raise ValueError(f"a record lacks {sorted(lacking)}")
    for key, kind in (("input", str), ("trial", str), ("prompt", str), ("raw", str)):
        if not isinstance(record[key], kind):
            raise ValueError(f"a record's {key} is not a str")
    if not isinstance(record["usage"], dict):
        raise ValueError("a record's usage is not a dict")
    for key in ("observation", "opening"):
        if record[key] is not None and not isinstance(record[key], str):
            raise ValueError(f"a record's {key} is not a str")


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
        _check_shape(record)
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
    """What a trial may produce (ablation; bypass, its designated opening; an
    inversion or input inversion, what it must reach): the labels listed, or,
    for ordered labels, those below (or above) the baseline."""
    rule = _read_once(frame)["allowed"][trial]
    if isinstance(rule, list):
        return rule
    order = list(_read_once(frame)["observe"]["order"])
    at = order.index(base)
    return order[:at] if rule == "lower" else order[at + 1 :]


def _finding(
    frame: Frame, x: str, levels: dict[str, str | None], samples: dict[str, list[str | None]]
) -> Finding:
    finding = Finding(input=x, category=UNRESOLVED, levels=levels)
    if _read_once(frame).get("outsideScope"):
        # The exclusion is the owner's; the trials do not test it, so only
        # its own check is open or settled here.
        finding.evidence.append(f"declared outside scope: {_read_once(frame).get('outsideScope')}")
        check = _read_once(frame).get("scopeCheck")
        if check:
            finding.category = OUTSIDE
            finding.evidence.append(
                f"{check['owner']} checked the scope at {check['encounter']}: "
                f"{check['statement']} ({check['source']})"
            )
        else:
            finding.obligations.append(
                "independent scope check: the exclusion is declared, not tested"
            )
            if _read_once(frame).get("carriage", "all-checks") == "listed":
                finding.category = OUTSIDE
            else:
                finding.evidence.append("not outside scope until the owner's check is recorded")
        return finding
    # An input the input inversion does not turn was asked as it stands: its
    # level is a repeat's, never a stay
    read = dict(levels)
    if "input-inversion" in levels and not _turned(frame, x):
        del read["input-inversion"]
        finding.evidence.append("the input inversion does not reach this input")
    _read(frame, finding, read, samples)
    # What the trials did not settle is listed whatever the category: a
    # category never hides an open check.
    base = levels.get("baseline")
    finding.obligations[:0] = _open_checks(frame, read, base)
    if _read_once(frame).get("carriage", "all-checks") == "all-checks":
        _hold(finding)
    return finding


def _turned(frame: Frame, x: str) -> bool:
    """Whether the frame's input inversion changes what input `x` asks."""
    from .interventions import rename

    mapping = tuple(
        sorted((_read_once(frame)["interventions"].get("inputInversion") or {}).items())
    )
    text = next(i["text"] for i in frame.inputs if i["id"] == x)
    return rename(text, mapping) != text


def _hold(finding: Finding) -> None:
    """Under all-checks a category is named only when the checks it needs have
    passed: every carriage check for carried, discrimination for cooled."""
    if finding.category == CARRIED and finding.obligations:
        n = len(finding.obligations)
        finding.category = UNRESOLVED
        finding.evidence.append(
            f"not carried while {n} carriage check{' is' if n == 1 else 's are'} open"
        )
    elif finding.category == COOLED and any(
        o.startswith("discrimination") for o in finding.obligations
    ):
        finding.category = UNRESOLVED
        finding.evidence.append("not cooled until a control shows the scorer can move")


def _read(
    frame: Frame,
    finding: Finding,
    levels: dict[str, str | None],
    samples: dict[str, list[str | None]],
) -> None:
    """The rules, in order: the first that matches names the category."""
    say = finding.evidence.append
    # each anchor alone is evidence only: its level is read after the ablation
    missing = [t for t, v in levels.items() if v is None and not t.startswith("ablation-")]
    if missing:
        say(f"no agreed level in: {', '.join(missing)}")
        return
    base = levels["baseline"]
    if _read_once(frame)["standing"].get("stable") and "repeat" in samples:
        pooled = samples["baseline"] + samples["repeat"]
        if len(set(pooled)) > 1:
            shown = ", ".join("an opening" if s is None else s for s in pooled)
            say(f"the baseline and repeat sessions split ({shown})")
            return
    if "repeat" in levels and levels["repeat"] != base:
        say(f"repeat gave {levels['repeat']}, baseline {base}: this grain cannot tell")
        return
    if "presentation" in levels and levels["presentation"] != base:
        finding.category = MISALIGNED
        say(f"presentation moved it {base} -> {levels['presentation']}")
        return
    if "placement" in levels and levels["placement"] != base:
        finding.category = MISALIGNED
        say(f"placement moved it {base} -> {levels['placement']}")
        return
    _ablated(frame, finding, levels, base)
    finding.evidence += _alone(frame, levels, base)


def _ablated(frame: Frame, finding: Finding, levels: dict[str, str | None], base: str) -> None:
    """The rules from the ablation on, once the answer is stable enough to read."""
    say = finding.evidence.append
    ablated = levels["ablation"]
    if ablated != base and ablated not in allowed_for(frame, base):
        finding.category = MISALIGNED
        say(f"ablation moved it {base} -> {ablated}, which the frame does not allow")
        return
    if ablated == base:
        if levels.get("control") == base:
            say(f"ablation left it at {base}, and so did the control: the scorer cannot tell")
            finding.obligations.append(f"discrimination: the control left it at {base} too")
        else:
            finding.category = COOLED
            say(f"ablation left it at {base}")
            if "control" in levels:
                say(f"the control moved it {base} -> {levels['control']}: the scorer can tell")
            else:
                finding.obligations.append(
                    "discrimination: no control trial shows the scorer can move"
                )
        for trial, _, _ in TURNS:
            if levels.get(trial) not in (None, base):
                name = trial.replace("-", " ")
                say(f"the {name} moved it {base} -> {levels[trial]}, though the ablation did not")
        # said whether or not the control moved: it is where else the decision rests
        if levels.get("cumulative") not in (None, base):
            say(
                f"the cumulative ablation moved it to {levels['cumulative']}: carried elsewhere too"
            )
        return
    moved = [t for t, v in levels.items() if t.startswith("sham-") and v != base]
    if moved:
        say(f"a sham moved it too ({', '.join(moved)}); the change is not specific")
        return
    # The answer rests on the relation; turned, it must move where the frame says.
    for trial, key, follows in TURNS:
        if trial not in levels:
            continue
        name, turned = trial.replace("-", " "), levels[trial]
        if turned == base:
            finding.category = MISALIGNED
            say(f"{name} left it at {base}: the answer does not follow {follows}")
            return
        if turned not in allowed_for(frame, base, key):
            finding.category = MISALIGNED
            say(f"{name} moved it {base} -> {turned}, which the frame does not allow")
            return
    finding.category = CARRIED
    shams = sum(t.startswith("sham-") for t in levels)
    held = [t for t in ("presentation", "placement") if t in levels] + (
        [f"{shams} sham{'s' if shams > 1 else ''}"] if shams else []
    )
    say(
        f"ablation moved it {base} -> {ablated}"
        + (f"; held under {', '.join(held)}" if held else "")
    )
    # The trials that settled more than the ablation are named too, so two
    # findings that ran different trials never read the same.
    for trial, _, follows in TURNS:
        if trial in levels:
            name = trial.replace("-", " ")
            say(f"{name} moved it {base} -> {levels[trial]}: the answer follows {follows}")
    if "bypass" in levels and _fallback(frame, levels, base) is None:
        say(f"bypass moved it {base} -> {levels['bypass']}: no hidden fallback")
    if "control" in levels:
        control = levels["control"]
        say(
            f"the control moved it {base} -> {control}"
            if control != base
            else f"the control left it at {base}"
        )


def _alone(frame: Frame, levels: dict[str, str | None], base: str) -> list[str]:
    """How the anchors carry it, read from each cut alone: evidence only, said
    once the ablation is read."""
    if not _read_once(frame)["interventions"].get("eachAnchor"):
        return []
    alone = {anchor: levels.get(f"ablation-{anchor}") for anchor in frame.anchors}
    lines = [f"{anchor} alone has no agreed level" for anchor, v in alone.items() if v is None]
    if levels["ablation"] == base:  # cutting more should not move it less
        return lines + [
            f"{anchor} alone moved it {base} -> {v}, though cutting every anchor did not"
            for anchor, v in alone.items()
            if v not in (None, base)
        ]
    moving = [anchor for anchor, v in alone.items() if v not in (None, base)]
    idle = [anchor for anchor, v in alone.items() if v == base]
    if len(moving) == len(alone):
        return ["each anchor carries it"]
    if len(idle) == len(alone):
        if len(alone) == 2:
            return ["the anchors carry it independently; either suffices"]
        return ["no anchor alone is needed: the others carry it without it"]
    parts = (
        [f"{', '.join(moving)} {'carries' if len(moving) == 1 else 'carry'} it"] if moving else []
    )
    if idle:
        parts.append(f"{', '.join(idle)} {'adds' if len(idle) == 1 else 'add'} nothing alone")
    return lines + (["; ".join(parts)] if parts else [])


def _fallback(frame: Frame, levels: dict[str, str | None], base: str | None) -> str | None:
    """The no-hidden-fallback check while it is open; None once the bypass
    settled it (it moved, or reached the designated opening)."""
    bypass = levels.get("bypass")
    if "bypass" not in levels:
        return "no hidden fallback: no bypass trial was declared"
    if bypass is None or base is None:
        return "no hidden fallback: the bypass has no agreed level to read against baseline"
    if "bypass" in _read_once(frame)["allowed"]:
        opening = allowed_for(frame, base, "bypass")
        if bypass not in opening:
            return (
                f"no hidden fallback: bypass gave {bypass}, "
                f"not the designated opening ({', '.join(opening)})"
            )
    if bypass == base:  # nothing moved, even where the opening names the baseline answer
        return f"no hidden fallback: bypass left it at {base}"
    return None


def _open_checks(frame: Frame, levels: dict[str, str | None], base: str | None) -> list[str]:
    """The carriage checks the trials did not settle: no hidden fallback,
    presentation invariance, specificity, monotonicity, direction (when an
    inversion is declared) and materialization."""
    open_ = []
    fallback = _fallback(frame, levels, base)
    if fallback:
        open_.append(fallback)
    if "presentation" not in levels:
        open_.append("presentation invariance: no presentation trial was declared")
    shams = sum(t.startswith("sham-") for t in levels)
    declared = _read_once(frame)["interventions"].get("sham")
    wanted = 0 if not declared else 1 if declared is True else declared["draws"]
    if not wanted:
        open_.append("specificity: no sham trial was declared")
    elif shams < wanted:
        open_.append(
            f"specificity: {shams} sham trial(s), {wanted} declared; "
            "the body has no span of the anchors' kind left that is not an "
            "anchor, bypassed or a fallback"
        )
    # A sham that moved it is listed whatever the category: misaligned and
    # cooled are read before the shams, and must not hide them.
    moved = [t for t, v in levels.items() if t.startswith("sham-") and v not in (None, base)]
    if moved and base is not None:
        open_.append(f"specificity: {', '.join(moved)} moved it too; the change is not specific")
    # Cutting more should not move it less: a control that cuts the anchors and
    # more, or the cumulative (always the anchors and more), yet holds where the
    # ablation moved, leaves the ablation's move in doubt.
    declared = _read_once(frame)["interventions"]
    wider = {"control": set(declared.get("control") or []) >= set(frame.anchors),
             "cumulative": bool(declared.get("cumulative"))}  # fmt: skip
    for trial, cuts_more in wider.items():
        if (
            cuts_more
            and base is not None
            and levels.get("ablation") not in (None, base)
            and levels.get(trial) == base
        ):
            open_.append(
                f"monotonicity: the {trial} removes the anchors and more, yet left it at {base}"
            )
    for trial, _, _ in TURNS:
        if trial in levels and levels[trial] is None:
            open_.append(f"direction: the {trial.replace('-', ' ')} has no agreed level")
    if not _read_once(frame).get("materialized"):
        open_.append(
            "materialization: the frame does not say the observation is "
            "the form the recipient receives"
        )
    return open_
