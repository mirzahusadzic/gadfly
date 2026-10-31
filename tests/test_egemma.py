"""The eGemma battery, against a fake eGemma on loopback. No model is called."""

import itertools
import json
import socket
from unittest.mock import patch

import pytest

from midwife.batteries import egemma
from midwife.batteries.egemma import EGemma, payload
from midwife.pipeline import calls_needed, judge, run, situate
from midwife.types import Budget
from tests.fakes import Fake


def reply(label="decline", **fields):
    answer = {"label": label} if label else None
    body = {
        "answer": answer,
        "text": json.dumps(answer) if answer else "",
        "truncated": False,
        "usage": {"input_tokens": 40, "output_tokens": 6},
        "model": "gemma",
        "revision": "r",
    }
    return (200, {"content-type": "application/json"}, json.dumps({**body, **fields}).encode())


@pytest.fixture
def frame(raw):
    raw["battery"] = {"kind": "egemma", "temperature": 0}
    return situate(raw)


@pytest.fixture
def key(monkeypatch):
    for name in ("EGEMMA_API_KEY_FILE", "WORKBENCH_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("EGEMMA_API_KEY", "local-key")


@pytest.fixture
def server():
    servers = []

    def start(answer, routes=None):
        servers.append(Fake(answer, routes))
        return servers[-1]

    yield start
    for fake in servers:
        fake.close()


def test_the_payload_is_the_instruction_the_text_and_the_schema_alone(frame):
    body = payload(frame, "the prompt", 32)
    assert set(body) == {"instructions", "input", "schema", "max_tokens", "temperature"}
    assert body["instructions"] == frame.instruction and body["input"] == "the prompt"
    assert body["schema"]["properties"]["label"]["enum"] == list(frame.labels)
    assert body["max_tokens"] == 32 and body["temperature"] == 0


def test_a_call_sends_the_key_and_reads_the_label(frame, key, server):
    fake = server(reply("decline"))
    observation = EGemma(fake.base + "/judge").observe(frame, "the prompt", 32)
    assert observation.label == "decline"
    assert observation.usage == {"input_tokens": 40, "output_tokens": 6}
    [(headers, body)] = fake.requests
    assert headers["authorization"] == "Bearer local-key" and body["input"] == "the prompt"


@pytest.mark.parametrize(
    "answer, opening",
    [
        (reply(None, text='{"label": "dec', truncated=True), "the answer was cut at its token cap"),
        (reply(None), "the answer is not JSON"),
        (reply("refund"), "the answer's /label is not one of this frame's labels"),
        ((401, {}, b"{}"), "eGemma answered 401"),
        ((422, {}, b"{}"), "eGemma answered 422"),
        ((200, {}, b"not json"), "eGemma's reply is not JSON"),
    ],
)
def test_what_eGemma_cannot_answer_is_an_opening(frame, key, server, answer, opening):
    fake = server(answer)
    assert EGemma(fake.base + "/judge").observe(frame, "p", 32).opening == opening


def test_a_call_past_its_deadline_is_an_opening(frame, key, server):
    fake = server(reply("decline"))
    clock = itertools.chain([0.0], itertools.repeat(999.0)).__next__
    battery = EGemma(fake.base + "/judge", timeout=10, clock=clock)
    late = battery.observe(frame, "p", 32)
    assert late.opening == "the call passed its timeout" and late.label is None
    assert late.raw  # what arrived before the deadline is kept, never read


def test_a_reply_past_the_size_cap_is_an_opening(frame, key, server, monkeypatch):
    monkeypatch.setattr(egemma, "MAX_RESPONSE_BYTES", 10)
    fake = server(reply("decline"))
    observation = EGemma(fake.base + "/judge").observe(frame, "p", 32)
    assert observation.opening == "the answer exceeded the size cap"


def test_a_redirect_is_not_followed(frame, key, server):
    elsewhere = server(reply("grant"))
    fake = server((302, {"location": elsewhere.base + "/judge"}, b""))
    assert EGemma(fake.base + "/judge").observe(frame, "p", 32).opening == "eGemma answered 302"
    assert elsewhere.requests == []


def test_eGemma_must_be_on_this_machine():
    with pytest.raises(ValueError, match="on this machine"):
        EGemma("http://example.com:8000/judge")


def test_check_refuses_unknown_keys_bad_temperatures_and_no_key(raw, monkeypatch, key):
    for battery, message in [
        ({"kind": "egemma", "persona": "x"}, "reads no"),
        ({"kind": "egemma", "model": ""}, "model and revision"),
        ({"kind": "egemma", "temperature": 3}, "between 0 and 2"),
        ({"kind": "egemma", "temperature": True}, "between 0 and 2"),
        ({"kind": "egemma", "output": {"schema": {}, "label": "x"}}, "JSON pointer"),
        ({"kind": "unified"}, "asks for the unified battery"),
    ]:
        with pytest.raises(ValueError, match=message):
            EGemma().check(situate({**raw, "battery": battery}))
    monkeypatch.delenv("EGEMMA_API_KEY")
    with pytest.raises(RuntimeError, match="no eGemma key"):
        EGemma().check(situate({**raw, "battery": {"kind": "egemma"}}))


def test_the_key_file_comes_first(monkeypatch, tmp_path, key):
    path = tmp_path / "key"
    path.write_text("from-file\n")
    monkeypatch.setenv("EGEMMA_API_KEY_FILE", str(path))
    assert egemma._key() == "from-file"
    path.write_text("")
    with pytest.raises(RuntimeError, match="empty file"):
        egemma._key()


def test_a_whole_run_through_the_battery(frame, key, server):
    fake = server(reply("decline"))
    result = run(frame, EGemma(fake.base + "/judge"), Budget(calls=calls_needed(frame)))
    assert result.stopped is None and len(fake.requests) == calls_needed(frame)
    [finding] = judge(frame, result.records)
    assert finding.category == "cooled"  # a battery that always declines: no influence


def test_a_busy_egemma_is_waited_for_as_long_as_it_asks(frame, key, server):
    waits = []
    fake = server(
        [
            (
                429,
                {},
                json.dumps({"detail": "Rate limit exceeded. Try again in 60 seconds."}).encode(),
            ),
            (503, {"retry-after": "2"}, b"{}"),
            reply("decline"),
        ]
    )
    observation = EGemma(fake.base + "/judge", sleep=waits.append).observe(frame, "p", 32)
    assert observation.label == "decline" and waits == [60.0, 2.0]
    assert len(fake.requests) == 3


def test_a_wait_is_capped_and_retries_end_in_an_opening(frame, key, server):
    waits = []
    fake = server((503, {"retry-after": "3600"}, b"{}"))
    observation = EGemma(fake.base + "/judge", sleep=waits.append).observe(frame, "p", 32)
    assert observation.opening == "eGemma answered 503 after 3 retries"
    assert waits == [60.0, 60.0, 60.0] and len(fake.requests) == 4


class Clock:
    """Time that moves only when the battery sleeps."""

    def __init__(self):
        self.now, self.waits = 100.0, []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.now += seconds


def test_calls_are_paced_to_the_budget_egemma_publishes(raw, key, server):
    limits = json.dumps({"judge": {"calls": 2, "seconds": 10}}).encode()
    fake = server(reply("decline"), routes={"/rate-limits": (200, {}, limits)})
    raw["battery"] = {"kind": "egemma"}
    frame, clock = situate(raw), Clock()
    battery = EGemma(fake.base + "/judge", sleep=clock.sleep, clock=clock)
    battery.check(frame)
    assert battery.budget == (2, 10.0)
    for _ in range(3):
        battery.observe(frame, "p", 32)
    assert clock.waits == [10.0]  # the third waits until the first two leave the window
    clock.now += 4  # t=114: only the call at 110 is in the window
    battery.observe(frame, "p", 32)
    assert clock.waits == [10.0]
    battery.observe(frame, "p", 32)  # 110 and 114 fill it: wait until 120
    assert clock.waits == [10.0, 6.0]


def test_without_a_published_budget_only_the_backoff_remains(raw, key, server):
    fake = server(reply("decline"), routes={"/rate-limits": (404, {}, b"{}")})
    raw["battery"] = {"kind": "egemma"}
    battery = EGemma(fake.base + "/judge", sleep=lambda s: None)
    battery.check(situate(raw))
    assert battery.budget is None
    assert battery.observe(situate(raw), "p", 32).label == "decline"


def test_an_answer_that_breaks_its_schema_is_an_opening(frame, key, server):
    # eGemma checks the whole schema; its grammar cannot hold every keyword.
    breaks = reply(
        "decline", valid=False, violations=[{"path": "/score", "message": "0 is less than 10"}]
    )
    fake = server(breaks)
    observation = EGemma(fake.base + "/judge").observe(frame, "p", 32)
    assert observation.label is None
    assert observation.opening == "the answer breaks its schema: /score 0 is less than 10"


def test_a_call_records_the_model_that_served(frame, key, server):
    fake = server(reply("decline"))
    assert EGemma(fake.base + "/judge").observe(frame, "p", 32).served == "gemma@r"


def test_a_pinned_model_that_does_not_serve_is_an_opening(raw, key, server):
    raw["battery"] = {"kind": "egemma", "model": "gemma", "revision": "other"}
    fake = server(reply("decline"))
    observation = EGemma(fake.base + "/judge").observe(situate(raw), "p", 32)
    assert observation.label is None and observation.served == "gemma@r"
    assert observation.opening == "eGemma served revision 'r'; the frame pins 'other'"
    raw["battery"]["revision"] = "r"
    assert EGemma(fake.base + "/judge").observe(situate(raw), "p", 32).label == "decline"


def test_a_reply_without_the_valid_field_is_read_as_before(frame, key, server):
    fake = server(reply("decline"))
    assert EGemma(fake.base + "/judge").observe(frame, "p", 32).label == "decline"


class Counted(bytes):
    """A chunk that counts the bytes copied whenever something is added to it."""

    copied = 0

    def __radd__(self, left):
        type(self).copied += len(left) + len(self)
        return bytes(left) + bytes(self)


class Replay:
    """An opener whose response hands back the chunks it was given."""

    def __init__(self, chunks):
        self.chunks = iter(chunks)
        self.headers = {}

    def open(self, request, timeout=None):
        return self

    def read1(self, size):
        return next(self.chunks, b"")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def copied_to_read(frame, chunks):
    piece = Counted(b'{"answer": null, "text": "", "truncated": false}')
    Counted.copied = 0
    with patch.object(egemma, "opener", lambda: Replay([piece] * chunks)):
        EGemma().observe(frame, "p", 8)
    return Counted.copied


def test_a_reply_is_read_without_copying_what_came_before(frame, key):
    small, large = copied_to_read(frame, 100), copied_to_read(frame, 200)
    assert large <= 2.5 * max(small, 1), (small, large)


@pytest.mark.parametrize("body", [b"[]", b'"text"', b"5"])
def test_a_reply_that_is_not_an_object_is_an_opening(frame, key, server, body):
    fake = server((200, {}, body))
    observation = EGemma(fake.base + "/judge").observe(frame, "p", 32)
    assert observation.opening == "eGemma's reply is not a JSON object"


def test_a_reply_of_the_wrong_shape_inside_is_still_read(frame, key, server):
    odd = reply("decline", usage=["not", "a", "dict"], valid=False, violations="none listed")
    observation = EGemma(server(odd).base + "/judge").observe(frame, "p", 32)
    assert observation.opening == "the answer breaks its schema" and observation.usage == {}


def test_an_egemma_that_cannot_be_reached_is_an_opening(frame, key):
    closed = socket.socket()
    closed.bind(("127.0.0.1", 0))
    port = closed.getsockname()[1]
    closed.close()
    observation = EGemma(f"http://127.0.0.1:{port}/judge").observe(frame, "p", 32)
    assert observation.opening.startswith("eGemma could not be reached")


@pytest.mark.parametrize("header", ["nan", "-5"])
def test_a_wait_that_is_not_a_finite_number_falls_back_to_a_second(frame, key, server, header):
    # sleep(nan) raises; a negative wait asks for nothing
    waits = []
    fake = server([(503, {"retry-after": header}, b"{}"), reply("decline")])
    observation = EGemma(fake.base + "/judge", sleep=waits.append).observe(frame, "p", 32)
    assert observation.label == "decline" and waits == [1.0]


@pytest.mark.parametrize("seconds", [True, float("inf"), "60"])
def test_a_budget_in_seconds_that_are_not_seconds_is_no_budget(raw, key, server, seconds):
    limits = json.dumps({"judge": {"calls": 2, "seconds": seconds}}).encode()
    fake = server(reply("decline"), routes={"/rate-limits": (200, {}, limits)})
    raw["battery"] = {"kind": "egemma"}
    battery = EGemma(fake.base + "/judge")
    battery.check(situate(raw))
    assert battery.budget is None
