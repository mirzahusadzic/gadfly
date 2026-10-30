# Reading a verdict

`judge(frame, records)` returns one `Finding` per input. `overall(findings)`
returns one `Overall` for the frame's test domain. Categories are read by fixed
rules, not by a model.

--8<-- "README.md:verdicts"

## The rules, in order

For each input, each trial's observations reduce to one level when exactly one
label has at least `agree` observations. The first matching rule names the category:

1. **unresolved** — any planned trial has no agreed level. With `stable`, baseline
   and repeat sessions must not split. A repeat level that differs from baseline
   is also unresolved: the grain cannot tell the levels apart.
2. **coupled but misaligned** — presentation moved the observation.
3. **coupled but misaligned** — ablation moved it outside `allowed`; for ordered
   labels, the move was in the wrong direction.
4. **cooled** — ablation left it unchanged. If a declared control also left it
   unchanged, the finding is unresolved because the scorer cannot tell. Without a
   control, `cooled` retains the discrimination obligation.
5. **unresolved** — a sham moved too, so the observed change is not specific.
6. **carried** — otherwise, with any untested carriage checks listed as obligations.

`outside scope` short-circuits the category when `outsideScope` is declared. The
current code still validates any supplied records, but it does not perform the
independent scope check required by the essay.

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
invariance, no hidden fallback, traceability and materialization. The current
implementation treats the last three differently: fallback and materialization
can be obligations on a carried finding, and traceability rests on the records.
That is a semantic gap between this commit and the essay, not a stronger result.

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
| `a record belongs to another frame` | any frame coordinate changed; the record's hash no longer names this frame |
| `a record was made by X, not the Y battery` | a frame is read only by the battery its hash names |
| `a record names an input or trial the plan does not have` | the plan or input id changed |
| `a X record was made on another body` | the trial's body hash does not match the current plan |
| `run N is outside the quorum of M` | re-situate with the intended standing; do not edit the record |
| `two records for input/trial run N` | the persisted set contains the same call twice |
| `... is not one of this frame's labels` | the scorer's answer was outside the declared observation map |

