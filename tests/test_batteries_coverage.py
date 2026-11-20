"""What the batteries share at a call's deadline, where a fake server cannot
put the head and the deadline in order, and the entry point run in-process.
No model is called, and nothing leaves this machine."""

import http.client
import json
import runpy
import signal
import socket
import sys
import time
import urllib.error
from pathlib import Path

import pytest

from midwife.batteries import critic
from midwife.batteries.local_json import LocalJSON
from midwife.pipeline import situate

REFUND = str(Path(__file__).parent / "fixtures" / "refund.json")


class Held:
    """The connections a call's watchdog finds at its deadline: one urllib
    has let go of (no socket), one whose socket is already shut (shutting
    it raises), and one still waiting on its head, which the deadline wakes."""

    def __init__(self):
        self.let_go = http.client.HTTPConnection("127.0.0.1")
        self.shut = http.client.HTTPConnection("127.0.0.1")
        self.shut.sock = socket.socket()  # never connected: shutdown raises OSError
        self.waiting = http.client.HTTPConnection("127.0.0.1")
        self.waiting.sock, self.peer = socket.socketpair()
        self.waiting.sock.settimeout(5)
        self.woken = False

    def opener(self, then):
        held = self

        class Director:
            def __init__(self, watched):
                self.watched = watched

            def open(self, request, timeout):
                self.watched.connections += [held.let_go, held.shut, held.waiting]
                # a read on the waiting socket ends only when the deadline shuts it
                held.woken = held.waiting.sock.recv(1) == b""
                return then()

        return Director

    def close(self):
        for sock in (self.shut.sock, self.waiting.sock, self.peer):
            sock.close()


@pytest.fixture
def held():
    connections = Held()
    yield connections
    connections.close()


def at(raw, timeout):
    raw["battery"] = {"kind": "local-json", "url": "http://127.0.0.1:1/judge", "timeout": timeout}
    return situate(raw)


def test_a_deadline_wakes_the_call_past_a_connection_let_go_of_or_already_shut(
    raw, held, monkeypatch
):
    # the head never comes: the read urllib waits on is cut, and the call is a timeout
    def cut():
        raise urllib.error.URLError(http.client.RemoteDisconnected("closed without response"))

    monkeypatch.setattr(critic, "opener", held.opener(cut))
    began = time.monotonic()
    seen = LocalJSON().observe(at(raw, 0.2), "p", 32)
    took = time.monotonic() - began
    assert (seen.label, seen.opening) == (None, "the call passed its timeout")
    assert held.woken and took < 2, took  # the last socket was shut, not left to its own wait


def test_a_head_that_comes_in_as_the_deadline_passes_is_closed_unread(raw, held, monkeypatch):
    class Response:
        closed = read = False

        def close(self):
            self.closed = True

        def read1(self, amount):
            self.read = True
            return json.dumps({"answer": {"label": "grant"}}).encode()

    response = Response()
    monkeypatch.setattr(critic, "opener", held.opener(lambda: response))
    seen = LocalJSON().observe(at(raw, 0.2), "p", 32)
    assert (seen.label, seen.opening, seen.raw) == (None, "the call passed its timeout", "")
    assert held.woken and response.closed and not response.read


@pytest.fixture
def as_the_program():
    # main as the program lets SIGPIPE end it; this process keeps its own
    before = signal.getsignal(signal.SIGPIPE) if hasattr(signal, "SIGPIPE") else None
    yield
    if before is not None:
        signal.signal(signal.SIGPIPE, before)


@pytest.mark.parametrize(
    "argv, status, said",
    [
        (["plan", REFUND], 0, ": 8 calls"),
        (["plan", REFUND + ".absent"], 7, "FileNotFoundError"),
    ],
)
def test_python_m_midwife_exits_with_the_commands_status(
    monkeypatch, capsys, as_the_program, argv, status, said
):
    monkeypatch.setattr(sys, "argv", ["gadfly", *argv])
    with pytest.raises(SystemExit) as done:
        runpy.run_module("midwife", run_name="__main__")
    assert done.value.code == status
    printed = capsys.readouterr()
    assert said in (printed.out if status == 0 else printed.err)
