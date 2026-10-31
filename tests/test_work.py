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
