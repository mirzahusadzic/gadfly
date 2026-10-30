"""The eGemma battery: Gemma 4 on this machine, through eGemma's /judge.

eGemma (github.com/mirzahusadzic/egemma) reads the prompt under the frame's
instruction, with no persona added, and a grammar holds its answer to the
schema: by default `{"label": <one of the frame's labels>}`, or a critic's own
schema with the label's place named, as for the unified battery. Nothing
leaves this machine, and nothing is cached, so the quorum's runs are fresh
samples; at `temperature: 0` the battery is close to deterministic.

    "battery": {"kind": "egemma", "temperature": 0.7}

What this battery promises, whatever the frame says:
- it talks only to an eGemma on this machine (loopback), through no proxy
  and no redirect;
- each call has a deadline (`timeout` seconds for the whole reply), the
  budget's cap on output tokens, and a cap on what it reads back;
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
import os
import re
import time
import urllib.error
import urllib.request
from collections import deque
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

from ..frame import Frame
from ..types import Observation
from .critic import MAX_RESPONSE_BYTES, check_output, label_at, loopback, opener, output_schema

DEFAULT_URL = os.environ.get("EGEMMA_URL", "http://127.0.0.1:8000").rstrip("/") + "/judge"
BATTERY_KEYS = {"kind", "temperature", "output", "model", "revision"}
BUSY = (429, 503)  # eGemma's rate limit, and its queue when full
RETRIES = 3
MAX_WAIT = 60.0


def _key() -> str:
    path = os.environ.get("EGEMMA_API_KEY_FILE")
    if path:
        key = Path(path).read_text(encoding="utf-8").strip()
        if not key:
            raise RuntimeError("EGEMMA_API_KEY_FILE names an empty file")
        return key
    key = os.environ.get("EGEMMA_API_KEY") or os.environ.get("WORKBENCH_API_KEY")
    if not key:
        raise RuntimeError("no eGemma key: set EGEMMA_API_KEY_FILE or EGEMMA_API_KEY")
    return key


def _wait(error: urllib.error.HTTPError) -> float:
    """How long eGemma asks a busy caller to wait: its Retry-After header, or
    the seconds its rate limiter names in the detail; at most MAX_WAIT."""
    header = error.headers.get("retry-after") if error.headers else None
    seconds = None
    if header is not None:
        try:
            seconds = float(header)
        except ValueError:
            seconds = None
    if seconds is None:
        try:
            detail = str(json.loads(error.read(4096) or b"{}").get("detail", ""))
        except (ValueError, AttributeError):
            detail = ""
        found = re.search(r"Try again in (\d+(?:\.\d+)?) seconds?", detail)
        seconds = float(found.group(1)) if found else 1.0
    return min(max(seconds, 0.0), MAX_WAIT)


def _read(response, deadline: float, clock: Callable[[], float]) -> bytes | None:
    """The reply as it comes, until it ends or passes the size cap; None if it
    is still coming at the deadline (the socket's timeout waits per read)."""
    body = bytearray()  # grown in place: an earlier chunk is never copied again
    while chunk := response.read1(65_536):
        body.extend(chunk)
        if len(body) > MAX_RESPONSE_BYTES:
            break
        if clock() > deadline:
            return None
    return bytes(body)


def payload(frame: Frame, text: str, max_output_tokens: int) -> dict:
    """The /judge request: the instruction, the text, the schema, the answer's
    cap, and the frame's temperature if it names one."""
    schema, _ = output_schema(frame)
    body = {
        "instructions": frame.instruction,
        "input": text,
        "schema": schema,
        "max_tokens": max_output_tokens,
    }
    if "temperature" in frame.battery:
        body["temperature"] = frame.battery["temperature"]
    return body


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
        valid = valid and isinstance(seconds, int | float) and seconds > 0
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

    def check(self, frame: Frame) -> None:
        """Refuse, before any call, a frame this battery must not serve:
        another battery's, an unknown key, a temperature outside 0 to 2, an
        empty pin, or no key; then read the budget eGemma publishes."""
        battery = frame.battery
        if battery.get("kind") != self.name:
            raise ValueError(f"this frame asks for the {battery.get('kind')} battery")
        unknown = set(battery) - BATTERY_KEYS
        if unknown:
            raise ValueError(f"the eGemma battery reads no {sorted(unknown)}")
        temperature = battery.get("temperature", 0.7)
        if isinstance(temperature, bool) or not isinstance(temperature, int | float):
            raise ValueError("battery.temperature is a number between 0 and 2")
        if not 0 <= temperature <= 2:
            raise ValueError("battery.temperature is a number between 0 and 2")
        check_output(battery)
        for pin in ("model", "revision"):
            if pin in battery and not (isinstance(battery[pin], str) and battery[pin]):
                raise ValueError("battery.model and revision name what eGemma must serve")
        _key()  # no key, no run: refuse before the first call, not at each
        self.read_budget()

    def observe(self, frame: Frame, prompt: str, max_output_tokens: int) -> Observation:
        """One /judge call, paced to eGemma's budget and retried while it is
        busy: the label at the frame's pointer, or an opening that says why
        there is none."""
        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload(frame, prompt, max_output_tokens)).encode(),
            method="POST",
            headers={"content-type": "application/json", "authorization": f"Bearer {_key()}"},
        )
        for attempt in range(RETRIES + 1):
            self.pace()  # a retry is a call too: eGemma's limiter counts it
            deadline = self.clock() + self.timeout  # waits for eGemma's pace are not the call's
            try:
                with opener().open(request, timeout=self.timeout) as response:
                    body = _read(response, deadline, self.clock)
                break
            except urllib.error.HTTPError as error:
                if error.code not in BUSY or attempt == RETRIES:
                    tried = f" after {attempt} retries" if attempt else ""
                    return Observation(label=None, opening=f"eGemma answered {error.code}{tried}")
                self.sleep(_wait(error))
            except (TimeoutError, urllib.error.URLError, OSError) as error:
                reason = getattr(error, "reason", error)
                if isinstance(reason, TimeoutError):
                    return Observation(label=None, opening="the call passed its timeout")
                return Observation(
                    label=None, opening=f"eGemma could not be reached: {type(reason).__name__}"
                )
        if body is None:
            return Observation(label=None, opening="the call passed its timeout")
        if len(body) > MAX_RESPONSE_BYTES:
            return Observation(label=None, opening="the answer exceeded the size cap")
        try:
            reply = json.loads(body)
        except json.JSONDecodeError:
            return Observation(label=None, opening="eGemma's reply is not JSON")
        if not isinstance(reply, dict):
            return Observation(label=None, opening="eGemma's reply is not a JSON object")
        text = str(reply.get("text", ""))
        reported = reply.get("usage")
        usage = {
            k: v
            for k, v in (reported if isinstance(reported, dict) else {}).items()
            if isinstance(v, int) and not isinstance(v, bool)
        }
        served = f"{reply.get('model', '')}@{reply.get('revision', '')}".strip("@")[:200]
        seen = {"raw": text, "usage": usage, "served": served}
        battery = frame.battery
        for pin in ("model", "revision"):
            if pin in battery and reply.get(pin) != battery[pin]:
                opening = f"eGemma served {pin} {reply.get(pin)!r}; the frame pins {battery[pin]!r}"
                return Observation(label=None, opening=opening, **seen)
        if reply.get("truncated"):
            return Observation(label=None, opening="the answer was cut at its token cap", **seen)
        if reply.get("answer") is None:
            return Observation(label=None, opening="the answer is not JSON", **seen)
        if reply.get("valid") is False:
            # eGemma checks the whole schema; its grammar cannot hold every keyword.
            violations = reply.get("violations")
            first = violations[0] if isinstance(violations, list) and violations else {}
            first = first if isinstance(first, dict) else {}
            where = f"{first.get('path', '')} {first.get('message', '')}".strip()
            opening = f"the answer breaks its schema: {where}"[:300].rstrip(": ")
            return Observation(label=None, opening=opening, **seen)
        label, opening = label_at(reply["answer"], frame)
        if label is None:
            return Observation(label=None, opening=opening, **seen)
        return Observation(label=label, **seen)
