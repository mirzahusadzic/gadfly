# Reading a verdict

`judge(frame, records)` returns one `Finding` per input. `overall(findings)`
returns one `Overall` for the frame's test domain. Categories are read by fixed
rules, not by a model.

<!-- copy README.md:verdicts -->
## What Gadfly says

Each input gets one **finding**; a multi-input frame gets one **overall**
category over the findings. The categories are not scores. The first matching
rule below names the category.

| Finding | Plain meaning |
|---|---|
| `carried` | Ablation moved the observation as the promise allows, and every carriage check passed: presentation and the shams held, the bypass exposed its opening, and the frame says the observation is what the recipient receives. |
| `coupled but misaligned` | The relation matters, but presentation or placement moved it, or ablation moved it where the promise disallows. |
| `cooled` | Ablation left the observation unchanged while a control showed the scorer can move: this relation has no operative influence here. |
| `unresolved` | There is not enough agreed evidence: a trial is missing or split, repeat is unstable, a sham moved too, the scorer cannot tell, or a check the category needs is still open. |
| `outside scope` | The receiving owner declares the distinction unnecessary, and their own check of that exclusion is recorded. |

Every finding separates **Evidence** (why this category) from **Obligations**
(what the trials did not settle). An obligation is not a passed check. By
default (`carriage: all-checks`) an open check keeps carried, cooled and
outside scope unresolved, and the evidence says so; a frame that says
`carriage: listed` names the category and lists its open checks beside it.
<!-- end copy -->

## The rules, in order

For each input, each trial's observations reduce to one level when exactly one
label has at least `agree` observations. The first matching rule names the category:

1. **unresolved** — any planned trial has no agreed level. With `stable`, baseline
   and repeat sessions must not split. A repeat level that differs from baseline
   is also unresolved: the grain cannot tell the levels apart.
2. **coupled but misaligned** — presentation moved the observation, or
   placement did.
3. **coupled but misaligned** — ablation moved it outside `allowed`; for ordered
   labels, the move was in the wrong direction.
4. **cooled** — ablation left it unchanged. If a declared control also left it
   unchanged, the finding is unresolved because the scorer cannot tell. Without a
   control, discrimination is open.
5. **unresolved** — a sham moved too, so the observed change is not specific.
6. **carried** — otherwise.

Then the open checks are listed, whatever the category: no hidden fallback,
presentation invariance, specificity and materialization, and discrimination for
cooled. Under the default `carriage: all-checks` a category is named only when
the checks it needs have passed: every carriage check for carried, a control
that moved for cooled. Otherwise the finding is unresolved, and its evidence
says which (`not carried while 1 carriage check is open`). Under
`carriage: listed` the category stands and its open checks are listed beside it.

`outside scope` comes first when `outsideScope` is declared: the trials do not
test an exclusion, so only the owner's check of it is open or settled. With
`scopeCheck` the finding is outside scope and says who checked it, from what and
when; without it, the finding is unresolved (under `listed`, outside scope with
the check open). Records are still checked either way.

## Evidence is not obligation

```python
[finding] = judge(frame, kept)
print(finding.category)      # the fixed-rule answer for this input
print(finding.levels)        # agreed level or None for each planned trial
print(finding.evidence)      # why this category
print(finding.obligations)   # what did not run or did not pass
```

An evidence line such as `ablation moved it decline -> grant` says why the rule
matched. An obligation such as `no hidden fallback: bypass left it at decline`
says that a required check remains open. A UI must not merge the two lists or
render an obligation as a warning on an otherwise unconditional success.

The five carriage checks in the essay are required influence, presentation
invariance, no hidden fallback, traceability and materialization. Required
influence is the ablation rule; presentation invariance, no hidden fallback and
materialization are open checks until their trials or the frame settle them;
traceability rests on the records, each of which names its frame, battery, body,
prompt and what served it.

## Several inputs

`overall` preserves each input's category and evidence:

- `outside scope` when declared for the frame;
- otherwise `coupled but misaligned` if any input is;
- otherwise `unresolved` if any input is unresolved, or if carried and cooled are mixed;
- otherwise the one category all inputs share.

Shared obligations appear once; other obligations keep the input id. The overall
category never makes a weaker input disappear.

## Partial and stopped runs

A stopped run is not a verdict on all planned trials. Continue it with the
records you kept:

```python
continued = run(frame, battery, Budget(calls=12), kept=kept)
all_records = [*kept, *continued.records]
```

The same `(input, trial, run)` is never made twice. If a record is lost, that call
becomes missing and the finding is unresolved until it is made again or dropped
from `kept` intentionally. Records from another frame or battery, an unknown
trial, a duplicate run, or a label outside `observe.labels` are refused.

## Refused records

| Refusal | Meaning |
|---|---|
| `a record lacks [...]` | the stored row is not a whole record; it is refused before its call is skipped |
| `a record belongs to another frame` | any frame coordinate changed; the record's hash no longer names this frame |
| `a record was made by X, not the Y battery` | a frame is read only by the battery its hash names |
| `a record names an input or trial the plan does not have` | the plan or input id changed |
| `a X record was made on another body` | the trial's body hash does not match the current plan |
| `run N is outside the quorum of M` | re-situate with the intended standing; do not edit the record |
| `two records for input/trial run N` | the persisted set contains the same call twice |
| `... is not one of this frame's labels` | the scorer's answer was outside the declared observation map |

