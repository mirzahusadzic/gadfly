"""The refund example, as a user runs it."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from examples import refund, refund_live
from gadfly.batteries.unified import Unified
from tests.fakes import Fake


def test_presentation_tells_a_phrase_from_a_rule(tmp_path):
    findings = refund.main(tmp_path / "records.jsonl")
    assert [(name, category) for name, category, _ in findings] == [
        ("phrase-matcher", "coupled but misaligned"),
        ("rule-reader", "carried"),
    ]
    assert findings[0][2] == [
        "presentation moved it decline -> grant",
        # a phrase holds whether or not the rules bind: its fallback is open too
        "no hidden fallback: bypass gave decline, not the designated opening (unclear)",
    ]
    # every check passed: the bypass exposed the opening, nothing is left open
    assert findings[1][2] == [
        "ablation moved it decline -> grant; held under presentation, 2 shams",
        "bypass moved it decline -> unclear: no hidden fallback",
        "the control moved it decline -> grant",
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
    assert result.stopped is None and len(fake.requests) == 24
    assert {b["reasoning"]["effort"] for _, b in fake.requests} == {"low"}
    # a critic that always declines: the control (no rules at all) leaves it too
    assert finding.category == "unresolved"
    assert "the scorer cannot tell" in finding.evidence[-1]
    assert len((tmp_path / "records.jsonl").read_text().splitlines()) == 24


def test_the_review_handoff_worked_example():
    from examples import review_handoff

    assert review_handoff.main() == [
        ("state projection", "carried", "carried"),
        # it says the same whatever it is given: the control cannot move it either
        ("summary: fix ready", "unresolved", "unresolved"),
        ("drops its openings", "coupled but misaligned", "carried"),
        ("projection, a record lost", "unresolved", "-"),
    ]


def categories(module):
    return [(name, category) for name, category, _ in module.main()]


def test_a_cited_source_tells_a_reader_from_a_word_matcher():
    from examples import citation

    assert categories(citation) == [
        ("word-matcher", "coupled but misaligned"),
        ("citation-reader", "carried"),
    ]


def test_a_system_prompt_line_is_cooled_only_by_a_scorer_that_can_move():
    from examples import system_prompt

    rows = system_prompt.main()
    assert [(name, category) for name, category, _ in rows] == [
        ("request-alarm", "cooled"),
        ("always-refuse", "unresolved"),
    ]
    assert "the control moved it refuse -> comply: the scorer can tell" in rows[0][2]


def test_a_tool_permission_moved_the_wrong_way_is_misaligned():
    from examples import tool_permission

    assert categories(tool_permission) == [
        ("eager-tool", "coupled but misaligned"),
        ("scope-reader", "carried"),
    ]


def test_a_code_invariant_its_lost_records_and_its_owners_exclusion():
    from examples import code_invariant

    assert categories(code_invariant) == [
        ("full run", "carried"),
        ("records lost", "unresolved"),
        ("declared out of scope", "unresolved"),
        ("declared and checked", "outside scope"),
    ]


def test_a_refused_live_run_leaves_no_records_file_behind(tmp_path, monkeypatch):
    # an empty file left by a refusal would refuse the next, keyed run
    monkeypatch.delenv("CODEX_ROUTER_TOKEN", raising=False)
    monkeypatch.setattr("gadfly.batteries.unified.ENV_FILE", tmp_path / "absent.env")
    out = tmp_path / "records.jsonl"
    with pytest.raises(RuntimeError, match="no router token"):
        refund_live.main(Unified("http://127.0.0.1:1/v1/responses"), "anthropic/x", out)
    assert not out.exists()


def test_the_live_example_says_why_it_refuses_in_one_line(tmp_path):
    env = {k: v for k, v in os.environ.items() if "EGEMMA" not in k and k != "WORKBENCH_API_KEY"}
    done = subprocess.run(
        [sys.executable, "examples/refund_live.py", "egemma", "gemma", str(tmp_path / "r.jsonl")],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
        env={**env, "PYTHONPATH": str(Path(__file__).parent.parent)},
        timeout=60,
    )
    assert done.returncode != 0 and "Traceback" not in done.stderr
    assert done.stderr.strip() == (
        "refund_live: no eGemma key: set EGEMMA_API_KEY_FILE or EGEMMA_API_KEY"
    )
    assert not (tmp_path / "r.jsonl").exists()
