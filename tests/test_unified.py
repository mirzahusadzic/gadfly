"""The unified battery, against a fake router on loopback: what it sends,
what it refuses, and how it reads the stream. No model is called."""

import itertools
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from midwife.batteries import unified
from midwife.batteries.critic import pointed, read_label
from midwife.batteries.unified import Unified, parse_stream, payload, pinned, policy, routing
from midwife.errors import BatteryError
from midwife.pipeline import situate
from tests.fakes import Fake

TOKEN = "ab" * 32
LISTS = unified.capabilities  # the router's health, asked as the battery asks it
DENY = {"x-codex-router-data-policy": "deny"}
FULL = {
    "dataPolicies": ["deny"],
    "endpointPins": True,
    "reports": ["provider"],
    "fallbackPolicies": ["none"],
    "thinkingBudgets": True,
}


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


@pytest.fixture(autouse=True)
def listed(monkeypatch):
    # a router that takes the deny data policy and endpoint pins, and reports
    # what served each call, unless a test asks its own
    monkeypatch.setattr(unified, "capabilities", lambda url, timeout: dict(FULL))


@pytest.fixture
def router():
    servers = []

    def start(reply, routes=None):
        servers.append(Fake(reply, routes))
        return servers[-1]

    yield start
    for server in servers:
        server.close()


def test_a_record_keeps_the_reasoning_a_call_spent(raw, token, router):
    # a model that decides on each call whether to think: the record says
    # whether this one did, from the breakdown the router passes on
    reported = {
        "input_tokens": 300,
        "output_tokens": 412,
        "total_tokens": 712,
        "output_tokens_details": {"reasoning_tokens": 400, "note": "x"},
        "input_tokens_details": {"cached_tokens": 128, "flag": True},
    }
    fake = router((200, {"content-type": "text/event-stream"}, answer("decline", reported)))
    observation = Unified(fake.url).observe(situate(raw), "the prompt", 1024)
    assert observation.usage == {
        "input_tokens": 300,
        "output_tokens": 412,
        "total_tokens": 712,
        "reasoning_tokens": 400,
        "cached_tokens": 128,
    }


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
    assert read_label(missing, frame) == (None, "the answer has nothing at '/review/verdict'")


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
    assert observation.opening == "the router reports 'upstream unavailable'"


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
    assert observation.opening == "the answer's '/label' is not one of this frame's labels"


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
        ({"tools": []}, "no tools"),
        ({"tools": False}, "no tools"),
        ({"model": "ultra-spark/deepseek-v4.1-flash-1017"}, "trains on its inputs"),
        ({"model": " "}, "slug the router serves"),
        ({"kind": "other"}, "asks for battery 'other'"),
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
    with pytest.raises(BatteryError, match="no router token"):
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
    # whether an endpoint keeps no data is the router's provider setting
    for model in (
        "deepseek/deepseek-v4.1-flash-1017",
        "openrouter/deepseek/deepseek-v4.1-flash-1017",
    ):
        raw["battery"].update(model=model, trainsOnInputs=[])
        Unified().check(situate(raw))
        assert policy(situate(raw)) == DENY and "provider" not in payload(situate(raw), "t", 8)
        raw["battery"]["trainsOnInputs"] = [model]
        assert policy(situate(raw)) == {}


@pytest.mark.parametrize(
    "reported, served",
    [
        ({"provider": "Anthropic"}, "deepseek/deepseek-v4.1-flash via Anthropic"),
        (
            {"provider": "unknown", "endpoint": "fireworks"},
            "deepseek/deepseek-v4.1-flash via fireworks",
        ),
        ({"provider": "unknown"}, "deepseek/deepseek-v4.1-flash"),  # never a guess
        ({}, "deepseek/deepseek-v4.1-flash"),
    ],
)
def test_a_call_records_what_the_router_reports_served_it(raw, token, router, reported, served):
    body = sse(
        {"type": "response.output_text.delta", "delta": json.dumps({"label": "decline"})},
        {
            "type": "response.completed",
            "response": {"model": "deepseek/deepseek-v4.1-flash", **reported},
        },
    )
    fake = router((200, {}, body))
    battery = Unified(fake.url)
    battery.check(situate(raw))
    assert battery.observe(situate(raw), "p", 16).served == served
    [(headers, _)] = fake.requests
    assert headers["x-codex-router-report"] == "provider"


def test_what_served_a_call_is_asked_only_of_a_router_that_reports_it(
    raw, token, router, monkeypatch
):
    monkeypatch.setattr(unified, "capabilities", lambda url, timeout: {"dataPolicies": ["deny"]})
    fake = router((200, {}, answer("decline")))
    battery = Unified(fake.url)
    battery.check(situate(raw))
    battery.observe(situate(raw), "p", 16)
    [(headers, _)] = fake.requests
    assert "x-codex-router-report" not in headers


def test_named_endpoints_are_pinned_without_fallbacks(raw, token):
    # a quorum read by one endpoint, not spread over whichever the router picks
    raw["battery"].update(
        model="deepseek/deepseek-v4.1-flash-1017", endpoints=["deepinfra/fp8", "fireworks"]
    )
    Unified().check(situate(raw))
    assert pinned(situate(raw)) == {"x-codex-router-endpoints": "deepinfra/fp8,fireworks"}
    assert "provider" not in payload(situate(raw), "t", 8)  # the router's header, not its field
    assert policy(situate(raw)) == DENY  # the router keeps pinned endpoints to no data too
    wrong = ("deepinfra/fp8", [f"e{i}" for i in range(17)], ["a,b"], [" fireworks"],
             ["two words"], ["tab\there"], ["bell\x07"])  # fmt: skip
    for endpoints in wrong:
        raw["battery"]["endpoints"] = endpoints
        with pytest.raises(ValueError, match="endpoints lists"):
            Unified().check(situate(raw))


def test_a_pin_goes_as_the_routers_header_and_needs_a_router_that_takes_it(
    raw, token, router, monkeypatch
):
    raw["battery"]["endpoints"] = ["fireworks"]
    fake = router((200, {}, answer("decline")))
    battery = Unified(fake.url)
    battery.check(situate(raw))
    battery.observe(situate(raw), "p", 16)
    [(headers, body)] = fake.requests
    assert headers["x-codex-router-endpoints"] == "fireworks" and "provider" not in body
    monkeypatch.setattr(unified, "capabilities", lambda url, timeout: {"dataPolicies": ["deny"]})
    with pytest.raises(BatteryError, match="the router takes no endpoint pins"):
        Unified(fake.url).check(situate(raw))


def test_consent_to_training_is_a_list_of_slugs_never_a_substring(raw, token):
    # "ultra-spark/deepseek" is a substring of the slug named: no consent
    named = "ultra-spark/deepseek-v4.1-flash-1017"
    raw["battery"].update(model="ultra-spark/deepseek", trainsOnInputs=named)
    with pytest.raises(ValueError, match="trainsOnInputs lists"):
        Unified().check(situate(raw))
    assert policy(situate(raw)) == DENY


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
    # any route the router takes may reach an endpoint that keeps data; only a
    # model the frame names as training on its inputs is sent without the request
    for model in (
        "anthropic/claude-sonnet-5-5",
        "openrouter/anthropic/claude-sonnet-5.5",
        "deepseek/deepseek-v4.1-flash-1017",
        "openrouter/vendor/model",
    ):
        raw["battery"]["model"] = model
        assert policy(situate(raw)) == DENY and "provider" not in payload(situate(raw), "t", 8)
    raw["battery"].update(model="ultra-spark/x", trainsOnInputs=["ultra-spark/x"])
    assert policy(situate(raw)) == {}


def test_a_call_goes_under_the_deny_data_policy_unless_the_frame_consents(raw, token, router):
    fake = router((200, {}, answer("decline")))
    assert Unified(fake.url).observe(situate(raw), "p", 16).label == "decline"
    raw["battery"].update(model="ultra-spark/x", trainsOnInputs=["ultra-spark/x"])
    assert Unified(fake.url).observe(situate(raw), "p", 16).label == "decline"
    (denied, body), (consented, _) = fake.requests
    assert denied["x-codex-router-data-policy"] == "deny" and "provider" not in body
    assert "x-codex-router-data-policy" not in consented


@pytest.mark.parametrize(
    "health, refused",
    [
        ({"capabilities": {"dataPolicies": ["deny"]}}, None),
        ({"capabilities": {"dataPolicies": []}}, "the router takes no data policy"),
        ({"capabilities": {}}, "the router takes no data policy"),
        ({"status": "ok"}, "the router takes no data policy"),
    ],
)
def test_a_router_that_takes_no_data_policy_is_refused_before_any_call(
    raw, token, router, monkeypatch, health, refused
):
    monkeypatch.setattr(unified, "capabilities", LISTS)
    fake = router((200, {}, answer("decline")), {"/health": (200, {}, json.dumps(health).encode())})
    if refused is None:
        Unified(fake.url).check(situate(raw))
    else:
        with pytest.raises(BatteryError, match=refused):
            Unified(fake.url).check(situate(raw))
    assert fake.requests == []  # no call before the check passes


def test_a_router_that_cannot_be_asked_is_refused_unless_the_frame_consents(
    raw, token, monkeypatch
):
    monkeypatch.setattr(unified, "capabilities", LISTS)
    with socket.socket() as held:  # a port nothing answers on
        held.bind(("127.0.0.1", 0))
        url = f"http://127.0.0.1:{held.getsockname()[1]}/v1/responses"
    with pytest.raises(BatteryError, match="could not be asked what it takes"):
        Unified(url).check(situate(raw))
    raw["battery"].update(model="ultra-spark/x", trainsOnInputs=["ultra-spark/x"])
    Unified(url).check(situate(raw))  # no policy sent, so none asked of the router


def test_a_model_the_router_refuses_under_the_policy_is_an_opening(raw, token, router):
    refused = {"error": {"code": "data_policy", "message": "trains on inputs"}}
    fake = router((409, {}, json.dumps(refused).encode()))
    observation = Unified(fake.url).observe(situate(raw), "p", 16)
    model = raw["battery"]["model"]
    assert (
        observation.opening
        == f"the router refused model {model!r}, whose provider trains on its inputs"
    )
    fake = router((409, {}, b"{}"))
    assert Unified(fake.url).observe(situate(raw), "p", 16).opening == "the router answered 409"


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


def test_the_routers_health_is_read_whole_within_its_timeout(monkeypatch):
    # a router that sends its head, then trickles the body: the check must
    # end at its deadline, not whenever the trickle does
    class Trickle:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, amount=None):
            time.sleep(0.3)
            return b'{"capabilities": {}}'

        def read1(self, amount=None):
            time.sleep(0.05)
            return b" "

    monkeypatch.setattr(unified, "capabilities", LISTS)
    monkeypatch.setattr(unified, "opened", lambda request, timeout: Trickle())
    started = time.monotonic()
    with pytest.raises(BatteryError, match="could not be asked what it takes"):
        unified.capabilities("http://127.0.0.1:18766/health", 0.1)
    assert time.monotonic() - started < 0.25


@pytest.mark.parametrize(
    "endpoints, reported, served",
    [
        (["fireworks"], {"provider": "unknown"}, "deepseek/deepseek-v4.1-flash via fireworks"),
        (["fireworks"], {}, "deepseek/deepseek-v4.1-flash via fireworks"),
        (["fireworks"], {"provider": "Fireworks"}, "deepseek/deepseek-v4.1-flash via Fireworks"),
        (["fireworks", "deepinfra"], {"provider": "unknown"}, "deepseek/deepseek-v4.1-flash"),
    ],
)
def test_one_pinned_endpoint_names_what_served_when_the_router_does_not(
    raw, token, router, endpoints, reported, served
):
    # one pin leaves no other endpoint to serve the call; two leave a guess
    raw["battery"]["endpoints"] = endpoints
    body = sse(
        {"type": "response.output_text.delta", "delta": json.dumps({"label": "decline"})},
        {
            "type": "response.completed",
            "response": {"model": "deepseek/deepseek-v4.1-flash", **reported},
        },
    )
    battery = Unified(router((200, {}, body)).url)
    battery.check(situate(raw))
    assert battery.observe(situate(raw), "p", 16).served == served


def completed(**response):
    # a streamed decline, its final event's response as given
    return sse(
        {"type": "response.output_text.delta", "delta": json.dumps({"label": "decline"})},
        {"type": "response.completed", "response": response},
    )


def test_fallback_none_keeps_a_claude_call_on_anthropics_api(raw, token, router):
    raw["battery"]["fallback"] = "none"
    fake = router((200, {}, answer("decline")))
    battery = Unified(fake.url)
    battery.check(situate(raw))
    assert battery.observe(situate(raw), "p", 16).label == "decline"
    [(headers, body)] = fake.requests
    assert headers["x-codex-router-fallback"] == "none" and "fallback" not in body
    assert routing(situate(raw)) == {"x-codex-router-fallback": "none"}
    del raw["battery"]["fallback"]
    assert routing(situate(raw)) == {}  # a frame that names none sends none


def test_a_thinking_budget_goes_as_the_routers_header_in_place_of_an_effort(raw, token, router):
    raw["battery"]["thinkingBudget"] = 2048
    fake = router((200, {}, answer("decline")))
    battery = Unified(fake.url)
    battery.check(situate(raw))
    battery.check_cap(situate(raw), 4096)
    assert battery.observe(situate(raw), "p", 4096).label == "decline"
    [(headers, body)] = fake.requests
    assert headers["x-codex-router-thinking-budget"] == "2048"
    assert "reasoning" not in body and body["max_output_tokens"] == 4096


@pytest.mark.parametrize(
    "line, said",
    [
        ({"fallback": "default"}, "battery.fallback is 'none' or left out"),
        ({"fallback": ["none"]}, "battery.fallback is 'none' or left out"),
        ({"thinkingBudget": 1023}, "battery.thinkingBudget is a whole number of tokens"),
        ({"thinkingBudget": 1_000_000}, "battery.thinkingBudget is a whole number of tokens"),
        ({"thinkingBudget": 2048.0}, "battery.thinkingBudget is a whole number of tokens"),
        ({"thinkingBudget": "2048"}, "battery.thinkingBudget is a whole number of tokens"),
        ({"thinkingBudget": True}, "battery.thinkingBudget is a whole number of tokens"),
        (
            {"fallback": "none", "model": "deepseek/deepseek-v4.1-flash"},
            "battery.fallback applies only to an anthropic/ model",
        ),
        (
            {"thinkingBudget": 2048, "model": "deepseek/deepseek-v4.1-flash"},
            "battery.thinkingBudget applies only to an anthropic/ model",
        ),
        (
            {"thinkingBudget": 2048, "reasoning": "low"},
            "battery.reasoning and battery.thinkingBudget cannot both be set",
        ),
    ],
)
def test_a_line_names_a_fallback_or_a_budget_only_as_the_router_keeps_it(raw, token, line, said):
    raw["battery"].update(line)
    with pytest.raises(BatteryError, match=said):
        Unified().check(situate(raw))


@pytest.mark.parametrize(
    "line, missing, said",
    [
        ({"fallback": "none"}, "fallbackPolicies", "the router takes no fallback policy"),
        ({"thinkingBudget": 2048}, "thinkingBudgets", "the router takes no thinking budget"),
    ],
)
def test_a_router_that_does_not_list_them_refuses_the_frame(
    raw, token, monkeypatch, line, missing, said
):
    raw["battery"].update(line)
    lists = {key: value for key, value in FULL.items() if key != missing}
    monkeypatch.setattr(unified, "capabilities", lambda url, timeout: lists)
    with pytest.raises(BatteryError, match=said):
        Unified().check(situate(raw))

    def unreachable(url, timeout):
        raise BatteryError("the router at 'x' could not be asked what it takes")

    monkeypatch.setattr(unified, "capabilities", unreachable)
    with pytest.raises(BatteryError, match="could not be asked"):  # needed, so not skipped
        Unified().check(situate(raw))


def test_a_budget_the_cap_cannot_hold_is_refused_before_any_call(raw, token, router):
    from midwife.pipeline import calls_needed, run
    from midwife.types import Budget

    raw["battery"]["thinkingBudget"] = 2048
    fake = router((200, {}, answer("decline")))
    frame = situate(raw)
    with pytest.raises(BatteryError, match="is not below each answer's cap of 2048 tokens"):
        run(
            frame, Unified(fake.url), Budget(calls=calls_needed(frame), output_tokens_per_call=2048)
        )
    assert fake.requests == []
    battery = Unified(fake.url)
    battery.check(frame)
    seen = battery.observe(frame, "p", 64)  # a caller past run: an opening, and no call
    assert seen.label is None and seen.opening == (
        "battery.thinkingBudget 2048 is not below each answer's cap of 64 tokens"
    )
    assert fake.requests == []


@pytest.mark.parametrize(
    "error, opening",
    [
        (
            {"code": "anthropic_refused", "reason": "credits"},
            "Anthropic's API refused the call ('credits'), and the battery line keeps it there",
        ),
        (
            {"code": "anthropic_refused"},
            "Anthropic's API refused the call, and the battery line keeps it there",
        ),
        ({"code": "other"}, "the router answered 502"),
    ],
)
def test_a_refusal_kept_on_anthropics_api_is_an_opening_that_says_why(
    raw, token, router, error, opening
):
    raw["battery"]["fallback"] = "none"
    fake = router(
        (502, {"content-type": "application/json"}, json.dumps({"error": error}).encode())
    )
    battery = Unified(fake.url)
    battery.check(situate(raw))
    seen = battery.observe(situate(raw), "p", 16)
    assert seen.label is None and seen.opening == opening and seen.served == ""


@pytest.mark.parametrize(
    "endpoints, reported, served",
    [
        ([], {"provider": "Anthropic", "route": "anthropic"}, "m via Anthropic (route anthropic)"),
        ([], {"provider": "unknown", "route": "openrouter"}, "m (route openrouter)"),
        (["fireworks"], {"provider": "unknown", "route": "openrouter"},
         "m via fireworks (route openrouter)"),
        ([], {"provider": "Anthropic", "route": "Open Router"}, "m via Anthropic"),  # no guess
        ([], {"provider": "Anthropic", "route": 7}, "m via Anthropic"),
    ],
)  # fmt: skip
def test_a_record_names_the_route_the_router_says_a_call_went(
    raw, token, router, endpoints, reported, served
):
    # a Claude call moved to another provider reads apart from one kept on Anthropic's
    if endpoints:
        raw["battery"]["endpoints"] = endpoints
    battery = Unified(router((200, {}, completed(model="m", **reported))).url)
    battery.check(situate(raw))
    assert battery.observe(situate(raw), "p", 16).served == served
