"""The local-json battery: any evaluator on this machine that answers JSON.

A local classifier, test oracle or retrieval checker that already reads an
instruction and a text and answers to a schema needs no adapter of its own:
name its address in the frame and this battery calls it with the same care
the shipped critics take.

    "battery": {"kind": "local-json", "url": "http://127.0.0.1:8765/judge",
                "timeout": 30, "output": {"schema": {...}, "label": "/verdict"}}

The evaluator receives `{"instructions", "input", "schema", "max_tokens"}`
and answers `{"answer", "text", "usage", "served"}`: `answer` is the JSON
the label is read from (at `/label`, or the frame's own pointer), `served`
names what read it.

What this battery promises, whatever the frame says:
- it talks only to the address named, on this machine (loopback), over
  plain http, through no proxy and no redirect;
- it sends the instruction, the exact prompt, the schema and the answer's
  cap, and nothing else: no credentials, no tools;
- each call has a deadline (`timeout` seconds for the whole reply, 30 by
  default) and a cap on what it reads back;
- a reply it cannot read is an opening, never a guessed label, and each
  record names what the evaluator says served it.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable

from ..frame import Frame
from ..types import Observation
from .critic import (
    MAX_RESPONSE_BYTES,
    Late,
    check_output,
    label_at,
    loopback,
    opener,
    output_schema,
    read_reply,
)

BATTERY_KEYS = {"kind", "url", "timeout", "output"}
DEFAULT_TIMEOUT = 30.0
MAX_TIMEOUT = 3600  # a whole call, in seconds: an hour is already more than a reader needs


def payload(frame: Frame, text: str, max_output_tokens: int) -> dict:
    """The request: the frame's instruction, the exact prompt, the schema the
    answer is held to, and the answer's cap."""
    schema, _ = output_schema(frame)
    return {
        "instructions": frame.instruction,
        "input": text,
        "schema": schema,
        "max_tokens": max_output_tokens,
    }


class LocalJSON:
    """`battery: {"kind": "local-json", "url": "http://127.0.0.1:8765/judge"}`"""

    name = "local-json"

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self.clock = clock

    def check(self, frame: Frame) -> None:
        """Refuse, before any call, a frame this battery must not serve:
        another battery's, an unknown key, an address off this machine, a
        timeout that is not a positive number of seconds, or an output that
        does not point at its label."""
        battery = frame.battery
        if battery.get("kind") != self.name:
            raise ValueError(f"this frame asks for the {battery.get('kind')} battery")
        unknown = set(battery) - BATTERY_KEYS
        if unknown:
            raise ValueError(f"the local-json battery reads no {sorted(unknown)}")
        if not isinstance(battery.get("url"), str):
            raise ValueError("battery.url is the evaluator's address on this machine")
        loopback(battery["url"], "the evaluator")
        timeout = battery.get("timeout", DEFAULT_TIMEOUT)
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, int | float)
            or not 0 < timeout <= MAX_TIMEOUT
        ):
            raise ValueError(f"battery.timeout is a number of seconds, up to {MAX_TIMEOUT}")
        check_output(battery)

    def observe(self, frame: Frame, prompt: str, max_output_tokens: int) -> Observation:
        """One call to the evaluator: the label at the frame's pointer, or an
        opening that says why there is none."""
        battery = frame.battery
        url = loopback(battery["url"], "the evaluator")
        timeout = float(battery.get("timeout", DEFAULT_TIMEOUT))
        request = urllib.request.Request(
            url,
            data=json.dumps(payload(frame, prompt, max_output_tokens)).encode(),
            method="POST",
            headers={"content-type": "application/json"},
        )
        deadline = self.clock() + timeout
        try:
            with opener().open(request, timeout=timeout) as response:
                body = read_reply(response, deadline, self.clock)
        except Late as late:  # what had arrived is kept, never read as an answer
            return Observation(label=None, opening="the call passed its timeout", raw=late.text)
        except urllib.error.HTTPError as error:
            return Observation(label=None, opening=f"the evaluator answered {error.code}")
        except (TimeoutError, urllib.error.URLError, OSError) as error:
            reason = getattr(error, "reason", error)
            if isinstance(reason, TimeoutError):
                return Observation(label=None, opening="the call passed its timeout")
            return Observation(
                label=None, opening=f"the evaluator could not be reached: {type(reason).__name__}"
            )
        if len(body) > MAX_RESPONSE_BYTES:
            return Observation(label=None, opening="the answer exceeded the size cap")
        try:
            reply = json.loads(body)
        except json.JSONDecodeError:
            return Observation(label=None, opening="the evaluator's reply is not JSON")
        if not isinstance(reply, dict):
            return Observation(label=None, opening="the evaluator's reply is not a JSON object")
        reported = reply.get("usage")
        seen = {
            "raw": str(reply.get("text", "")),
            "usage": {
                k: v
                for k, v in (reported if isinstance(reported, dict) else {}).items()
                if isinstance(v, int) and not isinstance(v, bool)
            },
            "served": str(reply.get("served") or "")[:200],
        }
        if reply.get("answer") is None:
            return Observation(label=None, opening="the answer is not JSON", **seen)
        label, opening = label_at(reply["answer"], frame)
        if label is None:
            return Observation(label=None, opening=opening, **seen)
        return Observation(label=label, **seen)
