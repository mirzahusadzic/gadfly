"""The crossing battery: a reading made on the far side of a boundary.

Evidence at one grain often reaches a decision only through something made
from it at the next: metrics become an incident's cause, a meeting becomes
its minutes, a draft becomes the brief a reviewer reads. A frame can test
whether the decision still rests on the evidence across that crossing. Its
spans are the evidence at the near side; a maker writes the artefact that
crosses from each trial's body; a reader decides from the artefact and the
input, and that decision is the call's label. Ablation, shams and every
other trial change the evidence before the maker sees it, so the verdict
says whether what the anchors said survived the making.

    "battery": {"kind": "crossing",
                "maker": {"kind": "unified", "model": "...",
                          "instruction": "Write the incident's cause."},
                "reader": {"kind": "unified", "model": "..."}}

The frame's instruction and labels are the reader's; the maker's
instruction is its own, in its line. `Crossing()` makes the artefact and
reads it through the router; `Crossing(maker, reader)` takes any maker and
any battery, from Python. An artefact that cannot be made again (a dream,
a poem already written) crosses the other way: its spans name the source
they came from (`source` on a span), and an ordinary battery reads it.

What this battery promises, whatever the frame says:
- the maker sees the trial's body and nothing else, neither the input nor
  the trial's id; the reader sees the artefact and the input;
- each call's cap is shared: the maker is given half and the reader what
  the maker left, so the call as a whole keeps the budget's cap;
- an artefact not made is an opening, never a guessed label, and the reader
  is not asked; every opening names the side that gave no answer, and the
  reader's answer is held to the protocol as `run` holds any battery's;
- a side's report of its spend is taken only as whole counts, none
  negative, so a report can never buy the other side a larger cap; a side
  that reports nothing, or no such count, is charged all it was given;
- the record keeps the artefact's SHA-256 whole, with as much of its text
  and of the reader's answer as fit the record, and names what made it and
  what read it;
- each side keeps its own promises: through the router, the deny data
  policy and every other check of the unified battery hold for the maker's
  line as for the reader's.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..errors import BatteryError, GadflyError, StopRun, quoted
from ..frame import Frame, parse
from ..interventions import plan, prompt
from ..pipeline import RAW_LIMIT, _checked
from ..types import Battery, Observation
from ..withhold import trains
from .unified import DEFAULT_URL, Unified, consented, over_cap, request_body

SEPARATOR = "\n\n---\n\n"  # what parts a prompt's body from its input
LINE_KEYS = {"kind", "maker", "reader"}
MAKER_KEYS = {
    "kind", "model", "instruction", "reasoning", "trainsOnInputs", "endpoints",
    "fallback", "thinkingBudget",
}  # fmt: skip
# what a model maker answers: the artefact's text, and nothing else
WRITTEN = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class Made:
    """What a maker made of a body: the artefact's text, or an opening that
    says why there is none, with what it said, spent and was served by."""

    text: str | None
    opening: str | None = None
    raw: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    served: str = ""

    def __post_init__(self) -> None:
        if (self.text is None) == (self.opening is None):
            raise BatteryError("a maker makes either an artefact or an opening")


@runtime_checkable
class Maker(Protocol):
    """What makes the artefact that crosses: from a trial's body, its text.
    Like a battery, it never sees which trial it is serving."""

    name: str

    def check(self, line: dict) -> None:
        """Refuse a maker line this maker must not serve (raise ValueError)."""

    def make(self, line: dict, text: str, max_output_tokens: int) -> Made:
        """Make the artefact from the body's text once, spending at most
        `max_output_tokens`."""

    # Optional: `trains(line) -> bool`, whether the maker's calls may reach a
    # model that trains on them; a maker that does not say is read as one that may.


class Function:
    """A maker that is a function of the body's text: a template, a parser,
    a fixed rule. Its line names it by its kind and nothing else, so the
    frame's hash names the function by that name alone: give a changed
    function a new one. It keeps no state, so calls may run at once."""

    concurrent = True

    def __init__(self, name: str, make: Callable[[str], str]):
        self.name, self._make = name, make

    def check(self, line: dict) -> None:
        """Refuse a line that says more than this maker's kind."""
        if set(line) != {"kind"}:
            raise BatteryError(
                f"maker {self.name!r} reads nothing but its kind",
                "a function's line names it; give a changed function a new name",
            )

    def make(self, line: dict, text: str, max_output_tokens: int) -> Made:
        """The function's text for this body; a function spends no tokens."""
        try:
            made = self._make(text)
        except StopRun:
            raise  # the harness failed: the run stops, as run says
        except Exception as error:  # noqa: BLE001 — the failure is what was made
            opening = f"the function failed ({type(error).__name__})"
            return Made(None, opening=opening, usage={"output_tokens": 0})
        if not isinstance(made, str):
            return Made(None, opening="the function returned no text", usage={"output_tokens": 0})
        return Made(made, usage={"output_tokens": 0})


class UnifiedMaker:
    """A model writes the artefact through the unified model router, under
    the maker line's own instruction: `{"kind": "unified", "model": ...,
    "instruction": ...}`, with `reasoning`, `trainsOnInputs` and
    `endpoints` read as the unified battery reads them."""

    name = "unified"
    concurrent = True

    def __init__(
        self,
        url: str = DEFAULT_URL,
        timeout: float = 120.0,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.router = Unified(url, timeout, clock)

    def trains(self, line: dict) -> bool:
        """Whether the maker's calls may reach a model that trains on them:
        only when its line names the model under trainsOnInputs."""
        return consented(line)

    def check(self, line: dict) -> None:
        """Refuse a line the router must not be sent, as the unified battery
        refuses one, and a line with no instruction to write by."""
        unknown = set(line) - MAKER_KEYS
        if unknown:
            raise BatteryError(f"the unified maker reads no {quoted(sorted(unknown))}")
        instruction = line.get("instruction")
        if not isinstance(instruction, str) or not instruction.strip():
            raise BatteryError("battery.maker.instruction says what the maker writes")
        self.router._check_line(line)

    def make(self, line: dict, text: str, max_output_tokens: int) -> Made:
        """One call through the router: the artefact the model wrote, or an
        opening that says why there is none."""
        body = request_body(line, line["instruction"], text, WRITTEN, max_output_tokens)
        answer, usage, opening, served = self.router._call(line, body)
        if opening:
            return Made(None, opening=opening, raw=answer, usage=usage, served=served)
        try:
            written = json.loads(answer).get("text")
        except (ValueError, AttributeError):
            written = None
        if not isinstance(written, str) or not written.strip():
            opening = "the answer held no text"
            return Made(None, opening=opening, raw=answer, usage=usage, served=served)
        return Made(written, raw=answer, usage=usage, served=served)


def _report(usage: object, allowance: int) -> tuple[dict[str, int], int, bool]:
    # a side's usage as counts, what it spent of its allowance, and whether
    # the report is sound: whole counts, none negative. A side that reports
    # nothing spent all it was allowed; one whose report is not sound may
    # have spent anything, and is charged all it was allowed. A report past
    # the allowance is kept as it is, for the run to stop on.
    if not isinstance(usage, dict) or not all(
        isinstance(key, str) and isinstance(value, int) and not isinstance(value, bool)
        and value >= 0
        for key, value in usage.items()
    ):  # fmt: skip
        return {}, allowance, False
    return dict(usage), usage.get("output_tokens", allowance), True


def _usage(made: dict[str, int], read: dict[str, int], spent: int) -> dict[str, int]:
    total = dict(made)
    for key, value in read.items():
        total[key] = total.get(key, 0) + value
    total["output_tokens"] = spent
    return total


def _named(served: object, name: str) -> str:
    # what a side says served it, or its name when it says nothing
    return served if isinstance(served, str) and served else name


def _raw(read: str, made: str, sha: str) -> str:
    # the artefact's hash, its text and the reader's answer, as one JSON
    # object that fits the record's raw whole: the longer of the two texts is
    # cut until it fits, so the hash is always kept and the record always
    # parses
    def written(read: str, made: str) -> str:
        kept = {"made": {"sha256": sha, "text": made}, "read": read}
        return json.dumps(kept, ensure_ascii=False)

    while len(whole := written(read, made)) > RAW_LIMIT:
        over = len(whole) - RAW_LIMIT
        if len(made) >= len(read):
            made = made[: max(0, len(made) - over)]
        else:
            read = read[: max(0, len(read) - over)]
    return whole


class Crossing:
    """`battery: {"kind": "crossing", "maker": {...}, "reader": {...}}`"""

    name = "crossing"

    def __init__(self, maker: Maker | None = None, reader: Battery | None = None):
        self.maker = maker if maker is not None else UnifiedMaker()
        self.reader = reader if reader is not None else Unified()
        # calls at once only when both sides take them
        self.concurrent = all(
            getattr(side, "concurrent", False) is True for side in (self.maker, self.reader)
        )
        self._readings: dict[str, Frame] = {}

    def _reading(self, frame: Frame) -> Frame:
        # the frame as the reader reads it: this frame, with the reader's line
        # as its battery
        reading = self._readings.get(frame.hash)
        if reading is None:
            reading = parse({**frame.raw, "battery": frame.battery.get("reader")})
            self._readings[frame.hash] = reading
        return reading

    def trains(self, frame: Frame) -> bool:
        """Whether either side's calls may reach a reader that trains on them;
        a maker or a reader that does not say is read as one that may."""
        says = getattr(self.maker, "trains", None)
        line = frame.battery.get("maker") if isinstance(frame.battery, dict) else None
        maker = (
            True if not callable(says) or not isinstance(line, dict) else says(line) is not False
        )
        try:
            reading = self._reading(frame)
        except GadflyError:
            return True
        return maker or trains(self.reader, reading)

    def check(self, frame: Frame) -> None:
        """Refuse, before any call, a frame this crossing must not serve:
        another battery's, an unknown key, a maker or reader line this
        crossing was not made with or that its side refuses, or a prompt
        whose body cannot be told from its input."""
        line = frame.battery
        if line.get("kind") != self.name:
            raise BatteryError(f"this frame asks for battery {line.get('kind')!r}")
        unknown = set(line) - LINE_KEYS
        if unknown:
            raise BatteryError(
                f"the crossing battery reads no {quoted(sorted(unknown))} under battery"
            )
        for side, made in (("maker", self.maker), ("reader", self.reader)):
            named = line.get(side)
            if not isinstance(named, dict) or not isinstance(named.get("kind"), str):
                raise BatteryError(
                    f"battery.{side} is a line of its own with a kind", "as battery is"
                )
            if named["kind"] != made.name:
                raise BatteryError(
                    f"battery.{side} names kind {named['kind']!r}, not {made.name!r}",
                    "this crossing was made with another; make one with Crossing(maker, reader)",
                )
        for trial in plan(frame):
            for x in frame.inputs:
                if prompt(frame, trial, x).rpartition(SEPARATOR)[0] != trial.text:
                    raise BatteryError(
                        f"input {x['id']!r} holds the line that parts a body from its input",
                        "the maker reads what comes before the last '---' line; "
                        "keep such lines out of inputs and renamings",
                    )
        try:
            self.maker.check(line["maker"])
        except ValueError as error:
            error.add_note("it is the crossing's maker line, battery.maker, that is refused")
            raise
        try:
            self.reader.check(self._reading(frame))
        except ValueError as error:
            error.add_note("it is the crossing's reader line, battery.reader, that is refused")
            raise

    def check_cap(self, frame: Frame, cap: int) -> None:
        """Refuse, before any call, a cap that leaves a side's thinking budget
        no room: the maker writes within half of each call's cap, and the
        reader reads within what the maker leaves, at least the other half."""
        share = max(1, cap // 2)
        for side, room in (("maker", share), ("reader", cap - share)):
            line = frame.battery.get(side)
            over = over_cap(line, room) if isinstance(line, dict) else None
            if over:
                raise BatteryError(
                    over,
                    f"the crossing's {side} gets {room!r} of each call's {cap!r} tokens; "
                    "raise --output-tokens, or lower the budget",
                )

    def observe(self, frame: Frame, prompt: str, max_output_tokens: int) -> Observation:
        """One call across the boundary: the maker makes the artefact from
        the body, then the reader reads it with the input; the reader's
        label, or an opening that says which side gave none, and why."""
        reading = self._reading(frame)
        line = frame.battery
        body, _, question = prompt.rpartition(SEPARATOR)
        share = max(1, max_output_tokens // 2)
        maker = f"made by {self.maker.name}"
        whole = {"output_tokens": share}  # what a maker that says nothing is charged
        try:
            made = self.maker.make(line["maker"], body, share)
        except StopRun:
            raise  # the harness failed: the run stops, as run says
        except Exception as error:  # noqa: BLE001 — the failure is the observation
            opening = f"the maker failed ({type(error).__name__})"
            return Observation(label=None, opening=opening, usage=whole, served=maker)
        if not isinstance(made, Made):
            opening = "the maker returned nothing it made"
            return Observation(label=None, opening=opening, usage=whole, served=maker)
        maker = f"made by {_named(made.served, self.maker.name)}"
        made_usage, spent, sound = _report(made.usage, share)
        raw = made.raw if isinstance(made.raw, str) else ""
        if not sound:
            opening = "the maker's report of what it spent is not a count of tokens"
            return Observation(label=None, opening=opening, raw=raw, usage=whole, served=maker)
        if made.opening is not None:
            return Observation(
                label=None,
                opening=f"the maker made nothing ({made.opening!r})",
                raw=raw,
                usage=_usage(made_usage, {}, spent),
                served=maker,
            )
        if not isinstance(made.text, str) or not made.text.strip():
            return Observation(
                label=None,
                opening="the maker made an empty artefact",
                usage=_usage(made_usage, {}, spent),
                served=maker,
            )
        try:
            sha = hashlib.sha256(made.text.encode("utf-8")).hexdigest()
        except UnicodeEncodeError:  # a lone surrogate: no text a file or a hash can hold
            return Observation(
                label=None,
                opening="the maker made text that is not valid Unicode",
                usage=_usage(made_usage, {}, spent),
                served=maker,
            )
        left = max_output_tokens - spent
        if left < 1:
            return Observation(
                label=None,
                opening="the maker spent the call's whole cap",
                raw=_raw("", made.text, sha),
                usage=_usage(made_usage, {}, spent),
                served=maker,
            )
        try:
            seen = self.reader.observe(reading, f"{made.text}{SEPARATOR}{question}", left)
        except StopRun:
            raise  # the harness failed: the run stops, as run says
        except Exception as error:  # noqa: BLE001 — the failure is the observation
            return Observation(
                label=None,
                opening=f"the reader failed ({type(error).__name__})",
                raw=_raw("", made.text, sha),
                usage=_usage(made_usage, {}, spent + left),
                served=maker,
            )
        seen = _checked(reading, seen)  # as run holds any battery's answer
        read_usage, read, sound = _report(seen.usage, left)
        served = f"{maker}, read by {_named(seen.served, self.reader.name)}"
        kept = _raw(seen.raw, made.text, sha)
        if not sound:
            opening = "the reader's report of what it spent is not a count of tokens"
            usage = _usage(made_usage, {}, spent + left)
            return Observation(label=None, opening=opening, raw=kept, usage=usage, served=served)
        usage = _usage(made_usage, read_usage, spent + read)
        if seen.opening is not None:
            opening = f"the reader gave no label ({seen.opening!r})"
            return Observation(label=None, opening=opening, raw=kept, usage=usage, served=served)
        return Observation(label=seen.label, raw=kept, usage=usage, served=served)
