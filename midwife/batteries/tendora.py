"""The tendora battery: Tendora's engine, asked again against a trial's statements.

Tendora's engine server (`node tools/serve.mjs --project P --port N`) answers
`POST /ask` with `statements` against exactly the statements given, in their
order, and saves nothing. This battery splits a trial's prompt by its
documented form (the statements one per line, a line `---` between blank
lines, then the input), asks the frame's saved question and case again
against those statements, and reads the label from the engine's answer.

    "battery": {"kind": "tendora", "url": "http://127.0.0.1:8791",
                "timeout": 60, "scope": "...", "offline": true}

Each input reads `Case: …` on its first line when there is a case, then
`Question: …`, exactly as the saved check asked it. The engine finds the
saved check by the question, the case and the scope, so all three must be
the check's own. When a trial has turned what is asked (an input inversion,
or a presentation that renames the input's words), the battery finds the
declared input that turned into it and names it as the `basis`, the saved
check to ask it against; it never learns the trial or the input's id.

The label, from the engine's answer:
- supported, with one answer whose text is a label: that label; several
  answers or another text: `another answer` when the frame lists it;
- open, conditional, ambiguous and conflict: the label of the same name when
  the frame lists it (a proposal one confirmation away is still open);
- limited, needs-reading, a refusal, and any status or answer the frame
  does not list are openings, never labels.

What this battery promises, whatever the frame says:
- it talks only to the address named, on this machine (loopback), over
  plain http, through no proxy and no redirect, and sends no credentials;
- it sends the question, the case, the scope, the statements and the
  offline flag, and nothing else; the trial's id is never among them;
- each call has a deadline (`timeout` seconds for the whole reply, 60 by
  default) and a cap on what it reads back;
- each record names the engine version, revision and packs that served it;
- each record keeps the answer, its status and each answer's text and
  condition, on its first line, then the reply as it came but for its echo
  of the statements: a long reply is cut at the record's cap, its answer
  line is not.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable

from ..frame import Frame
from ..types import Observation
from .critic import MAX_RESPONSE_BYTES, Late, loopback, opener, read_reply

BATTERY_KEYS = {"kind", "url", "timeout", "scope", "offline"}
DEFAULT_TIMEOUT = 60.0
MAX_TIMEOUT = 3600  # a whole call, in seconds
RULE = "\n\n---\n\n"  # between the body and the input, as interventions.prompt writes it
OPEN, CONDITIONAL, ANOTHER = "open", "conditional", "another answer"
# the engine's outcomes a frame may observe under their own names
OUTCOMES = (OPEN, CONDITIONAL, "ambiguous", "conflict")


def asked(text: str) -> tuple[str, str | None] | None:
    """The question and the case an input holds, or None when it is not in
    the form `Case: …` (optional, first) then `Question: …`."""
    lines = text.split("\n")
    case = None
    if lines and lines[0].startswith("Case: "):
        case = lines.pop(0).removeprefix("Case: ")
    if len(lines) != 1 or not lines[0].startswith("Question: "):
        return None
    question = lines[0].removeprefix("Question: ")
    return (question, case) if question and case != "" else None


def request_body(frame: Frame, prompt: str) -> dict | None:
    """What the engine is sent for one prompt, or None when the prompt is not
    in Gadfly's form: the question, the case and the scope, the statements in
    their order, and the offline flag."""
    body, rule, given = prompt.rpartition(RULE)
    where = asked(given) if rule else None
    if where is None:
        return None
    question, case = where
    sent: dict = {"question": question, "statements": body.split("\n") if body else []}
    if case is not None:
        sent["case"] = case
    basis = _basis(frame, given)
    if basis is not None:
        sent["basis"] = basis
    battery = frame.battery
    if "scope" in battery:
        sent["scope"] = battery["scope"]
    if "offline" in battery:
        sent["offline"] = battery["offline"]
    return sent


def _basis(frame: Frame, given: str) -> dict | None:
    """The saved check a turned input is asked against: the declared input
    whose input inversion, or presentation, gives what the prompt asks.
    None when the prompt asks a declared input as it stands, even one another
    input turned into (a swap): that is its own saved check, asked again."""
    from ..interventions import rename

    texts = [x["text"] for x in frame.inputs]
    if given in texts:
        return None
    iv = frame.interventions
    for key in ("inputInversion", "presentation"):
        mapping = tuple(sorted((iv.get(key) or {}).items()))
        for text in texts:
            if mapping and rename(text, mapping) == given:
                question, case = asked(text)
                return {"question": question, **({"case": case} if case is not None else {})}
    return None


def label_of(reply: dict, labels: tuple[str, ...]) -> tuple[str | None, str | None]:
    """The label the engine's answer gives, or the opening that says why it
    gives none."""
    status = reply.get("status")
    answers = [a for a in reply.get("answers") or [] if isinstance(a, dict)]
    if status == "supported" and any(a.get("conditional") for a in answers):
        status = CONDITIONAL  # an answer that holds only on a condition
    if status in OUTCOMES:
        return (status, None) if status in labels else (None, f"the engine answered {status}")
    if status == "supported":
        texts = [a.get("text") for a in answers]
        if len(texts) == 1 and texts[0] in labels:
            return texts[0], None
        if texts and ANOTHER in labels:
            return ANOTHER, None
        return None, f"the engine answered {texts}, which no label names"[:300]
    if status == "needs-reading":
        unread = reply.get("unread") if isinstance(reply.get("unread"), list) else []
        return None, f"the engine answered needs-reading: {len(unread)} text(s) have no reading"
    return None, f"the engine answered {status}"[:300]


def answer_line(reply: dict) -> dict:
    """The answer alone: its status, and each answer's text and condition."""
    answers = [a for a in reply.get("answers") or [] if isinstance(a, dict)]
    return {
        "status": reply.get("status"),
        "answers": [
            {"text": a.get("text"), "conditional": bool(a.get("conditional"))} for a in answers
        ],
    }


def served_by(reply: dict) -> str:
    served = reply.get("served") if isinstance(reply.get("served"), dict) else {}
    parts = [
        f"tendora {served.get('tendora', '')}".strip(),
        str(served.get("revision") or "")[:16],
        str(served.get("packs") or ""),
    ]
    return " ".join(part for part in parts if part)[:200]


class Tendora:
    """`battery: {"kind": "tendora", "url": "http://127.0.0.1:8791"}`"""

    name = "tendora"

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self.clock = clock

    def check(self, frame: Frame) -> None:
        """Refuse, before any call, a frame this battery must not serve:
        another battery's, an unknown key, an address off this machine, a
        timeout that is not a positive number of seconds, a scope or offline
        flag of the wrong type, no `open` among the labels, or an input not
        in the form `Case: …` then `Question: …`."""
        battery = frame.battery
        if battery.get("kind") != self.name:
            raise ValueError(f"this frame asks for the {battery.get('kind')} battery")
        unknown = set(battery) - BATTERY_KEYS
        if unknown:
            raise ValueError(f"the tendora battery reads no {sorted(unknown)}")
        if not isinstance(battery.get("url"), str):
            raise ValueError("battery.url is the engine server's address on this machine")
        loopback(battery["url"], "the engine")
        timeout = battery.get("timeout", DEFAULT_TIMEOUT)
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, int | float)
            or not 0 < timeout <= MAX_TIMEOUT
        ):
            raise ValueError(f"battery.timeout is a number of seconds, up to {MAX_TIMEOUT}")
        if "scope" in battery and not (isinstance(battery["scope"], str) and battery["scope"]):
            raise ValueError("battery.scope names the check's scope")
        if "offline" in battery and not isinstance(battery["offline"], bool):
            raise ValueError("battery.offline is true or false")
        if OPEN not in frame.labels:
            raise ValueError("the tendora battery needs open among the labels")
        for x in frame.inputs:
            if asked(x["text"]) is None:
                raise ValueError(
                    f"input {x['id']} is not 'Case: …' then 'Question: …', as the check asked it"
                )

    def observe(self, frame: Frame, prompt: str, max_output_tokens: int) -> Observation:
        """One ask of the engine: the label its answer gives, or an opening
        that says why there is none."""
        sent = request_body(frame, prompt)
        if sent is None:
            return Observation(label=None, opening="the prompt is not in Gadfly's form")
        battery = frame.battery
        url = loopback(battery["url"].rstrip("/") + "/ask", "the engine")
        timeout = float(battery.get("timeout", DEFAULT_TIMEOUT))
        request = urllib.request.Request(
            url,
            data=json.dumps(sent).encode(),
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
            said = _said(error)
            return Observation(label=None, opening=f"the engine answered {error.code}{said}")
        except (TimeoutError, urllib.error.URLError, OSError) as error:
            reason = getattr(error, "reason", error)
            if isinstance(reason, TimeoutError):
                return Observation(label=None, opening="the call passed its timeout")
            return Observation(
                label=None, opening=f"the engine could not be reached: {type(reason).__name__}"
            )
        if len(body) > MAX_RESPONSE_BYTES:
            return Observation(label=None, opening="the answer exceeded the size cap")
        try:
            reply = json.loads(body)
        except json.JSONDecodeError:
            return Observation(label=None, opening="the engine's reply is not JSON")
        if not isinstance(reply, dict):
            return Observation(label=None, opening="the engine's reply is not a JSON object")
        # the reply as it came, but for its echo of the statements sent, which
        # the frame and the trial give again: what a reproduction needs. The
        # answer comes first, on a line of its own, so the record's cap never
        # cuts it.
        kept = {k: v for k, v in reply.items() if k != "statements"}
        seen = {
            "raw": json.dumps(answer_line(reply), ensure_ascii=False)
            + "\n"
            + json.dumps(kept, ensure_ascii=False),
            "usage": {"output_tokens": 0},  # the engine reasons; it writes no tokens
            "served": served_by(reply),
        }
        label, opening = label_of(reply, frame.labels)
        if label is None:
            return Observation(label=None, opening=opening, **seen)
        return Observation(label=label, **seen)


def _said(error: urllib.error.HTTPError) -> str:
    # the engine's own reason for a refusal (409, 422), short and on one line
    try:
        said = json.loads(error.read(4096) or b"{}")
    except (json.JSONDecodeError, OSError, ValueError):
        return ""
    message = said.get("error") if isinstance(said, dict) else None
    return f": {' '.join(str(message).split())[:200]}" if message else ""
