# Interventions

An intervention changes or removes the declared relation while preserving the
frame, input and encounter. The plan is derived from the frame alone, before a
call is made.

<!-- copy README.md:trials -->
## The interventions

| Trial | What changes | What it tests | Cost |
|---|---|---|---|
| `baseline` | nothing | the level being explained | `quorum` calls |
| `repeat` | nothing | whether that level is stable enough to compare | `quorum` calls |
| `ablation` | the anchors are removed | required influence | `quorum` calls |
| `cumulative` | anchors plus the spans they may fall back on | support carried elsewhere | `quorum` calls |
| `sham-*` | as much unanchored text, of the anchors' kinds | specificity of the change | one `quorum` per draw |
| `presentation` | mapped words renamed in one pass, body and input | whether wording rather than meaning drives the scorer | `quorum` calls |
| `placement` | one span moved after another, its text unchanged | whether the structure rather than the meaning drives the scorer | `quorum` calls |
| `bypass` | a named connection is cut | no hidden fallback; with `allowed.bypass`, only that opening clears it | `quorum` calls |
| `control` | spans any reader needs | whether the scorer can move at all; cooled needs it to | `quorum` calls |

`bypass` asks whether a fallback keeps the relation working without its
connection. `control` asks whether the scorer changes under a removal that
should matter to any reader. They answer different questions.

The full cost is `inputs × planned trials × quorum`. `calls_needed(frame)` gives
it without making a call.
<!-- end copy -->

## What each trial can establish

| Trial | A move means | No move means | What it cannot establish |
|---|---|---|---|
| `baseline` | the starting level | — | that the relation matters |
| `repeat` | a split level is unstable at this quorum | the observed level recurred | that the input is representative |
| `ablation` | the anchors influenced the outcome | no operative influence here | that another span is not a fallback |
| `cumulative` | support moved elsewhere | the initial cut removed the effect | carriage on its own |
| `sham` | the scorer responds to irrelevant same-kind text | the ablation's change is more specific | that every possible irrelevant change is controlled |
| `presentation` | wording drives the observation | the tested wording change is invariant | that all paraphrases are |
| `placement` | the span's place drives the observation | the tested move is invariant | that every reordering is |
| `bypass` | a hidden connection still carries the relation | no tested fallback is visible | receiving-system materialization |
| `control` | the scorer can move under a required removal | the scorer or task is insensitive | that it moves for the right reason |

## Bypass and control are different

A **bypass** cuts the connection that makes the relation operative. It asks
whether some fallback still produces the required outcome. When the frame says
`allowed.bypass`, the bypass must land on that designated opening to clear the
check. Without `allowed.bypass`, any move from baseline clears the current
implementation's check; that is a weaker claim and should be stated as such.

A **control** cuts material that any competent reader of the task should need.
It is a discrimination check: if ablation leaves the observation but the control
also leaves it, an all-constant scorer and an idle relation are not distinguishable.
Under the default `carriage: all-checks`, a finding is `cooled` only when a
control moved.

## Presentation is one pass

`presentation` maps words to replacements. The mapping is applied once, longest
phrase first, consistently to body spans and the input. This prevents swaps from
collapsing and chains from compounding. A mapping that reaches no input and no
body span is refused as a trial identical to baseline.

## Placement is one move

`placement` moves one span to follow another and changes no text. It asks the
question presentation cannot: does the clause's place matter, a grant before or
after an instruction, a caveat moved out of its section? A move that changes the
level reads as `coupled but misaligned`, right after presentation. A move that
leaves the order as it is would repeat the baseline, and is refused.

## Cost

For one input, the call count is the number of planned trials times `quorum`.
For the whole frame it is inputs times trials times quorum. A sham with
`{"draws": n}` adds up to `n` trials; an unmatched draw is left out and the
finding says so.

```python
from gadfly.pipeline import calls_needed, plan

for trial in plan(frame):
    print(trial.id, len(trial.removed), trial.body_hash)
print("full run:", calls_needed(frame), "calls")
```

Run a subset with `run(..., only={"baseline", "ablation"})`. Missing planned trials
make the finding unresolved unless they are not part of the plan at all; use a
partial run for diagnosis, not for a final carried verdict.

## Choosing a useful first set

For a deterministic scorer, start with `repeat`, `ablation`, one `sham`, and
`presentation`. Add `bypass` when the relation has a separate connection or
binding line whose removal should expose an opening. Add `control` when a cooled
result is plausible. Add `cumulative` only when support could shift rather than disappear.

For a sampled model, use a quorum of at least three and decide `agree` before the
run. Do not increase the quorum after seeing labels; that changes the frame hash.

