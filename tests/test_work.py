"""Work that must grow no faster than its input, counted at two sizes."""

import copy
import json

from midwife.interventions import sham_draws
from midwife.pipeline import judge, plan, situate
from midwife.types import Record
from tests.conftest import REFUND
from tests.work import instructions


def _many_anchors(n):
    raw = copy.deepcopy(REFUND)
    raw["body"]["spans"] = [
        {"id": f"s{i}", "text": "x" * (i + 1), "kind": "rule"} for i in range(2 * n)
    ]
    raw["anchors"] = [f"s{i}" for i in range(n)]
    raw["interventions"] = {"ablation": True, "sham": True}
    raw["allowed"] = {"ablation": ["grant", "unclear"]}
    return situate(raw)


def test_sham_draws_grow_with_the_anchors_not_their_square():
    # each anchor's nearest free span is found without rescanning the pool
    frames = [_many_anchors(n) for n in (100, 200)]
    small, large = (instructions(lambda f=frame: sham_draws(f, 1)) for frame in frames)
    assert large < 2.6 * small, (small, large)


def _inputs(n):
    raw = copy.deepcopy(REFUND)
    raw["inputs"] = [{"id": f"x{i}", "text": f"case {i}"} for i in range(n)]
    frame = situate(raw)
    records = [
        Record(frame.hash, x["id"], t.id, run, t.body_hash, "p", frame.battery["kind"],
               "decline", None, "", {})
        for x in frame.inputs for t in plan(frame) for run in range(frame.quorum)
    ]  # fmt: skip
    return frame, records


def test_judge_decodes_the_frame_once_not_once_per_input(monkeypatch):
    # the frame's text is decoded a fixed number of times, whatever the inputs
    decoded = []
    loads = json.loads
    monkeypatch.setattr("midwife.frame.json.loads", lambda s: decoded.append(len(s)) or loads(s))
    sizes = []
    for n in (40, 80):
        frame, records = _inputs(n)
        decoded.clear()
        judge(frame, records)
        sizes.append(sum(decoded))
    assert sizes[1] < 2.6 * sizes[0], sizes


def test_the_watch_data_digests_each_prompt_once(monkeypatch):
    # a prompt is asked many times; its digest is taken once
    from tools import watch_data

    calls = []
    digest = watch_data.digest
    monkeypatch.setattr(watch_data, "digest", lambda text: calls.append(text) or digest(text))
    watch_data.watched("upgrade")
    frame = situate(json.loads((watch_data.ROOT / "examples/upgrade.json").read_text()))
    slots = len(frame.inputs) * len(plan(frame))  # one per input and trial, not per record
    assert len(calls) == slots, (len(calls), slots)


def test_a_frame_shown_in_words_finds_its_span_lines_in_one_pass(tmp_path):
    # each span links to its line: the file is read once, not once per span
    from tools.doc_outputs import readable

    def shown(n):
        raw = copy.deepcopy(REFUND)
        raw["body"]["spans"] += [
            {"id": f"f{i}", "text": f"free {i}", "kind": "rule"} for i in range(n)
        ]
        path = tmp_path / f"frame-{n}.json"
        path.write_text(json.dumps(raw, indent=2))
        return instructions(lambda: readable(str(path), "docs/first-frame.md"))

    small, large = shown(100), shown(200)
    assert large < 2.6 * small, (small, large)


class _CountedId(str):
    # a span id that counts how often it is compared
    comparisons = 0

    def __eq__(self, other):
        type(self).comparisons += 1
        return str.__eq__(self, other)

    __hash__ = str.__hash__


def test_anchor_lookups_grow_with_the_anchors_not_their_square():
    # parsing a frame and drawing its shams look anchors up, never scan for them
    from midwife.frame import parse

    def compared(n):
        raw = copy.deepcopy(REFUND)
        ids = [_CountedId(f"s{i}") for i in range(2 * n)]
        raw["body"]["spans"] = [
            {"id": ids[i], "text": "x" * (i + 1), "kind": "rule"} for i in range(2 * n)
        ]
        raw["anchors"] = ids[:n]
        raw["interventions"] = {"ablation": True, "sham": True}
        raw["allowed"] = {"ablation": ["grant", "unclear"]}
        _CountedId.comparisons = 0
        frame = parse(raw)
        sham_draws(frame, 1)
        return _CountedId.comparisons

    small, large = compared(100), compared(200)
    assert large <= 2.6 * small, (small, large)  # a lookup may need no comparison at all


def test_a_frames_sham_draws_are_made_once(monkeypatch):
    # the seeded draw among equally near spans is part of what a frame means, so
    # it is kept as it is; but a frame's draws are made once, not for every count
    import midwife.interventions as interventions
    from midwife.interventions import trial_ids
    from midwife.pipeline import calls_needed

    raw = copy.deepcopy(REFUND)
    raw["body"]["spans"] = [{"id": f"s{i}", "text": "same", "kind": "rule"} for i in range(60)]
    raw["anchors"] = [f"s{i}" for i in range(20)]
    raw["interventions"] = {"ablation": True, "sham": {"draws": 2}}
    raw["allowed"] = {"ablation": ["grant", "unclear"]}
    frame = situate(raw)
    draws = []
    original = interventions.random.Random

    class Counted(original):
        def random(self):
            draws.append(1)
            return super().random()

    monkeypatch.setattr(interventions.random, "Random", Counted)
    first = trial_ids(frame)
    made = len(draws)
    assert made and trial_ids(frame) == first and calls_needed(frame) and plan(frame)
    assert len(draws) == made  # counted and planned again, drawn once
