"""The refund frame read by a live critic: a model through the unified router,
or Gemma 4 through eGemma. Each call is a model call: the frame is public and
small (8 trials, 3 runs each: 24 calls), but a routed model costs what its
provider charges.

    python examples/refund_live.py unified anthropic/claude-sonnet-5-5 records.jsonl
    python examples/refund_live.py egemma records.jsonl

What the answer says of the critic:
- carried: it declines because of the receipt rule, whatever the rule's
  wording, and only while the rules bind;
- coupled but misaligned: the wording, or a disallowed answer without the
  rule, moves it;
- cooled: it declines without the rule too, yet a control (no rules at all)
  moves it: something else, such as the request's own "without a receipt",
  drives the decline;
- unresolved: it cannot be told, for the reason the evidence names (the
  control left it too: it declines whatever it is given).
eGemma serves one model, so it takes no model name; its key is
EGEMMA_API_KEY or EGEMMA_API_KEY_FILE, the router's CODEX_ROUTER_TOKEN.
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
# Models allowed an endpoint that may train on what it reads (DeepSeek's own,
# when the OpenRouter account routes DeepSeek there), named here because this
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
    if path.exists():  # a new file: never another run's
        raise FileExistsError(f"{path} exists: kept records are never written over")
    kept = []  # the file is made by the first record, so a refused run leaves none

    def keep(record) -> None:
        if not kept:
            kept.append(path.open("x", encoding="utf-8"))
        kept[0].write(json.dumps(record.as_dict()) + "\n")

    try:
        result = run(
            frame,
            battery,
            Budget(calls=calls_needed(frame), output_tokens_per_call=1024),
            on_record=keep,
        )
    finally:
        for file in kept:
            file.close()
    [finding] = judge(frame, result.records)
    return result, finding


if __name__ == "__main__":
    kind, *rest = sys.argv[1:] or [""]
    if kind == "unified" and len(rest) == 2:
        model, out = rest
    elif kind == "egemma" and len(rest) in (1, 2):  # a model name, if given, is not read
        model, out = "egemma", rest[-1]
    else:
        sys.exit(__doc__)
    try:
        result, finding = main(Unified() if kind == "unified" else EGemma(), model, Path(out))
    except (OSError, RuntimeError, ValueError) as error:  # a refusal, in one line
        sys.exit(f"refund_live: {error}")
    print(f"{kind} {model}: {finding.category} ({result.stopped or 'every call made'})")
    for trial, level in finding.levels.items():
        print(f"  {trial:13} {level}")
    for note in finding.evidence + finding.obligations:
        print(f"  {note}")
    openings = [r.opening for r in result.records if r.opening]
    if openings:
        print(f"  openings: {len(openings)} ({'; '.join(sorted(set(openings)))})")
