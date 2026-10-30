"""The unified battery: an LLM critic through the unified model router.

The router (github.com/mirzahusadzic/codex-unified-model-router) serves the
Responses API on loopback and maps a model slug to its provider:
`anthropic/...` runs on Anthropic's API, `openrouter/...` and `deepseek/...`
on OpenRouter (DeepSeek's models through it), each with the router's own key. One battery covers
them all; calling a provider's own endpoint is a different battery (a native
one). An unprefixed slug is OpenAI's, which the router reaches only with the
caller's Codex sign-in: this battery refuses it.

The critic answers in JSON to a schema, by default `{"label": <one of the
frame's labels>}`. A critic of your own (its output schema, as your project
already has it) is adapted by saying where in its answer the label is:

    "battery": {"kind": "unified", "model": "anthropic/claude-sonnet-5-5",
                "reasoning": "low",
                "output": {"schema": {...}, "label": "/verdict"}}

What this battery promises, whatever the frame says:
- it talks only to a router on this machine (loopback);
- it sends no tools: the router's web search runs on another provider, and a
  body would leave the model's own provider with it;
- it refuses a model whose provider trains on its inputs unless the frame
  names that model under `battery.trainsOnInputs`, and asks every other
  request to reach only endpoints that keep no data (`data_collection: deny`;
  which endpoints serve a model is the OpenRouter account's provider setting,
  and DeepSeek's own endpoint may train on prompts);
- it uses no proxy and follows no redirect, so the body and the token go to
  the loopback address named and nowhere else;
- each call has a deadline (`timeout` seconds for the whole answer), the
  budget's cap on output tokens, and a cap on what it reads back;
- each record names what served it: the model the response names and the
  endpoint the router reports; `endpoints` pins OpenRouter endpoints, in
  order and without fallbacks, so one endpoint reads a quorum;
- the router's token comes from the environment or the router's own env file
  and is never logged, returned or recorded.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from ..frame import Frame
from ..types import Observation
from .critic import MAX_RESPONSE_BYTES, check_output, loopback, opener, output_schema, read_label

DEFAULT_URL = "http://127.0.0.1:18766/v1/responses"
ENV_FILE = Path.home() / ".codex" / "unified-router" / "openrouter.env"
# Slugs whose provider trains on what it receives (the router's own warning).
TRAINS_ON_INPUTS = ("ultra-spark/", "openrouter/meta/")
# The router's diagnostic when OpenRouter has no endpoint for the model that
# keeps no data: which endpoints serve a model is the OpenRouter account's
# provider setting (DeepSeek's own endpoint may train on prompts).
NO_ENDPOINT_WITHOUT_DATA = "openrouter-data-policy"
EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh", "max")
# Providers the router reaches with its own keys. An unprefixed slug is OpenAI's,
# which the router reaches only with the caller's Codex sign-in.
ROUTED_PREFIXES = ("anthropic/", "openrouter/", "deepseek/", "ultra-spark/")
BATTERY_KEYS = {"kind", "model", "reasoning", "output", "trainsOnInputs", "tools", "endpoints"}
LINE_LIMIT = 65_536


def _token() -> str:
    token = os.environ.get("CODEX_ROUTER_TOKEN", "")
    if not token and ENV_FILE.is_file():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "CODEX_ROUTER_TOKEN":
                token = value.strip().strip("'\"")
    if not re.fullmatch(r"[0-9a-f]{64}", token):
        raise RuntimeError("no router token: set CODEX_ROUTER_TOKEN or install the router")
    return token


def consented(battery: dict) -> bool:
    """Whether the frame lets this model go where inputs train: its slug,
    exactly, in the list under trainsOnInputs (a string is no list)."""
    named = battery.get("trainsOnInputs")
    return isinstance(named, list) and battery["model"] in named


def payload(frame: Frame, text: str, max_output_tokens: int) -> dict:
    """The request body. No `tools` key, ever."""
    battery = frame.battery
    schema, _ = output_schema(frame)
    body = {
        "model": battery["model"],
        "instructions": frame.instruction,
        "input": [{"role": "user", "content": [{"type": "input_text", "text": text}]}],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "observation",
                "schema": schema,
                "strict": True,
            }
        },
        "max_output_tokens": max_output_tokens,
        "store": False,
        "stream": True,
    }
    if battery.get("reasoning"):
        body["reasoning"] = {"effort": battery["reasoning"]}
    provider = {}
    if battery.get("endpoints"):
        # One endpoint reads every run, or the call fails: the router's own
        # endpoint preference applies only to a request that names none.
        provider.update(order=list(battery["endpoints"]), allow_fallbacks=False)
    if not consented(battery):
        # OpenRouter then reaches only endpoints that keep no data to train on.
        provider["data_collection"] = "deny"
    if provider:
        body["provider"] = provider
    return body


def _lines(response):
    """The response's lines, none read longer than LINE_LIMIT."""
    while line := response.readline(LINE_LIMIT):
        yield line


def parse_stream(
    lines, deadline: float | None = None, clock=time.monotonic
) -> tuple[str, dict[str, int], str | None, str]:
    """The answer's text, its usage, an opening if the call did not complete,
    and the model the response names, from the router's server-sent events.
    A stream still coming at `deadline` (on `clock`) is cut there."""
    deltas: list[str] = []
    usage: dict[str, int] = {}
    final_text = ""
    status = None
    model = ""
    read = 0
    for raw in lines:
        read += len(raw)
        if read > MAX_RESPONSE_BYTES:
            return "".join(deltas), usage, "the answer exceeded the size cap", model
        if deadline is not None and clock() > deadline:
            return "".join(deltas), usage, "the call passed its timeout", model
        line = raw.decode("utf-8", "replace").strip() if isinstance(raw, bytes) else raw.strip()
        if not line.startswith("data:"):
            continue
        try:
            event = json.loads(line[5:].strip())
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        kind = event.get("type")
        if kind == "response.output_text.delta":
            deltas.append(str(event.get("delta", "")))
        elif kind in ("response.completed", "response.failed", "response.incomplete"):
            response = event.get("response")
            response = response if isinstance(response, dict) else {}
            status = kind.rsplit(".", 1)[1]
            if isinstance(response.get("model"), str):
                model = response["model"]
            reported = response.get("usage")
            for key, value in (reported if isinstance(reported, dict) else {}).items():
                if isinstance(value, int):
                    usage[key] = value
            for item in response.get("output") or []:
                for part in item.get("content") or [] if isinstance(item, dict) else []:
                    if isinstance(part, dict) and part.get("type") == "output_text":
                        final_text += str(part.get("text", ""))
    text = "".join(deltas) or final_text
    if status != "completed":
        return text, usage, f"the call ended {status or 'without completing'}", model
    return text, usage, None, model


class Unified:
    """`battery: {"kind": "unified", "model": "anthropic/claude-sonnet-5-5"}`"""

    name = "unified"

    def __init__(
        self,
        url: str = DEFAULT_URL,
        timeout: float = 120.0,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.url, self.timeout, self.clock = loopback(url, "the router"), timeout, clock

    def check(self, frame: Frame) -> None:
        battery = frame.battery
        if battery.get("kind") != self.name:
            raise ValueError(f"this frame asks for the {battery.get('kind')} battery")
        unknown = set(battery) - BATTERY_KEYS
        if unknown:
            raise ValueError(f"the unified battery reads no {sorted(unknown)}")
        model = battery.get("model")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("battery.model is a slug the router serves (GET /v1/models)")
        if not model.startswith(ROUTED_PREFIXES):
            raise ValueError(
                f"{model} is an OpenAI slug: the router reaches OpenAI only with the "
                "caller's Codex sign-in, which this battery does not send"
            )
        if battery.get("tools"):
            raise ValueError("the critic sends no tools")
        endpoints = battery.get("endpoints", ["any"])
        if not (
            isinstance(endpoints, list)
            and endpoints
            and all(isinstance(e, str) and e for e in endpoints)
        ):
            raise ValueError("battery.endpoints lists OpenRouter endpoint tags, in order")
        if battery.get("reasoning") not in (None, *EFFORTS):
            raise ValueError(f"battery.reasoning is one of {', '.join(EFFORTS)}")
        check_output(battery)
        named = battery.get("trainsOnInputs", [])
        if not (isinstance(named, list) and all(isinstance(m, str) and m for m in named)):
            raise ValueError("battery.trainsOnInputs lists the model slugs that may train")
        if model.startswith(TRAINS_ON_INPUTS) and not consented(battery):
            raise ValueError(
                f"{model}'s provider trains on its inputs; "
                "name it under battery.trainsOnInputs to send the body there"
            )
        _token()  # no token, no run: refuse before the first call, not at each

    def observe(self, frame: Frame, prompt: str, max_output_tokens: int) -> Observation:
        body = json.dumps(payload(frame, prompt, max_output_tokens)).encode()
        request = urllib.request.Request(
            self.url,
            data=body,
            method="POST",
            headers={"content-type": "application/json", "x-codex-router-token": _token()},
        )
        deadline = self.clock() + self.timeout
        try:
            with opener().open(request, timeout=self.timeout) as response:
                if response.headers.get("x-codex-router-diagnostic"):
                    diagnostic = response.headers["x-codex-router-diagnostic"][:200]
                    if diagnostic == NO_ENDPOINT_WITHOUT_DATA:
                        return Observation(
                            label=None,
                            opening="no endpoint that keeps no data serves this model (the "
                            "OpenRouter account's provider setting); naming it under "
                            "trainsOnInputs allows one that may train",
                        )
                    return Observation(label=None, opening=f"router diagnostic: {diagnostic}")
                text, usage, opening, model = parse_stream(_lines(response), deadline, self.clock)
                endpoint = response.headers.get("x-provider-name", "")[:200]
        except urllib.error.HTTPError as error:
            return Observation(label=None, opening=f"the router answered {error.code}")
        served = " via ".join(part for part in (model, endpoint) if part)
        if opening:
            return Observation(label=None, opening=opening, raw=text, usage=usage, served=served)
        label, opening = read_label(text, frame)
        if label is None:
            return Observation(label=None, opening=opening, raw=text, usage=usage, served=served)
        return Observation(label=label, raw=text, usage=usage, served=served)
