"""Two deterministic scorers for the command-line and schema tests: no model.

Both decline a refund while the receipt rule is in the policy and grant it once
the rule is removed. The phrase matcher reads one wording, so the presentation
trial moves it; the rule reader reads either wording, and decides only while the
policy's binding line says the rules decide (its bypass cuts that line).
"""

from __future__ import annotations

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


class Unreachable(RuleReader):
    """The rule reader when its service is down: every call is an opening."""

    def observe(self, frame, prompt, max_output_tokens):
        return Observation(label=None, opening="the reader could not be reached: ConnectionRefused")


class Interrupted(RuleReader):
    """The rule reader, stopped by Ctrl-C on its third call."""

    def __init__(self):
        self.calls = 0

    def observe(self, frame, prompt, max_output_tokens):
        self.calls += 1
        if self.calls == 3:
            raise KeyboardInterrupt
        return super().observe(frame, prompt, max_output_tokens)


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
