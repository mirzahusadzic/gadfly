"""Boundary crossings: a span that names the source it crossed from, and a
reading made through a maker at one grain and a reader at the next. No model
is called; the makers and readers are rules."""

import copy
import hashlib
import json

import pytest

from midwife.errors import BatteryError, FrameError
from midwife.frame import parse
from midwife.interventions import plan
from midwife.pipeline import calls_needed, judge, run
from midwife.types import Budget, Observation
from tests.fixtures.incident import INCIDENT, CauseReader, cause, headline
from tests.test_schema import VALIDATOR


def sourced(text, origin="the refund policy, version 3"):
    return {"sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "from": origin}


def test_a_span_that_crossed_names_the_exact_text_that_left(raw):
    plain = parse(copy.deepcopy(raw))
    text = raw["body"]["spans"][1]["text"]
    raw["body"]["spans"][1]["source"] = sourced(text)
    frame = parse(raw)
    assert VALIDATOR.is_valid(raw)
    assert frame.spans[1] == plain.spans[1]  # the reader gets the same text
    assert frame.hash != plain.hash  # the frame names where it came from, so it is another frame
    raw["body"]["spans"][1]["source"] = {"sha256": sourced(text)["sha256"]}  # from is optional
    parse(raw)


def test_a_span_whose_text_is_not_what_crossed_is_refused(raw):
    raw["body"]["spans"][1]["source"] = sourced("A refund requires a receipt, kept 30 days.")
    with pytest.raises(FrameError, match="span 'r2' does not hash to its source") as refused:
        parse(raw)
    found = hashlib.sha256(raw["body"]["spans"][1]["text"].encode()).hexdigest()
    assert refused.value.__notes__ == [
        f"its text hashes to {found!r}; it must be byte for byte the text that crossed"
    ]
    assert VALIDATOR.is_valid(raw)  # only the parser reads the text against its hash
    raw["body"]["spans"][1]["source"] = {"sha256": "0" * 64, "from": ""}
    with pytest.raises(FrameError, match="names a source that is not"):
        parse(raw)


def crossed(maker=None, reader=None, raw=None, battery=None):
    from midwife.batteries.crossing import Crossing, Function

    raw = copy.deepcopy(raw or INCIDENT)
    if battery:
        raw["battery"] = battery
    frame = parse(raw)
    crossing = Crossing(maker or Function("cause", cause), reader or CauseReader())
    result = run(frame, crossing, Budget(calls=calls_needed(frame)))
    return frame, crossing, result


def test_a_decision_that_rests_on_its_evidence_across_the_crossing_is_carried():
    frame, _, result = crossed()
    finding = judge(frame, result.records)[0]
    assert finding.category == "carried"
    assert result.records[0].usage == {"output_tokens": 3}  # the function spent nothing
    assert finding.levels["baseline"] == "rollback" and finding.levels["ablation"] == "investigate"
    assert finding.levels["presentation"] == "rollback"  # the maker reads either wording
    record = result.records[0].as_dict()
    assert (
        record["battery"] == "crossing"
        and record["served"] == "made by cause, read by cause-reader 1"
    )
    kept = json.loads(record["raw"])
    assert record["trial"] == "baseline"
    text = cause(plan(frame)[0].text)  # the record names its prompt by hash alone
    assert kept["made"] == {"sha256": hashlib.sha256(text.encode()).hexdigest(), "text": text}


def test_a_maker_that_drops_the_anchor_cools_the_decision_at_the_crossing():
    from midwife.batteries.crossing import Function

    frame, _, result = crossed(Function("cause", headline))
    finding = judge(frame, result.records)[0]
    assert finding.levels["baseline"] == finding.levels["ablation"] == "investigate"
    assert finding.category == "cooled"  # what the anchor said never crossed


def test_the_maker_sees_the_body_alone_and_the_reader_the_artefact_and_the_input():
    from midwife.batteries.crossing import Crossing, Made

    seen = []

    class Watching:
        name = "cause"
        concurrent = True

        def check(self, line):
            pass

        def make(self, line, text, max_output_tokens):
            seen.append((line, text, max_output_tokens))
            return Made(cause(text), usage={"output_tokens": 40})

    reader = CauseReader()
    frame = parse(copy.deepcopy(INCIDENT))
    crossing = Crossing(Watching(), reader)
    crossing.check(frame)
    o = crossing.observe(frame, f"{frame.spans[1].text}\n\n---\nQ\n\n---\n\nShould it?", 100)
    assert seen == [({"kind": "cause"}, f"{frame.spans[1].text}\n\n---\nQ", 50)]  # half the cap
    assert reader.prompts == [(f"{cause(seen[0][1])}\n\n---\n\nShould it?", 60)]  # what is left
    assert o.usage == {"output_tokens": 43}  # the call's whole spend, within its cap


def test_an_artefact_not_made_is_an_opening_and_the_reader_is_not_asked():
    from midwife.batteries.crossing import Crossing, Made

    class Failing:
        name = "cause"
        concurrent = True

        def __init__(self, made):
            self.made = made

        def check(self, line):
            pass

        def make(self, line, text, max_output_tokens):
            if isinstance(self.made, Exception):
                raise self.made
            return self.made

    frame = parse(copy.deepcopy(INCIDENT))
    reader = CauseReader()
    cases = [
        (Made(None, opening="the call passed its timeout", raw="{", usage={"output_tokens": 9}),
         "the maker made nothing ('the call passed its timeout')"),
        (Made("Cause.", usage={"output_tokens": 100}), "the maker spent the call's whole cap"),
        (Made("  "), "the maker made an empty artefact"),
        (RuntimeError("down"), "the maker failed (RuntimeError)"),
        ("text", "the maker returned nothing it made"),
    ]  # fmt: skip
    for made, opening in cases:
        o = Crossing(Failing(made), reader).observe(frame, "body\n\n---\n\nQ", 100)
        assert (o.label, o.opening) == (None, opening)
    assert reader.prompts == []
    first = Crossing(Failing(cases[0][0]), reader).observe(frame, "b\n\n---\n\nQ", 100)
    assert first.raw == "{" and first.usage == {"output_tokens": 9}
    unreported = Crossing(Failing(Made("  ")), reader).observe(frame, "b\n\n---\n\nQ", 100)
    assert unreported.usage == {"output_tokens": 50}  # a side that reports nothing spent its share
    with pytest.raises(BatteryError, match="either an artefact or an opening"):
        Made("text", opening="and why not")


def test_a_reader_that_fails_keeps_the_artefact_and_spends_what_it_was_given():
    from midwife.batteries.crossing import Crossing, Function

    class Broken(CauseReader):
        def observe(self, frame, prompt, max_output_tokens):
            raise OSError("gone")

    frame = parse(copy.deepcopy(INCIDENT))
    o = Crossing(Function("cause", cause), Broken()).observe(frame, "b\n\n---\n\nQ", 100)
    assert o.opening == "the reader failed (OSError)" and o.served == "made by cause"
    assert o.usage == {
        "output_tokens": 100
    }  # a function spends nothing; the reader all it was given
    assert json.loads(o.raw)["made"]["text"] == cause("b")


def test_a_crossing_refuses_a_line_it_was_not_made_for():
    from midwife.batteries.crossing import Crossing, Function

    def refused(battery, match, raw=None):
        frame = parse({**copy.deepcopy(raw or INCIDENT), "battery": battery})
        with pytest.raises(BatteryError, match=match):
            Crossing(Function("cause", cause), CauseReader()).check(frame)

    line = INCIDENT["battery"]
    refused({**line, "kind": "unified"}, "asks for battery 'unified'")
    refused({**line, "context": []}, "reads no 'context' under battery")
    refused({**line, "maker": "cause"}, "battery.maker is a line of its own")
    refused({**line, "reader": {"kind": "unified"}}, "names kind 'unified', not 'cause-reader'")
    refused({**line, "maker": {"kind": "cause", "v": 2}}, "reads nothing but its kind")
    asked = {**copy.deepcopy(INCIDENT), "inputs": [{"id": "q1", "text": "a\n\n---\n\nb"}]}
    refused(line, "input 'q1' holds the line that parts a body from its input", asked)


def test_a_sides_refusal_says_which_line_it_refused():
    from midwife.batteries.crossing import Crossing, Function

    class Refusing(CauseReader):
        def check(self, frame):
            raise BatteryError("this reader serves no frame")

    frame = parse(copy.deepcopy(INCIDENT))
    with pytest.raises(BatteryError) as refused:
        Crossing(Function("cause", cause), Refusing()).check(frame)
    assert refused.value.__notes__ == [
        "it is the crossing's reader line, battery.reader, that is refused"
    ]


def test_calls_run_at_once_only_when_both_sides_take_them():
    from midwife.batteries.crossing import Crossing, Function

    class Sequential(CauseReader):
        concurrent = False

    assert Crossing(Function("cause", cause), CauseReader()).concurrent is True
    assert Crossing(Function("cause", cause), Sequential()).concurrent is False
    frame, _, result = crossed()
    parallel = run(frame, Crossing(Function("cause", cause), CauseReader()),
                   Budget(calls=calls_needed(frame)), parallel=4)  # fmt: skip
    assert judge(frame, parallel.records) == judge(frame, result.records)


MAKER = {
    "kind": "unified",
    "model": "anthropic/claude-sonnet-5-5",
    "instruction": "Write the incident's cause in one sentence.",
}
READER = {"kind": "unified", "model": "deepseek/deepseek-v4.1-flash", "reasoning": "low"}


@pytest.fixture
def through_router(monkeypatch, tmp_path):
    """A fake router that writes a cause for a maker's request and decides
    for a reader's, as the rules above would."""
    from midwife.batteries import unified
    from tests.fakes import Fake

    monkeypatch.setenv("CODEX_ROUTER_TOKEN", "ab" * 32)
    monkeypatch.setattr(unified, "ENV_FILE", tmp_path / "absent.env")
    monkeypatch.setattr(
        unified,
        "capabilities",
        lambda url, timeout: {
            "dataPolicies": ["deny"],
            "endpointPins": True,
            "reports": ["provider"],
        },
    )

    def reply(body):
        text = body["input"][0]["content"][0]["text"]
        if "text" in body["text"]["format"]["schema"]["properties"]:
            answer, used = {"text": cause(text)}, 30
        else:
            label = CauseReader().observe(None, text, 0).label
            answer, used = {"label": label}, 4
        events = [
            {"type": "response.output_text.delta", "delta": json.dumps(answer)},
            {
                "type": "response.completed",
                "response": {"model": body["model"], "provider": "Example",
                             "usage": {"output_tokens": used, "input_tokens": 50}},
            },
        ]  # fmt: skip
        return 200, {}, b"".join(b"data: " + json.dumps(e).encode() + b"\n\n" for e in events)

    servers = []

    def start(answer=reply):
        servers.append(Fake(answer))
        return servers[-1]

    yield start
    for server in servers:
        server.close()


def test_a_model_writes_the_artefact_and_another_reads_it_through_the_router(through_router):
    from midwife.batteries.crossing import WRITTEN, Crossing, UnifiedMaker
    from midwife.batteries.unified import Unified

    router = through_router()
    battery = {"kind": "crossing", "maker": MAKER, "reader": READER}
    crossing = Crossing(UnifiedMaker(router.url), Unified(router.url))
    raw = {**copy.deepcopy(INCIDENT), "battery": battery}
    frame = parse(raw)
    result = run(frame, crossing, Budget(calls=calls_needed(frame), output_tokens_per_call=200))
    assert judge(frame, result.records)[0].category == "carried"
    (made_headers, made), (read_headers, read) = router.requests[:2]
    assert made["instructions"] == MAKER["instruction"] and made["max_output_tokens"] == 100
    assert made["text"]["format"]["schema"] == WRITTEN and "tools" not in made
    assert made["input"][0]["content"][0]["text"] == plan(frame)[0].text  # the body alone
    assert made_headers["x-codex-router-data-policy"] == "deny"
    assert read["instructions"] == INCIDENT["observe"]["instruction"]
    assert read["max_output_tokens"] == 170 and read["reasoning"] == {"effort": "low"}
    written = cause(plan(frame)[0].text)
    question = INCIDENT["inputs"][0]["text"]
    assert read["input"][0]["content"][0]["text"] == f"{written}\n\n---\n\n{question}"
    record = result.records[0]
    assert record.usage == {"output_tokens": 34, "input_tokens": 100}
    assert record.served == (
        "made by anthropic/claude-sonnet-5-5 via Example, "
        "read by deepseek/deepseek-v4.1-flash via Example"
    )


def test_the_maker_line_is_held_to_the_unified_batterys_checks(through_router):
    from midwife.batteries.crossing import Crossing, UnifiedMaker

    router = through_router()

    def refused(maker, match):
        frame = parse({**copy.deepcopy(INCIDENT), "battery": {"kind": "crossing", "maker": maker,
                                                              "reader": READER}})  # fmt: skip
        with pytest.raises(BatteryError, match=match) as error:
            Crossing(UnifiedMaker(router.url)).check(frame)
        return error.value

    refused({**MAKER, "output": {}}, "the unified maker reads no 'output'")
    refused({k: v for k, v in MAKER.items() if k != "instruction"}, "says what the maker writes")
    error = refused({**MAKER, "model": "gpt-5.5"}, "model 'gpt-5.5' is an OpenAI slug")
    assert error.__notes__[-1] == "it is the crossing's maker line, battery.maker, that is refused"
    muse = "openrouter/meta/muse-spark-1.3"
    refused({**MAKER, "model": muse}, "trains on its inputs")
    frame = parse({**copy.deepcopy(INCIDENT), "battery": {
        "kind": "crossing", "maker": {**MAKER, "model": muse, "trainsOnInputs": [muse]},
        "reader": READER}})  # fmt: skip
    Crossing(UnifiedMaker(router.url)).check(frame)  # named, it may go there


def test_a_maker_answer_with_no_text_or_a_refusal_is_an_opening(through_router):
    from midwife.batteries.crossing import Crossing, UnifiedMaker

    events = [
        {"type": "response.output_text.delta", "delta": json.dumps({"text": " "})},
        {"type": "response.completed", "response": {"usage": {"output_tokens": 7}}},
    ]
    empty = through_router(
        lambda body: (
            200,
            {},
            b"".join(b"data: " + json.dumps(e).encode() + b"\n\n" for e in events),
        )
    )
    frame = parse({**copy.deepcopy(INCIDENT), "battery": {"kind": "crossing", "maker": MAKER,
                                                          "reader": READER}})  # fmt: skip
    o = Crossing(UnifiedMaker(empty.url), CauseReader()).observe(frame, "b\n\n---\n\nQ", 100)
    assert o.opening == "the maker made nothing ('the answer held no text')"
    assert o.usage == {"output_tokens": 7}
    events[0]["delta"] = json.dumps(["a list, not an answer"])
    o = Crossing(UnifiedMaker(empty.url), CauseReader()).observe(frame, "b\n\n---\n\nQ", 100)
    assert o.opening == "the maker made nothing ('the answer held no text')"
    refusal = json.dumps({"error": {"code": "data_policy"}}).encode()
    refusing = through_router(lambda body: (409, {}, refusal))
    o = Crossing(UnifiedMaker(refusing.url), CauseReader()).observe(frame, "b\n\n---\n\nQ", 100)
    assert o.opening == (
        "the maker made nothing (\"the router refused model 'anthropic/claude-sonnet-5-5', "
        'whose provider trains on its inputs")'
    )


def test_a_side_that_returns_the_wrong_thing_is_an_opening_never_a_label():
    from midwife.batteries.crossing import Crossing, Function, Made

    class Odd:
        name = "cause"

        def check(self, line):
            pass

        def make(self, line, text, max_output_tokens):
            return Made("Deploy 42 shrank the connection pool.", usage=self.usage)

    class Silent(CauseReader):
        def observe(self, frame, prompt, max_output_tokens):
            return "rollback"

    frame = parse(copy.deepcopy(INCIDENT))
    blank = Crossing(Function("cause", lambda body: None), CauseReader())
    o = blank.observe(frame, "b\n\n---\n\nQ", 10)
    assert o.opening == "the maker made nothing ('the function returned no text')"
    odd, reader = Odd(), CauseReader()
    for usage in (["not", "counts"], {"output_tokens": -5}, {"output_tokens": "5"}):
        odd.usage = usage
        o = Crossing(odd, reader).observe(frame, "b\n\n---\n\nQ", 10)
        assert o.opening == "the maker's report of what it spent is not a count of tokens"
        assert o.usage == {"output_tokens": 5}  # what it may have spent: all of its share
    assert reader.prompts == []  # a negative report never buys the reader a larger cap
    odd.usage = {"output_tokens": 1}
    o = Crossing(odd, Silent()).observe(frame, "b\n\n---\n\nQ", 10)
    assert o.opening == "the reader gave no label ('the battery returned no observation')"
    assert o.usage == {"output_tokens": 10}  # the reader said nothing: all it was given


def test_the_command_line_runs_a_crossing_made_in_a_module_of_your_own(tmp_path, capsys):
    from midwife.cli import main

    path, out = tmp_path / "incident.json", tmp_path / "incident.jsonl"
    path.write_text(json.dumps(INCIDENT))
    frame = parse(copy.deepcopy(INCIDENT))
    battery = "tests.fixtures.incident:crossing"
    calls = str(calls_needed(frame))
    assert main(["run", str(path), "--battery", battery, "--calls", calls,
                 "--output-tokens", "100", "--out", str(out)]) == 0  # fmt: skip
    capsys.readouterr()
    assert main(["report", str(path), str(out)]) == 0
    assert "q1: carried" in capsys.readouterr().out


class Reporting(CauseReader):
    """The cause reader, answering with what it is told to answer and report."""

    def __init__(self, label="rollback", opening=None, usage=None):
        super().__init__()
        usage = {"output_tokens": 3} if usage is None else usage
        self.answer = Observation(label=label, opening=opening, raw="its answer", usage=usage)

    def observe(self, frame, prompt, max_output_tokens):
        self.prompts.append((prompt, max_output_tokens))
        return self.answer


def test_each_opening_says_which_side_gave_no_answer():
    from midwife.batteries.crossing import Crossing, Function

    frame = parse(copy.deepcopy(INCIDENT))
    for reader, opening in [
        (Reporting(None, "the router answered 500"),
         "the reader gave no label ('the router answered 500')"),
        (Reporting("maybe"),
         "the reader gave no label ('the battery returned no label of this frame')"),
        (Reporting(usage={"output_tokens": "3"}),
         "the reader gave no label ('the battery returned a malformed observation (usage)')"),
        (Reporting(usage={"output_tokens": -40}),
         "the reader's report of what it spent is not a count of tokens"),
    ]:  # fmt: skip
        o = Crossing(Function("cause", cause), reader).observe(frame, "b\n\n---\n\nQ", 100)
        assert (o.label, o.opening) == (None, opening)
        assert json.loads(o.raw)["made"]["text"] == cause("b")
    assert o.usage == {"output_tokens": 100}  # a reader whose report is unsound: all it was given


def test_a_maker_that_fails_is_charged_its_share_and_a_function_nothing():
    from midwife.batteries.crossing import Crossing, Function, Made

    def broken(body):
        raise RuntimeError("no artefact")

    class Raising:
        name = "cause"

        def check(self, line):
            pass

        def make(self, line, text, max_output_tokens):
            raise OSError("gone")

    frame = parse(copy.deepcopy(INCIDENT))
    o = Crossing(Function("cause", broken), CauseReader()).observe(frame, "b\n\n---\n\nQ", 100)
    assert o.opening == "the maker made nothing ('the function failed (RuntimeError)')"
    assert o.usage == {"output_tokens": 0} and o.served == "made by cause"
    o = Crossing(Raising(), CauseReader()).observe(frame, "b\n\n---\n\nQ", 100)
    assert (o.opening, o.usage) == ("the maker failed (OSError)", {"output_tokens": 50})
    budget = Budget(calls=frame.quorum, output_tokens_per_call=100, tokens=100)
    failing = run(frame, Crossing(Function("cause", broken), CauseReader()), budget,
                  only=["baseline"])  # fmt: skip
    assert failing.stopped is None and len(failing.records) == frame.quorum  # it spent nothing

    class Surrogate(Raising):
        def make(self, line, text, max_output_tokens):
            return Made("bad \ud800", usage={"output_tokens": 4})

    o = Crossing(Surrogate(), CauseReader()).observe(frame, "b\n\n---\n\nQ", 100)
    assert o.opening == "the maker made text that is not valid Unicode"
    assert o.usage == {"output_tokens": 4}


def test_a_negative_report_never_hides_spend_from_the_token_budget():
    from midwife.batteries.crossing import Crossing, Made

    class Refunding:
        name = "cause"

        def check(self, line):
            pass

        def make(self, line, text, max_output_tokens):
            return Made("Deploy 42 shrank the connection pool.", usage=self.usage)

    frame = parse(copy.deepcopy(INCIDENT))
    reader = Reporting(usage={"output_tokens": 50})
    maker = Refunding()
    maker.usage = {"output_tokens": -50}
    budget = Budget(calls=frame.quorum, output_tokens_per_call=100, tokens=100)
    result = run(frame, Crossing(maker, reader), budget, only=["baseline"])
    assert reader.prompts == [] and result.stopped == "the token budget (100) is spent"
    maker.usage = {"output_tokens": 1_000}  # past the cap: reported as it is, and the run stops
    result = run(frame, Crossing(maker, reader), Budget(calls=3, output_tokens_per_call=100),
                 only=["baseline"])  # fmt: skip
    assert result.records[0].usage == {"output_tokens": 1_000}
    assert result.stopped == "the battery reported 1000 output tokens for a call capped at 100"


def test_the_record_keeps_the_artefacts_hash_whole_and_parses_however_long():
    from midwife.batteries.crossing import Crossing, Made
    from midwife.pipeline import RAW_LIMIT

    class Long:
        name = "cause"

        def check(self, line):
            pass

        def make(self, line, text, max_output_tokens):
            return Made(self.text, usage={"output_tokens": 10})

    frame = parse(copy.deepcopy(INCIDENT))
    maker = Long()
    for made, read in [("Artefact.", "x" * 2_500), ("é\n" * 3_000, "short"), ("a" * 5, "b" * 5)]:
        maker.text = made
        reader = Reporting()
        reader.answer = Observation(label="rollback", raw=read, usage={"output_tokens": 3})
        result = run(frame, Crossing(maker, reader), Budget(calls=3), only=["baseline"])
        raw = result.records[0].raw
        kept = json.loads(raw)  # whole JSON, never cut mid-string
        assert len(raw) <= RAW_LIMIT
        assert kept["made"]["sha256"] == hashlib.sha256(made.encode()).hexdigest()
        assert made.startswith(kept["made"]["text"]) and read.startswith(kept["read"])
    assert kept == {"made": {"sha256": kept["made"]["sha256"], "text": "aaaaa"}, "read": "bbbbb"}
