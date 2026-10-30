"""The router battery, against a fake router on loopback: what it sends, what
it refuses, and how it reads the stream. No model is called."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from gadfly.batteries import router_critic
from gadfly.batteries.router_critic import RouterCritic, parse_stream, payload, read_label
from gadfly.pipeline import situate

TOKEN = "ab" * 32


def sse(*events):
    return b"".join(b"data: " + json.dumps(e).encode() + b"\n\n" for e in events)


def answer(text, usage=None, status="completed"):
    return sse(
        {"type": "response.output_text.delta", "delta": text},
        {"type": f"response.{status}", "response": {"usage": usage or {"output_tokens": 2}}},
    )


class Fake:
    """A loopback server that records each request and replies as told."""

    def __init__(self, reply):
        self.requests, self.reply = [], reply
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers["content-length"])
                headers = {k.lower(): v for k, v in self.headers.items()}
                fake.requests.append((headers, json.loads(self.rfile.read(length))))
                status, headers, body = fake.reply
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(body)

            do_GET = do_POST

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1/responses"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def token(monkeypatch, tmp_path):
    monkeypatch.setenv("CODEX_ROUTER_TOKEN", TOKEN)
    monkeypatch.setattr(router_critic, "ENV_FILE", tmp_path / "absent.env")


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
    body = payload(situate(raw), "anthropic/claude-sonnet-5-5", "text", 32)
    assert "tools" not in body and body["store"] is False and body["max_output_tokens"] == 32
    assert body["instructions"].endswith("Answer with exactly one of: grant, decline, unclear.")


def test_a_call_sends_the_prompt_the_cap_and_the_token(raw, token, router):
    fake = router((200, {"content-type": "text/event-stream"}, answer("Decline.")))
    observation = RouterCritic(fake.url).observe(situate(raw), "the prompt", 16)
    assert observation.label == "decline" and observation.usage == {"output_tokens": 2}
    [(headers, body)] = fake.requests
    assert headers["x-codex-router-token"] == TOKEN and "tools" not in body
    assert (
        body["input"][0]["content"][0]["text"] == "the prompt" and body["max_output_tokens"] == 16
    )


def test_a_redirect_is_not_followed_and_the_token_goes_nowhere_else(raw, token, router):
    elsewhere = router((200, {}, answer("grant")))
    fake = router((302, {"location": elsewhere.url}, b""))
    observation = RouterCritic(fake.url).observe(situate(raw), "p", 16)
    assert observation.label is None and observation.opening == "the router answered 302"
    assert elsewhere.requests == []


def test_a_proxy_in_the_environment_is_not_used(raw, token, router, monkeypatch):
    proxy = router((200, {}, answer("grant")))
    fake = router((200, {}, answer("decline")))
    for name in ("http_proxy", "HTTP_PROXY"):
        monkeypatch.setenv(name, proxy.url.rsplit("/v1", 1)[0])
    monkeypatch.delenv("no_proxy", raising=False)
    monkeypatch.delenv("NO_PROXY", raising=False)
    assert RouterCritic(fake.url).observe(situate(raw), "p", 16).label == "decline"
    assert proxy.requests == []


def test_a_diagnostic_answer_is_an_opening(raw, token, router):
    fake = router((200, {"x-codex-router-diagnostic": "upstream unavailable"}, answer("grant")))
    observation = RouterCritic(fake.url).observe(situate(raw), "p", 16)
    assert observation.opening == "router diagnostic: upstream unavailable"


def test_an_error_status_is_an_opening(raw, token, router):
    fake = router((401, {}, b"no"))
    assert (
        RouterCritic(fake.url).observe(situate(raw), "p", 16).opening == "the router answered 401"
    )


def test_an_answer_naming_no_single_label_is_an_opening(raw, token, router):
    fake = router((200, {}, answer("grant or decline, hard to say")))
    observation = RouterCritic(fake.url).observe(situate(raw), "p", 16)
    assert observation.opening == "no single label in the answer"
    assert observation.raw == "grant or decline, hard to say"


def test_the_router_must_be_on_this_machine():
    for url in ("http://example.com/v1/responses", "https://127.0.0.1:1/v1", "file:///etc/hosts"):
        with pytest.raises(ValueError, match="on this machine"):
            RouterCritic(url)


def test_check_refuses_tools_training_providers_wrong_kinds_and_no_token(
    raw, monkeypatch, tmp_path
):
    monkeypatch.setattr(router_critic, "ENV_FILE", tmp_path / "absent.env")
    monkeypatch.setenv("CODEX_ROUTER_TOKEN", TOKEN)
    critic = RouterCritic()
    critic.check(situate(raw))
    for change, message in [
        ({"tools": ["web_search"]}, "no tools"),
        ({"model": "ultra-spark/deepseek-v4.1-flash-1017"}, "trains on its inputs"),
        ({"model": "claude"}, "routed slug"),
        ({"kind": "other"}, "asks for the other battery"),
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
    monkeypatch.setattr(router_critic, "ENV_FILE", env)
    assert router_critic._token() == TOKEN


@pytest.mark.parametrize(
    "text, label",
    [
        ("Decline.", "decline"),
        ("I would grant it", "grant"),
        ("grant; no, decline", None),
        ("ungranted", None),
        ("", None),
    ],
)
def test_read_label_takes_one_whole_word_label(text, label):
    assert read_label(text, ("grant", "decline", "unclear")) == label


def test_read_label_does_not_read_level_1_inside_level_10():
    assert read_label("level-10", ("level-1", "level-2")) is None


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


def test_the_stream_stops_at_its_size_cap(monkeypatch):
    monkeypatch.setattr(router_critic, "MAX_RESPONSE_BYTES", 100)
    lines = [
        b"data: " + json.dumps({"type": "response.output_text.delta", "delta": "x" * 40}).encode()
    ] * 5
    assert parse_stream(lines)[2] == "the answer exceeded the size cap"
