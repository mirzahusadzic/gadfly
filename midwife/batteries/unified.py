"""The unified battery: an LLM critic through the unified model router.

The [unified model router](https://github.com/mirzahusadzic/unified-model-router)
serves the Responses API on loopback and maps a model slug to the provider
that serves it, with the router's own key: this battery sees only the router.
A slug whose provider trains on its inputs, by the router's own list, is sent
only when the frame names it exactly under `trainsOnInputs`.

One battery covers them all; calling a provider's own endpoint is a
different battery (a native one). An unprefixed slug is OpenAI's, which the
router reaches only with the caller's Codex sign-in: this battery refuses
it.

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
  names that model under `battery.trainsOnInputs`, and sends every other call
  under the router's deny data policy (`X-Codex-Router-Data-Policy: deny`),
  so the router refuses a model whose provider trains and reaches only
  endpoints that keep no data; before the first call it checks that the
  router lists the policy at `GET /health`, and refuses to run if not;
- it uses no proxy and follows no redirect, so the body and the token go to
  the loopback address named and nowhere else;
- each call has a deadline (`timeout` seconds for the whole answer), the
  budget's cap on output tokens, and a cap on what it reads back;
- each record names what served it: the model the response names, and the
  provider the router reports (`X-Codex-Router-Report: provider`, asked when
  the router lists it), or, for one pinned endpoint, that endpoint's tag;
  never a provider the router calls unknown;
- `endpoints` pins the endpoints the router may use, in order and without
  fallbacks, through the router's `X-Codex-Router-Endpoints`, so one endpoint
  reads a quorum; the router must list endpoint pins at `GET /health`;
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
from urllib.parse import urlparse

from ..errors import BatteryError, quoted
from ..frame import Frame
from ..types import Observation
from .critic import (
    MAX_RESPONSE_BYTES,
    check_output,
    loopback,
    opened,
    output_schema,
    read_error,
    read_label,
    read_reply,
    wait_at_most,
)

DEFAULT_URL = "http://127.0.0.1:18766/v1/responses"
ENV_FILE = Path.home() / ".codex" / "unified-router" / "openrouter.env"
# Slugs whose provider trains on what it receives (the router's own warning).
TRAINS_ON_INPUTS = ("ultra-spark/", "openrouter/meta/")
# The router's diagnostic when no endpoint it may use for the model keeps no
# data: which endpoints serve a model is the router's provider setting.
NO_ENDPOINT_WITHOUT_DATA = "openrouter-data-policy"
EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh", "max")
# The router's data policy for a call whose frame gives no consent to train:
# the router refuses a model whose provider trains (HTTP 409, data_policy) and
# reaches only endpoints that keep no data.
DATA_POLICY = "deny"
MAX_ENDPOINTS = 16  # the most tags the router's endpoints header takes
# Providers the router reaches with its own keys. An unprefixed slug is OpenAI's,
# which the router reaches only with the caller's Codex sign-in.
ROUTED_PREFIXES = ("anthropic/", "openrouter/", "deepseek/", "ultra-spark/")
BATTERY_KEYS = {"kind", "model", "reasoning", "output", "trainsOnInputs", "tools", "endpoints"}
CHUNK = 65_536  # the most one read asks the socket for


def _token() -> str:
    token = os.environ.get("CODEX_ROUTER_TOKEN", "")
    if not token and ENV_FILE.is_file():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "CODEX_ROUTER_TOKEN":
                token = value.strip().strip("'\"")
    if not re.fullmatch(r"[0-9a-f]{64}", token):
        raise BatteryError(
            "no router token",
            "set the environment variable CODEX_ROUTER_TOKEN, or install the router",
        )
    return token


def _code(body: bytes) -> str | None:
    # the code of the router's refusal, {"error": {"code": ...}}, if it holds one
    try:
        reply = json.loads(body)
    except ValueError:
        return None
    error = reply.get("error") if isinstance(reply, dict) else None
    return error.get("code") if isinstance(error, dict) else None


def consented(battery: dict) -> bool:
    """Whether the frame lets this model go where inputs train: its slug,
    exactly, in the list under trainsOnInputs (a string is no list)."""
    named = battery.get("trainsOnInputs")
    return isinstance(named, list) and battery["model"] in named


def policy(frame: Frame) -> dict[str, str]:
    """The router's headers each call of this frame sends: the deny data
    policy, unless the frame names its model under trainsOnInputs."""
    return _policy(frame.battery)


def pinned(frame: Frame) -> dict[str, str]:
    """The router's header that pins this frame's endpoints, in order and
    without fallbacks; none when the frame names none."""
    return _pinned(frame.battery)


def _policy(battery: dict) -> dict[str, str]:
    return {} if consented(battery) else {"x-codex-router-data-policy": DATA_POLICY}


def _pinned(battery: dict) -> dict[str, str]:
    endpoints = battery.get("endpoints")
    return {"x-codex-router-endpoints": ",".join(endpoints)} if endpoints else {}


def capabilities(url: str, timeout: float) -> dict:
    """What the router lists under `capabilities` at its health address,
    which takes no token; empty when it lists nothing. The whole answer, its
    body too, is read within `timeout` seconds."""
    deadline = time.monotonic() + timeout
    try:
        with opened(urllib.request.Request(url, method="GET"), timeout) as response:
            reply = json.loads(read_reply(response, deadline, time.monotonic))
    except (urllib.error.URLError, OSError, ValueError):
        raise BatteryError(
            f"the router at {url!r} could not be asked what it takes",
            "start the router, or install it",
        ) from None
    found = reply.get("capabilities") if isinstance(reply, dict) else None
    return found if isinstance(found, dict) else {}


def payload(frame: Frame, text: str, max_output_tokens: int) -> dict:
    """The request body. No `tools` key, ever; the data policy and the
    endpoints go in the router's headers (`policy`, `pinned`)."""
    schema, _ = output_schema(frame)
    return request_body(frame.battery, frame.instruction, text, schema, max_output_tokens)


def request_body(
    battery: dict, instructions: str, text: str, schema: dict, max_output_tokens: int
) -> dict:
    """A request for one answer to `schema`, under `instructions`, from the
    battery line's model: what `payload` sends for a frame, and what a maker
    sends for an artefact. No `tools` key, ever."""
    if not isinstance(battery.get("model"), str) or not battery["model"].strip():
        raise BatteryError("battery.model is a slug the router serves (GET /v1/models)")
    body = {
        "model": battery["model"],
        "instructions": instructions,
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
    return body


def _lines(response, deadline: float | None = None, clock=time.monotonic):
    """The response's lines as they arrive. It reads what the socket has, in
    chunks, and joins a line across them, so an event longer than a chunk
    arrives whole; each read waits at most until the deadline, so a stream
    that never ends a line is still cut there (TimeoutError)."""
    pending = bytearray()
    while True:
        if deadline is not None:
            left = deadline - clock()
            if left <= 0:
                raise TimeoutError("the call passed its timeout")
            wait_at_most(response, left)
        chunk = response.read1(CHUNK)
        if not chunk:
            break
        pending += chunk
        while (end := pending.find(b"\n")) >= 0:
            yield bytes(pending[: end + 1])
            del pending[: end + 1]
        if len(pending) > MAX_RESPONSE_BYTES:  # one line past the cap: parse_stream says so
            yield bytes(pending)
            return
    if pending:
        yield bytes(pending)


def parse_stream(
    lines, deadline: float | None = None, clock=time.monotonic
) -> tuple[str, dict[str, int], str | None, str]:
    """The answer's text, its usage, an opening if the call did not complete,
    and what served it, from the router's server-sent events: the model the
    response names, then the provider the router reports, or the tag of the
    one endpoint the call was pinned to, joined by " via ".
    A stream still coming at `deadline` (on `clock`) is cut there, and a
    connection that times out or fails mid-stream keeps what arrived."""
    deltas: list[str] = []
    usage: dict[str, int] = {}
    final_text = ""
    status = None
    served = ""
    read = 0
    try:
        for raw in lines:
            read += len(raw)
            if read > MAX_RESPONSE_BYTES:
                return "".join(deltas), usage, "the answer exceeded the size cap", served
            if deadline is not None and clock() > deadline:
                return "".join(deltas), usage, "the call passed its timeout", served
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
                model = response.get("model") if isinstance(response.get("model"), str) else ""
                by = response.get("provider")
                if not (isinstance(by, str) and by and by != "unknown"):  # never a guess
                    by = response.get("endpoint")
                by = by[:200] if isinstance(by, str) else ""
                served = " via ".join(part for part in (model, by) if part)
                reported = response.get("usage")
                for key, value in (reported if isinstance(reported, dict) else {}).items():
                    if isinstance(value, int) and not isinstance(value, bool):
                        usage[key] = value
                for item in response.get("output") or []:
                    for part in item.get("content") or [] if isinstance(item, dict) else []:
                        if isinstance(part, dict) and part.get("type") == "output_text":
                            final_text += str(part.get("text", ""))
    except TimeoutError:
        return "".join(deltas) or final_text, usage, "the call passed its timeout", served
    except OSError as error:
        opening = f"the connection failed ({type(error).__name__})"
        return "".join(deltas) or final_text, usage, opening, served
    text = "".join(deltas) or final_text
    if status != "completed":
        return text, usage, f"the call ended {status or 'without completing'}", served
    return text, usage, None, served


class Unified:
    """`battery: {"kind": "unified", "model": "anthropic/claude-sonnet-5-5"}`"""

    name = "unified"
    concurrent = True  # each call builds its own connection; the router takes several

    def __init__(
        self,
        url: str = DEFAULT_URL,
        timeout: float = 120.0,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.url, self.timeout, self.clock = loopback(url, "the router"), timeout, clock
        self.health = urlparse(self.url)._replace(path="/health", query="", fragment="").geturl()
        self.reports = False  # whether to ask what served each call; check() reads it

    def check(self, frame: Frame) -> None:
        """Refuse, before any call, a frame this battery must not serve: another
        battery's, an unknown key, an OpenAI slug, tools, a model whose
        provider trains on its inputs without the frame's consent, or no
        router token."""
        battery = frame.battery
        if battery.get("kind") != self.name:
            raise BatteryError(f"this frame asks for battery {battery.get('kind')!r}")
        unknown = set(battery) - BATTERY_KEYS
        if unknown:
            raise BatteryError(
                f"the unified battery reads no {quoted(sorted(unknown))} under battery"
            )
        self._check_line(battery)

    def _check_line(self, battery: dict) -> None:
        # what any line sent to the router must hold: a model it serves, no
        # tools, consent where the provider trains, a token, and a router that
        # takes the policy and pins the line needs
        model = battery.get("model")
        if not isinstance(model, str) or not model.strip():
            raise BatteryError("battery.model is a slug the router serves (GET /v1/models)")
        if not model.startswith(ROUTED_PREFIXES):
            raise BatteryError(
                f"model {model!r} is an OpenAI slug",
                "the router reaches OpenAI only with the caller's Codex sign-in, which this "
                "battery does not send; choose another model",
            )
        if "tools" in battery:  # any value, even an empty list: the critic sends none
            raise BatteryError("the critic sends no tools")
        endpoints = battery.get("endpoints", ["any"])
        if not (
            isinstance(endpoints, list)
            and endpoints
            and all(isinstance(e, str) and e for e in endpoints)
        ):
            raise BatteryError("battery.endpoints lists the router's endpoint tags, in order")
        if len(endpoints) > MAX_ENDPOINTS or any(
            "," in e or any(c.isspace() or not c.isprintable() for c in e) for e in endpoints
        ):
            raise BatteryError(
                f"battery.endpoints lists 1 to {MAX_ENDPOINTS} endpoint tags",
                "each a tag the router knows, with no comma, space or control character in it",
            )
        if battery.get("reasoning") not in (None, *EFFORTS):
            raise BatteryError(f"battery.reasoning is one of {', '.join(EFFORTS)}")
        check_output(battery)
        named = battery.get("trainsOnInputs", [])
        if not (isinstance(named, list) and all(isinstance(m, str) and m for m in named)):
            raise BatteryError("battery.trainsOnInputs lists the model slugs that may train")
        if model.startswith(TRAINS_ON_INPUTS) and not consented(battery):
            raise BatteryError(
                f"the provider of model {model!r} trains on its inputs",
                "name it under battery.trainsOnInputs to send the body there",
            )
        _token()  # no token, no run: refuse before the first call, not at each
        # A router without the policy could reach an endpoint that keeps data,
        # and one without pins could spread a quorum: either refuses the run.
        # What served each call is asked only of a router that reports it.
        needed = bool(_policy(battery)) or bool(_pinned(battery))
        try:
            listed = capabilities(self.health, self.timeout)
        except BatteryError:
            if needed:
                raise
            listed = {}
        taken = listed.get("dataPolicies")
        if _policy(battery) and not (isinstance(taken, list) and DATA_POLICY in taken):
            raise BatteryError(
                "the router takes no data policy",
                "update the router, so that each call reaches only endpoints that keep no data",
            )
        if _pinned(battery) and listed.get("endpointPins") is not True:
            raise BatteryError(
                "the router takes no endpoint pins",
                "update the router, or leave battery.endpoints out",
            )
        reports = listed.get("reports")
        self.reports = isinstance(reports, list) and "provider" in reports

    def observe(self, frame: Frame, prompt: str, max_output_tokens: int) -> Observation:
        """One call through the router: the prompt under the frame's
        instruction, answered to its schema; the label at the frame's
        pointer, or an opening that says why there is none."""
        body = payload(frame, prompt, max_output_tokens)
        text, usage, opening, served = self._call(frame.battery, body)
        if opening:
            return Observation(label=None, opening=opening, raw=text, usage=usage, served=served)
        label, opening = read_label(text, frame)
        if label is None:
            return Observation(label=None, opening=opening, raw=text, usage=usage, served=served)
        return Observation(label=label, raw=text, usage=usage, served=served)

    def _call(self, battery: dict, body: dict) -> tuple[str, dict[str, int], str | None, str]:
        """One request through the router, with the battery line's headers:
        the answer's text, its usage, an opening when there is no answer to
        read, and what served it. The battery's `observe` and a maker share
        it."""
        request = urllib.request.Request(
            self.url,
            data=json.dumps(body).encode(),
            method="POST",
            headers={
                "content-type": "application/json",
                "x-codex-router-token": _token(),
                **_policy(battery),
                **_pinned(battery),
                **({"x-codex-router-report": "provider"} if self.reports else {}),
            },
        )
        deadline = self.clock() + self.timeout
        try:
            with opened(request, self.timeout) as response:
                if response.headers.get("x-codex-router-diagnostic"):
                    diagnostic = response.headers["x-codex-router-diagnostic"][:200]
                    if diagnostic == NO_ENDPOINT_WITHOUT_DATA:
                        opening = (
                            "no endpoint that keeps no data serves this model (the router's "
                            "provider setting); naming it under trainsOnInputs allows one "
                            "that may train"
                        )
                        return "", {}, opening, ""
                    return "", {}, f"the router reports {diagnostic!r}", ""
                lines = _lines(response, deadline, self.clock)
                return parse_stream(lines, deadline, self.clock)
        except urllib.error.HTTPError as error:
            if (
                error.code == 409
                and _code(read_error(error, deadline, self.clock)) == "data_policy"
            ):
                model = battery["model"]
                opening = f"the router refused model {model!r}, whose provider trains on its inputs"
                return "", {}, opening, ""
            return "", {}, f"the router answered {error.code}", ""
        except (TimeoutError, urllib.error.URLError, OSError) as error:
            reason = getattr(error, "reason", error)
            if isinstance(reason, TimeoutError):
                return "", {}, "the call passed its timeout", ""
            return "", {}, f"the router could not be reached ({type(reason).__name__})", ""
