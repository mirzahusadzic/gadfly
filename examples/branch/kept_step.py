"""The branch with its step kept: each example's maker returns the step its
branch run A made for the same question, from kept-steps.json, so no making
is paid and every reading can start at once. The reader is the frame's own
line, Sonnet 5.5 at none through the router.

    uv run gadfly run examples/branch/19-kept-step.json \
        --battery examples.branch.kept_step:battery_19 ...
"""

import json
from pathlib import Path

from midwife.batteries.branch import Branch
from midwife.batteries.crossing import Function
from midwife.batteries.unified import Unified

STEPS = json.loads((Path(__file__).parent / "kept-steps.json").read_text(encoding="utf-8"))


def kept(example: str) -> Branch:
    """A branch whose maker is run A's steps for `example`; a question run A
    never asked has no step, and the call is an opening."""
    steps = STEPS[example]
    return Branch(Function(f"kept-step-{example}-a", steps.__getitem__), Unified())


battery_19 = kept("19")
battery_22 = kept("22")
battery_22c = kept("22c")
