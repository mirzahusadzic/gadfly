"""The local-json battery, against a fake evaluator on loopback. No model is called."""

import itertools
import json
import socket

import pytest

from midwife.batteries.local_json import LocalJSON, payload
from midwife.pipeline import calls_needed, judge, run, situate
from midwife.types import Budget
from tests.fakes import Fake


def reply(label="decline", **fields):
    answer = {"label": label} if label else None
    body = {"answer": answer, "text": json.dumps(answer), "usage": {"output_tokens": 4}}
    return (200, {"content-type": "application/json"}, json.dumps({**body, **fields}).encode())


@pytest.fixture
def evaluator():
    servers = []

    def start(answer):
        servers.append(Fake(answer))
        return servers[-1]

    yield start
    for fake in servers:
        fake.close()


def frame_at(raw, url, **battery):
    raw["battery"] = {"kind": "local-json", "url": url, **battery}
    return situate(raw)


def test_the_request_is_the_instruction_the_prompt_the_schema_and_the_cap_alone(raw, evaluator):
    fake = evaluator(reply("decline", served="classifier@r3"))
    frame = frame_at(raw, fake.base + "/judge")
    observation = LocalJSON().observe(frame, "the prompt", 32)
    assert observation.label == "decline" and observation.served == "classifier@r3"
    assert observation.usage == {"output_tokens": 4}
    [(headers, body)] = fake.requests
    assert body == payload(frame, "the prompt", 32)
    assert set(body) == {"instructions", "input", "schema", "max_tokens"}
    assert body["input"] == "the prompt" and body["max_tokens"] == 32
    assert "authorization" not in headers  # no credentials, ever


@pytest.mark.parametrize(
    "battery, message",
    [
        ({"url": "http://example.com/judge"}, "on this machine"),
        ({"url": "https://127.0.0.1:1/judge"}, "on this machine"),
        ({}, "battery.url"),
        ({"url": "http://127.0.0.1:1/judge", "timeout": 0}, "timeout"),
        ({"url": "http://127.0.0.1:1/judge", "timeout": True}, "timeout"),
        ({"url": "http://127.0.0.1:1/judge", "timeout": 10**1000}, "timeout"),
        ({"url": "http://127.0.0.1:bad/judge"}, "port"),
        ({"url": "http://user:secret@127.0.0.1:1/judge"}, "user or password"),
        ({"url": "http://127.0.0.1:1/judge", "token": "x"}, "reads no"),
        ({"url": "http://127.0.0.1:1/judge", "output": {"schema": {}, "label": "x"}}, "pointer"),
    ],
)
def test_check_refuses_what_the_battery_must_not_serve(raw, battery, message):
    raw["battery"] = {"kind": "local-json", **battery}
    with pytest.raises(ValueError, match=message):
        LocalJSON().check(situate(raw))


def test_a_refusal_never_shows_a_password(raw):
    # a refused address is named without the credentials it may hold
    for url in ("https://user:secret@example.com/judge", "http://user:secret@127.0.0.1:1/x"):
        raw["battery"] = {"kind": "local-json", "url": url}
        with pytest.raises(ValueError) as refused:
            LocalJSON().check(situate(raw))
        assert "secret" not in str(refused.value)


def test_check_refuses_another_batterys_frame(raw):
    with pytest.raises(ValueError, match="asks for the rules battery"):
        LocalJSON().check(situate({**raw, "battery": {"kind": "rules"}}))


@pytest.mark.parametrize(
    "answer, opening",
    [
        ((500, {}, b"{}"), "the evaluator answered 500"),
        ((302, {"location": "http://127.0.0.1:1/x"}, b""), "the evaluator answered 302"),
        ((200, {}, b"not json"), "the evaluator's reply is not JSON"),
        ((200, {}, b"[]"), "the evaluator's reply is not a JSON object"),
        (reply(None), "the answer is not JSON"),
        (reply("refund"), "the answer's /label is not one of this frame's labels"),
    ],
)
def test_what_the_evaluator_cannot_answer_is_an_opening(raw, evaluator, answer, opening):
    fake = evaluator(answer)
    assert LocalJSON().observe(frame_at(raw, fake.base + "/judge"), "p", 32).opening == opening


def test_an_evaluator_that_cannot_be_reached_is_an_opening(raw):
    closed = socket.socket()
    closed.bind(("127.0.0.1", 0))
    port = closed.getsockname()[1]
    closed.close()
    observation = LocalJSON().observe(frame_at(raw, f"http://127.0.0.1:{port}/judge"), "p", 32)
    assert observation.opening.startswith("the evaluator could not be reached")


def test_a_call_past_its_deadline_is_an_opening(raw, evaluator):
    fake = evaluator(reply("decline"))
    clock = itertools.chain([0.0], itertools.repeat(999.0)).__next__
    frame = frame_at(raw, fake.base + "/judge", timeout=10)
    late = LocalJSON(clock=clock).observe(frame, "p", 32)
    assert late.opening == "the call passed its timeout" and late.label is None
    assert '"decline"' in late.raw  # what arrived before the deadline is kept, never read


def test_a_proxy_in_the_environment_is_not_used(raw, evaluator, monkeypatch):
    proxy, fake = evaluator(reply("grant")), evaluator(reply("decline"))
    for name in ("http_proxy", "HTTP_PROXY"):
        monkeypatch.setenv(name, proxy.base)
    monkeypatch.delenv("no_proxy", raising=False)
    monkeypatch.delenv("NO_PROXY", raising=False)
    assert LocalJSON().observe(frame_at(raw, fake.base + "/judge"), "p", 32).label == "decline"
    assert proxy.requests == []


def test_a_whole_run_through_the_battery(raw, evaluator):
    fake = evaluator(reply("decline"))
    frame = frame_at(raw, fake.base + "/judge")
    result = run(frame, LocalJSON(), Budget(calls=calls_needed(frame)))
    assert result.stopped is None and len(fake.requests) == calls_needed(frame)
    [finding] = judge(frame, result.records)
    assert finding.category == "cooled"  # a scorer that always declines


def test_a_reply_that_stalls_after_its_first_chunk_ends_at_the_deadline(raw):
    # the first chunk comes just before the deadline and the rest never does:
    # the next read waits only what is left, not a whole timeout again (pass 4, R09)
    import threading
    import time
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Stalling(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers["content-length"]))
            self.send_response(200)
            self.send_header("content-length", "1000")
            self.end_headers()
            self.wfile.flush()
            time.sleep(0.4)
            self.wfile.write(b'{"answer": ')
            self.wfile.flush()
            time.sleep(1.5)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Stalling)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        frame = frame_at(raw, f"http://127.0.0.1:{server.server_port}/judge", timeout=0.6)
        began = time.monotonic()
        late = LocalJSON().observe(frame, "p", 32)
        took = time.monotonic() - began
    finally:
        server.shutdown()
        server.server_close()
    assert late.opening == "the call passed its timeout" and late.raw == '{"answer": '
    assert took < 0.9, took  # one deadline, not a deadline and a timeout more
