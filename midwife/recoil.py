"""Recoil: something found deep in a chain of frames, carried back up.

A frame knows where its text came from, by each span's `source`, and nothing
above that. A piece is a text found in a kept run, with a kind. It climbs from
the frame it was found in to each frame whose own text that frame quotes, and
on up, and fits any of those frames' holes of its kind; a frame with no such
hole passes it on, at no cost. A hole may defer: its fit is listed, kept
and not asked. Given a crossing's records, each artefact it made is text
that frame made, so a frame quoting the artefact climbs to the crossing.
Sideways, the piece is also offered one step aside, to the frames quoting
a text the frame it was found in quotes, and climbs on from each.
The walk reads frames and makes no call; given vectors, it orders the fits
by cosine, and given a budget, it counts each fit's calls before the first
and lists those it cannot cover.

A fit is asked again as a successor: the frame with the piece as a span and
its anchor. `successor` drafts it for the frame's author and writes nothing.
The successor's category is the gate: carried or coupled but misaligned, the
frame's own decision climbs on, as a piece of the kind the frame `offers`;
cooled or outside scope, the recoil is absorbed; unresolved, it stops with
the open check named. A successor that changes anything but its evidence, or
any hole but closing the one it fills, asks another question, and is a
reframing opening, read against no category.

A successor is asked lightly, and again only while it must be (`until_firm`):
one run at a time, until the fixed rules read every input's category the same
in nearly every draw of the latest run's calls, and the same as the run before
it; then it disengages. Runs already kept count as runs made, so a frame
already firm is asked nothing.

Each step is also a command: `gadfly walk`, `gadfly successor`, `gadfly firm`
and `gadfly gate`.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import warnings
from collections import deque
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from .errors import GadflyError, RecordsError, StoppedWarning, UsageError, is_plain, quoted
from .frame import SALIENCE, Frame, _read_once, digest, parse
from .interventions import plan, prompt
from .pipeline import _check_parallel, _usage, calls_needed, run
from .stats import stability
from .types import Battery, Budget, Record
from .verdict import (
    CARRIED,
    COOLED,
    MISALIGNED,
    OUTSIDE,
    UNRESOLVED,
    Finding,
    _check_shape,
    check_records,
)
from .verdict import judge as judge_records
from .verdict import overall as overall_of

# What a successor may change while it fills a declared hole: its evidence,
# and how many calls read each trial. Any other key asks another question,
# and so does any change to its holes but closing the one it fills.
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
# A vector's key: the SHA-256 of the exact text it stands for, as a span's
# source names it, and the id of the space it was made in
SHA256 = re.compile(r"[0-9a-f]{64}")
VECTOR_KEYS = {"text", "space", "values"}


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
class Vectors:
    """Whole-text vectors a caller acquired: each a tuple of floats, keyed by
    the SHA-256 of the exact text it stands for and the opaque id of the
    space it was made in; and the SHA-256 of what they were read from."""

    values: Mapping[tuple[str, str], tuple[float, ...]]
    sha256: str

    @property
    def spaces(self) -> tuple[str, ...]:
        """Each space a vector names, in sorted order."""
        return tuple(sorted({space for _, space in self.values}))


def read_vectors(data: bytes | str, *, path: str | None = None) -> Vectors:
    """Vectors from JSON Lines, one line each,
    `{"text": SHA256, "space": ID, "values": [...]}`, as a caller acquired
    them: whole texts only, one vector a text in each space. Spaces may mix,
    and a walk compares two vectors only within one. A text named twice in
    one space refuses them all, even with the same values, and a value that
    is not finite is kept, to give no order where it is read. A refusal
    names the file at `path` they were read from, `-` standard input."""
    try:  # a str holding a lone surrogate is no text a file could hold
        raw = data.encode("utf-8") if isinstance(data, str) else bytes(data)
        text = raw.decode("utf-8")
    except UnicodeError:
        raise UsageError(f"{_named(path)} is not UTF-8 text") from None
    values: dict[tuple[str, str], tuple[float, ...]] = {}
    lines: dict[tuple[str, str], int] = {}
    for line, written in enumerate(text.split("\n"), 1):
        if not written.strip():
            continue
        try:
            entry = json.loads(written)
        except (ValueError, RecursionError):
            raise UsageError(f"{_named(path)} cannot be read as JSON at line {line}") from None
        if not (isinstance(entry, dict) and set(entry) == VECTOR_KEYS):
            raise UsageError(
                f"{_named(path)} holds a vector that is not {{text, space, values}} at line {line}"
            )
        key, space, numbers = entry["text"], entry["space"], entry["values"]
        if not (isinstance(key, str) and SHA256.fullmatch(key)):
            raise UsageError(
                f"{_named(path)} keys a vector by {key!r} at line {line}, which is no SHA-256",
                "text is the SHA-256 of the exact text, 64 lowercase hex digits",
            )
        if not (isinstance(space, str) and space and is_plain(space) and _utf8(space)):
            raise UsageError(
                f"{_named(path)} names space {space!r} at line {line}, not one plain name"
            )
        if not (
            isinstance(numbers, list)
            and numbers
            and all(isinstance(x, int | float) and not isinstance(x, bool) for x in numbers)
        ):
            raise UsageError(
                f"{_named(path)} holds values that are not a list of numbers at line {line}"
            )
        if (key, space) in lines:
            at = lines[key, space]
            raise UsageError(
                f"{_named(path)} holds text {key!r} in space {space!r} twice, "
                f"at lines {at} and {line}",
                "a text has one vector in a space; even the same values twice are refused",
            )
        lines[key, space] = line
        values[key, space] = tuple(_float(x) for x in numbers)
    return Vectors(values, hashlib.sha256(raw).hexdigest())


def _utf8(text: str) -> bool:
    # whether a text can be printed and written: an escaped lone surrogate
    # reads as JSON, and is no UTF-8 text
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _named(path: str | None) -> str:
    # the vectors as a refusal names them: by the file they were read from
    if path is None:
        return "the text given"
    return "standard input" if path == "-" else f"file {path!r}"


def _float(number: int | float) -> float:
    # a whole number past a float's range is no finite value, and gives no order
    try:
        return float(number)
    except OverflowError:
        return math.inf


@dataclass(frozen=True)
class Fit:
    """A hole a piece fits, as a walk would ask it: the frame and the hole;
    when the walk was given vectors, its cosine to the piece, or why it has
    none, kept in its place; when it was given a budget, the most calls
    asking its successor until firm can make, and whether the budget covers
    them; when the walk reached the frame through an artefact it made, the
    trial and input of each record that made it; and whether it reached the
    frame sideways, as a sibling of the frame the piece was found in."""

    frame: Frame
    hole: str
    cosine: float | None = None
    unordered: str | None = None
    calls: int | None = None
    asked: bool | None = None
    made: tuple[tuple[str, str], ...] = ()
    sideways: bool = False


@dataclass(frozen=True)
class Walk:
    """Where a piece fits above the frame it was found in: each frame it
    fits, with the holes it fits there that are considered; each frame it
    passed; the frontier, each quoted text no frame given holds as its own;
    each frame with the holes it fits there that defer, kept and not asked;
    every considered fit, one hole each, in the order it would be asked;
    the space its fits were ordered by and the SHA-256 of the vectors, when
    it was given them; the budget in calls and the most runs a fit, when one
    was given; for each frame it reached through an artefact the frame
    made, by its hash, the trial and input of each record that made it; and
    each frame it reached sideways, a sibling of the frame it started from."""

    piece: Piece
    fits: tuple[tuple[Frame, tuple[str, ...]], ...]
    passed: tuple[Frame, ...]
    frontier: tuple[str, ...]
    deferred: tuple[tuple[Frame, tuple[str, ...]], ...] = ()
    order: tuple[Fit, ...] = ()
    budget: int | None = None
    most: int | None = None
    space: str | None = None
    vectors: str | None = None
    made: Mapping[str, tuple[tuple[str, str], ...]] = field(default_factory=dict)
    siblings: tuple[Frame, ...] = ()

    def __post_init__(self) -> None:
        # a walk made by hand, as 0.10.0 made one, names its fits and no order:
        # each hole is then a fit in the order the fits name them
        if self.fits and not self.order:
            order = tuple(Fit(frame, hole) for frame, holes in self.fits for hole in holes)
            object.__setattr__(self, "order", order)

    @property
    def complete(self) -> bool:
        """Every frame above was given: a walk with a frontier is never complete."""
        return not self.frontier

    @property
    def unasked(self) -> tuple[Fit, ...]:
        """Each fit the budget does not cover, in the order it would be asked."""
        return tuple(fit for fit in self.order if fit.asked is False)

    def lines(self) -> list[dict[str, Any]]:
        """The walk as its record, one line each: every hole it fits, in the
        order it would be asked, with its cosine or why it has none when it
        was ordered, and its calls and whether the budget asks it when there
        is one; then every frame whose holes of its kind defer, then every
        frame that passed it on, each in the order the walk reached it; then
        every text it could not follow. Each line names the space and the
        vectors it was ordered by, and the budget, when there were any, and
        each frame line the records that made the artefact it was reached
        through, and whether it was reached sideways."""
        head: dict[str, Any] = {"piece": self.piece.sha256, "kind": self.piece.kind}
        if self.space is not None:
            head |= {"space": self.space, "vectors": self.vectors}
        if self.budget is not None:
            head |= {"budget": self.budget, "most": self.most}
        aside = {sibling.hash for sibling in self.siblings}  # each looked up once a line
        fitted = []
        for fit in self.order:
            line = {**head, "frame": fit.frame.hash, "name": fit.frame.name, "fits": [fit.hole]}
            if self.space is not None:
                line |= {"cosine": fit.cosine} if fit.unordered is None else {}
                line |= {} if fit.unordered is None else {"unordered": fit.unordered}
            if fit.calls is not None:
                line |= {"calls": fit.calls, "asked": fit.asked}
            fitted.append(line | self._through(fit.frame, aside))
        reached = (
            fitted
            + [
                {**head, "frame": frame.hash, "name": frame.name, "deferred": list(holes)}
                | self._through(frame, aside)
                for frame, holes in self.deferred
            ]
            + [
                {**head, "frame": frame.hash, "name": frame.name, "passed": True}
                | self._through(frame, aside)
                for frame in self.passed
            ]
        )
        return reached + [{**head, "frontier": text} for text in self.frontier]

    def _through(self, frame: Frame, aside: set[str]) -> dict[str, Any]:
        # how the walk reached a frame: sideways, or through an artefact it made
        how: dict[str, Any] = {"sideways": True} if frame.hash in aside else {}
        if frame.hash in self.made:
            how["made"] = [{"trial": t, "input": x} for t, x in self.made[frame.hash]]
        return how


def walk(
    piece: Piece,
    start: Frame,
    frames: Iterable[Frame],
    *,
    made: Iterable[Iterable[Record | dict[str, Any]]] = (),
    sideways: bool = False,
    vectors: Vectors | None = None,
    space: str | None = None,
    calls: int | None = None,
    most: int = MOST,
) -> Walk:
    """Climb from the frame a piece was found in to each frame whose own text
    it quotes, and on up, visiting each frame once by its hash. A frame with
    holes of the piece's kind is a fit, and the piece climbs on past it,
    since it may fit at more than one height; any other frame passes it on.
    A hole whose salience is defer is listed under `deferred`, its fit kept
    and not asked, never dropped.

    `made` holds runs of crossing frames given, each a list of its records,
    each checked against its frame first; a run cut short still links what
    its records made. Each artefact a record says its maker made is text
    that frame made, so a frame quoting the artefact by `source` climbs to
    the crossing, and the walk names the trial and input of each record
    that made it.

    `sideways` offers the piece one step aside too, from the start frame
    only: to each frame given that quotes, by `source`, a text the start
    frame quotes. Siblings come from that fixed rule, never from nearness,
    so none is dropped; each then climbs as usual, and is not followed
    sideways again.

    Each considered hole is a fit in `order`, in the order the walk reached
    its frame and the frame lists its holes. Given `vectors`, the fits are
    ordered by the cosine of the piece's vector to the vector of what each
    hole is read for, its `about`, both in one `space`, highest first, and
    ties by frame hash. A fit with no cosine keeps its place, with why, and
    the others are sorted among theirs, so no fit takes a default score and
    a vector only orders.

    Given `calls`, each fit is counted before the first call, as
    `calls_until_firm` counts its successor as drafted over at most `most`
    runs, and the budget asks the fits in order up to the first it cannot
    cover: that one and every one after it are listed as not asked, so no
    fit is asked before an earlier one. No call is made: the walk reads
    frames, and is given no battery."""
    if space is not None and vectors is None:
        raise UsageError(
            "space is given without vectors", "name the space to order by among the vectors given"
        )
    _check_budget(calls, most)
    given = {frame.hash: frame for frame in frames}
    given[start.hash] = start  # its own texts are held too, though it is never its own parent
    makers: dict[str, dict[str, Frame]] = {}
    for frame in given.values():
        for text in _made(frame):
            makers.setdefault(text, {})[frame.hash] = frame
    artefacts = _artefacts(given, made)
    for text, by in artefacts.items():
        for name in by:
            makers.setdefault(text, {})[name] = given[name]
    through: dict[str, tuple[tuple[str, str], ...]] = {}
    seen, fits, passed, deferred, frontier = {start.hash}, [], [], [], set()
    siblings: list[Frame] = []
    followed: set[str] = set()  # a text once followed has every maker of it seen
    climbing = deque([start])  # drained from the front: a list would shift every frame left

    def offer(frame: Frame) -> None:
        # the piece offered to a frame reached: a fit, deferred, or passed on
        seen.add(frame.hash)
        kind = [h for h in frame.holes if h["kind"] == piece.kind]
        asked = tuple(h["id"] for h in kind if _salience(h) == "consider")
        held = tuple(h["id"] for h in kind if _salience(h) == "defer")
        if asked:
            fits.append((frame, asked))
        if held:
            deferred.append((frame, held))
        if not kind:
            passed.append(frame)
        climbing.append(frame)

    while climbing:
        frame = climbing.popleft()
        for text in sorted(_quoted(frame) - followed):
            followed.add(text)
            if text not in makers:
                frontier.add(text)
            for parent in makers.get(text, {}).values():
                if parent.hash in seen:
                    continue
                if parent.hash in artefacts.get(text, {}):
                    through[parent.hash] = tuple(artefacts[text][parent.hash])
                offer(parent)
        if sideways and frame is start:  # one step aside, from the start alone
            for sibling in _siblings(start, given):
                if sibling.hash not in seen:
                    siblings.append(sibling)
                    offer(sibling)
    aside = {sibling.hash for sibling in siblings}
    order = tuple(
        Fit(frame, hole, made=through.get(frame.hash, ()), sideways=frame.hash in aside)
        for frame, holes in fits
        for hole in holes
    )
    if vectors is not None:
        space = _space(vectors, space)
        order = _ordered(order, piece, vectors, space)
    if calls is not None:
        order = _budgeted(order, piece, calls, most)
    return Walk(
        piece,
        tuple(fits),
        tuple(passed),
        tuple(sorted(frontier)),
        tuple(deferred),
        order,
        calls,
        None if calls is None else most,
        space,
        None if vectors is None else vectors.sha256,
        through,
        tuple(siblings),
    )


def _siblings(start: Frame, given: Mapping[str, Frame]) -> list[Frame]:
    # each frame given that quotes, by source, a text the start quotes: by
    # that text's hash, then as given, once each
    quoters: dict[str, list[Frame]] = {}
    for frame in given.values():
        for text in _quoted(frame):
            quoters.setdefault(text, []).append(frame)
    found = {}
    for text in sorted(_quoted(start)):
        for frame in quoters.get(text, ()):
            if frame.hash != start.hash:
                found.setdefault(frame.hash, frame)
    return list(found.values())


def _artefacts(
    given: Mapping[str, Frame], made: Iterable[Iterable[Record | dict[str, Any]]]
) -> dict[str, dict[str, dict[tuple[str, str], None]]]:
    # each artefact's SHA-256, the crossing frame that made it, and the trial
    # and input of each record that did, once each, in the records' order;
    # each run's records checked against their frame as a kept run is
    artefacts: dict[str, dict[str, dict[tuple[str, str], None]]] = {}
    for run_ in made:
        if isinstance(run_, dict | Record):
            raise UsageError(
                "made holds a record where a run belongs",
                "give each run's records as a list, made=[records]",
            )
        records = [r.as_dict() if isinstance(r, Record) else r for r in run_]
        if not records:
            raise RecordsError("a made run holds no records", "give each run's records as a list")
        frames: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            _check_shape(record)
            frames.setdefault(record["frame"], []).append(record)
        for name, kept in frames.items():
            if name not in given:
                raise RecordsError(
                    f"a made record names frame {name!r}, which is not among the frames given",
                    "give the crossing frame whose records they are",
                )
            frame = given[name]
            if frame.battery.get("kind") != "crossing":  # its raw is a reader's, made by none
                raise RecordsError(
                    f"frame {frame.name!r} is no crossing, so its records made no artefact",
                    "give the records of a crossing frame, whose battery kind is crossing",
                )
            _own(frame, kept)
            texts = [(_artefact(record), record) for record in kept]
            if not any(text for text, _ in texts):
                raise RecordsError(
                    f"the records of frame {frame.name!r} hold no artefact its maker made",
                    "give the records of a crossing frame, whose maker made one for each call",
                )
            for text, record in texts:  # a dict keeps each pair once, in order, by hash
                if text:
                    pairs = artefacts.setdefault(text, {}).setdefault(name, {})
                    pairs[record["trial"], record["input"]] = None
    return artefacts


def _artefact(record: dict[str, Any]) -> str | None:
    # the SHA-256 of the artefact a crossing's record says its maker made
    try:
        kept = json.loads(record["raw"])
    except (ValueError, RecursionError):  # not JSON, or deeper than Python reads
        return None
    made = kept.get("made") if isinstance(kept, dict) else None
    text = made.get("sha256") if isinstance(made, dict) else None
    return text if isinstance(text, str) and SHA256.fullmatch(text) else None


def _space(vectors: Vectors, space: str | None) -> str:
    # the one space a walk orders by: the one named, or the only one given
    spaces = vectors.spaces
    if not spaces:
        raise UsageError("the vectors hold no vector", "give vectors, or leave them out")
    if space is None:
        many = len(spaces)
        if many > 1:
            raise UsageError(
                f"the vectors hold {many} spaces, {quoted(spaces)}",
                "name the one to order by, since a cosine compares two vectors of one space only",
            )
        return spaces[0]
    if space not in spaces:
        raise UsageError(
            f"the vectors hold no vector in space {space!r}", f"they hold {quoted(spaces)}"
        )
    return space


def _ordered(order: tuple[Fit, ...], piece: Piece, vectors: Vectors, space: str) -> tuple[Fit, ...]:
    # each fit's cosine, or why it has none; the fits with one sorted among
    # the places they hold, highest first and ties by frame hash, and the
    # rest left where the walk put them
    near = vectors.values.get((piece.sha256, space))
    abouts: dict[str, dict[str, str | None]] = {}  # each frame's holes, read once
    read = []
    for fit in order:
        if fit.frame.hash not in abouts:
            holes = _read_once(fit.frame).get("holes", ())
            abouts[fit.frame.hash] = {hole["id"]: hole.get("about") for hole in holes}
        about = abouts[fit.frame.hash][fit.hole]
        if near is None:
            cosine, why = None, "the piece has no vector in this space"
        elif about is None:
            cosine, why = None, "the hole says nothing under about"
        elif (sha256(about), space) not in vectors.values:
            cosine, why = None, "what the hole is read for has no vector in this space"
        else:
            cosine, why = _cosine(near, vectors.values[sha256(about), space])
        read.append(replace(fit, cosine=cosine, unordered=why))
    places = [i for i, fit in enumerate(read) if fit.cosine is not None]
    ranked = sorted(places, key=lambda i: (-read[i].cosine, read[i].frame.hash, i))
    ordered = list(read)
    for place, i in zip(places, ranked, strict=True):
        ordered[place] = read[i]
    return tuple(ordered)


def _cosine(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float | None, str | None]:
    # dot / (|a| |b|), each sum exact with fsum, or why there is none
    if len(a) != len(b):
        return None, f"its vector has {len(b)} values, and the piece's {len(a)}"
    if not all(map(math.isfinite, a + b)):
        return None, "a vector holds a value that is not finite"
    try:
        dot = math.fsum(x * y for x, y in zip(a, b, strict=True))
        norms = math.sqrt(math.fsum(x * x for x in a)) * math.sqrt(math.fsum(y * y for y in b))
    except (OverflowError, ValueError):
        return None, "its cosine overflows"
    if norms == 0:
        return None, "a vector has no length"
    cosine = dot / norms
    if not (math.isfinite(dot) and math.isfinite(norms) and math.isfinite(cosine)):
        return None, "its cosine overflows"
    return cosine, None


def _check_budget(calls: int | None, most: int) -> None:
    # a walk's budget, refused before anything is read: the calls, a whole
    # number of at least 1 when given, and the most runs each fit may take,
    # a whole number of at least 1 whether or not calls are
    if calls is not None and (isinstance(calls, bool) or not isinstance(calls, int) or calls < 1):
        raise UsageError("a walk's budget is a whole number of calls, at least 1")
    if isinstance(most, bool) or not isinstance(most, int) or most < 1:
        raise UsageError("most is a whole number of runs, at least 1")


def _budgeted(order: tuple[Fit, ...], piece: Piece, calls: int, most: int) -> tuple[Fit, ...]:
    # each fit's calls until firm, on its successor as drafted, and whether
    # the calls left cover them: up to the first fit they cannot, and none
    # after it, so the order the walk asks in is never jumped
    left, covering, counted = calls, True, []
    for fit in order:
        try:
            cost = calls_until_firm(parse(successor(fit.frame, fit.hole, piece)), most=most)
        except GadflyError as error:  # the frame's own refusal, said where the walk met it
            error.add_note(
                f"the walk's budget counts the successor of frame {fit.frame.name!r} "
                f"with hole {fit.hole!r} filled, as drafted"
            )
            raise
        covering = covering and cost <= left
        left -= cost if covering else 0
        counted.append(replace(fit, calls=cost, asked=covering))
    return tuple(counted)


def _salience(hole: dict[str, str]) -> str:
    # whether a walk asks a fit of a hole: consider, unless it defers
    return hole.get("salience", SALIENCE[0])


def successor(
    frame: Frame, hole: str, piece: Piece, *, after: str | None = None, **changes: Any
) -> dict[str, Any]:
    """A draft of the successor a fit is asked as, for the frame's author to
    finish and keep: the piece a span with the hole's id, quoting the text it
    was found as by its SHA-256, and the frame's one anchor; the hole closed.
    The piece's span comes last, or right after the span `after` names, as
    the line it amends; either way its ablation is the frame's body, byte
    for byte. `changes` sets any other key, such as the trials that read the
    anchor. Nothing is written, and the draft is not checked: parse it."""
    holes = {h["id"]: h["kind"] for h in frame.holes}
    if hole not in holes:
        raise UsageError(f"frame {frame.name!r} has no hole {hole!r}")
    if holes[hole] != piece.kind:
        raise UsageError(
            f"hole {hole!r} is of kind {holes[hole]!r}, and the piece is of kind {piece.kind!r}"
        )
    raw = copy.deepcopy(frame.raw)
    spans = raw["body"]["spans"]
    at = len(spans)
    if after is not None:
        ids = [each["id"] for each in spans]
        if after not in ids:
            raise UsageError(
                f"frame {frame.name!r} has no span {after!r} to place the piece after",
                "name one of its spans, the line the piece amends",
            )
        at = ids.index(after) + 1
    span = {"id": hole, "text": piece.text, "kind": piece.kind}
    spans.insert(at, {**span, "source": {"sha256": piece.sha256}})
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
    trials and standing. Its holes are the frame's, in any order, less at
    most the one it filled, now a span of the hole's kind: a hole added,
    changed, dropped unfilled or closed by a span of another kind changes
    what the frame can take in, and lists `holes`."""
    old, new = before.raw, after.raw
    keys = (set(old) | set(new)) - set(EVIDENCE)
    changed = {key for key in keys if old.get(key) != new.get(key)}
    if not _closes_one(before, after):
        changed.add("holes")
    return sorted(changed)


def _closes_one(before: Frame, after: Frame) -> bool:
    # the holes as they were, or less the one hole now filled by a span of
    # its kind; a hole's id is unique, so each is looked up once by it
    old = {hole["id"]: hole for hole in before.raw.get("holes", [])}
    new = {hole["id"]: hole for hole in after.raw.get("holes", [])}
    if any(old.get(name) != hole for name, hole in new.items()):
        return False  # a hole added, or changed
    closed = [hole for name, hole in old.items() if name not in new]
    if not closed:
        return True
    kinds = {span.id: span.kind for span in after.spans}
    return len(closed) == 1 and kinds.get(closed[0]["id"]) == closed[0]["kind"]


@dataclass(frozen=True)
class Firm:
    """What asking a frame until its verdict was firm made: every run, kept
    ones first, and the last cut short when it stopped short; the findings
    of the latest whole run; how often the draws of its calls read each
    input's category; whether that was firm; the calls made now; and why it
    stopped short, if it did. `usage` sums each whole count the calls made
    now reported, such as `input_tokens` and `output_tokens`, by name; a
    count no call reported is absent, never a zero."""

    frame: Frame
    runs: tuple[tuple[dict[str, Any], ...], ...]
    findings: tuple[Finding, ...]
    shares: dict[str, float]
    firm: bool
    made: int
    stopped: str | None = None
    usage: dict[str, int] = field(default_factory=dict)

    @property
    def category(self) -> str | None:
        """The frame's one category over its inputs, in the latest run."""
        return overall_of(list(self.findings)).category if self.findings else None


def _own(frame: Frame, records: Sequence[dict[str, Any]]) -> None:
    # a kept run is this frame's, each call once, each trial's body and each
    # call's prompt the ones its plan makes, as run checks what it is kept
    trials = {trial.id: trial for trial in plan(frame)}
    check_records(frame, list(records), {t: trial.body_hash for t, trial in trials.items()})
    inputs = {x["id"]: x for x in frame.inputs}
    for record in records:
        asked = prompt(frame, trials[record["trial"]], inputs[record["input"]])
        if record["prompt"] != digest(asked):
            raise RecordsError(
                f"a kept record of trial {record['trial']!r} was made from another prompt"
            )


def _charged(usage: dict[str, Any], cap: int) -> int:
    # what a call spent, as run charges it: what the battery reports, or the
    # cap when it reports no whole count
    used = usage.get("output_tokens")
    return cap if not isinstance(used, int) or isinstance(used, bool) else used


def _read(
    frame: Frame, runs: Sequence[Sequence[dict[str, Any]]], place: int
) -> tuple[list[Finding], dict]:
    # a run's findings, and its draws seeded by its place, as gadfly stats
    # reads them: that run alone, so each place is drawn once
    findings = judge_records(frame, list(runs[place]))
    [drawn] = stability(frame, [runs[place]], start=place)
    shares = {f.input: drawn.get(f.input, {}).get(f.category, 0.0) for f in findings}
    return findings, shares


def until_firm(
    frame: Frame,
    battery: Battery | None,
    budget: Budget,
    *,
    kept: Sequence[Iterable[Record | dict[str, Any]]] = (),
    firm: float = FIRM,
    most: int = MOST,
    on_record: Callable[[Record], None] = lambda record: None,
    parallel: int = 1,
) -> Firm:
    """Ask a frame one whole run at a time, and disengage once its verdict
    is firm: every input's category read alike in at least `firm` of the
    draws of the latest run's calls (`midwife.stats.stability`), and the
    same as the run before it, if there was one. Each kept run, a list of
    one run's records, counts as a run made, in the order given, and only
    the latest decides, so a frame whose last kept run is firm is asked
    nothing. It reads at most `most` runs in all, kept ones included, and
    starts none the budget cannot cover whole, in calls and, when it caps
    them, in tokens at each call's cap: a run cut short is never firm, and
    a stop for the budget is a `StoppedWarning`, as a run's is. With no
    battery, it reads the kept runs alone and asks nothing. `parallel`
    makes up to that many calls at once within each run, as `run`'s does;
    the runs stay one after another, since each decides whether the next
    is asked."""
    _asked_again(frame)
    _check_parallel(parallel, battery)
    if isinstance(firm, bool) or not isinstance(firm, int | float) or not 0 < firm <= 1:
        raise UsageError("firm is a share above 0, up to 1")
    runs = _kept(frame, kept, most)
    each, made, spent = calls_needed(frame), 0, 0
    made_now: list[Record] = []
    findings: list[Finding] = []
    shares: dict[str, float] = {}
    before: dict[str, str] | None = None
    stopped = None
    for place in range(most):
        if place >= len(runs):
            if battery is None:  # the kept runs alone are read
                break
            tokens = None if budget.tokens is None else budget.tokens - spent
            if budget.calls - made < each:
                stopped = f"the budget covers no further run of {each} calls"
            elif tokens is not None and tokens < each * budget.output_tokens_per_call:
                stopped = f"the token budget covers no further run of {each} calls"
            if stopped:  # nothing passes in silence: said as a run's own stop is
                many = len(runs)
                warnings.warn(
                    StoppedWarning(
                        f"asking stopped after {many} of at most {most} runs, "
                        f"its verdict not yet firm; {stopped}"
                    ),
                    stacklevel=2,
                )
                break
            result = run(
                frame,
                battery,
                Budget(each, budget.output_tokens_per_call, tokens),
                on_record=on_record,
                parallel=parallel,
            )
            runs.append(tuple(record.as_dict() for record in result.records))
            made += len(result.records)
            made_now.extend(result.records)
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
            return Firm(
                frame, tuple(runs), tuple(findings), shares, True, made, usage=_usage(made_now)
            )
        before = read
    return Firm(frame, tuple(runs), tuple(findings), shares, False, made, stopped, _usage(made_now))


def calls_until_firm(
    frame: Frame,
    *,
    kept: Sequence[Iterable[Record | dict[str, Any]]] = (),
    most: int = MOST,
) -> int:
    """The most calls `until_firm` can make on a frame, counted before its
    first: a whole run's for each run `most` allows beyond the runs `kept`
    holds. It is refused as `until_firm` refuses the frame or its kept
    runs, and is a ceiling: asking stops sooner once a run is firm, and
    makes no call when the latest kept run is."""
    _asked_again(frame)
    runs = _kept(frame, kept, most)  # its checks first, in until_firm's order
    return calls_needed(frame) * (most - len(runs))


def _asked_again(frame: Frame) -> None:
    # a run whose trials are each asked once has no calls to draw again
    if frame.quorum < 2:
        raise UsageError(
            f"frame {frame.name!r} asks each trial once, so a run has no calls to draw again",
            "give it a quorum of 2 or more",
        )


def _kept(
    frame: Frame, kept: Sequence[Iterable[Record | dict[str, Any]]], most: int
) -> list[tuple[dict[str, Any], ...]]:
    # the kept runs, each this frame's own and whole, no more than most reads
    if isinstance(most, bool) or not isinstance(most, int) or most < 1:
        raise UsageError("most is a whole number of runs, at least 1")
    kept = list(kept)
    if len(kept) > most:
        raise UsageError(
            "kept holds more runs than most lets until_firm read",
            "give it the latest runs only, or raise most",
        )
    runs = []
    for records in kept:
        records = tuple(r.as_dict() if isinstance(r, Record) else r for r in records)
        if not records:
            raise RecordsError("a kept run holds no records", "give each run's records as a list")
        _own(frame, records)
        runs.append(records)
    if any(len(records) != calls_needed(frame) for records in runs):
        raise RecordsError(
            "a kept run is not whole, so its verdict cannot be read as firm",
            "give whole runs only, and leave out one that stopped short",
        )
    return runs


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
    and a firm unresolved one stops with its open check named,
    and when it climbs, its decision climbs on as one piece for each label
    its inputs' baselines read, if the frame offers a kind."""
    changed = reframes(before, after)
    if changed:
        return Recoil("reframing", changed=tuple(changed))
    if asked is None or asked.frame.hash != after.hash:
        raise UsageError("a successor that asks the same question is read from its own runs")
    if not asked.firm:
        many = len(asked.runs)
        runs = f"{many} run{'s' * (many != 1)}"
        why = asked.stopped or f"its verdict was not firm after {runs}"
        return Recoil("stops", asked.category, open=why)
    category = asked.category  # a firm run read a finding for every input
    gated = GATE[category] if category else "stops"
    if gated == "stops":  # unresolved names its open check, in its findings' words
        several = len(asked.findings) > 1
        said = [
            f"in {f.input}, {'; '.join(f.evidence)}" if several else "; ".join(f.evidence)
            for f in asked.findings
            if f.category == UNRESOLVED and f.evidence
        ]
        return Recoil("stops", category, open="; ".join(said) or "its verdict was unresolved")
    climbs: tuple[Piece, ...] = ()
    if gated == "climbs" and after.offers is not None:
        labels = sorted({f.levels.get("baseline") for f in asked.findings} - {None})
        climbs = tuple(decided(after, label) for label in labels)
    return Recoil(gated, category, climbs)
