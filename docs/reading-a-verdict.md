# Reading a verdict

`judge(frame, records)` returns one `Finding` per input. `overall(findings)`
returns one `Overall` for the frame's test domain. Categories are read by fixed
rules, not by a model.

---

<!-- copy README.md:verdicts -->
### What Gadfly says

Each input gets one **finding**, and a frame with several inputs gets one
**overall** category over them. The categories are not scores; the first rule
that matches names the category.

- **`carried`:** ablation moved the observation as the promise allows, and
  every carriage check passed: presentation and the shams held, the bypass
  exposed its opening, and the frame says the observation is what the
  recipient receives.
- **`coupled but misaligned`:** the relation matters, but presentation or
  placement moved it, or ablation moved it where the promise disallows.
- **`cooled`:** ablation left the observation unchanged while a control
  showed the scorer can move, so this relation has no operative influence
  here.
- **`unresolved`:** there is not enough agreed evidence: a trial is missing
  or split, repeat is unstable, a sham moved too, the scorer cannot tell, or a
  check the category needs is still open.
- **`outside scope`:** the receiving owner declares the distinction
  unnecessary, and their own check of that exclusion is recorded.

Every finding keeps its **evidence** (why this category) apart from its
**obligations** (what the trials did not settle), and an obligation is not a
passed check. Under the default `carriage: all-checks`, an open check keeps
carried, cooled and outside scope unresolved; a frame with
`carriage: listed` names the category and lists its open checks beside it.
<!-- end copy -->

---

### The rules, in order

For each input, a trial's observations reduce to one level when exactly one
label has at least `agree` of them. The first rule that matches names the
category:

1. **unresolved:** a planned trial has no agreed level. With `stable`, the
   baseline and repeat sessions must not split, and a repeat level that
   differs from the baseline is unresolved too: the grain cannot tell the
   levels apart.
2. **coupled but misaligned:** presentation moved the observation, or
   placement did.
3. **coupled but misaligned:** ablation moved it outside `allowed`, or, for
   ordered labels, in the wrong direction.
4. **cooled:** ablation left it unchanged. If a declared control also left it
   unchanged, the finding is unresolved because the scorer cannot tell; with
   no control, discrimination is open.
5. **unresolved:** a sham moved too, so the change is not specific.
6. **carried:** otherwise.

#### Open checks

Whatever the category, the checks still open are listed after it: no hidden
fallback, presentation invariance, specificity and materialization, and
discrimination for cooled.

- **Under the default `carriage: all-checks`:** a category is named only when
  the checks it needs have passed, every carriage check for carried and a
  control that moved for cooled. Otherwise the finding is unresolved, and its
  evidence says why (`not carried while 1 carriage check is open`).
- **Under `carriage: listed`:** the category stands, with its open checks
  listed beside it.

#### Outside scope

`outside scope` comes first when the frame declares `outsideScope`, because
the trials do not test an exclusion; only the owner's check of it is open or
settled. With `scopeCheck`, the finding is outside scope and says who checked
it, from what and when. Without it the finding is unresolved, or outside scope
with the check open under `listed`, and the records are checked either way.

---

### Evidence is not obligation

A finding keeps why its category was named apart from what is still open:

```python
[finding] = judge(frame, kept)
print(finding.category)
print(finding.levels)
print(finding.evidence)
print(finding.obligations)
```

- **`category`:** the fixed-rule answer for this input.
- **`levels`:** each planned trial's agreed level, or `None`.
- **`evidence`:** why this category, such as
  `ablation moved it decline -> grant`.
- **`obligations`:** what did not run or did not pass, such as
  `no hidden fallback: bypass left it at decline`.

A UI must not merge the two lists, or show an obligation as a warning on an
otherwise unconditional success. Of the essay's five carriage checks, required
influence is the ablation rule, and presentation invariance, no hidden
fallback and materialization stay open until their trials or the frame settle
them. Traceability rests on the records, each of which names its frame,
battery, body, prompt and what served it.

---

### Several inputs

`overall` keeps each input's category and evidence, and names one category for
the frame:

- `outside scope` when declared for the frame;
- otherwise `coupled but misaligned` if any input is;
- otherwise `unresolved` if any input is unresolved, or if carried and cooled
  are mixed;
- otherwise the one category all inputs share.

Shared obligations appear once, and others keep their input's id. The overall
category never makes a weaker input disappear.

---

### Partial and stopped runs

A stopped run is not a verdict on all the planned trials. Continue it with the
records you kept:

```python
continued = run(frame, battery, Budget(calls=12), kept=kept)
all_records = [*kept, *continued.records]
```

The same `(input, trial, run)` is never made twice. A lost record makes its
call missing, and the finding stays unresolved until the call is made again
or deliberately dropped from `kept`. Records from another frame or battery, an
unknown trial, a duplicate run, or a label outside `observe.labels` are
refused.

---

### Refused records

Each refusal says what went wrong with a kept record, before any verdict is
read from it.

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
