"""What every critic battery shares: one safe way to call a loopback server,
and one way to read a label from a JSON answer (the frame's observation map).
"""

from __future__ import annotations

import http.client
import json
import socket
import threading
import urllib.error
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


def opener(*handlers: urllib.request.BaseHandler) -> urllib.request.OpenerDirector:
    """No proxy from the environment, no redirect: only the address named is
    called. Built per call, so no environment read at import can linger."""
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect(), *handlers)


class _Watched(urllib.request.HTTPHandler):
    # opens each connection where a watchdog can reach its socket
    def __init__(self):
        super().__init__()
        self.connections: list[http.client.HTTPConnection] = []

    def http_open(self, req):
        def connection(*args, **kwargs):
            self.connections.append(http.client.HTTPConnection(*args, **kwargs))
            return self.connections[-1]

        return self.do_open(connection, req)


def opened(request: urllib.request.Request, timeout: float):
    """The response to a request, opened through `opener()`, its status line
    and headers in within `timeout` seconds of the call: a server still
    sending the answer's head then is cut off, and the call raises
    TimeoutError. The body is `read_reply`'s to bound, and a refusal's
    `read_error`'s, both by the same deadline."""
    watched = _Watched()
    cut = threading.Event()

    def at_deadline():
        cut.set()
        for connection in watched.connections:
            sock = connection.sock  # None once the head is in: urllib lets go of it
            if sock is not None:
                try:
                    sock.shutdown(socket.SHUT_RDWR)  # wakes a read waiting on it
                except OSError:
                    pass

    timer = threading.Timer(timeout, at_deadline)  # real seconds, as the socket's own
    timer.daemon = True
    timer.start()
    try:
        response = opener(watched).open(request, timeout=timeout)
    except urllib.error.HTTPError:
        raise  # the head came in time; the refusal's body is read_error's
    except Exception:
        if cut.is_set():
            raise TimeoutError("the call passed its timeout") from None
        raise
    finally:
        timer.cancel()
    if cut.is_set():  # the deadline came with the head: nothing after it is read
        response.close()
        raise TimeoutError("the call passed its timeout")
    return response


class Late(TimeoutError):
    """A reply still coming at its deadline, with the bytes that had arrived:
    kept beside the opening, never read as an answer."""

    def __init__(self, received: bytes):
        super().__init__("the call passed its timeout")
        self.received = received

    @property
    def text(self) -> str:
        """What had arrived, as text, for the record's raw."""
        return self.received.decode("utf-8", errors="replace")


def wait_at_most(response, seconds: float) -> None:
    """Let the next read on the response's socket wait at most `seconds`."""
    sock = getattr(getattr(getattr(response, "fp", None), "raw", None), "_sock", None)
    if sock is not None:
        sock.settimeout(max(seconds, 0.001))


def read_reply(response, deadline: float, clock: Callable[[], float]) -> bytes:
    """A reply as it comes, until it ends or passes the size cap; Late, with
    what had arrived, if it is still coming at the deadline. Each read waits
    only what is left of the deadline, so a stall never runs past it."""
    body = bytearray()  # grown in place: an earlier chunk is never copied again
    try:
        while True:
            wait_at_most(response, deadline - clock())  # what has arrived is still read
            chunk = response.read1(65_536)
            if not chunk:
                break
            body.extend(chunk)
            if len(body) > MAX_RESPONSE_BYTES:
                break
            if clock() > deadline:
                raise Late(bytes(body))
    except Late:
        raise
    except TimeoutError:  # the socket's own wait ran out mid-reply
        raise Late(bytes(body)) from None
    return bytes(body)


def read_error(error: urllib.error.HTTPError, deadline: float, clock: Callable[[], float]) -> bytes:
    """Up to 4,096 bytes of a refusal's body, read by the deadline: what had
    arrived by then, or nothing. Each read waits only what is left."""
    body = bytearray()
    try:
        while len(body) < 4096 and clock() < deadline:
            wait_at_most(error.fp, deadline - clock())
            chunk = error.read1(4096 - len(body))
            if not chunk:
                break
            body.extend(chunk)
    except (OSError, ValueError, AttributeError):  # a wait run out, or no body to read
        pass
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
