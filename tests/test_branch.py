"""The branch battery: what an answer needs is written once from the input
alone, and every trial is read against it. No model is called; the makers
and readers are rules."""

import copy
import hashlib
import json
import threading

import pytest

from midwife.errors import BatteryError
from midwife.frame import parse
from midwife.interventions import plan
from midwife.pipeline import calls_needed, judge, run
from midwife.types import Budget, Observation
from tests.fixtures.incident import cause
from tests.fixtures.needs import NEEDS, PARTS, NeedsReader, needs

QUESTION = NEEDS["inputs"][0]["text"]


def branched(maker=None, reader=None, raw=None, **how):
    from midwife.batteries.branch import Branch
    from midwife.batteries.crossing import Function

    frame = parse(copy.deepcopy(raw or NEEDS))
    branch = Branch(maker or Function("needs", needs), reader or NeedsReader())
    budget = how.pop("budget", None) or Budget(calls=calls_needed(frame))
    result = run(frame, branch, budget, **how)
    return frame, branch, result


class Watching:
    """A maker that keeps what it was given and says what it spent."""

    name = "needs"
    concurrent = True

    def __init__(self, spend=40):
        self.seen, self.spend = [], spend

    def check(self, line):
        pass

    def make(self, line, text, max_output_tokens):
        from midwife.batteries.crossing import Made

        self.seen.append((line, text, max_output_tokens))
        return Made(needs(text), usage={"output_tokens": self.spend}, served="needs 1")


def test_a_decision_read_against_what_it_needs_is_carried():
    frame, _, result = branched()
    finding = judge(frame, result.records)[0]
    assert finding.category == "carried"
    assert finding.levels["baseline"] == "rollback" and finding.levels["ablation"] == "investigate"
    record = result.records[0].as_dict()
    assert record["battery"] == "branch" and record["trial"] == "baseline"
    assert record["served"] == "made by needs, read by needs-reader 1"
    text = needs(QUESTION)
    kept = json.loads(record["raw"])
    assert kept["made"] == {"sha256": hashlib.sha256(text.encode()).hexdigest(), "text": text}


def test_the_maker_sees_the_input_alone_and_once_for_the_whole_run():
    maker, reader = Watching(), NeedsReader()
    budget = Budget(calls=calls_needed(parse(copy.deepcopy(NEEDS))), output_tokens_per_call=100)
    frame, _, result = branched(maker, reader, budget=budget)
    assert maker.seen == [({"kind": "needs"}, QUESTION, 50)]  # the input, within half a cap
    for span in frame.spans:
        assert span.text not in maker.seen[0][1]  # nothing of the evidence reached it
    first, later = result.records[0], result.records[1:]
    assert first.usage == {"output_tokens": 43}  # the call that made it is charged for it
    assert {record.usage["output_tokens"] for record in later} == {3}  # the rest only read
    assert reader.prompts[0][1] == 60  # what the maker left of the first call's cap
    assert {cap for _, cap in reader.prompts[1:]} == {100}  # then the whole cap
    made = needs(QUESTION)
    for record in result.records:  # every record names the one artefact it was read against
        assert json.loads(record.raw)["made"]["text"] == made
        assert record.served == "made by needs 1, read by needs-reader 1"


def test_the_reader_is_given_the_artefact_then_the_body_then_the_input():
    reader = NeedsReader()
    frame, _, _ = branched(reader=reader)
    bodies = [trial.text for trial in plan(frame)]
    for asked, _ in reader.prompts:
        artefact, body, question = asked.split(PARTS)
        assert artefact == needs(QUESTION) and question == QUESTION and body in bodies


def test_what_an_ablation_took_out_cannot_come_back_through_the_artefact():
    # the maker writes the same artefact for the baseline and for the ablation,
    # so the ablation's label moves on the evidence alone
    reader = NeedsReader()
    frame, _, result = branched(reader=reader)
    anchor = frame.spans[1].text
    assert anchor not in needs(QUESTION)
    cut = [asked for asked, _ in reader.prompts if anchor not in asked.split(PARTS)[1]]
    assert cut and all(asked.split(PARTS)[0] == needs(QUESTION) for asked in cut)
    assert judge(frame, result.records)[0].levels["ablation"] == "investigate"


def test_an_artefact_not_made_is_an_opening_and_the_next_call_makes_it_again():
    from midwife.batteries.branch import Branch
    from midwife.batteries.crossing import Made

    class Flaky(Watching):
        def make(self, line, text, max_output_tokens):
            if not self.seen:
                self.seen.append((line, text, max_output_tokens))
                return Made(None, opening="the call ended incomplete", usage={"output_tokens": 9})
            return super().make(line, text, max_output_tokens)

    maker, reader = Flaky(), NeedsReader()
    frame = parse(copy.deepcopy(NEEDS))
    branch = Branch(maker, reader)
    body = plan(frame)[0].text
    first = branch.observe(frame, f"{body}{PARTS}{QUESTION}", 100)
    assert first.label is None and reader.prompts == []  # the reader is not asked
    assert first.opening == "the maker made nothing ('the call ended incomplete')"
    assert first.usage == {"output_tokens": 9}
    second = branch.observe(frame, f"{body}{PARTS}{QUESTION}", 100)
    third = branch.observe(frame, f"{body}{PARTS}{QUESTION}", 100)
    assert second.label == third.label == "rollback"
    assert len(maker.seen) == 2  # made again once, then kept
    assert second.usage == {"output_tokens": 43} and third.usage == {"output_tokens": 3}


def test_an_artefact_that_holds_the_parting_line_is_an_opening():
    from midwife.batteries.branch import Branch
    from midwife.batteries.crossing import Function

    reader = NeedsReader()
    frame = parse(copy.deepcopy(NEEDS))
    branch = Branch(Function("needs", lambda question: f"one{PARTS}two"), reader)
    seen = branch.observe(frame, f"{plan(frame)[0].text}{PARTS}{QUESTION}", 100)
    assert seen.label is None and reader.prompts == []
    assert seen.opening == "the maker made text that holds the line that parts it from the body"
    assert json.loads(seen.raw)["made"]["text"] == f"one{PARTS}two"  # kept, to be looked at


def test_each_input_has_an_artefact_of_its_own():
    raw = copy.deepcopy(NEEDS)
    raw["inputs"].append({"id": "q2", "text": "Should deploy 42 be kept?"})
    maker = Watching()
    frame, _, result = branched(maker, raw=raw)
    assert [text for _, text, _ in maker.seen] == [QUESTION, "Should deploy 42 be kept?"]
    made = {json.loads(record.raw)["made"]["text"] for record in result.records}
    assert made == {needs(QUESTION), needs("Should deploy 42 be kept?")}


def test_an_input_a_trial_renames_has_an_artefact_of_its_own():
    raw = copy.deepcopy(NEEDS)
    raw["interventions"]["presentation"] = {"rolled": "pulled"}  # a word of the input alone
    renamed = "Should deploy 42 be pulled back now?"
    maker = Watching()
    frame, _, result = branched(maker, raw=raw)
    assert [text for _, text, _ in maker.seen] == [QUESTION, renamed]
    for record in result.records:
        made = json.loads(record.raw)["made"]["text"]
        assert made == needs(renamed if record.trial == "presentation" else QUESTION)
        if record.trial == "presentation":
            assert "rolled" not in made  # the renamed word does not come back through it


def test_a_record_keeps_the_artefacts_hash_whole_where_its_text_is_cut():
    class Long(Watching):
        def make(self, line, text, max_output_tokens):
            from midwife.batteries.crossing import Made

            return Made("- a line it rests on\n" * 90, usage={"output_tokens": 40})

    class Answering(NeedsReader):
        def observe(self, frame, prompt, max_output_tokens):
            seen = super().observe(frame, prompt, max_output_tokens)
            return Observation(label=seen.label, raw="because " * 40, usage=seen.usage)

    frame, _, result = branched(Long(), Answering())
    whole = "- a line it rests on\n" * 90
    for record in result.records:
        assert len(record.raw) <= 2_000
        kept = json.loads(record.raw)
        assert kept["made"]["sha256"] == hashlib.sha256(whole.encode()).hexdigest()
        assert whole.startswith(kept["made"]["text"]) and kept["made"]["text"] != whole
        assert kept["read"] == "because " * 40  # the shorter text is kept whole


@pytest.mark.parametrize("whole", ["e\n" * 3000, 'say "so"\\\n' * 600, "plain words " * 400])
def test_a_record_keeps_the_longest_beginning_of_the_artefact_that_fits(whole):
    from midwife.pipeline import RAW_LIMIT

    class Long(Watching):
        def make(self, line, text, max_output_tokens):
            from midwife.batteries.crossing import Made

            return Made(whole, usage={"output_tokens": 40})

    _, _, result = branched(Long())
    sha = hashlib.sha256(whole.encode()).hexdigest()
    for record in result.records:
        kept = json.loads(record.raw)
        read = kept["read"]

        def written(n, read=read):
            made = {"made": {"sha256": sha, "text": whole[:n]}, "read": read}
            return json.dumps(made, ensure_ascii=False)

        longest = max(n for n in range(len(whole) + 1) if len(written(n)) <= RAW_LIMIT)
        assert kept["made"]["sha256"] == sha and len(record.raw) <= RAW_LIMIT
        assert kept["made"]["text"] == whole[:longest]


def test_calls_at_once_still_make_one_artefact():
    class Slow(Watching):
        def make(self, line, text, max_output_tokens):
            gate.wait(2)  # every call of the first round is waiting at the lock by now
            return super().make(line, text, max_output_tokens)

    gate = threading.Event()
    maker = Slow()
    threading.Timer(0.2, gate.set).start()
    frame, branch, result = branched(maker, parallel=6)
    assert branch.concurrent is True and len(maker.seen) == 1
    assert judge(frame, result.records)[0].category == "carried"
    charged = [r for r in result.records if r.usage["output_tokens"] == 43]
    assert len(charged) == 1  # one call paid for the artefact, whichever it was


def test_calls_run_at_once_only_when_both_sides_take_them():
    from midwife.batteries.branch import Branch
    from midwife.batteries.crossing import Function

    class OneAtATime(NeedsReader):
        concurrent = False

    assert Branch(Function("needs", needs), NeedsReader()).concurrent is True
    assert Branch(Function("needs", needs), OneAtATime()).concurrent is False


def test_a_branch_refuses_a_line_it_was_not_made_for():
    from midwife.batteries.branch import Branch
    from midwife.batteries.crossing import Function

    branch = Branch(Function("needs", needs), NeedsReader())

    def refused(battery):
        with pytest.raises(BatteryError) as error:
            branch.check(parse({**copy.deepcopy(NEEDS), "battery": battery}))
        return error.value

    line = NEEDS["battery"]
    assert "asks for battery 'crossing'" in str(refused({**line, "kind": "crossing"}))
    error = refused({**line, "also": 1})
    assert str(error) == "the branch battery reads no 'also' under battery"
    assert str(refused({"kind": "branch", "maker": line["maker"]})) == (
        "battery.reader is a line of its own with a kind"
    )
    error = refused({**line, "reader": {"kind": "unified"}})
    assert str(error) == "battery.reader names kind 'unified', not 'needs-reader'"
    assert error.__notes__ == [
        "this branch was made with another; make one with Branch(maker, reader)"
    ]
    error = refused({**line, "maker": {"kind": "needs", "extra": 1}})
    assert error.__notes__[-1] == "it is the branch's maker line, battery.maker, that is refused"


def test_a_readers_refusal_says_which_line_it_refused():
    from midwife.batteries.branch import Branch
    from midwife.batteries.crossing import Function

    class Strict(NeedsReader):
        def check(self, frame):
            raise BatteryError("the reader takes no such line")

    with pytest.raises(BatteryError) as error:
        Branch(Function("needs", needs), Strict()).check(parse(copy.deepcopy(NEEDS)))
    assert error.value.__notes__ == [
        "it is the branch's reader line, battery.reader, that is refused"
    ]


def test_a_body_or_an_input_that_holds_the_parting_line_is_refused():
    from midwife.batteries.branch import Branch
    from midwife.batteries.crossing import Function

    branch = Branch(Function("needs", needs), NeedsReader())
    raw = copy.deepcopy(NEEDS)
    raw["inputs"][0]["text"] = f"Should it?{PARTS}Really?"
    with pytest.raises(BatteryError, match="input 'q1' holds the line that parts") as error:
        branch.check(parse(raw))
    assert error.value.__notes__[0].startswith("the maker reads what comes after the last")
    raw = copy.deepcopy(NEEDS)
    raw["body"]["spans"][2]["text"] = f"The error rate held.{PARTS}It did."
    with pytest.raises(BatteryError, match="a trial's body holds the line that parts") as error:
        branch.check(parse(raw))
    assert error.value.__notes__[0].startswith("the reader tells the artefact, the body")


@pytest.mark.parametrize(
    "made", ["one\n---\ntwo", "one\n  ---  \ntwo", "one\r\n---\r\ntwo", "---\ntwo", "one\n---"]
)
def test_a_dash_line_in_any_form_in_the_artefact_is_an_opening(made):
    from midwife.batteries.branch import Branch
    from midwife.batteries.crossing import Function

    reader = NeedsReader()
    frame = parse(copy.deepcopy(NEEDS))
    branch = Branch(Function("needs", lambda question: made), reader)
    seen = branch.observe(frame, f"{plan(frame)[0].text}{PARTS}{QUESTION}", 100)
    assert seen.label is None and reader.prompts == []
    assert seen.opening == "the maker made text that holds the line that parts it from the body"


@pytest.mark.parametrize(
    "where, text",
    [
        ("input", "Should it?\n---\nReally?"),
        ("input", "---\nShould it?"),
        ("input", "Should it?\r\n---"),
        ("body", "The error rate held.\n  ---\nIt did."),
        ("body", "---"),
    ],
)
def test_a_dash_line_in_any_form_in_a_body_or_an_input_is_refused(where, text):
    from midwife.batteries.branch import Branch
    from midwife.batteries.crossing import Function

    branch = Branch(Function("needs", needs), NeedsReader())
    raw = copy.deepcopy(NEEDS)
    if where == "input":
        raw["inputs"][0]["text"] = text
        expected = "input 'q1' holds the line that parts"
    else:
        raw["body"]["spans"][2]["text"] = text
        expected = "a trial's body holds the line that parts"
    with pytest.raises(BatteryError, match=expected):
        branch.check(parse(raw))


def test_a_side_that_fails_is_an_opening_that_names_it():
    from midwife.batteries.branch import Branch
    from midwife.batteries.crossing import Function

    class Broken(NeedsReader):
        def observe(self, frame, prompt, max_output_tokens):
            raise RuntimeError("down")

    frame = parse(copy.deepcopy(NEEDS))
    asked = f"{plan(frame)[0].text}{PARTS}{QUESTION}"
    seen = Branch(Function("needs", needs), Broken()).observe(frame, asked, 100)
    assert seen.opening == "the reader failed (RuntimeError)"
    assert json.loads(seen.raw)["made"]["text"] == needs(QUESTION)  # the artefact is kept

    def fails(question):
        raise RuntimeError("down")

    seen = Branch(Function("needs", fails), NeedsReader()).observe(frame, asked, 100)
    assert seen.opening == "the maker made nothing ('the function failed (RuntimeError)')"


MAKER = {
    "kind": "unified",
    "model": "anthropic/claude-sonnet-5-5",
    "instruction": "List what the lines would have to say. Use only the question.",
}
READER = {"kind": "unified", "model": "deepseek/deepseek-v4.1-flash", "reasoning": "none"}


@pytest.fixture
def through_router(monkeypatch, tmp_path):
    """A fake router that writes what is needed for a maker's request and
    decides for a reader's, as the rules above would."""
    from midwife.batteries import unified
    from tests.fakes import Fake

    monkeypatch.setenv("CODEX_ROUTER_TOKEN", "ab" * 32)
    monkeypatch.setattr(unified, "ENV_FILE", tmp_path / "absent.env")
    lists = {
        "dataPolicies": ["deny"],
        "endpointPins": True,
        "reports": ["provider"],
        "fallbackPolicies": ["none"],
        "thinkingBudgets": True,
    }
    monkeypatch.setattr(unified, "capabilities", lambda url, timeout: lists)

    def reply(body):
        text = body["input"][0]["content"][0]["text"]
        if "text" in body["text"]["format"]["schema"]["properties"]:
            answer, used = {"text": needs(text)}, 30
        else:
            label = NeedsReader().observe(None, text, 0).label
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


def test_one_model_writes_what_is_needed_and_another_reads_through_the_router(through_router):
    from midwife.batteries.branch import Branch
    from midwife.batteries.crossing import WRITTEN, UnifiedMaker
    from midwife.batteries.unified import Unified

    router = through_router()
    battery = {"kind": "branch", "maker": MAKER, "reader": READER}
    branch = Branch(UnifiedMaker(router.url), Unified(router.url))
    frame = parse({**copy.deepcopy(NEEDS), "battery": battery})
    result = run(frame, branch, Budget(calls=calls_needed(frame), output_tokens_per_call=200))
    assert judge(frame, result.records)[0].category == "carried"
    writes = [b for _, b in router.requests if b["text"]["format"]["schema"] == WRITTEN]
    assert len(writes) == 1 and len(router.requests) == calls_needed(frame) + 1
    (made_headers, made), (read_headers, read) = router.requests[:2]
    assert made["instructions"] == MAKER["instruction"] and made["max_output_tokens"] == 100
    assert made["input"][0]["content"][0]["text"] == QUESTION and "tools" not in made
    assert made_headers["x-codex-router-data-policy"] == "deny"
    assert read_headers["x-codex-router-data-policy"] == "deny"
    assert read["instructions"] == NEEDS["observe"]["instruction"]
    assert read["max_output_tokens"] == 170 and read["reasoning"] == {"effort": "none"}
    body = plan(frame)[0].text
    asked = f"{needs(QUESTION)}{PARTS}{body}{PARTS}{QUESTION}"
    assert read["input"][0]["content"][0]["text"] == asked
    assert router.requests[2][1]["max_output_tokens"] == 200  # a later call reads with it all
    first, second = result.records[:2]
    assert first.usage == {"output_tokens": 34, "input_tokens": 100}
    assert second.usage == {"output_tokens": 4, "input_tokens": 50}
    assert (
        first.served
        == second.served
        == (
            "made by anthropic/claude-sonnet-5-5 via Example, "
            "read by deepseek/deepseek-v4.1-flash via Example"
        )
    )


def test_a_side_kept_on_anthropic_with_a_budget_must_fit_its_share_of_the_cap(through_router):
    from midwife.batteries.branch import Branch
    from midwife.batteries.crossing import UnifiedMaker
    from midwife.batteries.unified import Unified

    router = through_router()
    maker = {**MAKER, "fallback": "none", "thinkingBudget": 1024}
    battery = {"kind": "branch", "maker": maker, "reader": READER}
    frame = parse({**copy.deepcopy(NEEDS), "battery": battery})
    branch = Branch(UnifiedMaker(router.url), Unified(router.url))
    branch.check(frame)
    with pytest.raises(BatteryError, match="not below each answer's cap of 1024") as error:
        run(frame, branch, Budget(calls=calls_needed(frame), output_tokens_per_call=2048))
    assert error.value.__notes__[-1].startswith(
        "the branch's maker gets 1024 of the 2048 tokens of a call that makes an artefact"
    )
    assert router.requests == []


def test_a_maker_line_with_no_instruction_is_refused(through_router):
    from midwife.batteries.branch import Branch
    from midwife.batteries.crossing import UnifiedMaker
    from midwife.batteries.unified import Unified

    router = through_router()
    maker = {key: value for key, value in MAKER.items() if key != "instruction"}
    frame = parse({**copy.deepcopy(NEEDS), "battery": {**NEEDS["battery"], "maker": maker,
                                                       "reader": READER}})  # fmt: skip
    with pytest.raises(BatteryError, match="battery.maker.instruction says what") as error:
        Branch(UnifiedMaker(router.url), Unified(router.url)).check(frame)
    assert error.value.__notes__[-1] == (
        "it is the branch's maker line, battery.maker, that is refused"
    )


def test_a_branch_may_train_when_either_side_may(through_router):
    from midwife.batteries.branch import Branch
    from midwife.batteries.crossing import Function, UnifiedMaker
    from midwife.batteries.unified import Unified

    router = through_router()
    battery = {"kind": "branch", "maker": MAKER, "reader": READER}
    frame = parse({**copy.deepcopy(NEEDS), "battery": battery})
    branch = Branch(UnifiedMaker(router.url), Unified(router.url))
    assert branch.trains(frame) is False  # both lines go under the deny data policy
    named = {**MAKER, "trainsOnInputs": [MAKER["model"]]}
    assert branch.trains(parse({**frame.raw, "battery": {**battery, "maker": named}})) is True
    rules = Branch(Function("needs", needs), NeedsReader())
    assert rules.trains(parse(copy.deepcopy(NEEDS))) is True  # sides that do not say may


def test_the_command_line_runs_a_branch_made_in_a_module_of_your_own(tmp_path, capsys):
    from midwife.cli import main

    path, out = tmp_path / "needs.json", tmp_path / "needs.jsonl"
    path.write_text(json.dumps(NEEDS), encoding="utf-8")
    calls = str(calls_needed(parse(copy.deepcopy(NEEDS))))
    assert main(["run", str(path), "--battery", "tests.fixtures.needs:branch", "--calls", calls,
                 "--output-tokens", "100", "--out", str(out)]) == 0  # fmt: skip
    capsys.readouterr()
    assert main(["report", str(path), str(out)]) == 0
    assert "q1: carried" in capsys.readouterr().out


def test_the_crossing_reads_as_it_did_before_its_parts_were_shared():
    # the making and the reading the two batteries share are the crossing's own
    from midwife.batteries.crossing import Crossing, Function
    from tests.fixtures.incident import INCIDENT, CauseReader

    reader = CauseReader()
    frame = parse(copy.deepcopy(INCIDENT))
    crossing = Crossing(Function("cause", cause), reader)
    seen = crossing.observe(frame, f"{plan(frame)[0].text}{PARTS}{QUESTION}", 100)
    assert isinstance(seen, Observation) and seen.label == "rollback"
    assert reader.prompts == [(f"{cause(plan(frame)[0].text)}{PARTS}{QUESTION}", 100)]
