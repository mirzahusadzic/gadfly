"""The refund example, as a user runs it."""

import json

import pytest

from examples import refund, refund_live
from gadfly.batteries.unified import Unified
from tests.fakes import Fake


def test_presentation_tells_a_phrase_from_a_rule(tmp_path):
    findings = refund.main(tmp_path / "records.jsonl")
    assert [(name, category) for name, category, _ in findings] == [
        ("phrase-matcher", "coupled but misaligned"),
        # carried needs every carriage check passed, and its fallback is open
        ("rule-reader", "unresolved"),
    ]
    assert findings[0][2] == [
        "presentation moved it decline -> grant",
        # misaligned lists its open checks too
        "no hidden fallback: bypass left it at decline",
    ]
    assert findings[1][2] == [
        "ablation moved it decline -> grant; held under presentation, 2 shams",
        "not carried while 1 carriage check is open",
        # it reads the rule whether or not the rules bind: a fallback, left open
        "no hidden fallback: bypass left it at decline",
    ]


def test_the_example_never_writes_over_kept_records(tmp_path):
    kept = tmp_path / "records.jsonl"
    kept.write_text("")
    with pytest.raises(FileExistsError):
        refund.main(kept)


def test_the_live_example_runs_through_a_battery_without_a_model(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_ROUTER_TOKEN", "ab" * 32)
    answer = json.dumps({"label": "decline"})
    events = [
        {"type": "response.output_text.delta", "delta": answer},
        {"type": "response.completed", "response": {"usage": {"output_tokens": 3}}},
    ]
    body = b"".join(b"data: " + json.dumps(e).encode() + b"\n\n" for e in events)
    fake = Fake((200, {}, body))
    try:
        result, finding = refund_live.main(
            Unified(fake.url), "anthropic/claude-sonnet-5-5", tmp_path / "records.jsonl"
        )
    finally:
        fake.close()
    assert result.stopped is None and len(fake.requests) == 21
    assert {b["reasoning"]["effort"] for _, b in fake.requests} == {"low"}
    # a critic that always declines: nothing shows it can tell, so not cooled
    assert finding.category == "unresolved"
    assert len((tmp_path / "records.jsonl").read_text().splitlines()) == 21


def test_the_review_handoff_worked_example():
    from examples import review_handoff

    assert review_handoff.main() == [
        # the authority frame declares no bypass and no sham, so carried waits
        ("state projection", "carried", "unresolved"),
        # nothing shows the summary's reading can move, so cooled waits
        ("summary: fix ready", "unresolved", "unresolved"),
        ("drops its openings", "coupled but misaligned", "unresolved"),
        ("projection, a record lost", "unresolved", "-"),
    ]
