"""An LLM critic through the unified model router.

The router (github.com/mirzahusadzic/codex-unified-model-router) serves the
Responses API on loopback and picks the upstream from the model slug: Claude
runs on Anthropic's API, other slugs on DeepSeek, OpenRouter or OpenAI.

What this battery promises, whatever the frame says:
- it talks only to a router on this machine (loopback);
- it sends no tools: the router's web search runs on another provider, and a
  body would leave the model's own provider with it;
- it refuses a model whose provider trains on its inputs unless the frame
  names that model under `battery.trainsOnInputs`;
- it uses no proxy and follows no redirect, so the body and the token go to
  the loopback address named and nowhere else;
- each call has a timeout, the budget's cap on output tokens, and a cap on
  what it reads back;
- the router's token comes from the environment or the router's own env file
  and is never logged, returned or recorded.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from ..frame import Frame
from ..types import Observation

DEFAULT_URL = "http://127.0.0.1:18766/v1/responses"
ENV_FILE = Path.home() / ".codex" / "unified-router" / "openrouter.env"
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
# Slugs whose provider trains on what it receives (the router's own warning).
TRAINS_ON_INPUTS = ("ultra-spark/", "openrouter/meta/")
MAX_RESPONSE_BYTES = 1_000_000
LINE_LIMIT = 65_536


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # a redirect becomes an HTTPError
        return None


def _opener() -> urllib.request.OpenerDirector:
    """No proxy from the environment, no redirect: only the address named is
    called. Built per call, so no environment read at import can linger."""
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


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


def read_label(text: str, labels: tuple[str, ...]) -> str | None:
    """The one label the answer names as a whole word, or None (none, or more
    than one: an answer that hedges between labels is no reading)."""
    found = {
        label
        for label in labels
        if re.search(rf"(?<![\w-]){re.escape(label)}(?![\w-])", text, re.IGNORECASE)
    }
    return found.pop() if len(found) == 1 else None


def payload(frame: Frame, model: str, text: str, max_output_tokens: int) -> dict:
    """The request body. No `tools` key, ever."""
    instruction = f"{frame.instruction}\n\nAnswer with exactly one of: {', '.join(frame.labels)}."
    return {
        "model": model,
        "instructions": instruction,
        "input": [{"role": "user", "content": [{"type": "input_text", "text": text}]}],
        "max_output_tokens": max_output_tokens,
        "store": False,
        "stream": True,
    }


def _lines(response):
    """The response's lines, none read longer than LINE_LIMIT."""
    while line := response.readline(LINE_LIMIT):
        yield line


def parse_stream(lines) -> tuple[str, dict[str, int], str | None]:
    """The answer's text, its usage, and an opening if the call did not
    complete, from the router's server-sent events."""
    deltas: list[str] = []
    usage: dict[str, int] = {}
    final_text = ""
    status = None
    read = 0
    for raw in lines:
        read += len(raw)
        if read > MAX_RESPONSE_BYTES:
            return "".join(deltas), usage, "the answer exceeded the size cap"
        line = raw.decode("utf-8", "replace").strip() if isinstance(raw, bytes) else raw.strip()
        if not line.startswith("data:"):
            continue
        try:
            event = json.loads(line[5:].strip())
        except json.JSONDecodeError:
            continue
        kind = event.get("type")
        if kind == "response.output_text.delta":
            deltas.append(str(event.get("delta", "")))
        elif kind in ("response.completed", "response.failed", "response.incomplete"):
            response = event.get("response") or {}
            status = kind.rsplit(".", 1)[1]
            for key, value in (response.get("usage") or {}).items():
                if isinstance(value, int):
                    usage[key] = value
            for item in response.get("output") or []:
                for part in item.get("content") or []:
                    if part.get("type") == "output_text":
                        final_text += part.get("text", "")
    text = "".join(deltas) or final_text
    if status != "completed":
        return text, usage, f"the call ended {status or 'without completing'}"
    return text, usage, None


class RouterCritic:
    """`battery: {"kind": "router-critic", "model": "anthropic/claude-sonnet-5-5"}`"""

    name = "router-critic"

    def __init__(self, url: str = DEFAULT_URL, timeout: float = 120.0):
        parsed = urlparse(url)
        if parsed.scheme != "http" or parsed.hostname not in LOOPBACK:
            raise ValueError(f"the router must be on this machine over http, not {url}")
        self.url, self.timeout = url, timeout

    def check(self, frame: Frame) -> None:
        battery = frame.battery
        if battery.get("kind") != self.name:
            raise ValueError(f"this frame asks for the {battery.get('kind')} battery")
        model = battery.get("model")
        if not isinstance(model, str) or "/" not in model:
            raise ValueError("battery.model is a routed slug such as anthropic/claude-sonnet-5-5")
        if battery.get("tools"):
            raise ValueError("the critic sends no tools")
        if model.startswith(TRAINS_ON_INPUTS) and model not in (
            battery.get("trainsOnInputs") or []
        ):
            raise ValueError(
                f"{model}'s provider trains on its inputs; "
                "name it under battery.trainsOnInputs to send the body there"
            )
        _token()  # no token, no run: refuse before the first call, not at each

    def observe(self, frame: Frame, prompt: str, max_output_tokens: int) -> Observation:
        body = json.dumps(
            payload(frame, frame.battery["model"], prompt, max_output_tokens)
        ).encode()
        request = urllib.request.Request(
            self.url,
            data=body,
            method="POST",
            headers={"content-type": "application/json", "x-codex-router-token": _token()},
        )
        try:
            with _opener().open(request, timeout=self.timeout) as response:
                if response.headers.get("x-codex-router-diagnostic"):
                    diagnostic = response.headers["x-codex-router-diagnostic"][:200]
                    return Observation(label=None, opening=f"router diagnostic: {diagnostic}")
                text, usage, opening = parse_stream(_lines(response))
        except urllib.error.HTTPError as error:
            return Observation(label=None, opening=f"the router answered {error.code}")
        if opening:
            return Observation(label=None, opening=opening, raw=text, usage=usage)
        label = read_label(text, frame.labels)
        if label is None:
            return Observation(
                label=None, opening="no single label in the answer", raw=text, usage=usage
            )
        return Observation(label=label, raw=text, usage=usage)
