"""Each shipped battery's whole-call deadline, against a loopback server that
sends its answer a byte at a time: the status line and headers, or a
refusal's body, never run a call past its timeout (pass 5, R02)."""

import json
import re
import socket
import threading
import time
from pathlib import Path

import pytest

from midwife.batteries.egemma import RETRIES, EGemma
from midwife.batteries.local_json import LocalJSON
from midwife.batteries.tendora import Tendora
from midwife.batteries.unified import Unified
from midwife.interventions import plan, prompt
from midwife.pipeline import situate

TIMEOUT = 0.4
CHAIN = Path(__file__).parent / "fixtures" / "payments-notify-chain.json"
GAP = 0.02  # seconds between bytes: each read waits far less than the timeout


class Trickle:
    """A loopback server that reads each request whole, sends `fast` at once,
    then `slow` a byte at a time."""

    def __init__(self, slow: bytes, fast: bytes = b""):
        self.slow, self.fast, self.stop = slow, fast, threading.Event()
        self.listener = socket.create_server(("127.0.0.1", 0))
        self.url = f"http://127.0.0.1:{self.listener.getsockname()[1]}"
        threading.Thread(target=self.serve, daemon=True).start()

    def serve(self):
        while not self.stop.is_set():
            try:
                connection, _ = self.listener.accept()
            except OSError:
                return
            threading.Thread(target=self.answer, args=(connection,), daemon=True).start()

    def answer(self, connection):
        with connection:
            data = b""
            while b"\r\n\r\n" not in data:
                chunk = connection.recv(65_536)
                if not chunk:
                    return
                data += chunk
            head, _, body = data.partition(b"\r\n\r\n")
            length = re.search(rb"content-length: *(\d+)", head, re.I)
            while length and len(body) < int(length.group(1)):
                body += connection.recv(65_536)
            try:
                connection.sendall(self.fast)
                for i in range(len(self.slow)):
                    if self.stop.is_set():
                        return
                    connection.sendall(self.slow[i : i + 1])
                    time.sleep(GAP)
            except OSError:  # the battery let go
                return

    def close(self):
        self.stop.set()
        self.listener.close()


@pytest.fixture
def trickle():
    servers = []

    def start(slow: bytes, fast: bytes = b""):
        servers.append(Trickle(slow, fast))
        return servers[-1]

    yield start
    for server in servers:
        server.close()


@pytest.fixture
def keys(monkeypatch, tmp_path):
    from midwife.batteries import unified

    monkeypatch.setenv("CODEX_ROUTER_TOKEN", "ab" * 32)
    monkeypatch.setattr(unified, "ENV_FILE", tmp_path / "absent.env")
    for name in ("EGEMMA_API_KEY_FILE", "WORKBENCH_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("EGEMMA_API_KEY", "local-key")


def asked(raw, kind: str, url: str):
    """A battery, a frame for it at `url`, and its baseline prompt."""
    if kind == "tendora":
        raw = json.loads(CHAIN.read_text(encoding="utf-8"))
        raw["battery"] = {"kind": "tendora", "url": url, "timeout": TIMEOUT}
        battery = Tendora()
    elif kind == "local-json":
        raw["observe"]["labels"] = ["grant", "decline", "unclear"]
        raw["battery"] = {"kind": "local-json", "url": url + "/judge", "timeout": TIMEOUT}
        battery = LocalJSON()
    elif kind == "egemma":
        raw["battery"] = {"kind": "egemma"}
        battery = EGemma(url=url + "/judge", timeout=TIMEOUT, sleep=lambda seconds: None)
    else:
        battery = Unified(url=url + "/v1/responses", timeout=TIMEOUT)
    frame = situate(raw)
    [baseline] = [t for t in plan(frame) if t.id == "baseline"]
    return battery, frame, prompt(frame, baseline, frame.inputs[0])


HEAD = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nX-Pad: " + b"a" * 200 + b"\r\n\r\n"


@pytest.mark.parametrize("kind", ["tendora", "local-json", "egemma", "unified"])
def test_headers_sent_a_byte_at_a_time_end_at_the_deadline(raw, keys, trickle, kind):
    # each byte comes long before the socket's own wait runs out, so only a
    # deadline over the whole head stops the call
    server = trickle(HEAD)
    battery, frame, text = asked(raw, kind, server.url)
    began = time.monotonic()
    seen = battery.observe(frame, text, 32)
    took = time.monotonic() - began
    assert seen.label is None and seen.opening == "the call passed its timeout"
    assert took < TIMEOUT + 0.5, took


def test_a_refusal_sent_a_byte_at_a_time_ends_at_the_deadline(trickle):
    # the engine's reason for a 409 is read by the same deadline: what came
    # in time is kept as far as it goes, and the code is never lost
    reason = json.dumps({"error": "no saved check " + "x" * 300}).encode()
    head = b"HTTP/1.1 409 Conflict\r\nContent-Type: application/json\r\n"
    server = trickle(reason, head + f"Content-Length: {len(reason)}\r\n\r\n".encode())
    battery, frame, text = asked(None, "tendora", server.url)
    began = time.monotonic()
    seen = battery.observe(frame, text, 32)
    took = time.monotonic() - began
    assert seen.label is None and seen.opening.startswith("the engine answered 409")
    assert took < TIMEOUT + 0.5, took


def test_a_busy_reply_sent_a_byte_at_a_time_ends_at_each_deadline(raw, keys, trickle):
    # eGemma names its wait in the body when no Retry-After says it: each
    # attempt reads that body by its own deadline, not a whole body more
    detail = json.dumps({"detail": "Rate limit exceeded. Try again in 0 seconds." + " " * 300})
    head = b"HTTP/1.1 503 Service Unavailable\r\nContent-Type: application/json\r\n"
    body = detail.encode()
    server = trickle(body, head + f"Content-Length: {len(body)}\r\n\r\n".encode())
    battery, frame, text = asked(raw, "egemma", server.url)
    began = time.monotonic()
    seen = battery.observe(frame, text, 32)
    took = time.monotonic() - began
    assert seen.label is None and seen.opening == f"eGemma answered 503 after {RETRIES} retries"
    assert took < RETRIES * TIMEOUT + 1.0, took
