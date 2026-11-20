"""The branch battery: one reading of the question, shared by every trial.

A reader that thinks before each label thinks much the same about the same
question in every trial of a frame. Here that thought is had once: a maker
reads a trial's input alone and writes what an answer would have to rest
on, before any evidence is seen; a reader then decides each trial from
that artefact, the trial's body and the input. Every call that carries the
same input branches from the same artefact, so the reader's line can ask
for little thinking, or for none.

    "battery": {"kind": "branch",
                "maker": {"kind": "unified", "model": "...",
                          "instruction": "List what would have to be said."},
                "reader": {"kind": "unified", "model": "...",
                           "reasoning": "none"}}

The frame's instruction and labels are the reader's, and its instruction
says how to read the three parts it is given; the maker's instruction is
its own, in its line. `Branch()` makes the artefact and reads it through
the router; `Branch(maker, reader)` takes any maker and any battery, from
Python. It is the crossing battery turned around: there the maker sees
the body and never the input, here the input and never the body.

What this battery promises, whatever the frame says:
- the maker sees the input and nothing else, neither the body nor the
  trial's id, so nothing a trial took out of the evidence can come back
  through what the maker wrote; the reader sees the artefact, then the
  body, then the input, each parted from the next by a line of three
  dashes;
- an input's artefact is made once for a frame by each battery object, and
  every later call that carries that input reads that same artefact; an
  artefact not made is an opening, never a guessed label, the reader is
  not asked, and the next call makes it again; an input a trial renames,
  as presentation and input inversion do, is another input, with an
  artefact of its own, so the words it renamed cannot come back through
  the first;
- the call that makes an artefact shares its cap as a crossing's does: the
  maker is given half and the reader what the maker left; a call that
  finds the artefact made gives the reader its whole cap, and its record
  counts nothing for the making;
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

import threading

from ..errors import BatteryError, GadflyError, quoted
from ..frame import Frame, parse
from ..interventions import plan, prompt
from ..types import Battery, Observation
from ..withhold import trains
from .crossing import SEPARATOR, Maker, UnifiedMaker, _Attempt, _attempt, _raw, _read, _usage
from .unified import Unified, over_cap

LINE_KEYS = {"kind", "maker", "reader"}


def _ruled(text: str) -> bool:
    """Whether a line of the text is a bare '---', in any spacing or line
    ending, which a reader could take for a line that parts the three parts."""
    return any(line.strip() == "---" for line in text.splitlines())


class Branch:
    """`battery: {"kind": "branch", "maker": {...}, "reader": {...}}`"""

    name = "branch"

    def __init__(self, maker: Maker | None = None, reader: Battery | None = None):
        self.maker = maker if maker is not None else UnifiedMaker()
        self.reader = reader if reader is not None else Unified()
        # calls at once only when both sides take them
        self.concurrent = all(
            getattr(side, "concurrent", False) is True for side in (self.maker, self.reader)
        )
        self._readings: dict[str, Frame] = {}
        self._made: dict[tuple[str, str], _Attempt] = {}
        self._making: dict[tuple[str, str], threading.Lock] = {}
        self._guard = threading.Lock()

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
        """Refuse, before any call, a frame this branch must not serve:
        another battery's, an unknown key, a maker or reader line this branch
        was not made with or that its side refuses, or a prompt whose
        artefact, body and input could not be told apart."""
        line = frame.battery
        if line.get("kind") != self.name:
            raise BatteryError(f"this frame asks for battery {line.get('kind')!r}")
        unknown = set(line) - LINE_KEYS
        if unknown:
            raise BatteryError(
                f"the branch battery reads no {quoted(sorted(unknown))} under battery"
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
                    "this branch was made with another; make one with Branch(maker, reader)",
                )
        for trial in plan(frame):
            if _ruled(trial.text):
                raise BatteryError(
                    "a trial's body holds the line that parts it from the artefact",
                    "the reader tells the artefact, the body and the input apart by '---' "
                    "lines; keep such lines out of spans and renamings",
                )
            for x in frame.inputs:
                body, _, question = prompt(frame, trial, x).rpartition(SEPARATOR)
                if body != trial.text or _ruled(question):
                    raise BatteryError(
                        f"input {x['id']!r} holds the line that parts a body from its input",
                        "the maker reads what comes after the last '---' line; "
                        "keep such lines out of inputs and renamings",
                    )
        try:
            self.maker.check(line["maker"])
        except ValueError as error:
            error.add_note("it is the branch's maker line, battery.maker, that is refused")
            raise
        try:
            self.reader.check(self._reading(frame))
        except ValueError as error:
            error.add_note("it is the branch's reader line, battery.reader, that is refused")
            raise

    def check_cap(self, frame: Frame, cap: int) -> None:
        """Refuse, before any call, a cap that leaves a side's thinking budget
        no room in the call that makes an artefact: the maker writes within
        half of that call's cap, and the reader reads within what the maker
        leaves, at least the other half. A reader with a `check_cap` of its
        own is asked for that half and for a later call's whole cap."""
        share = max(1, cap // 2)
        for side, room in (("maker", share), ("reader", cap - share)):
            line = frame.battery.get(side)
            over = over_cap(line, room) if isinstance(line, dict) else None
            if over:
                raise BatteryError(
                    over,
                    f"the branch's {side} gets {room!r} of the {cap!r} tokens of a call that "
                    "makes an artefact; raise --output-tokens, or lower the budget",
                )
        fits = getattr(self.reader, "check_cap", None)  # the reader's own, where it has one
        if callable(fits):
            reading = self._reading(frame)
            try:
                for room in sorted({cap - share, cap}):
                    fits(reading, room)
            except ValueError as error:
                error.add_note("it is the branch's reader line, battery.reader, that is refused")
                raise

    def _stem(self, frame: Frame, question: str, cap: int) -> _Attempt:
        # the artefact every call with this input branches from: made by the
        # first call to ask, which is charged for it, and read by the rest as
        # it was made; the calls beside the one that makes it wait for it
        key = (frame.hash, question)
        with self._guard:
            making = self._making.setdefault(key, threading.Lock())
        with making:
            kept = self._made.get(key)
            if kept is not None:
                return kept
            share = max(1, cap // 2)
            tried = _attempt(self.maker, frame.battery["maker"], question, share, cap)
            if tried.ended is not None:
                return tried
            if _ruled(tried.text):
                return _Attempt(
                    Observation(
                        label=None,
                        opening="the maker made text that holds the line that parts it from "
                        "the body",
                        raw=_raw("", tried.text, tried.sha),
                        usage=_usage(tried.usage, {}, tried.spent),
                        served=tried.served,
                    )
                )
            # kept without its cost: the calls that find it made did not pay for it
            self._made[key] = _Attempt(None, tried.text, tried.sha, served=tried.served)
            return tried

    def observe(self, frame: Frame, prompt: str, max_output_tokens: int) -> Observation:
        """One call from the shared artefact: the maker's reading of the
        input, made now or by an earlier call, then the reader's label from
        it, the body and the input; or an opening that says which side gave
        none, and why."""
        reading = self._reading(frame)
        body, _, question = prompt.rpartition(SEPARATOR)
        tried = self._stem(frame, question, max_output_tokens)
        if tried.ended is not None:
            return tried.ended
        asked = f"{tried.text}{SEPARATOR}{body}{SEPARATOR}{question}"
        return _read(self.reader, reading, asked, tried, max_output_tokens - tried.spent)
