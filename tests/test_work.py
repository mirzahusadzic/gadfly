"""Work that must grow no faster than its input, counted at two sizes."""

import copy

from midwife.interventions import sham_draws
from midwife.pipeline import situate
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
