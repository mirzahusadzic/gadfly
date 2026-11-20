"""The eGemma battery: Gemma 4 on this machine, through eGemma's /judge.

[eGemma](https://github.com/mirzahusadzic/egemma) reads the prompt under the frame's
instruction, with no persona added, and a grammar holds its answer to the
schema: by default `{"label": <one of the frame's labels>}`, or a critic's own
schema with the label's place named, as for the unified battery. Nothing
leaves this machine, and nothing is cached, so the quorum's runs are fresh
samples; at `temperature: 0` the battery is close to deterministic. With
`reasoning: true`, Gemma thinks before every answer, and only the answer is
held to the schema.

    "battery": {"kind": "egemma", "temperature": 0.7}

What this battery promises, whatever the frame says:
- it talks only to an eGemma on this machine (loopback), through no proxy
  and no redirect;
- each call has a deadline (`timeout` seconds for the whole reply), the
  budget's cap on output tokens, and a cap on what it reads back; with
  reasoning, the cap is the thought's and the answer's together: the answer
  keeps ANSWER_TOKENS of it and the thought gets the rest, up to
  MAX_THOUGHT_TOKENS, and a cap with no room left for a thought is an
  opening;
- it calls one at a time and paces itself to the judge budget eGemma
  publishes at GET /rate-limits (read once, before the first call); when
  eGemma is busy anyway (429 or 503) it waits as long as eGemma asks, at most
  a minute, and tries at most three more times before the call becomes an
  opening;
- each record names the model and revision eGemma reports; a frame that
  pins them (`model`, `revision`) gets an opening from any other;
- the key comes from the file named by EGEMMA_API_KEY_FILE, else from
  EGEMMA_API_KEY or WORKBENCH_API_KEY, and is never logged or recorded.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from collections import deque
from collections.abc import Callable
from functools import partial
from pathlib import Path
from urllib.parse import urlparse

from ..errors import BatteryError, quoted
from ..frame import Frame
from ..types import Observation
from .critic import (
    MAX_RESPONSE_BYTES,
    Late,
    check_output,
    label_at,
    loopback,
    opened,
    opener,
    output_schema,
    read_error,
    read_reply,
)
from .crossing import Made

DEFAULT_URL = os.environ.get("EGEMMA_URL", "http://127.0.0.1:8000").rstrip("/") + "/judge"
BATTERY_KEYS = {"kind", "temperature", "output", "model", "revision", "reasoning"}
# With reasoning, the answer's share of a call's cap: a label answer takes
# about ten tokens. The thought gets the rest, up to eGemma's own cap.
ANSWER_TOKENS = 64
MAX_THOUGHT_TOKENS = 4096
# A maker's text, a step of a few short lines, keeps this much of a call's
# cap; with reasoning the thought gets the rest, up to MAX_THOUGHT_TOKENS.
STEP_TOKENS = 512
MAKER_KEYS = {"kind", "instruction", "temperature", "model", "revision", "reasoning"}
WRITTEN = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"],
    "additionalProperties": False,
}
BUSY = (429, 503)  # eGemma's rate limit, and its queue when full
RETRIES = 3
MAX_WAIT = 60.0


def _key() -> str:
    path = os.environ.get("EGEMMA_API_KEY_FILE")
    if path:
        key = Path(path).read_text(encoding="utf-8").strip()
        if not key:
            raise BatteryError(
                f"file {path!r} is empty",
                "the environment variable EGEMMA_API_KEY_FILE names it; write eGemma's key into it",
            )
        return key
    key = os.environ.get("EGEMMA_API_KEY") or os.environ.get("WORKBENCH_API_KEY")
    if not key:
        raise BatteryError(
            "no eGemma key",
            "name a file that holds it in the environment variable EGEMMA_API_KEY_FILE, "
            "or set EGEMMA_API_KEY",
        )
    return key


def _wait(error: urllib.error.HTTPError, body: Callable[[], bytes]) -> float:
    """How long eGemma asks a busy caller to wait: its Retry-After header, or
    the seconds its rate limiter names in the detail (the refusal's `body`,
    read only when needed), or a second; at most MAX_WAIT. A wait that is not
    a finite, non-negative number is not one."""
    header = error.headers.get("retry-after") if error.headers else None
    seconds = None
    if header is not None:
        try:
            seconds = float(header)
        except ValueError:
            seconds = None
        if seconds is not None and not (math.isfinite(seconds) and seconds >= 0):
            seconds = None
    if seconds is None:
        try:
            detail = str(json.loads(body() or b"{}").get("detail", ""))
        except (ValueError, AttributeError):
            detail = ""
        found = re.search(r"Try again in (\d+(?:\.\d+)?) seconds?", detail)
        seconds = float(found.group(1)) if found else 1.0
    return min(max(seconds, 0.0), MAX_WAIT)


def payload(frame: Frame, text: str, max_output_tokens: int) -> dict:
    """The /judge request: the instruction, the text, the schema, the answer's
    cap, and the frame's temperature if it names one. With reasoning, the call's
    cap is split: the answer keeps ANSWER_TOKENS and the thought the rest."""
    schema, _ = output_schema(frame)
    body = {
        "instructions": frame.instruction,
        "input": text,
        "schema": schema,
        "max_tokens": max_output_tokens,
    }
    if "temperature" in frame.battery:
        body["temperature"] = frame.battery["temperature"]
    if frame.battery.get("reasoning"):
        if max_output_tokens <= ANSWER_TOKENS:  # a thought of no tokens is no request
            raise BatteryError(
                f"a cap of {max_output_tokens} output tokens leaves no room "
                f"for a thought beside the answer's {ANSWER_TOKENS}"
            )
        body["max_tokens"] = ANSWER_TOKENS
        body["reasoning"] = True
        body["max_reasoning_tokens"] = min(max_output_tokens - ANSWER_TOKENS, MAX_THOUGHT_TOKENS)
    return body


def _read(line: dict, reply: dict) -> tuple[dict, str | None]:
    """What a reply holds for the record, its text, usage and what served it,
    and an opening where it gives no answer: a pin it breaks, a cut, no JSON,
    or a schema it breaks. `served` says whether Gemma thought where eGemma
    reports its reasoning tokens: eGemma's word, never guessed."""
    text = str(reply.get("text", ""))
    reported = reply.get("usage")
    usage = {
        k: v
        for k, v in (reported if isinstance(reported, dict) else {}).items()
        if isinstance(v, int) and not isinstance(v, bool)
    }
    served = f"{reply.get('model', '')}@{reply.get('revision', '')}".strip("@")[:200]
    if "reasoning_tokens" in usage:
        served = f"{served} (thinking {'on' if usage['reasoning_tokens'] else 'off'})".strip()
    seen = {"raw": text, "usage": usage, "served": served}
    for pin in ("model", "revision"):
        if pin in line and reply.get(pin) != line[pin]:
            return seen, f"eGemma served {pin} {reply.get(pin)!r}; the frame pins {line[pin]!r}"
    if reply.get("truncated"):
        return seen, "the answer was cut at its token cap"
    if reply.get("answer") is None:
        return seen, "the answer is not JSON"
    if reply.get("valid") is False:
        # eGemma checks the whole schema; its grammar cannot hold every keyword.
        violations = reply.get("violations")
        first = violations[0] if isinstance(violations, list) and violations else {}
        first = first if isinstance(first, dict) else {}
        where = f"{first.get('path', '')} {first.get('message', '')}".strip()
        opening = "the answer breaks its schema" + (f" ({where!r})" if where else "")
        return seen, opening[:300]
    return seen, None


class EGemma:
    """`battery: {"kind": "egemma"}`"""

    name = "egemma"

    def __init__(
        self,
        url: str = DEFAULT_URL,
        timeout: float = 120.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.url, self.timeout, self.sleep = loopback(url, "eGemma"), timeout, sleep
        self.clock = clock
        self.budget: tuple[int, float] | None = None  # (calls, seconds), from /rate-limits
        self.starts: deque[float] = deque()

    def read_budget(self) -> None:
        """The judge budget eGemma publishes; without one, only the backoff."""
        parsed = urlparse(self.url)
        request = urllib.request.Request(f"{parsed.scheme}://{parsed.netloc}/rate-limits")
        try:
            with opener().open(request, timeout=10) as response:
                limits = json.loads(response.read(MAX_RESPONSE_BYTES))
            calls, seconds = limits["judge"]["calls"], limits["judge"]["seconds"]
        except (OSError, ValueError, KeyError, TypeError):
            self.budget = None
            return
        valid = isinstance(calls, int) and not isinstance(calls, bool) and calls >= 1
        valid = valid and isinstance(seconds, int | float) and not isinstance(seconds, bool)
        valid = valid and math.isfinite(seconds) and seconds > 0
        self.budget = (calls, float(seconds)) if valid else None

    def pace(self) -> None:
        """Wait until one more call fits the budget's window, then count it."""
        if self.budget is None:
            return
        calls, seconds = self.budget

        def prune(now: float) -> None:  # eGemma counts the calls of the last `seconds`
            while self.starts and now - self.starts[0] >= seconds:
                self.starts.popleft()

        now = self.clock()
        prune(now)
        if len(self.starts) >= calls:
            self.sleep(self.starts[0] + seconds - now)
            now = self.clock()
            prune(now)
        self.starts.append(now)

    def trains(self, frame: Frame) -> bool:
        """Never: what it reads stays on this machine."""
        return False

    def check(self, frame: Frame) -> None:
        """Refuse, before any call, a frame this battery must not serve:
        another battery's, an unknown key, a temperature outside 0 to 2, an
        empty pin, reasoning that is not true or false, or no key; then read the
        budget eGemma publishes."""
        battery = frame.battery
        if battery.get("kind") != self.name:
            raise BatteryError(f"this frame asks for battery {battery.get('kind')!r}")
        unknown = set(battery) - BATTERY_KEYS
        if unknown:
            raise BatteryError(
                f"the eGemma battery reads no {quoted(sorted(unknown))} under battery"
            )
        temperature = battery.get("temperature", 0.7)
        if isinstance(temperature, bool) or not isinstance(temperature, int | float):
            raise BatteryError("battery.temperature is a number between 0 and 2")
        if not 0 <= temperature <= 2:
            raise BatteryError("battery.temperature is a number between 0 and 2")
        if not isinstance(battery.get("reasoning", False), bool):
            raise BatteryError("battery.reasoning is true or false")
        check_output(battery)
        for pin in ("model", "revision"):
            if pin in battery and not (isinstance(battery[pin], str) and battery[pin]):
                raise BatteryError("battery.model and revision name what eGemma must serve")
        _key()  # no key, no run: refuse before the first call, not at each
        self.read_budget()

    def observe(self, frame: Frame, prompt: str, max_output_tokens: int) -> Observation:
        """One /judge call, paced to eGemma's budget and retried while it is
        busy: the label at the frame's pointer, or an opening that says why
        there is none."""
        if frame.battery.get("reasoning") and max_output_tokens <= ANSWER_TOKENS:
            return Observation(
                label=None,
                opening=f"a cap of {max_output_tokens} output tokens leaves no room "
                f"for a thought beside the answer's {ANSWER_TOKENS}",
                usage={"output_tokens": 0},  # no call was made, so a token budget spent none
            )
        reply = self._judge(payload(frame, prompt, max_output_tokens))
        if isinstance(reply, Observation):
            return reply
        seen, opening = _read(frame.battery, reply)
        if opening is not None:
            return Observation(label=None, opening=opening, **seen)
        label, opening = label_at(reply["answer"], frame)
        if label is None:
            return Observation(label=None, opening=opening, **seen)
        return Observation(label=label, **seen)

    def _judge(self, body: dict) -> dict | Observation:
        # one /judge request, paced to eGemma's budget and retried while it is
        # busy: its reply, a JSON object, or an opening that says why there is
        # none; the battery and an eGemma maker that shares it share the pace
        request = urllib.request.Request(
            self.url,
            data=json.dumps(body).encode(),
            method="POST",
            headers={"content-type": "application/json", "authorization": f"Bearer {_key()}"},
        )
        attempt = 0
        while True:  # each pass reads an answer, opens, or waits and tries again
            self.pace()  # a retry is a call too: eGemma's limiter counts it
            deadline = self.clock() + self.timeout  # waits for eGemma's pace are not the call's
            try:
                with opened(request, self.timeout) as response:
                    got = read_reply(response, deadline, self.clock)
                break
            except Late as late:  # what had arrived is kept, never read as an answer
                return Observation(label=None, opening="the call passed its timeout", raw=late.text)
            except urllib.error.HTTPError as error:
                if error.code not in BUSY or attempt == RETRIES:
                    tried = f" after {attempt} retries" if attempt else ""
                    return Observation(label=None, opening=f"eGemma answered {error.code}{tried}")
                self.sleep(_wait(error, partial(read_error, error, deadline, self.clock)))
            except (TimeoutError, urllib.error.URLError, OSError) as error:
                reason = getattr(error, "reason", error)
                if isinstance(reason, TimeoutError):
                    return Observation(label=None, opening="the call passed its timeout")
                return Observation(
                    label=None, opening=f"eGemma could not be reached ({type(reason).__name__})"
                )
            attempt += 1
        if len(got) > MAX_RESPONSE_BYTES:
            return Observation(label=None, opening="the answer exceeded the size cap")
        try:
            reply = json.loads(got)
        except json.JSONDecodeError:
            return Observation(label=None, opening="eGemma's reply is not JSON")
        if not isinstance(reply, dict):
            return Observation(label=None, opening="eGemma's reply is not a JSON object")
        return reply


class EGemmaMaker:
    """A maker on this machine's eGemma, for a crossing or a branch: it writes
    from the text it is given under its line's instruction, held to one string
    field, and nothing leaves this machine.

        "maker": {"kind": "egemma", "reasoning": true,
                  "instruction": "Take the claim apart, ..."}

    With `reasoning: true`, Gemma thinks before it writes: the call's cap is
    split, the text keeping STEP_TOKENS and the thought the rest, up to
    MAX_THOUGHT_TOKENS, and a cap with no room for a thought is an opening.
    Given an `EGemma`, it shares that battery's pace, so a branch's maker and
    reader stay within eGemma's budget together. It never trains."""

    name = "egemma"

    def __init__(self, egemma: EGemma | None = None):
        self.egemma = egemma if egemma is not None else EGemma()

    def trains(self, line: dict) -> bool:
        """Never: what it reads stays on this machine."""
        return False

    def check(self, line: dict) -> None:
        """Refuse, before any call, a maker line it must not serve: an unknown
        key, no instruction, a temperature outside 0 to 2, reasoning that is
        not true or false, an empty pin, or no key; then read eGemma's budget."""
        unknown = set(line) - MAKER_KEYS
        if unknown:
            raise BatteryError(f"the eGemma maker reads no {quoted(sorted(unknown))}")
        instruction = line.get("instruction")
        if not isinstance(instruction, str) or not instruction.strip():
            raise BatteryError("battery.maker.instruction says what the maker writes")
        temperature = line.get("temperature", 0.7)
        if isinstance(temperature, bool) or not isinstance(temperature, int | float):
            raise BatteryError("battery.maker.temperature is a number between 0 and 2")
        if not 0 <= temperature <= 2:
            raise BatteryError("battery.maker.temperature is a number between 0 and 2")
        if not isinstance(line.get("reasoning", False), bool):
            raise BatteryError("battery.maker.reasoning is true or false")
        for pin in ("model", "revision"):
            if pin in line and not (isinstance(line[pin], str) and line[pin]):
                raise BatteryError("battery.maker.model and revision name what eGemma must serve")
        _key()  # no key, no run: refuse before the first call
        self.egemma.read_budget()

    def check_cap(self, line: dict, cap: int) -> None:
        """Refuse, before any call, a share of the cap with no room for a
        thought beside the text, where the line asks Gemma to think."""
        if line.get("reasoning") and cap <= STEP_TOKENS:
            raise BatteryError(
                f"a share of {cap!r} output tokens leaves the eGemma maker no room "
                f"for a thought beside its text's {STEP_TOKENS!r}",
                "raise --output-tokens, so that the maker's share holds a thought",
            )

    def make(self, line: dict, text: str, max_output_tokens: int) -> Made:
        """One /judge call: the text Gemma wrote, or an opening that says why
        there is none."""
        body = {
            "instructions": line["instruction"],
            "input": text,
            "schema": WRITTEN,
            "max_tokens": min(max_output_tokens, STEP_TOKENS),
        }
        if "temperature" in line:
            body["temperature"] = line["temperature"]
        if line.get("reasoning"):
            if max_output_tokens <= STEP_TOKENS:  # a thought of no tokens is no request
                opening = (
                    f"a cap of {max_output_tokens} output tokens leaves no room "
                    f"for a thought beside the text's {STEP_TOKENS!r}"
                )
                return Made(None, opening=opening, usage={"output_tokens": 0})
            body["max_tokens"] = STEP_TOKENS
            body["reasoning"] = True
            body["max_reasoning_tokens"] = min(max_output_tokens - STEP_TOKENS, MAX_THOUGHT_TOKENS)
        reply = self.egemma._judge(body)
        if isinstance(reply, Observation):
            return Made(None, opening=reply.opening, raw=reply.raw, usage=reply.usage)
        seen, opening = _read(line, reply)
        if opening is None:
            answer = reply["answer"]
            written = answer.get("text") if isinstance(answer, dict) else None
            if isinstance(written, str):
                return Made(written, **seen)
            opening = "the answer holds no text"
        return Made(None, opening=opening, **seen)
