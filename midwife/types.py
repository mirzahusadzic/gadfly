"""The types a pipeline passes from stage to stage, and the one a battery
implements. Gadfly keeps no state: every value here is returned to the caller,
who keeps it (a file, a database, a test fixture) as they see fit.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol, runtime_checkable

from .frame import Frame


@dataclass(frozen=True)
class Observation:
    """What a battery saw: one of the frame's labels, or a typed opening when
    there is no outcome to read (a refusal, an unreadable answer, a failure).
    `served` names the scorer that answered, as the service reports it (a
    model, its revision, the endpoint), so a record says who read."""

    label: str | None
    opening: str | None = None
    raw: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    served: str = ""

    def __post_init__(self) -> None:
        if (self.label is None) == (self.opening is None):
            raise ValueError("an observation is either a label or an opening")


@dataclass(frozen=True)
class Record:
    """One scorer call: which frame, input, trial and run, what was read and
    what it cost. A verdict is recomputed from records alone."""

    frame: str
    input: str
    trial: str
    run: int
    body: str
    prompt: str
    battery: str
    observation: str | None
    opening: str | None
    raw: str
    usage: dict[str, int]
    served: str = ""

    def as_dict(self) -> dict[str, Any]:
        """The record as a plain dict, as a caller keeps it (JSON Lines, say)."""
        return asdict(self)


@runtime_checkable
class Battery(Protocol):
    """A scorer: given the frame and the exact text it must read, one
    observation. It never sees which trial it is serving. A battery that
    can serve several calls at once says so with a class attribute
    `concurrent = True`; without it, `run` makes one call at a time."""

    name: str

    def check(self, frame: Frame) -> None:
        """Refuse a frame this battery must not serve (raise ValueError)."""

    def observe(self, frame: Frame, prompt: str, max_output_tokens: int) -> Observation:
        """Read the prompt once and return what it observed, spending at most
        `max_output_tokens` (the budget's cap per call) on the answer."""


@dataclass(frozen=True)
class Budget:
    """The most a run may spend: `calls` scorer calls, each answer capped at
    `output_tokens_per_call`, and, if `tokens` is set, that many output tokens
    in all. Because every call is capped, a call is never started that could
    pass the budget; a battery that reports more than the cap has broken that
    promise, and the run stops after its call."""

    calls: int
    output_tokens_per_call: int = 64
    tokens: int | None = None

    def __post_init__(self) -> None:
        def whole(value: Any) -> bool:
            return isinstance(value, int) and not isinstance(value, bool)

        if not (whole(self.calls) and whole(self.output_tokens_per_call)):
            raise ValueError("a budget counts calls and tokens in whole numbers")
        if self.calls < 1 or self.output_tokens_per_call < 1:
            raise ValueError("a budget allows at least one call of at least one token")
        if self.tokens is not None and not (whole(self.tokens) and self.tokens >= 0):
            raise ValueError("a token budget is a whole number of tokens, or None")
