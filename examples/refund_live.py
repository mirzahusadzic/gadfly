"""The refund frame read by a live critic: a model through the unified router,
or Gemma 4 through eGemma. Each call is a model call: the frame is public and
small (7 trials, 3 runs each), but a routed model costs what its provider
charges.

    python examples/refund_live.py unified anthropic/claude-sonnet-5-5 records.jsonl
    python examples/refund_live.py egemma gemma records.jsonl
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from gadfly.batteries.egemma import EGemma
from gadfly.batteries.unified import Unified
from gadfly.pipeline import calls_needed, judge, run, situate
from gadfly.types import Budget

FRAME = Path(__file__).with_name("refund.json")
# Models whose provider may train on what it reads, named here because this
# frame is public. A frame with private text names none.
TRAINING_CONSENT = {"deepseek/deepseek-v4.1-flash-1017"}


def frame_for(kind: str, model: str):
    raw = json.loads(FRAME.read_text(encoding="utf-8"))
    battery = (
        {"kind": kind, "model": model, "reasoning": "low"} if kind == "unified" else {"kind": kind}
    )
    if model in TRAINING_CONSENT:  # the frame is public: it may go where inputs train
        battery["trainsOnInputs"] = [model]
    # A sampled critic: three runs a trial, two must agree.
    return situate({**raw, "battery": battery, "standing": {"quorum": 3, "agree": 2}})


def main(battery, model: str, path: Path):
    frame = frame_for(battery.name, model)
    with path.open("x", encoding="utf-8") as kept:  # a new file: never another run's
        result = run(
            frame,
            battery,
            Budget(calls=calls_needed(frame), output_tokens_per_call=1024),
            on_record=lambda r: kept.write(json.dumps(r.as_dict()) + "\n"),
        )
    [finding] = judge(frame, result.records)
    return result, finding


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] not in ("unified", "egemma"):
        sys.exit(__doc__)
    kind, model, out = sys.argv[1:]
    result, finding = main(Unified() if kind == "unified" else EGemma(), model, Path(out))
    print(f"{kind} {model}: {finding.category} ({result.stopped or 'every call made'})")
    for trial, level in finding.levels.items():
        print(f"  {trial:13} {level}")
    for note in finding.evidence + finding.obligations:
        print(f"  {note}")
    openings = [r.opening for r in result.records if r.opening]
    if openings:
        print(f"  openings: {len(openings)} ({'; '.join(sorted(set(openings)))})")
