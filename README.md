# Gadfly

**A load-bearing test for a premise that has to survive a handoff.** Declare the
relation, its grain and the promise a recipient needs. Gadfly removes or changes
the relation under fixed interventions, has a scorer read each trial, and reads
one verdict by fixed rules. The method is [When meaning is load-bearing](docs/load-bearing.md).

Use Gadfly when you can name the premise and a consequence that should change
when the premise is gone: a policy clause, a cited source, one line of a system
prompt, a tool's permission, or a code invariant. Use an ordinary evaluation
when you need a score, a ranking, or a broad quality measurement.

<!-- --8<-- [start:verdicts] -->
## What Gadfly says

Each input gets one **finding**; a multi-input frame gets one **overall**
category over the findings. The categories are not scores. The first matching
rule below names the category.

| Finding | Plain meaning |
|---|---|
| `carried` | Ablation moved the observation as the promise allows. Tested presentation and specificity checks held; anything not tested appears under **Obligations**. |
| `coupled but misaligned` | The relation matters, but presentation moved it or ablation moved it where the promise disallows. |
| `cooled` | Ablation left the observation unchanged: this relation has no operative influence here. A control can show the scorer was able to move. |
| `unresolved` | There is not enough agreed evidence: a trial is missing or split, repeat is unstable, or a sham moved too. |
| `outside scope` | The receiving owner declares the distinction unnecessary. The code currently records the independent scope check as an obligation rather than performing it. |

Every finding separates **Evidence** (why this category) from **Obligations**
(what the trials did not settle). An obligation is not a passed check.
<!-- --8<-- [end:verdicts] -->

## Quick start

```bash
git clone https://github.com/mirzahusadzic/gadfly.git
cd gadfly
uv sync
uv run python examples/refund.py tmp/refund-records.jsonl
```

```text
phrase-matcher: coupled but misaligned
  presentation moved it decline -> grant
rule-reader: carried
  ablation moved it decline -> grant; held under presentation, 2 shams
  no hidden fallback: bypass left it at decline
```

The same test in Python:

<!-- --8<-- [start:use] -->
```python
import json
from pathlib import Path

from examples.refund import RuleReader
from gadfly.pipeline import calls_needed, judge, run, situate
from gadfly.types import Budget

frame = situate(json.loads(Path("examples/refund.json").read_text()))
kept = []
result = run(
    frame,
    RuleReader(),
    Budget(calls=calls_needed(frame)),
    on_record=kept.append,
)
[finding] = judge(frame, kept)
print(finding.category, finding.evidence, finding.obligations)
```
<!-- --8<-- [end:use] -->

The frame's `battery.kind` must equal the battery's `name`. A different battery
is a different frame coordinate, so call `situate()` again when you swap it.
For several inputs, `overall(judge(frame, kept))` returns one category over all
of them. A stopped run is continued with `run(..., kept=kept)`; records already
in `kept` are not made again.

<!-- --8<-- [start:model] -->
## The path from premise to verdict

| Stage | What it makes | What stays fixed |
|---|---|---|
| `situate` | a checked `Frame` and its SHA-256 | every declared coordinate, including grain and battery |
| `plan` | the trials derived from the frame | trial bodies and order; the caller may inspect them before spending anything |
| `run` | one `Record` per call | the exact body, input, trial and quorum index recorded beside the observation |
| `judge` | one `Finding` per input | the frame, battery, body hashes, trial set, quorum and label vocabulary |
| `overall` | one `Overall` over the findings | every input's category and evidence while combining the frame-level answer |

Gadfly is a library with no hidden store. `run()` is the only stage that calls a
battery; records go to your `on_record` callback as they are made. `judge()`
recomputes the reading from those records. Keep them as JSON Lines, database
rows, or fixtures, but keep them.
<!-- --8<-- [end:model] -->

## Write a frame

Start from `examples/refund.json` or the [first-frame tutorial](docs/first-frame.md).

<!-- --8<-- [start:frame] -->
The top-level keys are all checked before a call:

| Key | What you write |
|---|---|
| `name` | a short label for this frame |
| `relation`, `locus`, `body` | the premise, where it acts, and `body.spans` carrying it |
| `role`, `grain`, `purpose` | whose reading, at which unit, for what |
| `trajectory`, `baseline`, `crossing`, `promise` | the path to the recipient, everything pinned, the boundary, and what must cross it |
| `anchors` | span ids the relation rests on; at least one |
| `inputs` | the finite test domain, each `{id, text}` with distinct ids |
| `observe` | `labels`, `instruction`, and `order` when labels are ordered |
| `interventions` | the trials; `ablation` is required |
| `allowed` | what `ablation` may produce, and optionally the opening `bypass` must expose |
| `standing` | `quorum`, `agree`, and optionally `stable` (which needs `repeat`) |
| `battery` | at least `kind`; shipped batteries use `model`, reasoning, schema or pins as documented below |
| `materialized` | `true` only when the observation is the form the recipient receives |
| `outsideScope` | the receiving owner's exclusion, in words; omit when there is none |

`body.spans` are `{id, text}` with an optional `kind` used to match sham spans.
`allowed` lists labels, or uses `lower`/`higher` along `observe.order`.
`allowed.bypass` is the label or labels a bypass must expose.

The frame is hashed whole. Rewording the promise, changing the grain or swapping
the battery makes a new frame, and records from the old hash will be refused.
<!-- --8<-- [end:frame] -->

<!-- --8<-- [start:trials] -->
## The interventions

| Trial | What changes | What it tests | Cost |
|---|---|---|---|
| `baseline` | nothing | the level being explained | `quorum` calls |
| `repeat` | nothing | whether that level is stable enough to compare | `quorum` calls |
| `ablation` | the anchors are removed | required influence | `quorum` calls |
| `cumulative` | anchors plus the spans they may fall back on | support carried elsewhere | `quorum` calls |
| `sham-*` | as much unanchored text, of the anchors' kinds | specificity of the change | one `quorum` per draw |
| `presentation` | mapped words renamed in one pass, body and input | whether wording rather than meaning drives the scorer | `quorum` calls |
| `bypass` | a named connection is cut | no hidden fallback; with `allowed.bypass`, only that opening clears it | `quorum` calls |
| `control` | spans any reader needs | whether the scorer can move at all | `quorum` calls |

`bypass` asks whether a fallback keeps the relation working without its
connection. `control` asks whether the scorer changes under a removal that
should matter to any reader. They answer different questions.

The full cost is `inputs × planned trials × quorum`. `calls_needed(frame)` gives
it without making a call.
<!-- --8<-- [end:trials] -->

## Batteries

A battery is a scorer. It reads the frame and the exact prompt for one call, and
returns one label or one typed opening. It is not told which trial it is serving.

<!-- --8<-- [start:protocol] -->
```python
class Battery(Protocol):
    name: str

    def check(self, frame: Frame) -> None: ...  # refuse before any call
    def observe(self, frame: Frame, prompt: str, max_output_tokens: int) -> Observation: ...
```
<!-- --8<-- [end:protocol] -->

Start with your own deterministic battery. It is the fastest way to test the
frame and has no provider cost. `examples/refund.py` contains the smallest
working template.

<!-- --8<-- [start:batteries] -->
| Battery | Reads with | Guarantees and recorded provenance |
|---|---|---|
| your own | an evaluation engine, deterministic rule, or local system | yours; the class's `name` is the frame's `battery.kind`; a battery never sees the trial id |
| `unified` | an LLM through the unified model router: `anthropic/`, `openrouter/`, `deepseek/`, `ultra-spark/` | loopback, no tools, no proxy, no redirects, `data_collection: deny` unless the exact model slug is listed under `trainsOnInputs`; refuses OpenAI slugs; `endpoints` pins OpenRouter endpoints; records the model and endpoint that served |
| `egemma` | Gemma through eGemma's `/judge` | loopback, no persona, no cache, paced to `GET /rate-limits`; caps time, tokens and bytes; records `model` and `revision`; optional frame pins are enforced |

The privacy and routing guarantees above belong to the two shipped batteries.
The `Battery` protocol does not constrain arbitrary third-party code.
<!-- --8<-- [end:batteries] -->

<!-- --8<-- [start:adapter] -->
Critics answer JSON to a schema, by default `{"label": <one of the frame's labels>}`.
A critic with its own schema names where the label lives with a JSON pointer:

```json
"battery": {
  "kind": "unified",
  "model": "anthropic/claude-sonnet-5-5",
  "reasoning": "low",
  "output": {
    "schema": {
      "type": "object",
      "properties": {"review": {"type": "object"}}
    },
    "label": "/review/verdict"
  }
}
```
<!-- --8<-- [end:adapter] -->

## Examples

<!-- --8<-- [start:examples] -->
| Example | Relation | What it teaches | Calls |
|---|---|---|---|
| `examples/refund.py` | a refund requires a receipt | a phrase matcher is misaligned by presentation; a rule reader carries, with a fallback left open | 7 per battery |
| `examples/review_handoff.py` | a failure reaches a review state; a grant bounds operations | the essay's worked example, including a cooled summary and a lost record | 6–7 per system |
| `examples/citation.py` | an answer rests on cited source S-2 | a source reader carries while a word matcher is exposed by presentation | 7 per battery |
| `examples/system_prompt.py` | one system line governs a refusal | a request-keyed scorer cools with a moved control; an always-refuse scorer is unresolved | 6 per battery |
| `examples/tool_permission.py` | a grant limits a tool to read-only | a scope reader carries; an eager tool permits a disallowed modification | 6 per battery |
| `examples/code_invariant.py` | a sort line governs output order | a removed trial record is no evidence; a full run carries with its fallback open | 6 |
| `examples/refund_live.py` | the refund relation through a routed model or eGemma | the same pipeline with a sampled battery and real token cost | 21 to a model |
<!-- --8<-- [end:examples] -->

## Boundaries

<!-- --8<-- [start:boundaries] -->
- A category is a fixed-rule reading of observations under one frame, not proof of causality and not a probability.
- `carried` still requires the checks in **Obligations** to be read. In the current code it can be returned while fallback, specificity or materialization checks remain open; the essay requires all five carriage checks to pass.
- `outside scope` is currently reached from the owner's declaration alone; the independent scope check remains an obligation.
- `materialized: true` is a declaration. Gadfly does not inspect a receiving document, field or program.
- A deterministic battery tests the frame and mechanism, not a model. A sampled live critic tests sampled behavior at that model and endpoint, not a provider's general policy.
- Gadfly has no authentication or signature on records. Keep records somewhere you trust and record the run metadata you need outside Gadfly.
<!-- --8<-- [end:boundaries] -->

## Documentation

Start with [Your first frame](docs/first-frame.md), then read [Reading a verdict](docs/reading-a-verdict.md).
The [reference](docs/reference.md) is the API lookup. The essay remains the
normative account of the method and the five carriage checks.

Build the site offline with:

```bash
uv run --group docs mkdocs build --strict
```

## Development

```bash
uv sync
uv run pytest
uv run ruff check gadfly examples tests hooks
uv run ruff format --check gadfly examples tests hooks
```

The After the Poem replay runs when `GADFLY_ATP_PLANS` names its plans.

## License

Code: Apache-2.0. The text of `docs/load-bearing.md`: © 2026 Mirza Husadzic,
[CC BY 4.0](LICENSES/CC-BY-4.0.txt).
