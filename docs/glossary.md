# Glossary

Gadfly's words come from the essay, and a few of them mean something narrower
here than in everyday use. Each is defined in a sentence or two, grouped by
where you meet it.

---

### The frame

A frame is the whole experiment, written as JSON and checked before any call.
These fragments are from `examples/upgrade.json`, the frame
[Write a frame](write-a-frame.md) starts from:

```json
"anchors": ["removed"],
"allowed": {"ablation": ["merge", "unclear"]},
"standing": {"quorum": 5, "agree": 4},
```

- **Frame:** the declared experiment, hashed whole; changing any key makes a
  new frame, and records made under the old one are refused.
- **Relation:** the premise under test, that a decision rests on certain
  evidence.
- **Body and spans:** the evidence, cut into spans at the frame's grain, each
  with an `id`, its `text` and a `kind`.
- **Anchor:** a span the decision is supposed to rest on; the ablation trial
  removes the anchors.
- **Locus, role, grain, purpose and trajectory:** where the relation acts,
  whose reading it is, at what unit it is cut, what for, and the path to the
  recipient.
- **Baseline:** everything pinned for the comparison, so only the
  intervention changes.
- **Crossing and promise:** the boundary the decision crosses, and the
  consequence required there, including what the reader must do without the
  anchor.
- **Input:** one case of the test domain, the question the reader is asked.
- **Labels:** the answers a reader may give, each defined in the instruction.
- **Allowed:** what the ablation may produce, and, for a bypass, the one
  opening it must expose.
- **Quorum and agree:** how many times each trial is asked, and how many
  answers must be alike to give it a level.
- **Materialized:** a declaration that the observation is the form the
  recipient receives.
- **Outside scope and scope check:** the receiving owner's exclusion of the
  relation, and the owner's own check of it.
- **Carriage policy:** `all-checks`, the default, holds a category back while
  a check it needs is open; `listed` names it with the open checks beside it.

---

### The trials

A trial is one change to the evidence, asked `quorum` times. These are the
trials of the same frame, and [Interventions](interventions.md) explains each
with its cost:

```json
"interventions": {
  "repeat": true,
  "ablation": true,
  "sham": {"draws": 2},
  "presentation": {
    "quill": "heron",
    "retry_after": "wait_hint",
    "backoff": "pause"
  },
  "bypass": ["use"],
  "control": ["removed", "use"]
}
```

- **Baseline trial:** the evidence as it is, giving the level to explain.
- **Repeat:** the same evidence again, to show the level is stable.
- **Ablation:** the anchors cut, to show whether the decision needs them.
- **Sham:** a harmless span of the anchors' kind cut instead, to show the
  change is specific.
- **Presentation:** names renamed in one pass, to show the reader follows
  meaning, not wording.
- **Placement:** one span moved after another, to show its place does not
  decide.
- **Inversion:** the anchors' sense inverted in their own words, to show the
  answer follows it.
- **Input inversion:** what is asked inverted, a case or a question, to show
  the answer follows it.
- **Bypass:** the connection that makes the anchor apply cut, to show no
  hidden fallback carries the decision.
- **Control:** what any reader needs cut, to show this reader can move at
  all.
- **Cumulative:** the anchors and the spans they may fall back on cut
  together, to show support carried elsewhere.

---

### The reading

Fixed rules, not a model, turn the answers into a verdict, and
[Reading a verdict](reading-a-verdict.md) gives the rules in order. This is
one kept run of the tutorial's fifth step, read back:

```text
$ uv run python examples/read.py examples/rung5.json \
    --verdict 1
pr: carried
  levels: baseline hold, repeat hold, ablation merge, sham-1 hold, sham-2 hold, presentation hold, bypass merge
  evidence: ablation moved it hold -> merge; held under presentation, 2 shams
  evidence: bypass moved it hold -> merge: no hidden fallback
```

- **Level:** the label at least `agree` of a trial's calls gave; a trial
  whose calls split has none.
- **Finding:** one input's category, with its levels, its evidence and its
  obligations.
- **Overall:** one category over a frame's findings, which keeps every
  input's own.
- **Evidence:** why the rules named the category.
- **Obligation, or open check:** what the trials did not settle; it is never
  a passed check.
- **Carriage checks:** the essay's five: required influence, presentation
  invariance, no hidden fallback, traceability and materialization.
- **Discrimination:** whether the reader can move at all, which a control
  that moved settles.
- **Categories:** `carried`, `coupled but misaligned`, `cooled`,
  `unresolved` and `outside scope`, none of them a score.

---

### Running

A run asks a battery each trial's prompt and keeps what comes back.
[Batteries](batteries.md) covers the shipped ones and writing your own.

> [!NOTE]
> A battery is never told which trial it is serving: it gets the frame and
> the prompt, not the trial's id.

- **Battery:** the scorer, which reads the frame and one exact prompt and
  answers with one label or one opening.
- **Opening:** a typed answer for a refusal, an unreadable answer or a failed
  call, never a guessed label.
- **Record:** one call kept: its frame, input, trial and run, the hashes of
  what was read, and what came back.
- **Kept run:** a run's records, one JSON line each, from which any verdict
  is read again without a model.
- **Budget:** the most a run may spend: a number of calls, a cap on each
  answer, and optionally a cap on all output tokens.
- **Prediction:** what you expect each trial to give, written before the
  first call; the examples keep theirs.
