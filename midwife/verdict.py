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

import itertools
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any

from .errors import RecordsError, UsageError, plain, quoted
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
        raise UsageError("there is no finding to read")
    inputs = {f.input: f.category for f in findings}
    found = set(inputs.values())
    evidence = [f"in {f.input}, {line}" for f in findings for line in f.evidence]
    if found == {CARRIED, COOLED}:
        carried = ", ".join(x for x, c in inputs.items() if c == CARRIED)
        cooled = ", ".join(x for x, c in inputs.items() if c == COOLED)
        evidence.insert(
            0,
            f"carried on {carried}, cooled on {cooled}, so the relation holds on some inputs only",
        )
    category = next(
        (c for c in (OUTSIDE, MISALIGNED, UNRESOLVED) if c in found),
        UNRESOLVED if len(found) > 1 else found.pop(),
    )
    shared = set.intersection(*(set(f.obligations) for f in findings))
    obligations = [o for o in findings[0].obligations if o in shared]
    obligations += [
        f"in {f.input}, {o}" for f in findings for o in f.obligations if o not in shared
    ]
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
    counts = Counter(o for o in observations if o is not None)
    return _fixed(counts, len(observations), quorum, agree, labels)


def _fixed(
    counts: Counter[str], answered: int, quorum: int, agree: int, labels: Iterable[str]
) -> bool:
    """`settled`, from each label's count and how many calls answered, so a
    run can keep the counts as it goes instead of counting again."""
    remaining = quorum - answered
    if remaining <= 0:
        return True
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
        findings.append(
            _unasked(frame, x["id"], levels, samples) or _finding(frame, x["id"], levels, samples)
        )
    return findings


def _unasked(
    frame: Frame, x: str, levels: dict[str, str | None], samples: dict[str, list[str | None]]
) -> Finding | None:
    """An input some of whose trials were never asked, or not to the end, read
    when every answer they could give reads unresolved: the evidence and open
    checks all those readings share, and the trials left. None while an answer
    could read otherwise; the rules then read each as having no level."""
    whole = {"baseline", "repeat"} if _read_once(frame)["standing"].get("stable") else set()
    # each trial left, each anchor alone included, and whether it was never asked
    short = {t: not s for t, s in samples.items() if _left(frame, s, t in whole)}
    outcomes = _outcomes(frame, x, samples) if short else None
    if outcomes is None:
        return None
    evidence: list[str] | None = None
    obligations: list[str] = []
    for finding, _, _ in outcomes:
        if finding.category != UNRESOLVED:
            return None
        if evidence is None:
            evidence, obligations = finding.evidence, finding.obligations
        evidence = [e for e in evidence if e in finding.evidence]
        obligations = [o for o in obligations if o in finding.obligations]
    evidence = evidence or []
    # under `stable`, answers that split already split every reading: say which
    split = _split(samples) if whole else None
    if split and split not in evidence:
        evidence.insert(0, split)
    said = [
        f"{what} ({', '.join(t for t, never in short.items() if never is unasked)})"
        for what, unasked in (("not asked", True), ("not asked to the end", False))
        if unasked in short.values()
    ]
    said.append("whatever they gave, it reads unresolved")
    return Finding(x, UNRESOLVED, levels, [*evidence, "; ".join(said)], obligations)


def unneeded(frame: Frame, x: str, samples: dict[str, list[str | None]]) -> frozenset[str]:
    """The trials input `x` need not be asked, given the answers so far: once
    every answer the rest could give reads unresolved, all those not asked to
    the end, but each anchor alone while a reading still gets as far as the
    ablation, where its evidence is read. Empty while an answer could read
    otherwise, or the answers are too many to read."""
    from .interventions import trial_ids

    whole = {"baseline", "repeat"} if _read_once(frame)["standing"].get("stable") else set()
    outcomes = _outcomes(frame, x, samples)
    if outcomes is None:
        return frozenset()
    reached = False
    for finding, _, ablation in outcomes:
        if finding.category != UNRESOLVED:
            return frozenset()
        reached = reached or ablation
    return frozenset(
        t
        for t in trial_ids(frame)
        if _left(frame, samples.get(t, []), t in whole)
        and not (reached and t.startswith("ablation-"))
    )


def out_of_reach(frame: Frame, x: str, samples: dict[str, list[str | None]], category: str) -> bool:
    """Whether input `x` can no longer read `category`, given the answers so
    far: none of the answers its trials not asked to the end could give reads
    it. False while one could, or the answers are too many to read."""
    outcomes = _outcomes(frame, x, samples)
    if outcomes is None:
        return False
    return all(finding.category != category for finding, _, _ in outcomes)


def _split(samples: dict[str, list[str | None]]) -> str | None:
    """Under `stable`, the line saying the baseline and repeat sessions split,
    read over all their calls together; None when they agree or there is no
    repeat."""
    pooled = samples["baseline"] + samples.get("repeat", [])
    if "repeat" not in samples or len(set(pooled)) < 2:
        return None
    shown = ", ".join("an opening" if s is None else s for s in pooled)
    return f"the baseline and repeat sessions split ({shown})"


def _level_of(frame: Frame, samples: list[str | None], whole: bool) -> str | None:
    """A trial's level, read only when its missing calls could not change it."""
    return None if _left(frame, samples, whole) else level(samples, frame.agree)


def _left(frame: Frame, samples: list[str | None], whole: bool) -> bool:
    """Whether a trial's missing calls could still change its level: always,
    for one read `whole`."""
    return len(samples) < frame.quorum and (
        whole or not settled(samples, frame.quorum, frame.agree, frame.labels)
    )


def unreachable(frame: Frame) -> dict[str, list[str]] | None:
    """What no answers can make this frame read, found before a call: carried
    or cooled, each with the checks open in every reading that would name it
    but for them (empty when none comes that near), or the exclusion when the
    frame is declared outside scope. The rules themselves read every answer
    each trial could give; None when the readings would be more than OUTCOMES
    for an input."""
    scope = _read_once(frame).get("outsideScope")
    if scope:  # the exclusion is the owner's: no answer reads either category
        return {
            category: [f"declared outside scope ({plain(scope)})"] for category in (CARRIED, COOLED)
        }
    blocked: dict[str, dict[str, list[str]]] = {CARRIED: {}, COOLED: {}}
    for x in frame.inputs:
        outcomes = _outcomes(frame, x["id"], {})
        if outcomes is None:
            return None
        reached: set[str] = set()
        near: dict[str, list[str] | None] = dict.fromkeys(blocked)
        for finding, before, _ in outcomes:
            reached.add(finding.category)
            if before in near and finding.category != before:
                holding = _holding(before, finding.obligations)
                seen = near[before]
                near[before] = holding if seen is None else [o for o in seen if o in holding]
        for category, inputs in blocked.items():
            if category not in reached:
                inputs[x["id"]] = near[category] or []
    # as in overall: what every input leaves open is said once, the rest names its input
    said: dict[str, list[str]] = {}
    for category, inputs in blocked.items():
        if not inputs:
            continue
        lists = list(inputs.values())
        every = len(inputs) == len(frame.inputs)
        shared = set.intersection(*map(set, lists)) if every else set()
        said[category] = [o for o in lists[0] if o in shared] + [
            f"in {x}, {o}" for x, held in inputs.items() for o in held if o not in shared
        ]
        if not every:
            said[category] += [f"in {x}, no answers come near" for x, h in inputs.items() if not h]
    return said


# The most readings a check makes of one input before it gives up: every
# answer each unasked trial could give, at about 3 µs a reading.
OUTCOMES = 200_000


def _outcomes(
    frame: Frame, x: str, samples: dict[str, list[str | None]]
) -> Iterator[tuple[Finding, str, bool]] | None:
    """Every finding input `x` can read once its trials not asked to the end
    answer: each one's calls left all at one label, after the answers it has
    (each label it can still agree on is reached so, and a split reads
    unresolved anyway), its shams all at one (any sham that moves reads
    alike), each anchor alone at none (evidence only, never a category).
    Each comes with its category before the all-checks hold and whether the
    reading got as far as the ablation. None when they number more than
    OUTCOMES."""
    from .interventions import trial_ids

    planned = trial_ids(frame)
    whole = {"baseline", "repeat"} if _read_once(frame)["standing"].get("stable") else set()
    left = {t for t in planned if _left(frame, samples.get(t, []), t in whole)}
    unasked = [t for t in planned if t in left and not t.startswith("ablation-")]
    shams = [t for t in unasked if t.startswith("sham-")]
    free = [t for t in unasked if t not in shams[1:]]
    if len(frame.labels) ** len(free) > OUTCOMES:
        return None
    asked = {t: [] if t in left else samples.get(t, []) for t in planned}
    levels = {t: _level_of(frame, s, t in whole) for t, s in asked.items()}
    held = _read_once(frame).get("carriage", "all-checks") == "all-checks"

    def read(answers: tuple[str, ...]) -> tuple[Finding, str, bool]:
        given = dict(zip(free, answers, strict=True))
        given.update(dict.fromkeys(shams[1:], given.get(shams[0]) if shams else None))
        drawn = dict(asked)
        for t, v in given.items():  # the answers it has, then the calls left at v
            had = samples.get(t, [])
            drawn[t] = [*had, *[v] * (frame.quorum - len(had))]
        completed = {t: _level_of(frame, drawn[t], t in whole) for t in given}
        finding, reached = _reading(frame, x, {**levels, **completed}, drawn)
        before = finding.category
        if held:
            _hold(finding)
        return finding, before, reached

    return (read(answers) for answers in itertools.product(frame.labels, repeat=len(free)))


def _check_shape(record: Any) -> None:
    """A record's shape, before anything is read from it: an object with every
    key, each of its kind."""
    if not isinstance(record, dict):
        raise RecordsError("a record is a JSON object")
    lacking = RECORD_KEYS - set(record)
    if lacking:
        raise RecordsError(f"a record lacks keys {quoted(sorted(lacking))}")
    for key in ("frame", "input", "trial", "body", "prompt", "battery", "raw"):
        if not isinstance(record[key], str):
            raise RecordsError(f"a record's {key} is not a str")
    if not isinstance(record["usage"], dict):
        raise RecordsError("a record's usage is not a dict")
    if not all(
        isinstance(key, str) and isinstance(value, int) and not isinstance(value, bool)
        for key, value in record["usage"].items()
    ):  # as run keeps them: whole numbers, by name
        raise RecordsError("a record's usage counts are not whole numbers")
    if "served" in record and not isinstance(record["served"], str):  # older records lack it
        raise RecordsError("a record's served is not a str")
    for key in ("observation", "opening"):
        if record[key] is not None and not isinstance(record[key], str):
            raise RecordsError(f"a record's {key} is not a str")


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
            raise RecordsError("a record belongs to another frame")
        if record["battery"] != battery:
            raise RecordsError(
                f"a record was made by battery {record['battery']!r}, not {battery!r}, "
                "which the frame names"
            )
        observation, opening = record["observation"], record["opening"]
        if (observation is None) == (opening is None):
            raise RecordsError("a record holds both a label and an opening, or neither")
        if observation is not None and observation not in frame.labels:
            raise RecordsError(f"{observation!r} is not one of this frame's labels")
        if record["input"] not in inputs or record["trial"] not in bodies:
            raise RecordsError(
                f"a record names input {record['input']!r} and trial {record['trial']!r}, "
                "which the plan does not have"
            )
        if record["body"] != bodies[record["trial"]]:
            raise RecordsError(f"a record of trial {record['trial']!r} was made on another body")
        run = record["run"]
        if not isinstance(run, int) or isinstance(run, bool) or not 0 <= run < frame.quorum:
            raise RecordsError(f"run {run!r} is outside the quorum of {frame.quorum}")
        key = (record["input"], record["trial"], run)
        if key in seen:
            raise RecordsError(f"two records for input {key[0]!r}, trial {key[1]!r}, run {run!r}")
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
    finding, _ = _reading(frame, x, levels, samples)
    if _read_once(frame).get("carriage", "all-checks") == "all-checks":
        _hold(finding)
    return finding


def _reading(
    frame: Frame, x: str, levels: dict[str, str | None], samples: dict[str, list[str | None]]
) -> tuple[Finding, bool]:
    """The finding before the all-checks hold, and whether the reading got as
    far as the ablation (where each anchor alone is read)."""
    finding = Finding(input=x, category=UNRESOLVED, levels=levels)
    if _read_once(frame).get("outsideScope"):
        # The exclusion is the owner's; the trials do not test it, so only
        # its own check is open or settled here.
        scope = plain(_read_once(frame)["outsideScope"])  # the owner's words, on one line
        finding.evidence.append(f"declared outside scope ({scope})")
        check = _read_once(frame).get("scopeCheck")
        if check:
            finding.category = OUTSIDE
            finding.evidence.append(
                f"{plain(check['owner'])} checked the scope at {plain(check['encounter'])} "
                f"and found {plain(check['statement'])} ({plain(check['source'])})"
            )
        else:
            finding.obligations.append(
                "independent scope check (the exclusion is declared, not tested)"
            )
            if _read_once(frame).get("carriage", "all-checks") == "listed":
                finding.category = OUTSIDE
            else:
                finding.evidence.append("not outside scope until the owner's check is recorded")
        return finding, False
    # An input the input inversion does not turn was asked as it stands: its
    # level is a repeat's, never a stay
    read = dict(levels)
    if "input-inversion" in levels and not _turned(frame, x):
        del read["input-inversion"]
        finding.evidence.append("the input inversion does not reach this input")
    reached = _read(frame, finding, read, samples)
    # What the trials did not settle is listed whatever the category: a
    # category never hides an open check.
    base = levels.get("baseline")
    finding.obligations[:0] = _open_checks(frame, read, base)
    return finding, reached


def _turned(frame: Frame, x: str) -> bool:
    """Whether the frame's input inversion changes what input `x` asks."""
    from .interventions import rename

    mapping = tuple(
        sorted((_read_once(frame)["interventions"].get("inputInversion") or {}).items())
    )
    text = next(i["text"] for i in frame.inputs if i["id"] == x)
    return rename(text, mapping) != text


def _holding(category: str, obligations: list[str]) -> list[str]:
    """The open checks that keep a category from being named under
    all-checks: every carriage check for carried, discrimination for cooled."""
    if category == CARRIED:
        return obligations
    if category == COOLED:
        return [o for o in obligations if o.startswith("discrimination")]
    return []


def _hold(finding: Finding) -> None:
    """Under all-checks a category is named only when the checks it needs have
    passed (`_holding`)."""
    n = len(_holding(finding.category, finding.obligations))
    if finding.category == CARRIED and n:
        finding.category = UNRESOLVED
        finding.evidence.append(
            f"not carried while {n} carriage check{' is' if n == 1 else 's are'} open"
        )
    elif finding.category == COOLED and n:
        finding.category = UNRESOLVED
        finding.evidence.append("not cooled until a control shows the scorer can move")


def _read(
    frame: Frame,
    finding: Finding,
    levels: dict[str, str | None],
    samples: dict[str, list[str | None]],
) -> bool:
    """The rules, in order: the first that matches names the category. True
    when the reading got as far as the ablation."""
    say = finding.evidence.append
    # each anchor alone is evidence only: its level is read after the ablation
    missing = [t for t, v in levels.items() if v is None and not t.startswith("ablation-")]
    if missing:
        say(f"no agreed level in {', '.join(missing)}")
        return False
    base = levels["baseline"]
    split = _split(samples) if _read_once(frame)["standing"].get("stable") else None
    if split:
        say(split)
        return False
    if "repeat" in levels and levels["repeat"] != base:
        say(f"repeat gave {levels['repeat']}, baseline {base}, so this grain cannot tell")
        return False
    if "presentation" in levels and levels["presentation"] != base:
        finding.category = MISALIGNED
        say(f"presentation moved it {base} -> {levels['presentation']}")
        return False
    if "placement" in levels and levels["placement"] != base:
        finding.category = MISALIGNED
        say(f"placement moved it {base} -> {levels['placement']}")
        return False
    _ablated(frame, finding, levels, base)
    finding.evidence += _alone(frame, levels, base)
    return True


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
            say(f"ablation left it at {base}, and so did the control; the scorer cannot tell")
            finding.obligations.append(f"discrimination (the control left it at {base} too)")
        else:
            finding.category = COOLED
            say(f"ablation left it at {base}")
            if "control" in levels:
                say(f"the control moved it {base} -> {levels['control']}, so the scorer can tell")
            else:
                finding.obligations.append(
                    "discrimination (no control trial shows the scorer can move)"
                )
        for trial, _, _ in TURNS:
            if levels.get(trial) not in (None, base):
                name = trial.replace("-", " ")
                say(f"the {name} moved it {base} -> {levels[trial]}, though the ablation did not")
        # said whether or not the control moved: it is where else the decision rests
        if levels.get("cumulative") not in (None, base):
            say(
                f"the cumulative ablation moved it to {levels['cumulative']}; carried elsewhere too"
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
            say(f"{name} left it at {base}; the answer does not follow {follows}")
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
            say(f"{name} moved it {base} -> {levels[trial]}; the answer follows {follows}")
    if "bypass" in levels and _fallback(frame, levels, base) is None:
        say(f"bypass moved it {base} -> {levels['bypass']}, so no hidden fallback")
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
        return ["no anchor alone is needed; the others carry it without it"]
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
        return "no hidden fallback (no bypass trial was declared)"
    if bypass is None or base is None:
        return "no hidden fallback (the bypass has no agreed level to read against baseline)"
    if "bypass" in _read_once(frame)["allowed"]:
        opening = allowed_for(frame, base, "bypass")
        if bypass not in opening:
            return (
                f"no hidden fallback (bypass gave {bypass}, "
                f"not the designated opening, {' or '.join(opening)})"
            )
    if bypass == base:  # nothing moved, even where the opening names the baseline answer
        return f"no hidden fallback (bypass left it at {base})"
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
        open_.append("presentation invariance (no presentation trial was declared)")
    shams = sum(t.startswith("sham-") for t in levels)
    declared = _read_once(frame)["interventions"].get("sham")
    wanted = 0 if not declared else 1 if declared is True else declared["draws"]
    if not wanted:
        open_.append("specificity (no sham trial was declared)")
    elif shams < wanted:
        open_.append(
            f"specificity ({shams} sham trial(s), {wanted} declared; "
            "the body has no span left of the kind its shams draw from that is "
            "not an anchor, bypassed or a fallback)"
        )
    # A sham that moved it is listed whatever the category: misaligned and
    # cooled are read before the shams, and must not hide them.
    moved = [t for t, v in levels.items() if t.startswith("sham-") and v not in (None, base)]
    if moved and base is not None:
        open_.append(f"specificity ({', '.join(moved)} moved it too; the change is not specific)")
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
                f"monotonicity (the {trial} removes the anchors and more, yet left it at {base})"
            )
    for trial, _, _ in TURNS:
        if trial in levels and levels[trial] is None:
            open_.append(f"direction (the {trial.replace('-', ' ')} has no agreed level)")
    if not _read_once(frame).get("materialized"):
        open_.append(
            "materialization (the frame does not say the observation is "
            "the form the recipient receives)"
        )
    return open_
