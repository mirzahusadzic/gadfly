"""The After the Poem example, as a test: its retained load-bearing sessions,
replayed through Gadfly, must reach every category the study published.

The study's data never enters this repository. Point the test at one or more
plan directories (each with plan.json and findings.json):

    GADFLY_ATP_PLANS=<plan>:<another plan> uv run pytest
"""

import os
from pathlib import Path

import pytest

from tests.fixtures.after_the_poem import replay

PLANS = [Path(p) for p in os.environ.get("GADFLY_ATP_PLANS", "").split(os.pathsep) if p]


@pytest.mark.skipif(not PLANS, reason="GADFLY_ATP_PLANS names no After the Poem plan")
@pytest.mark.parametrize("directory", PLANS, ids=[p.name for p in PLANS])
def test_every_published_category_is_reached(directory):
    rows = replay(directory)
    assert rows
    assert [(name, ours) for name, _, ours, _ in rows] == [
        (name, theirs) for name, theirs, _, _ in rows
    ]
