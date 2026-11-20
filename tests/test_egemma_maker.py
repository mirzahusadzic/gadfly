"""The eGemma maker and a branch whose two sides are this machine's eGemma,
against a fake eGemma on loopback. No model is called."""

import copy
import json
import threading
import time

import pytest

from midwife.batteries import branch as branch_module
from midwife.batteries.branch import Branch
from midwife.batteries.crossing import Crossing, Function
from midwife.batteries.egemma import STEP_TOKENS, WRITTEN, EGemma, EGemmaMaker
from midwife.batteries.unified import Unified
from midwife.errors import BatteryError
from midwife.pipeline import calls_needed, judge, run, situate
from midwife.types import Budget
from tests.fakes import Fake
from tests.fixtures.needs import NEEDS, NeedsReader, needs

LINE = {"kind": "egemma", "reasoning": True, "instruction": "List what the lines must say."}
LOCAL = {
    "kind": "branch",
    "maker": dict(LINE),
    "reader": {"kind": "egemma", "reasoning": False},
}


def written(text, **fields):
    body = {
        "answer": {"text": text},
        "text": json.dumps({"text": text}),
        "truncated": False,
        "usage": {"input_tokens": 30, "output_tokens": 620, "reasoning_tokens": 600},
        "model": "gemma",
        "revision": "r",
    }
    return (200, {"content-type": "application/json"}, json.dumps({**body, **fields}).encode())


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


def test_the_maker_asks_for_its_text_with_a_thought_beside_it(key, server):
    fake = server(written("1. Kiran is the doll\n2. Boy means male"))
    made = EGemmaMaker(EGemma(fake.base + "/judge")).make(LINE, "Claim: Kiran is a boy.", 2000)
    assert made.text == "1. Kiran is the doll\n2. Boy means male"
    assert made.served == "gemma@r (thinking on)"
    assert made.usage["reasoning_tokens"] == 600
    headers, body = fake.requests[0]
    assert headers["authorization"] == "Bearer local-key"
    assert body == {
        "instructions": LINE["instruction"],
        "input": "Claim: Kiran is a boy.",
        "schema": WRITTEN,
        "max_tokens": STEP_TOKENS,
        "reasoning": True,
        "max_reasoning_tokens": 2000 - STEP_TOKENS,
    }


def test_without_reasoning_the_maker_asks_for_no_thought(key, server):
    fake = server(written("a step", usage={"output_tokens": 5, "reasoning_tokens": 0}))
    line = {"kind": "egemma", "instruction": "Write.", "temperature": 0}
    made = EGemmaMaker(EGemma(fake.base + "/judge")).make(line, "a claim", 300)
    assert made.text == "a step" and made.served == "gemma@r (thinking off)"
    body = fake.requests[0][1]
    assert body["max_tokens"] == 300 and body["temperature"] == 0 and "reasoning" not in body


def test_a_share_with_no_room_for_a_thought_is_an_opening_and_no_call(key, server):
    fake = server(written("never"))
    made = EGemmaMaker(EGemma(fake.base + "/judge")).make(LINE, "a claim", STEP_TOKENS)
    assert made.text is None and made.usage == {"output_tokens": 0}
    assert made.opening == (
        f"a cap of {STEP_TOKENS} output tokens leaves no room "
        f"for a thought beside the text's {STEP_TOKENS}"
    )
    assert fake.requests == []


@pytest.mark.parametrize(
    "reply, opening",
    [
        (written("cut", truncated=True), "the answer was cut at its token cap"),
        (written("x", answer=None), "the answer is not JSON"),
        (written("x", answer={"label": "grant"}), "the answer holds no text"),
        (written("x", model="other"), "eGemma served model 'other'; the frame pins 'gemma'"),
        (written("x", valid=False, violations=[]), "the answer breaks its schema"),
        ((500, {}, b"{}"), "eGemma answered 500"),
    ],
)
def test_what_egemma_cannot_write_is_an_opening(key, server, reply, opening):
    fake = server(reply)
    line = {**LINE, "model": "gemma"}
    made = EGemmaMaker(EGemma(fake.base + "/judge")).make(line, "a claim", 2000)
    assert (made.text, made.opening) == (None, opening)


@pytest.mark.parametrize(
    "line, said",
    [
        ({**LINE, "also": 1}, "the eGemma maker reads no 'also'"),
        ({"kind": "egemma"}, "battery.maker.instruction says what the maker writes"),
        ({**LINE, "instruction": " "}, "battery.maker.instruction says what the maker writes"),
        ({**LINE, "temperature": True}, "battery.maker.temperature is a number between 0 and 2"),
        ({**LINE, "temperature": 3}, "battery.maker.temperature is a number between 0 and 2"),
        ({**LINE, "reasoning": "yes"}, "battery.maker.reasoning is true or false"),
        ({**LINE, "model": ""}, "battery.maker.model and revision name what eGemma must serve"),
    ],
)
def test_the_maker_refuses_a_line_it_must_not_serve(key, line, said):
    with pytest.raises(BatteryError, match=said):
        EGemmaMaker(EGemma()).check(line)


def test_the_maker_needs_a_key_and_reads_egemmas_budget(key, server, monkeypatch):
    limits = json.dumps({"judge": {"calls": 2, "seconds": 60}}).encode()
    fake = server(written("x"), {"/rate-limits": (200, {}, limits)})
    egemma = EGemma(fake.base + "/judge")
    EGemmaMaker(egemma).check(LINE)
    assert egemma.budget == (2, 60.0)
    monkeypatch.delenv("EGEMMA_API_KEY")
    with pytest.raises(BatteryError, match="no eGemma key"):
        EGemmaMaker(egemma).check(LINE)


def test_the_maker_never_trains_and_refuses_a_share_too_small_to_think_in(key):
    maker = EGemmaMaker(EGemma())
    assert maker.trains(LINE) is False
    maker.check_cap({"kind": "egemma", "instruction": "Write."}, 100)  # no thought: any share
    with pytest.raises(BatteryError, match="leaves the eGemma maker no room") as error:
        maker.check_cap(LINE, STEP_TOKENS)
    assert error.value.__notes__ == [
        "raise --output-tokens, so that the maker's share holds a thought"
    ]


def test_a_reader_on_egemma_says_whether_it_thought(key, server):
    reply = {
        "answer": {"label": "keep"},
        "text": '{"label": "keep"}',
        "usage": {"input_tokens": 9, "output_tokens": 4, "reasoning_tokens": 0},
        "model": "gemma",
        "revision": "r",
    }
    fake = server((200, {}, json.dumps(reply).encode()))
    raw = copy.deepcopy(NEEDS)
    raw["battery"] = {"kind": "egemma"}
    seen = EGemma(fake.base + "/judge").observe(situate(raw), "p", 32)
    assert seen.served == "gemma@r (thinking off)"


# ---- a branch on this machine


def local(fake, concurrent=None):
    # the fake eGemma writes what is needed for a maker's request and decides
    # for a reader's, as the rules of tests/fixtures/needs.py would
    def reply(body):
        if concurrent is not None:
            concurrent.enter()
        try:
            if "text" in body["schema"]["properties"]:
                return written(needs(body["input"]))
            label = NeedsReader().observe(None, body["input"], 0).label
            return (
                200,
                {},
                json.dumps(
                    {
                        "answer": {"label": label},
                        "text": json.dumps({"label": label}),
                        "usage": {"input_tokens": 60, "output_tokens": 4, "reasoning_tokens": 0},
                        "model": "gemma",
                        "revision": "r",
                    }
                ).encode(),
            )
        finally:
            if concurrent is not None:
                concurrent.leave()

    return reply


class Here(EGemma):
    url_now = ""

    def __init__(self):
        super().__init__(Here.url_now)


def local_frame():
    raw = copy.deepcopy(NEEDS)
    raw["battery"] = copy.deepcopy(LOCAL)
    raw["observe"]["instruction"] = "Decide from the metric lines, against what is needed."
    return situate(raw)


def test_branch_makes_each_side_from_its_lines_kind(key, server, monkeypatch):
    fake = server(local(server))
    Here.url_now = fake.base + "/judge"
    monkeypatch.setattr(branch_module, "EGemma", Here)
    frame = local_frame()
    branch = Branch()
    assert branch.concurrent is True and branch.maker is None
    branch.check(frame)
    assert isinstance(branch.maker, EGemmaMaker) and isinstance(branch.reader, Here)
    assert branch.maker.egemma is branch.reader  # one pace for both sides
    assert branch.trains(frame) is False


def test_a_whole_run_on_this_machine_is_carried_and_says_who_thought(key, server, monkeypatch):
    fake = server(local(None))
    Here.url_now = fake.base + "/judge"
    monkeypatch.setattr(branch_module, "EGemma", Here)
    frame = local_frame()
    result = run(frame, Branch(), Budget(calls=calls_needed(frame), output_tokens_per_call=2000))
    assert judge(frame, result.records)[0].category == "carried"
    served = {record.served for record in result.records}
    assert served == {"made by gemma@r (thinking on), read by gemma@r (thinking off)"}


class Overlap:
    """How many requests the fake eGemma serves at once, at most."""

    def __init__(self):
        self.now = self.most = 0
        self.lock = threading.Lock()

    def enter(self):
        with self.lock:
            self.now += 1
            self.most = max(self.most, self.now)
        time.sleep(0.02)

    def leave(self):
        with self.lock:
            self.now -= 1


def test_egemma_sides_take_calls_at_once_and_make_them_one_at_a_time(key, server, monkeypatch):
    overlap = Overlap()
    fake = server(local(None, overlap))
    Here.url_now = fake.base + "/judge"
    monkeypatch.setattr(branch_module, "EGemma", Here)
    frame = local_frame()
    budget = Budget(calls=calls_needed(frame), output_tokens_per_call=2000)
    result = run(frame, Branch(), budget, parallel=3)
    assert len(result.records) == calls_needed(frame) and overlap.most == 1


@pytest.mark.parametrize(
    "maker, reader, kinds",
    [
        ("egemma", "unified", (EGemmaMaker, Unified)),
        ("unified", "unified", (branch_module.UnifiedMaker, Unified)),
    ],
)
def test_branch_makes_a_mixed_pair_or_the_routers_from_their_kinds(key, maker, reader, kinds):
    raw = copy.deepcopy(NEEDS)
    raw["battery"] = {
        "kind": "branch",
        "maker": {**LINE, "kind": maker, "model": "m"} if maker == "unified" else dict(LINE),
        "reader": {"kind": reader, "model": "m"},
    }
    branch = Branch()
    branch._sides(situate(raw))  # chosen without a call, before check reaches the router
    assert (type(branch.maker), type(branch.reader)) == kinds
    assert branch._one is (None if maker == "unified" else branch._one)


def test_branch_refuses_a_kind_it_does_not_make_and_reads_it_as_training(key):
    raw = copy.deepcopy(NEEDS)  # its sides are "needs" and "needs-reader"
    frame = situate(raw)
    with pytest.raises(BatteryError, match="battery.maker names kind 'needs'") as error:
        Branch().check(frame)
    assert "for another, make one with Branch(maker, reader)" in error.value.__notes__[0]
    assert Branch().trains(frame) is True  # fail closed: a side it cannot make may train


def test_a_branch_asks_its_makers_own_cap_check_before_any_call(key, server, monkeypatch):
    fake = server(local(None))
    Here.url_now = fake.base + "/judge"
    monkeypatch.setattr(branch_module, "EGemma", Here)
    frame = local_frame()
    budget = Budget(calls=calls_needed(frame), output_tokens_per_call=2 * STEP_TOKENS)
    with pytest.raises(BatteryError, match="leaves the eGemma maker no room") as error:
        run(frame, Branch(), budget)
    assert "it is the branch's maker line, battery.maker, that is refused" in error.value.__notes__
    assert fake.requests == []


def test_a_crossing_asks_its_makers_own_cap_check_too(key):
    raw = copy.deepcopy(NEEDS)
    raw["battery"] = {"kind": "crossing", "maker": dict(LINE), "reader": {"kind": "needs-reader"}}
    frame = situate(raw)
    crossing = Crossing(EGemmaMaker(EGemma()), NeedsReader())
    with pytest.raises(BatteryError, match="leaves the eGemma maker no room") as error:
        crossing.check_cap(frame, 2 * STEP_TOKENS)
    assert (
        "it is the crossing's maker line, battery.maker, that is refused" in error.value.__notes__
    )
    crossing.check_cap(frame, 4 * STEP_TOKENS)  # room enough
    assert Function("f", str).check({"kind": "f"}) is None  # a maker with no cap check is not asked
