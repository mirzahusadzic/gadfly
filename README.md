# Gadfly

Gadfly tests whether a premise is **load-bearing**: you situate a relation (its
grain, scope and the promise a recipient needs), Gadfly removes or changes it
under declared interventions, runs a scorer, and reads the result by fixed
rules. It never reasons about the content itself.

The method is the counterfactual load-bearing test formalized in
[When meaning is load-bearing](https://github.com/mirzahusadzic/mirzahusadzic#when-meaning-is-load-bearing):
fix the setting and the recipient's requirements, remove or change a relation,
observe. An observed difference makes the relation a candidate; independent
checks decide whether it is carried.

Gadfly is a pipeline, not a service. It keeps no state: every stage returns
typed values, and you keep them (a file, a database, a test fixture).

```
situate(frame)  ->  plan(frame)  ->  run(frame, battery, budget)  ->  judge(frame, records)
   checked,         the trials,      the only stage that calls        the verdict, from
   hashed           fixed first      out; each record to you          your records alone
```

## The formulation you declare

| README | Gadfly field | What you write |
|---|---|---|
| relation $I$ at locus $v$ in body $B$ | `relation`, `locus`, `body` | the premise under test, where it acts, and the material it lives in |
| role $r$, grain $g$, purpose $P$ | `role`, `grain`, `purpose` | whose reading, at which unit (a line, a claim, a span), for what |
| trajectory $T$, baseline $B_0$ | `trajectory`, `baseline` | the path from body to recipient; everything pinned (hashes, versions, models) |
| crossing $C$, promise $p$ | `crossing`, `promise` | the boundary to the recipient and the distinction it must receive |
| anchors $A$, observation map $o_p$ | `anchors`, `observe` | the source spans the relation rests on; how a scorer's output becomes the observable |
| test domain $X$, interventions $\Delta_I$ | `inputs`, `interventions` | the finite inputs; the admissible changes to the relation |
| $\simeq_p$, $E_{p,\delta}$ | `observe.labels`, `allowed` | two observations are the same when they carry the same label; which labels ablation may produce (a list, or `lower` / `higher` along `observe.order`) |
| standing $\sigma$ | `standing` | how far an observation counts: `quorum` runs per trial, `agree` of them for a level, `stable` when every run must agree |

The whole frame is hashed before any trial runs. Changing any coordinate,
the grain included, makes a new frame that is assessed separately.

## The internals

| Intervention | What changes | What it can show |
|---|---|---|
| `baseline` | nothing | the observation the others are compared with |
| `repeat` | nothing, fresh run | whether the scorer is stable enough to read (stochastic scorers need a quorum) |
| `presentation` | the domain's distinctive words masked or renamed consistently | presentation invariance (carriage check 2) |
| `ablation` | the anchors removed | required influence (check 1) |
| `cumulative ablation` | the anchors and what the first ablation fell back on | whether support is carried elsewhere |
| `sham` | spans of the same size and kind, not cited, removed | specificity: an effect from any removal is not this relation's |
| `bypass` | the connection that makes the relation operative removed | no hidden fallback (check 3): the designated opening must appear |

Verdicts are read by fixed rules, in this order:

1. **unresolved** when a planned trial has no agreed level, the baseline and
   repeat runs split under `stable`, or repeat differs from baseline;
2. **coupled but misaligned** when presentation moves it, or ablation moves it
   to a label the frame does not allow;
3. **cooled** when ablation leaves it as it was;
4. **unresolved** when a sham moves it too (the change is not specific);
5. **carried** otherwise, with the carriage checks the trials did not settle
   kept as open obligations (no hidden fallback, presentation, specificity,
   materialization).

**Outside scope** only by the recipient's declared exclusion (`outsideScope`),
never inferred. Each finding keeps its category, levels, evidence and
obligations.

## Use

```python
import json
from pathlib import Path

from examples.refund import RuleReader  # or your own battery
from gadfly.pipeline import calls_needed, judge, run, situate
from gadfly.types import Budget

frame = situate(json.loads(Path("examples/refund.json").read_text()))
kept = []  # your state, kept your way
result = run(frame, RuleReader(), Budget(calls=calls_needed(frame)), on_record=kept.append)
[finding] = judge(frame, kept)
print(finding.category, finding.evidence)
```

[`examples/refund.py`](examples/refund.py) runs this with two scorers on a
refund policy. Both decline a request without a receipt and grant it once the
receipt rule is removed; only presentation (renaming "receipt" consistently)
shows that one reads a phrase and the other the rule:

```
phrase-matcher: coupled but misaligned
  presentation moved it decline -> grant
rule-reader: carried
  ablation moved it decline -> grant, and it held under presentation and the sham
```

[`examples/after_the_poem.py`](examples/after_the_poem.py) replays a study's
retained load-bearing sessions through Gadfly with no new calls, and checks
that each case reaches the category the study published. Both examples run as
tests.

## Batteries (scorers)

A battery reads the exact text of one trial (it never learns which trial) and
returns an observation: one of the frame's labels, or a typed opening when
there is no outcome to read. It implements `gadfly.types.Battery`:

```python
class Battery(Protocol):
    name: str

    def check(self, frame: Frame) -> None: ...  # refuse a frame it must not serve
    def observe(self, frame: Frame, prompt: str, max_output_tokens: int) -> Observation: ...
```

| Battery | Scorer | Kind |
|---|---|---|
| `router-critic` | an LLM critic through the [unified model router](https://github.com/mirzahusadzic/codex-unified-model-router) (`POST /v1/responses` on loopback; any routed slug, Claude on Anthropic's API included) | stochastic: `quorum` runs per trial |
| your own | a project's evaluation (a rubric reader, a prompt pack's eval gate), or a deterministic engine | deterministic: `quorum: 1`; repeat is its determinism check |

The router critic talks only to loopback, over no proxy and through no
redirect; it sends no tools (through the router, Claude runs on Anthropic's
API but web search runs elsewhere, so a body would leave Anthropic); and it
refuses a model whose provider trains on its inputs unless the frame names
that model under `battery.trainsOnInputs`. Its token comes from the
environment or the router's env file and is never logged or recorded.

## Runs and records

`run` makes every planned trial of every input `quorum` times, in a fixed
order. It never starts a call the `Budget` cannot cover (calls, and output
tokens capped per call), stops between calls when `cancelled()` says so, and
hands each `Record` to `on_record` as soon as it exists, so what was spent is
kept even when a run stops early. A battery that fails gives an opening, never
a guessed label. `judge` reads only records the plan could have made: this
frame's hash, its inputs and trials, each trial's own body hash, runs within
the quorum, each run once.

## Development

```
uv sync
uv run pytest            # the After the Poem replay runs when GADFLY_ATP_PLANS names its plans
uv run ruff check . && uv run ruff format --check .
```
