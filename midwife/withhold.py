"""Text that must not leave this machine, checked before any call.

A withhold set is read from a file, `{"always": {...}, "training": {...}}`.
What `always` holds no call may carry, such as a credential; what `training`
holds may go to a reader that keeps no data, never to one that may train on
what it reads, such as a private name or a line read from elsewhere. Each part
may list `names`, matched as whole words in any case; `lines`, each the
SHA-256 of a line in its normal form, its words joined by single spaces; and
`patterns`, Python regular expressions. A line that opens with a diff marker,
`+` or `-`, is also read without it, so a line copied into a diff still
matches its source.

`withheld` reads every prompt a frame's plan makes, which is all a run sends,
and names each place that holds withheld text; `refuse_withheld` refuses the
frame at the first, naming where and what kind, never the text. Whether the
`training` part applies is the battery's to say (`trains`); one that does not
say is read as one that may train. In a crossing, what the maker writes is not
checked before the reader reads it.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

from .errors import FrameError, UsageError
from .frame import Frame
from .interventions import plan, prompt

PARTS = ("always", "training")
LISTS = ("names", "lines", "patterns")
SHA256 = re.compile(r"[0-9a-f]{64}")
SHAPE = (
    "a withhold set is a JSON object with the parts always and training, each "
    "listing names, lines (SHA-256) or patterns, as lists of strings"
)


@dataclass(frozen=True)
class Part:
    """One part of a withhold set: whole-word names, line hashes, patterns."""

    names: tuple[str, ...] = ()
    lines: frozenset[str] = frozenset()
    patterns: tuple[re.Pattern[str], ...] = ()
    named: re.Pattern[str] | None = field(default=None, repr=False, compare=False)

    def kinds(self, text: str) -> list[str]:
        """The kinds of withheld text `text` holds: a name, a line, a pattern."""
        found = []
        if self.named is not None and self.named.search(text.casefold()):
            found.append("a name")
        if self.lines and any(digest in self.lines for digest in _line_digests(text)):
            found.append("a line")
        if any(pattern.search(text) for pattern in self.patterns):
            found.append("a pattern")
        return found


@dataclass(frozen=True)
class Withhold:
    """What no call may carry (`always`), and what no call that may train may
    carry (`training`)."""

    always: Part = Part()
    training: Part = Part()


@dataclass(frozen=True)
class Held:
    """A place a run would send withheld text: the trial and input whose
    prompt holds it, its kind, and the part of the set that withholds it. A
    trial or input whose id the set itself withholds is named by its place
    instead, `trial 3` or `input 2`, counted from 1 in the plan's and the
    frame's order, so a refusal never says the text."""

    trial: str
    input: str
    kind: str
    part: str

    def as_dict(self) -> dict[str, str]:
        """The place as JSON: its trial, input, kind and part."""
        return {"trial": self.trial, "input": self.input, "kind": self.kind, "part": self.part}


def normal(line: str) -> str:
    """A line's normal form, as its hash is taken: its words joined by single spaces."""
    return " ".join(line.split())


def line_sha256(line: str) -> str:
    """The SHA-256 a withhold set lists a line by: of its normal form, as UTF-8."""
    return hashlib.sha256(normal(line).encode("utf-8")).hexdigest()


def _line_digests(text: str) -> set[str]:
    # each line as it is and, after a diff marker, without it
    digests = set()
    for line in text.split("\n"):
        forms = [line]
        if line[:1] in ("+", "-"):
            forms.append(line[1:])
        for form in forms:
            if normal(form):
                digests.add(line_sha256(form))
    return digests


def read_withhold(data: bytes | str, *, path: str | None = None) -> Withhold:
    """A withhold set from its JSON. A refusal names the file at `path` it
    was read from, `-` standard input."""
    try:  # a str holding a lone surrogate is no text a file could hold
        raw = data.encode("utf-8") if isinstance(data, str) else bytes(data)
        text = raw.decode("utf-8")
    except UnicodeError:
        raise UsageError(f"{_named(path)} is not UTF-8 text") from None
    try:
        document = json.loads(text)
    except (ValueError, RecursionError):
        raise UsageError(f"{_named(path)} cannot be read as JSON") from None
    if not (isinstance(document, dict) and set(document) <= set(PARTS)):
        raise UsageError(f"{_named(path)} is not a withhold set", SHAPE)
    parts = {}
    for name in PARTS:
        parts[name] = _part(document.get(name, {}), path)
    return Withhold(**parts)


def _part(value: Any, path: str | None) -> Part:
    if not (isinstance(value, dict) and set(value) <= set(LISTS)):
        raise UsageError(f"{_named(path)} is not a withhold set", SHAPE)
    lists = {}
    for key in LISTS:
        items = value.get(key, [])
        if not (isinstance(items, list) and all(isinstance(i, str) and i for i in items)):
            raise UsageError(f"{_named(path)} is not a withhold set", SHAPE)
        lists[key] = items
    if not all(SHA256.fullmatch(digest) for digest in lists["lines"]):
        raise UsageError(
            f"{_named(path)} lists a line that is no SHA-256",
            "each line is the SHA-256 of its normal form, 64 lowercase hex digits",
        )
    patterns = []
    for written in lists["patterns"]:
        try:
            patterns.append(re.compile(written))
        except (re.error, OverflowError, RecursionError) as error:
            raise UsageError(
                f"{_named(path)} holds a pattern that is no regular expression",
                f"Python's re module said {str(error)!r}",
            ) from None
    names = tuple(lists["names"])
    folded = sorted({name.casefold() for name in names}, key=len, reverse=True)
    union = "|".join(re.escape(name) for name in folded)
    # matched in full case folding, so Straße holds STRASSE back too
    matcher = re.compile(rf"(?<!\w)(?:{union})(?!\w)") if names else None
    return Part(names, frozenset(lists["lines"]), tuple(patterns), matcher)


def trains(battery: Any, frame: Frame) -> bool:
    """Whether a battery says its calls for this frame may reach a reader
    that trains on them; one that does not say may."""
    says = getattr(battery, "trains", None)
    # only an answer of exactly False keeps the training part off; None, 0 or
    # anything else is no answer, and is read as one that may train
    return True if not callable(says) else says(frame) is not False


def withheld(frame: Frame, withhold: Withhold, *, training: bool = True) -> list[Held]:
    """Each trial and input whose prompt holds withheld text, of what kind,
    and under which part: `always` for every frame, `training` too when the
    frame's calls may train. Read over every prompt the plan makes, before
    any call."""
    parts = [("always", withhold.always)]
    if training:
        parts.append(("training", withhold.training))
    held = []
    for place, trial in enumerate(plan(frame), 1):
        for at, x in enumerate(frame.inputs, 1):
            text = prompt(frame, trial, x)
            named = (
                _shown(withhold, trial.id, f"trial {place}"),
                _shown(withhold, x["id"], f"input {at}"),
            )
            for name, part in parts:
                held.extend(Held(*named, kind, name) for kind in part.kinds(text))
    return held


def _shown(withhold: Withhold, identifier: str, place: str) -> str:
    # an id as a refusal may say it: by its place when the set withholds the id
    held = any(part.kinds(identifier) for part in (withhold.always, withhold.training))
    return place if held else identifier


def refuse_withheld(frame: Frame, withhold: Withhold, *, training: bool = True) -> None:
    """Refuse a frame whose run would send withheld text, at its first
    place, naming where and of what kind, never the text itself."""
    held = withheld(frame, withhold, training=training)
    if not held:
        return
    first = held[0]
    which = "the frame" if _shown(withhold, frame.name, "") == "" else f"frame {frame.name!r}"
    error = FrameError(
        f"{which} would send withheld text, {first.kind}, "
        f"in trial {first.trial!r} for input {first.input!r}"
    )
    if first.part == "training":
        error.add_note(
            "its battery may train on what it reads; read it with a reader that keeps "
            "no data, or take the text out of the frame"
        )
    else:
        error.add_note("no call may carry it; take the text out of the frame")
    places = len({(h.trial, h.input) for h in held})
    if places > 1:
        error.add_note(f"{places} prompts in all hold withheld text")
    raise error


def _named(path: str | None) -> str:
    # the set as a refusal names it: by the file it was read from
    if path is None:
        return "the text given"
    return "standard input" if path == "-" else f"file {path!r}"
