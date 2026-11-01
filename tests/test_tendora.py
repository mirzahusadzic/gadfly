"""The tendora battery, against a fake engine on loopback. No engine is called.

The frame is Tendora's reference frame on its bundled demo, Payments On-Call
(Apache-2.0): who notifies the customers when a certificate expires."""

import json
from pathlib import Path

import pytest

from midwife.batteries.tendora import Tendora, asked, label_of, request_body
from midwife.interventions import plan, prompt
from midwife.pipeline import calls_needed, judge, run, situate
from midwife.types import Budget
from tests.fakes import Fake

FRAME = Path(__file__).parent / "fixtures" / "payments-notify-chain.json"
EXPIRY = "If a certificate expires, Priya, the security engineer, {} the certificate."
NOTIFY = "If Priya {} the certificate, Sam, the support lead, notifies the customers."


def reply(status, *answers, **fields):
    body = {
        "status": status,
        "answers": [{"text": text, "conditional": False, "sourceIds": []} for text in answers],
        "served": {"tendora": "0.3.0", "revision": "578493dc7d85" * 4, "packs": "sha256:a423"},
        "saved": False,
        **fields,
    }
    return (200, {"content-type": "application/json"}, json.dumps(body).encode())


def engine(body):
    # Sam only while both rules are there, in either wording; open otherwise
    given = set(body["statements"])
    chain = any(
        EXPIRY.format(verb) in given and NOTIFY.format(verb) in given
        for verb in ("renews", "replaces")
    )
    return reply("supported", "Sam") if chain else reply("open")


@pytest.fixture
def raw():
    return json.loads(FRAME.read_text(encoding="utf-8"))


@pytest.fixture
def server():
    servers = []

    def start(answer):
        servers.append(Fake(answer))
        return servers[-1]

    yield start
    for fake in servers:
        fake.close()


def at(raw, url, **battery):
    raw["battery"] = {"kind": "tendora", "url": url, **battery}
    return situate(raw)


def test_the_reference_frame_plans_nine_calls(raw):
    assert calls_needed(situate(raw)) == 9


def test_an_ask_is_the_question_the_case_and_the_trials_statements_alone(raw, server):
    fake = server(reply("supported", "Sam"))
    frame = at(raw, fake.base, scope="incident-commander", offline=True)
    trials = {trial.id: trial for trial in plan(frame)}
    for trial in trials.values():
        Tendora().observe(frame, prompt(frame, trial, frame.inputs[0]), 64)
    asks = [body for _, body in fake.requests]
    assert {tuple(sorted(body)) for body in asks} == {
        ("case", "offline", "question", "scope", "statements")
    }
    baseline, ablation = asks[0], asks[2]
    assert baseline["question"] == "Who notifies the customers?"
    assert baseline["case"] == "A certificate expires."
    assert baseline["statements"] == [span.text for span in frame.spans]
    assert EXPIRY.format("renews") not in ablation["statements"]
    assert "ablation" not in json.dumps(asks)  # the trial's id is never sent
    assert all("authorization" not in headers for headers, _ in fake.requests)


def test_a_control_that_cuts_every_statement_sends_none(raw):
    raw["interventions"]["control"] = [span["id"] for span in raw["body"]["spans"]]
    frame = situate(raw)
    control = next(t for t in plan(frame) if t.id == "control")
    assert request_body(frame, prompt(frame, control, frame.inputs[0]))["statements"] == []


@pytest.mark.parametrize(
    "status, answers, fields, label, opening",
    [
        ("supported", ["Sam"], {}, "Sam", None),
        ("supported", ["Sam", "Priya"], {}, "another answer", None),
        ("supported", ["the support lead"], {}, "another answer", None),
        ("conditional", ["Sam"], {}, "conditional", None),
        ("open", [], {"candidates": [{"text": "Sam"}]}, "open", None),
        ("ambiguous", ["Sam", "Priya"], {}, None, "the engine answered ambiguous"),
        ("conflict", [], {}, None, "the engine answered conflict"),
        ("limited", [], {}, None, "the engine answered limited"),
        (
            "needs-reading",
            [],
            {"unread": [{"text": "x", "reason": "offline"}] * 3},
            None,
            "the engine answered needs-reading: 3 text(s) have no reading",
        ),
    ],
)
def test_the_engines_answer_gives_its_label_or_an_opening(
    raw, status, answers, fields, label, opening
):
    body = json.loads(reply(status, *answers, **fields)[2])
    assert label_of(body, situate(raw).labels) == (label, opening)


def test_ambiguous_and_conflict_are_labels_a_frame_may_declare(raw):
    # determinate outcomes, observed under their own names when declared;
    # limited and needs-reading stay openings whatever the frame lists
    raw["observe"]["labels"] += ["ambiguous", "conflict", "limited", "needs-reading"]
    labels = situate(raw).labels
    for status in ("ambiguous", "conflict"):
        assert label_of(json.loads(reply(status)[2]), labels) == (status, None)
    for status in ("limited", "needs-reading"):
        assert label_of(json.loads(reply(status)[2]), labels)[0] is None


def test_an_answer_no_label_names_is_an_opening_without_another_answer(raw):
    raw["observe"]["labels"].remove("another answer")
    body = json.loads(reply("supported", "Sam", "Priya")[2])
    label, opening = label_of(body, situate(raw).labels)
    assert label is None and opening.startswith("the engine answered ['Sam', 'Priya']")


def test_a_refusal_is_an_opening_in_the_engines_words(raw, server):
    said = {"error": "“Who notifies the customers?” has no saved check at this revision"}
    fake = server((409, {"content-type": "application/json"}, json.dumps(said).encode()))
    frame = at(raw, fake.base)
    baseline = plan(frame)[0]
    observation = Tendora().observe(frame, prompt(frame, baseline, frame.inputs[0]), 64)
    assert observation.label is None
    assert observation.opening == f"the engine answered 409: {said['error']}"


def test_each_record_names_what_served_it(raw, server):
    fake = server(reply("supported", "Sam"))
    frame = at(raw, fake.base)
    observation = Tendora().observe(frame, prompt(frame, plan(frame)[0], frame.inputs[0]), 64)
    assert observation.served == "tendora 0.3.0 578493dc7d855784 sha256:a423"
    assert observation.usage == {"output_tokens": 0}
    answer, kept = map(json.loads, observation.raw.split("\n"))
    assert answer == {"status": "supported", "answers": [{"text": "Sam", "conditional": False}]}
    # then the reply, but for the statements it echoes
    assert kept["status"] == "supported" and kept["served"]["tendora"] == "0.3.0"
    assert "statements" not in kept


@pytest.mark.parametrize(
    "change, message",
    [
        ({"battery": {"kind": "tendora", "url": "http://example.com"}}, "on this machine"),
        ({"battery": {"kind": "tendora"}}, "battery.url"),
        ({"battery": {"kind": "tendora", "url": "http://127.0.0.1:1", "timeout": 0}}, "timeout"),
        ({"battery": {"kind": "tendora", "url": "http://127.0.0.1:1", "scope": ""}}, "scope"),
        ({"battery": {"kind": "tendora", "url": "http://127.0.0.1:1", "offline": 1}}, "offline"),
        ({"battery": {"kind": "tendora", "url": "http://127.0.0.1:1", "model": "x"}}, "reads no"),
        ({"inputs": [{"id": "x", "text": "Who notifies the customers?"}]}, "Case:"),
    ],
)
def test_check_refuses_what_the_battery_must_not_serve(raw, change, message):
    raw.update(change)
    with pytest.raises(ValueError, match=message):
        Tendora().check(situate(raw))


def test_check_needs_open_among_the_labels(raw):
    raw["observe"]["labels"].remove("open")
    raw["allowed"] = {"ablation": ["Maya"], "bypass": ["Maya"]}
    with pytest.raises(ValueError, match="open among the labels"):
        Tendora().check(situate(raw))


@pytest.mark.parametrize(
    "text, where",
    [
        ("Case: A certificate expires.\nQuestion: Who?", ("Who?", "A certificate expires.")),
        ("Question: Who?", ("Who?", None)),
        ("Who?", None),
        ("Case: \nQuestion: Who?", None),
        ("Case: x\nQuestion: Who?\nmore", None),
    ],
)
def test_an_input_holds_a_question_and_perhaps_a_case(text, where):
    assert asked(text) == where


def test_the_reference_frame_through_an_engine_that_follows_the_chain(raw, server):
    # the predictions written before any call: Sam wherever both rules stand,
    # open without them, and the verdict carried with no check left open
    fake = server(engine)
    frame = at(raw, fake.base)
    result = run(frame, Tendora(), Budget(calls=calls_needed(frame)))
    levels = {record.trial: record.observation for record in result.records}
    assert levels == {
        "baseline": "Sam",
        "repeat": "Sam",
        "ablation": "open",
        "sham-1": "Sam",
        "sham-2": "Sam",
        "presentation": "Sam",
        "placement": "Sam",
        "bypass": "open",
        "control": "open",
    }
    [finding] = judge(frame, result.records)
    assert finding.category == "carried" and not finding.obligations


def test_a_turned_question_is_asked_against_its_basis(server):
    # Tendora's route: the asked question and case, and the check they turn
    raw = json.loads((FRAME.parent / "restore-question-inversion.json").read_text())
    fake = server(reply("open"))
    frame = at(raw, fake.base)
    turned = next(t for t in plan(frame) if t.id == "input-inversion")
    approved = next(x for x in frame.inputs if x["id"] == "approved")
    Tendora().observe(frame, prompt(frame, turned, approved), 64)
    [(_, sent)] = fake.requests
    question = "May Jordan, the database administrator, restore the database from a backup?"
    assert sent["question"] == question.replace("the database", "not the database", 1)
    assert sent["basis"] == {
        "question": question,
        "case": "The incident commander has approved the restore.",
    }
    assert "basis" not in request_body(frame, prompt(frame, plan(frame)[0], approved))


def test_a_swapped_case_asks_the_other_declared_check_as_it_stands():
    # the approved case turned is the other input's own text: its saved check
    raw = json.loads((FRAME.parent / "restore-case-inversion.json").read_text())
    raw["battery"] = {"kind": "tendora", "url": "http://127.0.0.1:1"}
    frame = situate(raw)
    turned = next(t for t in plan(frame) if t.id == "input-inversion")
    sent = request_body(frame, prompt(frame, turned, frame.inputs[0]))
    assert sent["case"] == "The incident commander has not approved the restore."
    assert "basis" not in sent


def test_a_presentation_that_renames_the_question_names_its_basis(raw):
    raw["interventions"]["presentation"] = {"customers": "clients"}
    frame = situate(raw)
    trial = next(t for t in plan(frame) if t.id == "presentation")
    sent = request_body(frame, prompt(frame, trial, frame.inputs[0]))
    assert sent["question"] == "Who notifies the clients?"
    assert sent["basis"] == {
        "question": "Who notifies the customers?",
        "case": "A certificate expires.",
    }
