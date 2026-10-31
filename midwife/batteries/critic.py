"""What every critic battery shares: one safe way to call a loopback server,
and one way to read a label from a JSON answer (the frame's observation map).
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable
from urllib.parse import urlparse

from ..frame import Frame

LOOPBACK = {"127.0.0.1", "localhost", "::1"}
MAX_RESPONSE_BYTES = 1_000_000


def loopback(url: str, what: str) -> str:
    """The URL, if it names this machine over plain http on a valid port;
    else ValueError, which never repeats a user or password the URL holds."""
    parsed = urlparse(url)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"{what}'s address must not hold a user or password")
    try:
        parsed.port  # noqa: B018 -- reading it checks it
    except ValueError:
        raise ValueError(f"{what}'s address has no valid port: {url}") from None
    if parsed.scheme != "http" or parsed.hostname not in LOOPBACK:
        raise ValueError(f"{what} must be on this machine over http, not {url}")
    return url


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # a redirect becomes an HTTPError
        return None


def opener() -> urllib.request.OpenerDirector:
    """No proxy from the environment, no redirect: only the address named is
    called. Built per call, so no environment read at import can linger."""
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


def read_reply(response, deadline: float, clock: Callable[[], float]) -> bytes | None:
    """A reply as it comes, until it ends or passes the size cap; None if it
    is still coming at the deadline (the socket's timeout waits per read)."""
    body = bytearray()  # grown in place: an earlier chunk is never copied again
    while chunk := response.read1(65_536):
        body.extend(chunk)
        if len(body) > MAX_RESPONSE_BYTES:
            break
        if clock() > deadline:
            return None
    return bytes(body)


def check_output(battery: dict) -> None:
    """Refuse a battery.output that is not {schema, label}, the label a JSON
    pointer into the answer."""
    output = battery.get("output")
    if output is not None and not (
        isinstance(output, dict)
        and set(output) == {"schema", "label"}
        and isinstance(output["schema"], dict)
        and isinstance(output["label"], str)
        and output["label"].startswith("/")
    ):
        raise ValueError("battery.output is {schema, label}, label a JSON pointer such as /verdict")


def output_schema(frame: Frame) -> tuple[dict, str]:
    """The schema the critic answers to and the JSON pointer to its label."""
    output = frame.battery.get("output")
    if output is None:
        schema = {
            "type": "object",
            "properties": {"label": {"type": "string", "enum": list(frame.labels)}},
            "required": ["label"],
            "additionalProperties": False,
        }
        return schema, "/label"
    return output["schema"], output["label"]


def pointed(document, pointer: str):
    """The value at a JSON pointer (RFC 6901), or KeyError."""
    value = document
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict) and token in value:
            value = value[token]
        elif isinstance(value, list) and token.isdigit() and int(token) < len(value):
            value = value[int(token)]
        else:
            raise KeyError(pointer)
    return value


def read_label(text: str, frame: Frame) -> tuple[str | None, str | None]:
    """The label the answer gives at the frame's pointer, or an opening."""
    try:
        answer = json.loads(text)
    except json.JSONDecodeError:
        return None, "the answer is not JSON"
    return label_at(answer, frame)


def label_at(answer, frame: Frame) -> tuple[str | None, str | None]:
    """The label at the frame's pointer in an answer already read as JSON."""
    _, pointer = output_schema(frame)
    try:
        label = pointed(answer, pointer)
    except KeyError:
        return None, f"the answer has nothing at {pointer}"
    if not isinstance(label, str) or label not in frame.labels:
        return None, f"the answer's {pointer} is not one of this frame's labels"
    return label, None
