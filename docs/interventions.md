# Interventions

An intervention changes or removes the declared relation while keeping the
frame, the input and the encounter as they are. The plan of trials is derived
from the frame alone, before any call.

---

### The trials

Each trial is asked `quorum` times. The full cost is the inputs times the
planned trials times `quorum`, which `calls_needed(frame)` gives without a
call.

| Trial | What changes | What it tests | Cost |
|---|---|---|---|
| `baseline` | nothing | the level being explained | `quorum` calls |
| `repeat` | nothing | whether that level is stable enough to compare | `quorum` calls |
| `ablation` | the anchors are removed | required influence | `quorum` calls |
| `cumulative` | anchors plus the spans they may fall back on | support carried elsewhere | `quorum` calls |
| `sham-*` | as much text of the anchors' kinds, never an anchor, a bypassed span or a declared fallback | specificity of the change | one `quorum` per draw |
| `presentation` | mapped words renamed in one pass, body and input | whether wording rather than meaning drives the scorer | `quorum` calls |
| `placement` | one span moved after another, its text unchanged | whether the structure rather than the meaning drives the scorer | `quorum` calls |
| `inversion` | the anchors' sense inverted in their own words; the input left as it is | whether the answer follows the relation's sense, reaching `allowed.inversion` | `quorum` calls |
| `bypass` | a named connection is cut | no hidden fallback; with `allowed.bypass`, only that opening clears it | `quorum` calls |
| `control` | spans any reader needs | whether the scorer can move at all; cooled needs it to | `quorum` calls |

A sham never cuts a span declared under `cumulative`. The frame says that
span may carry the relation, so cutting it would test nothing. This is a
change to how shams are planned; no kept example's plan changes, as none
drew one.

A sham matches the anchors by length in characters, within their kind, so
`kind` is how a frame chooses the unit a sham matches. To cut as many lines
as the anchors, give each block a kind that names its line count, such as
`lines-8`.

---

### What each trial can establish

A trial shows something when the answer moves and something else when it
holds, and neither settles everything.

| Trial | A move means | No move means | What it cannot establish |
|---|---|---|---|
| `baseline` | the starting level | nothing yet: it is what the others are read against | that the relation matters |
| `repeat` | a split level is unstable at this quorum | the observed level recurred | that the input is representative |
| `ablation` | the anchors influenced the outcome | no operative influence here | that another span is not a fallback |
| `cumulative` | support moved elsewhere | the initial cut removed the effect | carriage on its own |
| `sham` | the scorer responds to irrelevant same-kind text | the ablation's change is more specific | that every possible irrelevant change is controlled |
| `presentation` | wording drives the observation | the tested wording change is invariant | that all paraphrases are |
| `placement` | the span's place drives the observation | the tested move is invariant | that every reordering is |
| `inversion` | the answer follows the relation's sense | after a carried ablation, the reading drops the sense: coupled but misaligned | that every way of stating the sense is read |
| `bypass` | a hidden connection still carries the relation | no tested fallback is visible | receiving-system materialization |
| `control` | the scorer can move under a required removal | the scorer or task is insensitive | that it moves for the right reason |

---

### Bypass and control are different

Both cut more than the anchors, but they answer different questions.

- **Bypass:** cuts the connection that makes the relation operative, and asks
  whether some fallback still produces the required outcome. With
  `allowed.bypass`, the bypass must land on that designated opening to clear
  the check; without it, any move from baseline clears it, a weaker claim to
  state as such.
- **Control:** cuts what any competent reader of the task needs, a check that
  the reader can tell at all. If the ablation and the control both leave the
  observation, a reader that never moves looks like an idle relation, so under
  `carriage: all-checks` a finding is `cooled` only beside a control that
  moved.

---

### Presentation is one pass

`presentation` maps words to their replacements and applies the mapping once,
longest phrase first, to the body and the input alike, so swaps cannot
collapse and chains cannot compound. A mapping that reaches nothing the reader
reads would repeat the baseline, and is refused. The tutorial's frame renames
three words:

```json
"presentation": {
  "quill": "heron",
  "retry_after": "wait_hint",
  "backoff": "pause"
}
```

---

### Placement is one move

`placement` moves one span to follow another and changes no text, asking what
presentation cannot: does a clause's place decide, such as a grant before or
after an instruction? A move that changes the level reads as `coupled but
misaligned`, and a move that leaves the order as it is would repeat the
baseline, so it is refused. This moves the grant after the audit line:

```json
"placement": {"span": "grant", "after": "audit"}
```

---

### Inversion asks for a direction

Every other trial asks whether the answer rests on the anchors; `inversion`
asks whether it follows their sense. It maps phrases of the anchors to their
inversions, applied once as presentation is, to the anchors alone: a phrase
found in any other span is refused, and the case and question stay as they
are. `allowed.inversion` names what the inverted answer must reach, and the
baseline's own label never counts:

```json
"interventions": {
  "inversion": {
    "the incident commander approves the restore":
      "the incident commander does not approve the restore"
  }
},
"allowed": {"ablation": ["open"], "inversion": ["Yes", "No", "open"]}
```

It is read after a carried ablation. An inversion that stays at the baseline,
or reaches a label `allowed.inversion` does not list, is coupled but
misaligned; one with no agreed level leaves direction open. It is a change
to the method, read only when a frame declares it, so no earlier frame reads
differently.

Its limits are three. A who-question may rightly keep its answer when a
description of the person is inverted, so a person declares the phrase. A
conditional answer reads only as `conditional`, so an inversion inside its
condition does not show at that grain; and it inverts words, so a reader
that works on graphs needs its own guard as well.

---

### Cost

For one input the call count is the planned trials times `quorum`, and a sham
with `{"draws": n}` adds up to `n` trials; a draw with no match is left out,
and the finding says so. Among spans of the same kind and length, the frame's
own seed picks each draw, one span at a time, so a frame with hundreds of such
spans takes noticeably longer to plan; varying their lengths or kinds avoids
it. This lists the plan and its cost without spending anything:

```python
from midwife.pipeline import calls_needed, plan

for trial in plan(frame):
    print(trial.id, len(trial.removed), trial.body_hash)
print("full run:", calls_needed(frame), "calls")
```

`run(..., only={"baseline", "ablation"})` runs a subset. A planned trial left
out makes the finding unresolved, so use a partial run for diagnosis, never
for a final carried verdict.

---

### Choosing a useful first set

Start small, and add a trial when its question becomes yours.

- **A deterministic scorer:** start with `repeat`, `ablation`, one `sham` and
  `presentation`.
- **A separate connection:** add `bypass` when a binding line, cut, should
  expose an opening.
- **A plausible cooled result:** add `control`, which cooled needs.
- **Support that could shift:** add `cumulative` only when support could move
  to another span rather than disappear.
- **A sampled model:** use a quorum of at least three, and decide `agree`
  before the run; raising the quorum after seeing labels changes the frame's
  hash.
