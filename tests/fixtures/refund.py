"""Two deterministic scorers for the command-line and schema tests: no model.

Both decline a refund while the receipt rule is in the policy and grant it once
the rule is removed. The phrase matcher reads one wording, so the presentation
trial moves it; the rule reader reads either wording, and decides only while the
policy's binding line says the rules decide (its bypass cuts that line).
"""

from __future__ import annotations

import random
import threading
import time
import warnings

from midwife.types import Observation


class PhraseMatcher:
    """Declines when the policy contains one of its phrases."""

    name = "phrase-matcher"
    phrases: tuple[str, ...] = ("requires a receipt",)

    def check(self, frame):
        if frame.battery["kind"] != self.name:
            raise ValueError(f"this frame asks for the {frame.battery['kind']} battery")

    def observe(self, frame, prompt, max_output_tokens):
        policy, _, _request = prompt.partition("\n\n---\n\n")
        return Observation(label="decline" if any(p in policy for p in self.phrases) else "grant")


class RuleReader(PhraseMatcher):
    """Reads the rule in either of its wordings, while the rules bind."""

    name = "rule-reader"
    phrases = ("requires a receipt", "requires a proof of purchase")

    def observe(self, frame, prompt, max_output_tokens):
        policy, _, _request = prompt.partition("\n\n---\n\n")
        if "These rules decide every request." not in policy:
            return Observation(label="unclear")  # no rule binds: nothing to decide by
        return super().observe(frame, prompt, max_output_tokens)


class AtOnce(RuleReader):
    """The rule reader taking calls at once: it keeps the most it had out together."""

    concurrent = True
    most = 0
    out = 0
    lock = threading.Lock()

    def observe(self, frame, prompt, max_output_tokens):
        held = type(self)
        with held.lock:
            held.out += 1
            held.most = max(held.most, held.out)
        time.sleep(0.01)
        try:
            return super().observe(frame, prompt, max_output_tokens)
        finally:
            with held.lock:
                held.out -= 1


class Metered(RuleReader):
    """The rule reader reporting the tokens each call spent, as a provider does."""

    def observe(self, frame, prompt, max_output_tokens):
        read = super().observe(frame, prompt, max_output_tokens)
        read.usage.update(input_tokens=1000, output_tokens=40, reasoning_tokens=30)
        return read


class Reflex(Metered):
    """The metered reader, reporting no reasoning whenever it cannot decide."""

    def observe(self, frame, prompt, max_output_tokens):
        read = super().observe(frame, prompt, max_output_tokens)
        if read.label == "unclear":
            read.usage["reasoning_tokens"] = 0
        return read


class Unreachable(RuleReader):
    """The rule reader when its service is down: every call is an opening."""

    def observe(self, frame, prompt, max_output_tokens):
        return Observation(
            label=None, opening="the reader could not be reached (ConnectionRefused)"
        )


class Interrupted(RuleReader):
    """The rule reader, stopped by Ctrl-C on its third call."""

    def __init__(self):
        self.calls = 0

    def observe(self, frame, prompt, max_output_tokens):
        self.calls += 1
        if self.calls == 3:
            raise KeyboardInterrupt
        return super().observe(frame, prompt, max_output_tokens)


class Wavering(RuleReader):
    """The rule reader that never settles: each answer drawn at random, the
    same draws on every run of the tests."""

    def __init__(self):
        self.draws = random.Random(7)

    def observe(self, frame, prompt, max_output_tokens):
        return Observation(label=self.draws.choice(frame.labels))


class InterruptedAtOnce(RuleReader):
    """The rule reader, stopped by Ctrl-C on its first call."""

    def observe(self, frame, prompt, max_output_tokens):
        raise KeyboardInterrupt


class InterruptedBetweenRuns(Wavering):
    """The wavering reader, stopped by Ctrl-C on the first call of a second
    run of 24 calls, as the refund frame asked three times a trial makes."""

    def __init__(self):
        super().__init__()
        self.calls = 0

    def observe(self, frame, prompt, max_output_tokens):
        self.calls += 1
        if self.calls == 25:
            raise KeyboardInterrupt
        return super().observe(frame, prompt, max_output_tokens)


class Warned(RuleReader):
    """The rule reader whose library warns on its first call, as another
    package's code may."""

    def __init__(self):
        self.warned = False

    def observe(self, frame, prompt, max_output_tokens):
        if not self.warned:
            self.warned = True
            warnings.warn("a library of the reader's warned", stacklevel=1)
        return super().observe(frame, prompt, max_output_tokens)


class Overspending(RuleReader):
    """The rule reader that says it wrote past the cap it was given."""

    def observe(self, frame, prompt, max_output_tokens):
        observation = super().observe(frame, prompt, max_output_tokens)
        return Observation(label=observation.label, usage={"output_tokens": max_output_tokens + 1})


class Garbled(RuleReader):
    """The rule reader whose replies carry a lone surrogate, as a JSON reply
    may: valid JSON, but not text a file can hold."""

    def observe(self, frame, prompt, max_output_tokens):
        observation = super().observe(frame, prompt, max_output_tokens)
        return Observation(label=observation.label, raw="ok \ud800", served="reader \udfff")


class Counted(RuleReader):
    """The rule reader, counting the calls made to it."""

    calls = 0

    def observe(self, frame, prompt, max_output_tokens):
        type(self).calls += 1
        return super().observe(frame, prompt, max_output_tokens)


class Stuck(RuleReader):
    """The rule reader taking calls at once, its third and later calls hung,
    as a service that never answers would leave them (for at most 20 s)."""

    concurrent = True

    def __init__(self):
        self.calls = 0

    def observe(self, frame, prompt, max_output_tokens):
        self.calls += 1
        if self.calls > 2:
            time.sleep(20)
        return super().observe(frame, prompt, max_output_tokens)


class Slow(RuleReader):
    """The rule reader, a twentieth of a second a call."""

    def observe(self, frame, prompt, max_output_tokens):
        time.sleep(0.05)
        return super().observe(frame, prompt, max_output_tokens)


class InterruptingAtOnce(RuleReader):
    """The rule reader taking calls at once, its third call raising Ctrl-C
    in its worker's thread."""

    concurrent = True

    def __init__(self):
        self.calls = 0

    def observe(self, frame, prompt, max_output_tokens):
        self.calls += 1
        if self.calls == 3:
            raise KeyboardInterrupt
        return super().observe(frame, prompt, max_output_tokens)


class Exiting(RuleReader):
    """The rule reader that calls sys.exit(0) on its second call, as a battery
    should never do."""

    def __init__(self):
        self.calls = 0

    def observe(self, frame, prompt, max_output_tokens):
        self.calls += 1
        if self.calls == 2:
            raise SystemExit(0)
        return super().observe(frame, prompt, max_output_tokens)


class Separated(RuleReader):
    """The rule reader whose replies hold Unicode line separators, as any
    text may: valid in a JSON string, but lines to str.splitlines()."""

    def observe(self, frame, prompt, max_output_tokens):
        observation = super().observe(frame, prompt, max_output_tokens)
        return Observation(label=observation.label, raw="a b c\x85d")


class UnreachableThenInterrupted(Unreachable):
    """The rule reader's service down for two calls, then Ctrl-C."""

    def __init__(self):
        self.calls = 0

    def observe(self, frame, prompt, max_output_tokens):
        self.calls += 1
        if self.calls == 3:
            raise KeyboardInterrupt
        return super().observe(frame, prompt, max_output_tokens)


class OnceUnreachable(RuleReader):
    """The rule reader whose service is down for its first call only."""

    def __init__(self):
        self.calls = 0

    def observe(self, frame, prompt, max_output_tokens):
        self.calls += 1
        if self.calls == 1:
            return Unreachable().observe(frame, prompt, max_output_tokens)
        return super().observe(frame, prompt, max_output_tokens)
