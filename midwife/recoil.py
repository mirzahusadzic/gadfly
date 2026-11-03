"""Recoil: something found deep in a chain of frames, carried back up.

A frame knows where its text came from, by each span's `source`, and nothing
above that. A piece is a text found in a kept run, with a kind. It climbs from
the frame it was found in to each frame whose own text that frame quotes, and
on up, and fits any of those frames' holes of its kind; a frame with no such
hole passes it on, at no cost. The walk reads frames and makes no call.

A fit is asked again as a successor: the frame with the piece as a span and
its anchor. `successor` drafts it for the frame's author and writes nothing.
The successor's category is the gate: carried or coupled but misaligned, the
frame's own decision climbs on, as a piece of the kind the frame `offers`;
cooled or outside scope, the recoil is absorbed; unresolved, it stops with
the open check named. A successor that changes anything but its evidence asks
another question, and is a reframing opening, read against no category.

A successor is asked lightly, and again only while it must be (`until_firm`):
one run at a time, until the fixed rules read every input's category the same
in nearly every draw of the latest run's calls, and the same as the run before
it; then it disengages. Runs already kept count as runs made, so a frame
already firm is asked nothing.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from .errors import RecordsError, UsageError
from .frame import Frame
from .pipeline import calls_needed, run
from .stats import stability
from .types import Battery, Budget, Record
from .verdict import CARRIED, COOLED, MISALIGNED, OUTSIDE, UNRESOLVED, Finding, check_records
from .verdict import judge as judge_records
from .verdict import overall as overall_of

# What a successor may change while it fills a declared hole: its evidence,
# and how many calls read each trial. Any other key asks another question.
EVIDENCE = ("name", "baseline", "body", "anchors", "interventions", "allowed", "standing", "holes")
# What the successor's category does to the recoil.
GATE = {
    CARRIED: "climbs",
    MISALIGNED: "climbs",
    COOLED: "absorbed",
    OUTSIDE: "absorbed",
    UNRESOLVED: "stops",
}
FIRM = 0.95  # the share of draws that must read each input's category alike
MOST = 5  # runs `until_firm` makes at most


def sha256(text: str) -> str:
    """The SHA-256 of a text, as a span's `source` names it."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Piece:
    """A text found in a kept run, and the kind of hole it fills."""

    text: str
    kind: str

    @property
    def sha256(self) -> str:
        return sha256(self.text)


def found(frame: Frame, span: str) -> Piece:
    """A span of a frame as a piece of its kind."""
    for each in frame.spans:
        if each.id == span:
            return Piece(each.text, each.kind)
    raise UsageError(f"frame {frame.name!r} has no span {span!r}")


def decided(frame: Frame, label: str) -> Piece:
    """A frame's decision as the piece it climbs as: its name and the label
    it reads, of the kind the frame offers."""
    if frame.offers is None:
        raise UsageError(
            f"frame {frame.name!r} offers no kind for its decision to climb as",
            "name one under offers",
        )
    if label not in frame.labels:
        raise UsageError(f"frame {frame.name!r} has no label {label!r}")
    return Piece(f"{frame.name} reads {label}", frame.offers)


def _quoted(frame: Frame) -> set[str]:
    # the SHA-256 of each text the frame's spans quote by source
    return {span["source"]["sha256"] for span in frame.raw["body"]["spans"] if "source" in span}


def _made(frame: Frame) -> set[str]:
    # the SHA-256 of each text the frame holds as its own, quoting nothing
    return {sha256(span["text"]) for span in frame.raw["body"]["spans"] if "source" not in span}


@dataclass(frozen=True)
class Walk:
    """Where a piece fits above the frame it was found in: each frame it
    fits, with the holes it fits there; each frame it passed; and the
    frontier, each quoted text no frame given holds as its own."""

    piece: Piece
    fits: tuple[tuple[Frame, tuple[str, ...]], ...]
    passed: tuple[Frame, ...]
    frontier: tuple[str, ...]

    @property
    def complete(self) -> bool:
        """Every frame above was given: a walk with a frontier is never complete."""
        return not self.frontier

    def lines(self) -> list[dict[str, Any]]:
        """The walk as its record, one line each: every frame it fits, then
        every frame that passed it on, each in the order the walk reached it,
        then every text it could not follow."""
        head = {"piece": self.piece.sha256, "kind": self.piece.kind}
        reached = [
            {**head, "frame": frame.hash, "name": frame.name, "fits": list(holes)}
            for frame, holes in self.fits
        ] + [
            {**head, "frame": frame.hash, "name": frame.name, "passed": True}
            for frame in self.passed
        ]
        return reached + [{**head, "frontier": text} for text in self.frontier]


def walk(piece: Piece, start: Frame, frames: Iterable[Frame]) -> Walk:
    """Climb from the frame a piece was found in to each frame whose own text
    it quotes, and on up, visiting each frame once by its hash. A frame with
    holes of the piece's kind is a fit, and the piece climbs on past it,
    since it may fit at more than one height; any other frame passes it on.
    No call is made: the walk reads frames, and is given no battery."""
    frames = [frame for frame in frames if frame.hash != start.hash]
    makers: dict[str, list[Frame]] = {}
    for frame in frames:
        for text in _made(frame):
            makers.setdefault(text, []).append(frame)
    seen, fits, passed, frontier = {start.hash}, [], [], set()
    climbing = [start]
    while climbing:
        for text in sorted(_quoted(climbing.pop(0))):
            if text not in makers:
                frontier.add(text)
            for parent in makers.get(text, ()):
                if parent.hash in seen:
                    continue
                seen.add(parent.hash)
                holes = tuple(h["id"] for h in parent.holes if h["kind"] == piece.kind)
                if holes:
                    fits.append((parent, holes))
                else:
                    passed.append(parent)
                climbing.append(parent)
    return Walk(piece, tuple(fits), tuple(passed), tuple(sorted(frontier)))


def successor(frame: Frame, hole: str, piece: Piece, **changes: Any) -> dict[str, Any]:
    """A draft of the successor a fit is asked as, for the frame's author to
    finish and keep: the piece a span with the hole's id, quoting the text it
    was found as by its SHA-256, and the frame's one anchor; the hole closed.
    `changes` sets any other key, such as the trials that read the anchor.
    Nothing is written, and the draft is not checked: parse it."""
    holes = {h["id"]: h["kind"] for h in frame.holes}
    if hole not in holes:
        raise UsageError(f"frame {frame.name!r} has no hole {hole!r}")
    if holes[hole] != piece.kind:
        raise UsageError(
            f"hole {hole!r} is of kind {holes[hole]!r}, and the piece is of kind {piece.kind!r}"
        )
    raw = copy.deepcopy(frame.raw)
    span = {"id": hole, "text": piece.text, "kind": piece.kind}
    raw["body"]["spans"].append({**span, "source": {"sha256": piece.sha256}})
    raw["anchors"] = [hole]
    left = [h for h in raw["holes"] if h["id"] != hole]
    if left:
        raw["holes"] = left
    else:
        del raw["holes"]
    raw.update(copy.deepcopy(changes))
    return raw


def reframes(before: Frame, after: Frame) -> list[str]:
    """The keys a successor changed beyond its evidence, in sorted order:
    none when it only filled a declared hole, and asked it with its own
    trials and standing."""
    old, new = before.raw, after.raw
    keys = (set(old) | set(new)) - set(EVIDENCE)
    return sorted(key for key in keys if old.get(key) != new.get(key))


@dataclass(frozen=True)
class Firm:
    """What asking a frame until its verdict was firm made: every run, kept
    ones first, and the last cut short when it stopped short; the findings
    of the latest whole run; how often the draws of its calls read each
    input's category; whether that was firm; the calls made now; and why it
    stopped short, if it did."""

    frame: Frame
    runs: tuple[tuple[dict[str, Any], ...], ...]
    findings: tuple[Finding, ...]
    shares: dict[str, float]
    firm: bool
    made: int
    stopped: str | None = None

    @property
    def category(self) -> str | None:
        """The frame's one category over its inputs, in the latest run."""
        return overall_of(list(self.findings)).category if self.findings else None


def _charged(usage: dict[str, Any], cap: int) -> int:
    # what a call spent, as run charges it: what the battery reports, or the
    # cap when it reports no whole count
    used = usage.get("output_tokens")
    return cap if not isinstance(used, int) or isinstance(used, bool) else used


def _read(
    frame: Frame, runs: Sequence[Sequence[dict[str, Any]]], place: int
) -> tuple[list[Finding], dict]:
    # a run's findings, and its draws seeded by its place, as gadfly stats reads them
    findings = judge_records(frame, list(runs[place]))
    drawn = stability(frame, runs[: place + 1])[place]
    shares = {f.input: drawn.get(f.input, {}).get(f.category, 0.0) for f in findings}
    return findings, shares


def until_firm(
    frame: Frame,
    battery: Battery,
    budget: Budget,
    *,
    kept: Sequence[Iterable[Record | dict[str, Any]]] = (),
    firm: float = FIRM,
    most: int = MOST,
    on_record: Callable[[Record], None] = lambda record: None,
) -> Firm:
    """Ask a frame one whole run at a time, and disengage once its verdict
    is firm: every input's category read alike in at least `firm` of the
    draws of the latest run's calls (`midwife.stats.stability`), and the
    same as the run before it, if there was one. Each kept run, a list of
    one run's records, counts as a run made, in the order given, and only
    the latest decides, so a frame whose last kept run is firm is asked
    nothing. It reads at most `most` runs in all, kept ones included, and
    starts none the budget cannot cover whole, in calls and, when it caps
    them, in tokens at each call's cap: a run cut short is never firm."""
    if frame.quorum < 2:
        raise UsageError(
            f"frame {frame.name!r} asks each trial once, so a run has no calls to draw again",
            "give it a quorum of 2 or more",
        )
    if isinstance(firm, bool) or not isinstance(firm, int | float) or not 0 < firm <= 1:
        raise UsageError("firm is a share above 0, up to 1")
    if isinstance(most, bool) or not isinstance(most, int) or most < 1:
        raise UsageError("most is a whole number of runs, at least 1")
    runs: list[tuple[dict[str, Any], ...]] = []
    kept = list(kept)
    if len(kept) > most:
        raise UsageError(
            "kept holds more runs than most lets until_firm read",
            "give it the latest runs only, or raise most",
        )
    for records in kept:
        records = tuple(r.as_dict() if isinstance(r, Record) else r for r in records)
        if not records:
            raise RecordsError("a kept run holds no records", "give each run's records as a list")
        check_records(frame, list(records))  # this frame's, and each call once
        runs.append(records)
    each, made, spent = calls_needed(frame), 0, 0
    if any(len(records) != each for records in runs):
        raise RecordsError(
            "a kept run is not whole, so its verdict cannot be read as firm",
            "give whole runs only, and leave out one that stopped short",
        )
    findings: list[Finding] = []
    shares: dict[str, float] = {}
    before: dict[str, str] | None = None
    stopped = None
    for place in range(most):
        if place >= len(runs):
            if budget.calls - made < each:
                stopped = f"the budget covers no further run of {each} calls"
                break
            tokens = None if budget.tokens is None else budget.tokens - spent
            if tokens is not None and tokens < each * budget.output_tokens_per_call:
                stopped = f"the token budget covers no further run of {each} calls"
                break
            result = run(
                frame,
                battery,
                Budget(each, budget.output_tokens_per_call, tokens),
                on_record=on_record,
            )
            runs.append(tuple(record.as_dict() for record in result.records))
            made += len(result.records)
            spent += sum(
                _charged(record.usage, budget.output_tokens_per_call) for record in result.records
            )
            if result.stopped:
                stopped = result.stopped
                break
        findings, shares = _read(frame, runs, place)
        read = {f.input: f.category for f in findings}
        alike = all(share >= firm for share in shares.values()) and before in (None, read)
        if alike and place == len(runs) - 1:  # a later kept run decides instead
            return Firm(frame, tuple(runs), tuple(findings), shares, True, made)
        before = read
    return Firm(frame, tuple(runs), tuple(findings), shares, False, made, stopped)


@dataclass(frozen=True)
class Recoil:
    """What a fit did: the gate (climbs, absorbed, stops, or reframing), the
    successor's category, what climbs on from it, what it changed when it
    reframes, and the open check when it stops."""

    gate: str
    category: str | None = None
    climbs: tuple[Piece, ...] = ()
    changed: tuple[str, ...] = ()
    open: str | None = None


def gate(before: Frame, after: Frame, asked: Firm | None = None) -> Recoil:
    """The gate a fit sets. A successor that changed more than its evidence
    is a reframing, read against no category and asked nothing. Any other is
    read from its own runs (`until_firm`): one whose verdict never came out
    firm stops, with why named; a firm one sets the gate by its category,
    and when it climbs, its decision climbs on as one piece for each label
    its inputs' baselines read, if the frame offers a kind."""
    changed = reframes(before, after)
    if changed:
        return Recoil("reframing", changed=tuple(changed))
    if asked is None or asked.frame.hash != after.hash:
        raise UsageError("a successor that asks the same question is read from its own runs")
    if not asked.firm:
        why = asked.stopped or f"its verdict was not firm after {len(asked.runs)} runs"
        return Recoil("stops", asked.category, open=why)
    category = asked.category  # a firm run read a finding for every input
    gated = GATE[category] if category else "stops"
    climbs: tuple[Piece, ...] = ()
    if gated == "climbs" and after.offers is not None:
        labels = sorted({f.levels.get("baseline") for f in asked.findings} - {None})
        climbs = tuple(decided(after, label) for label in labels)
    return Recoil(gated, category, climbs)
