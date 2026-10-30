"""The unified battery, against a fake router on loopback: what it sends,
what it refuses, and how it reads the stream. No model is called."""

import itertools
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from gadfly.batteries import unified
from gadfly.batteries.critic import pointed, read_label
from gadfly.batteries.unified import Unified, parse_stream, payload
from gadfly.pipeline import situate
from tests.fakes import Fake

TOKEN = "ab" * 32


def sse(*events):
    return b"".join(b"data: " + json.dumps(e).encode() + b"\n\n" for e in events)


def answer(text, usage=None, status="completed"):
    """A streamed answer; a label alone is sent as the default schema's JSON."""
    if not text.startswith(("{", "[")) and " " not in text:
        text = json.dumps({"label": text})
    return sse(
        {"type": "response.output_text.delta", "delta": text},
        {"type": f"response.{status}", "response": {"usage": usage or {"output_tokens": 2}}},
    )


@pytest.fixture
def token(monkeypatch, tmp_path):
    monkeypatch.setenv("CODEX_ROUTER_TOKEN", TOKEN)
    monkeypatch.setattr(unified, "ENV_FILE", tmp_path / "absent.env")


@pytest.fixture
def router():
    servers = []

    def start(reply):
        servers.append(Fake(reply))
        return servers[-1]

    yield start
    for server in servers:
        server.close()


def test_the_payload_has_no_tools_stores_nothing_and_caps_the_answer(raw):
    body = payload(situate(raw), "text", 32)
    assert "tools" not in body and body["store"] is False and body["max_output_tokens"] == 32
    assert body["model"] == "anthropic/claude-sonnet-5-5" and "reasoning" not in body
    schema = body["text"]["format"]["schema"]
    assert schema["properties"]["label"]["enum"] == ["grant", "decline", "unclear"]
    assert schema["additionalProperties"] is False and schema["required"] == ["label"]


def test_a_critic_of_your_own_keeps_its_schema_and_names_where_the_label_is(raw):
    own = {"type": "object", "properties": {"review": {"type": "object"}}}
    raw["battery"].update(reasoning="low", output={"schema": own, "label": "/review/verdict"})
    frame = situate(raw)
    body = payload(frame, "text", 32)
    assert body["text"]["format"]["schema"] == own and body["reasoning"] == {"effort": "low"}
    answer = json.dumps({"review": {"verdict": "decline", "notes": ["no receipt"]}})
    assert read_label(answer, frame) == ("decline", None)
    missing = json.dumps({"review": {}})
    assert read_label(missing, frame) == (None, "the answer has nothing at /review/verdict")


def test_a_call_sends_the_prompt_the_cap_and_the_token(raw, token, router):
    fake = router((200, {"content-type": "text/event-stream"}, answer("decline")))
    observation = Unified(fake.url).observe(situate(raw), "the prompt", 16)
    assert observation.label == "decline" and observation.usage == {"output_tokens": 2}
    [(headers, body)] = fake.requests
    assert headers["x-codex-router-token"] == TOKEN and "tools" not in body
    assert (
        body["input"][0]["content"][0]["text"] == "the prompt" and body["max_output_tokens"] == 16
    )


def test_a_redirect_is_not_followed_and_the_token_goes_nowhere_else(raw, token, router):
    elsewhere = router((200, {}, answer("grant")))
    fake = router((302, {"location": elsewhere.url}, b""))
    observation = Unified(fake.url).observe(situate(raw), "p", 16)
    assert observation.label is None and observation.opening == "the router answered 302"
    assert elsewhere.requests == []


def test_a_proxy_in_the_environment_is_not_used(raw, token, router, monkeypatch):
    proxy = router((200, {}, answer("grant")))
    fake = router((200, {}, answer("decline")))
    for name in ("http_proxy", "HTTP_PROXY"):
        monkeypatch.setenv(name, proxy.url.rsplit("/v1", 1)[0])
    monkeypatch.delenv("no_proxy", raising=False)
    monkeypatch.delenv("NO_PROXY", raising=False)
    assert Unified(fake.url).observe(situate(raw), "p", 16).label == "decline"
    assert proxy.requests == []


def test_a_diagnostic_answer_is_an_opening(raw, token, router):
    fake = router((200, {"x-codex-router-diagnostic": "upstream unavailable"}, answer("grant")))
    observation = Unified(fake.url).observe(situate(raw), "p", 16)
    assert observation.opening == "router diagnostic: upstream unavailable"


def test_an_error_status_is_an_opening(raw, token, router):
    fake = router((401, {}, b"no"))
    assert Unified(fake.url).observe(situate(raw), "p", 16).opening == "the router answered 401"


def test_an_answer_outside_the_schema_is_an_opening(raw, token, router):
    fake = router((200, {}, answer("grant or decline, hard to say")))
    observation = Unified(fake.url).observe(situate(raw), "p", 16)
    assert observation.opening == "the answer is not JSON"
    assert observation.raw == "grant or decline, hard to say"
    fake.reply = (200, {}, answer('{"label": "refund"}'))
    observation = Unified(fake.url).observe(situate(raw), "p", 16)
    assert observation.opening == "the answer's /label is not one of this frame's labels"


def test_the_router_must_be_on_this_machine():
    for url in ("http://example.com/v1/responses", "https://127.0.0.1:1/v1", "file:///etc/hosts"):
        with pytest.raises(ValueError, match="on this machine"):
            Unified(url)


def test_check_refuses_tools_training_providers_wrong_kinds_and_no_token(
    raw, monkeypatch, tmp_path
):
    monkeypatch.setattr(unified, "ENV_FILE", tmp_path / "absent.env")
    monkeypatch.setenv("CODEX_ROUTER_TOKEN", TOKEN)
    critic = Unified()
    critic.check(situate(raw))
    for change, message in [
        ({"tools": ["web_search"]}, "no tools"),
        ({"model": "ultra-spark/deepseek-v4.1-flash-1017"}, "trains on its inputs"),
        ({"model": " "}, "slug the router serves"),
        ({"kind": "other"}, "asks for the other battery"),
        ({"reasoning": "extreme"}, "reasoning is one of"),
        ({"output": {"schema": {}, "label": "verdict"}}, "JSON pointer"),
        ({"temperature": 0}, "reads no"),
    ]:
        frame = situate({**raw, "battery": {**raw["battery"], **change}})
        with pytest.raises(ValueError, match=message):
            critic.check(frame)
    named = {"model": "ultra-spark/x", "trainsOnInputs": ["ultra-spark/x"]}
    critic.check(situate({**raw, "battery": {**raw["battery"], **named}}))
    monkeypatch.setenv("CODEX_ROUTER_TOKEN", "short")
    with pytest.raises(RuntimeError, match="no router token"):
        critic.check(situate(raw))


def test_the_token_is_read_from_the_router_env_file(monkeypatch, tmp_path):
    env = tmp_path / "openrouter.env"
    env.write_text(f"OTHER=1\nCODEX_ROUTER_TOKEN='{TOKEN}'\n")
    monkeypatch.delenv("CODEX_ROUTER_TOKEN", raising=False)
    monkeypatch.setattr(unified, "ENV_FILE", env)
    assert unified._token() == TOKEN


def test_an_openai_slug_is_refused_before_any_call(raw, token):
    # The router answers it with its own 401: OpenAI needs the caller's Codex sign-in.
    raw["battery"]["model"] = "gpt-6.1-sol"
    with pytest.raises(ValueError, match="OpenAI slug"):
        Unified().check(situate(raw))
    raw["battery"]["model"] = "openrouter/anthropic/claude-sonnet-5.5"
    Unified().check(situate(raw))


def test_deepseek_is_sent_with_deny_unless_the_frame_consents(raw, token):
    # Whether an endpoint keeps no data is the OpenRouter account's setting
    # (DeepSeek's own endpoint may train; another provider may not).
    for model in (
        "deepseek/deepseek-v4.1-flash-1017",
        "openrouter/deepseek/deepseek-v4.1-flash-1017",
    ):
        raw["battery"].update(model=model, trainsOnInputs=[])
        Unified().check(situate(raw))
        assert payload(situate(raw), "t", 8)["provider"] == {"data_collection": "deny"}
        raw["battery"]["trainsOnInputs"] = [model]
        assert "provider" not in payload(situate(raw), "t", 8)


def test_a_call_records_the_model_and_endpoint_that_served(raw, token, router):
    body = sse(
        {"type": "response.output_text.delta", "delta": json.dumps({"label": "decline"})},
        {"type": "response.completed", "response": {"model": "deepseek/deepseek-v4.1-flash"}},
    )
    fake = router((200, {"x-provider-name": "DeepInfra"}, body))
    observation = Unified(fake.url).observe(situate(raw), "p", 16)
    assert observation.served == "deepseek/deepseek-v4.1-flash via DeepInfra"


def test_named_endpoints_are_pinned_without_fallbacks(raw, token):
    # a quorum read by one endpoint, not spread over whichever OpenRouter picks
    raw["battery"].update(model="deepseek/deepseek-v4.1-flash-1017", endpoints=["deepinfra/fp8"])
    Unified().check(situate(raw))
    assert payload(situate(raw), "t", 8)["provider"] == {
        "order": ["deepinfra/fp8"],
        "allow_fallbacks": False,
        "data_collection": "deny",
    }
    raw["battery"]["endpoints"] = "deepinfra/fp8"
    with pytest.raises(ValueError, match="endpoints lists"):
        Unified().check(situate(raw))


def test_consent_to_training_is_a_list_of_slugs_never_a_substring(raw, token):
    # "ultra-spark/deepseek" is a substring of the slug named: no consent
    named = "ultra-spark/deepseek-v4.1-flash-1017"
    raw["battery"].update(model="ultra-spark/deepseek", trainsOnInputs=named)
    with pytest.raises(ValueError, match="trainsOnInputs lists"):
        Unified().check(situate(raw))
    assert payload(situate(raw), "t", 8)["provider"]["data_collection"] == "deny"


def test_no_endpoint_without_data_is_an_opening_that_says_why(raw, token, router):
    fake = router((200, {"x-codex-router-diagnostic": "openrouter-data-policy"}, b""))
    observation = Unified(fake.url).observe(situate(raw), "p", 16)
    assert observation.opening.startswith("no endpoint that keeps no data serves this model")


def test_a_json_pointer_reads_objects_lists_and_escapes():
    document = {"a/b": {"c~d": [{"v": "x"}]}}
    assert pointed(document, "/a~1b/c~0d/0/v") == "x"
    with pytest.raises(KeyError):
        pointed(document, "/a~1b/c~0d/1")


def test_the_stream_is_read_to_completion_or_says_how_it_ended():
    assert parse_stream(answer("grant").splitlines(keepends=True))[2] is None
    assert (
        parse_stream(answer("gr", status="incomplete").splitlines())[2]
        == "the call ended incomplete"
    )
    assert parse_stream([b"data: {broken", b": comment"])[2] == "the call ended without completing"
    final = sse(
        {
            "type": "response.completed",
            "response": {"output": [{"content": [{"type": "output_text", "text": "decline"}]}]},
        }
    )
    assert parse_stream(final.splitlines())[0] == "decline"


def test_a_call_past_its_deadline_is_an_opening(raw, token, router):
    # the socket's timeout waits per read; a stream that keeps coming needs a deadline
    fake = router((200, {}, answer("decline")))
    clock = itertools.chain([0.0, 1.0], itertools.repeat(999.0)).__next__
    observation = Unified(fake.url, timeout=10, clock=clock).observe(situate(raw), "p", 16)
    assert observation.opening == "the call passed its timeout"


def test_an_event_that_is_not_an_object_is_skipped():
    odd = [b"data: 5\n", b"data: [1]\n"]
    odd += sse(
        {"type": "response.completed", "response": {"output": [5, {"content": [7]}]}}
    ).split()
    assert parse_stream([*odd, *answer("grant").splitlines()])[:3:2] == ('{"label": "grant"}', None)


def test_the_stream_stops_at_its_size_cap(monkeypatch):
    monkeypatch.setattr(unified, "MAX_RESPONSE_BYTES", 100)
    lines = [
        b"data: " + json.dumps({"type": "response.output_text.delta", "delta": "x" * 40}).encode()
    ] * 5
    assert parse_stream(lines)[2] == "the answer exceeded the size cap"


def test_every_request_asks_for_endpoints_that_do_not_collect_data(raw):
    # Through OpenRouter, DeepSeek's own endpoint may train on prompts; Claude
    # falls back to OpenRouter when Anthropic refuses. Only a model the frame
    # names as training on its inputs is sent without the request.
    for model in (
        "anthropic/claude-sonnet-5-5",
        "openrouter/anthropic/claude-sonnet-5.5",
        "deepseek/deepseek-v4.1-flash-1017",
        "openrouter/vendor/model",
    ):
        raw["battery"]["model"] = model
        assert payload(situate(raw), "t", 8)["provider"] == {"data_collection": "deny"}
    raw["battery"].update(model="ultra-spark/x", trainsOnInputs=["ultra-spark/x"])
    assert "provider" not in payload(situate(raw), "t", 8)


class Trickle:
    """A loopback router that sends one byte at a time and never a newline,
    so no line ever ends and no single read waits long."""

    def __init__(self, seconds=3.0):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers.get("content-length") or 0))
                self.send_response(200)
                self.end_headers()
                stop = time.monotonic() + seconds
                try:
                    while time.monotonic() < stop:
                        self.wfile.write(b"x")
                        self.wfile.flush()
                        time.sleep(0.02)
                except OSError:  # the battery hung up: what the deadline is for
                    pass

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1/responses"
        threading.Thread(target=self.server.serve_forever, args=(0.05,), daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def test_a_stream_that_never_ends_a_line_is_cut_at_the_deadline(raw, token):
    trickle = Trickle()
    try:
        started = time.monotonic()
        observation = Unified(trickle.url, timeout=0.3).observe(situate(raw), "p", 16)
        elapsed = time.monotonic() - started
    finally:
        trickle.close()
    assert observation.opening == "the call passed its timeout"
    assert elapsed < 1.5, elapsed


def test_an_event_longer_than_a_read_arrives_whole(raw, token, router):
    # one 70 kB event used to be split, skipped, and read as an empty answer
    long = json.dumps({"label": "decline", "note": "x" * 70_000})
    fake = router((200, {}, answer(long)))
    assert Unified(fake.url).observe(situate(raw), "p", 16).label == "decline"


def test_a_router_that_cannot_be_reached_is_an_opening(raw, token):
    closed = socket.socket()
    closed.bind(("127.0.0.1", 0))
    port = closed.getsockname()[1]
    closed.close()  # nothing listens there now
    observation = Unified(f"http://127.0.0.1:{port}/v1/responses").observe(situate(raw), "p", 16)
    assert observation.label is None
    assert observation.opening.startswith("the router could not be reached")


def test_a_frame_without_a_model_is_a_battery_error_not_a_key_error(raw, token):
    del raw["battery"]["model"]
    with pytest.raises(ValueError, match="battery.model"):
        Unified().observe(situate(raw), "p", 16)
