# Statistics

A verdict is read by fixed rules from a run's calls, and five calls a trial
are evidence, not proof. `gadfly stats` says how much each verdict rests on:
how firm each trial's answers are, whether a trial moved the answer or held
it, how likely the quorum was to reach a level, and how often a run's verdict
comes out the same when its calls are drawn again. Nothing it reports changes
a verdict.

---

### One run is a hint

This is one kept run of the upgrade frame, five calls a trial. Every call of
the ablation moved the answer from `hold` to `merge`:

```text
$ uv run gadfly stats examples/upgrade.json \
    examples/runs/upgrade/1.jsonl
frame: quill-upgrade (569c71692864ab0fcfbfcd41baaa0011ee213bc0b90ca9bcb95dd40b7f085679)
records: 1 run, 40 calls
agreement: 100% of calls give their trial's most common answer in their own run
power: at 100% agreement, a trial reaches a level of 4 of 5 100% of the time, and all 8 trials the plan asks of an input 100%
input pr
  baseline        5 calls  hold 5  top 100% (57%-100%)
  repeat          5 calls  hold 5  top 100% (57%-100%), at most 43% differ from hold
  ablation        5 calls  merge 5  top 100% (57%-100%), p 0.0079 against hold (Holm 0.056)
  sham-1          5 calls  hold 5  top 100% (57%-100%), at most 43% differ from hold
  sham-2          5 calls  hold 5  top 100% (57%-100%), at most 43% differ from hold
  presentation    5 calls  hold 5  top 100% (57%-100%), at most 43% differ from hold
  bypass          5 calls  merge 5  top 100% (57%-100%), p 0.0079 against hold (Holm 0.056)
  control         5 calls  merge 5  top 100% (57%-100%), p 0.0079 against hold (Holm 0.056)
verdicts, each run's calls drawn again 200 times
  run 1, pr  carried; drawn again carried 100%
```

Five of five against none of five is a p-value of 0.0079 on its own, but the
run tests seven trials against the baseline at once, and Holm's adjustment
for that makes it 0.056. Pooled over three of the frame's five kept runs, the
same move is fifteen of fifteen, and no chance explains it:

```text
$ uv run gadfly stats examples/upgrade.json \
    examples/runs/upgrade/1.jsonl \
    examples/runs/upgrade/2.jsonl \
    examples/runs/upgrade/3.jsonl --resamples 0
frame: quill-upgrade (569c71692864ab0fcfbfcd41baaa0011ee213bc0b90ca9bcb95dd40b7f085679)
records: 3 runs, 120 calls
agreement: 100% of calls give their trial's most common answer in their own run
power: at 100% agreement, a trial reaches a level of 4 of 5 100% of the time, and all 8 trials the plan asks of an input 100%
input pr
  baseline       15 calls  hold 15  top 100% (80%-100%)
  repeat         15 calls  hold 15  top 100% (80%-100%), at most 20% differ from hold
  ablation       15 calls  merge 15  top 100% (80%-100%), p 1.3e-08 against hold (Holm 9e-08)
  sham-1         15 calls  hold 15  top 100% (80%-100%), at most 20% differ from hold
  sham-2         15 calls  hold 15  top 100% (80%-100%), at most 20% differ from hold
  presentation   15 calls  hold 15  top 100% (80%-100%), at most 20% differ from hold
  bypass         15 calls  merge 15  top 100% (80%-100%), p 1.3e-08 against hold (Holm 9e-08)
  control        15 calls  merge 15  top 100% (80%-100%), p 1.3e-08 against hold (Holm 9e-08)
  run 1, pr  carried
  run 2, pr  carried
  run 3, pr  carried
```

---

### What each number says

- **Agreement:** the share of calls that gave their trial's most common
  answer in their own run, how steadily the reader answers when nothing
  changes between its calls. An opening never agrees, and a call its trial
  asked once in the run is left out, so a quorum of one has no agreement to
  measure.
- **Power:** at that agreement, how often a trial reaches a level of `agree`
  of `quorum`, and how often every trial the plan asks of an input does, the
  one-anchor trials aside. A trial with no level leaves its input unresolved,
  so this is the most a run can resolve, whatever the evidence.
- **Top and its interval:** the most common answer's share of the trial's
  calls, with its 95% Wilson interval. Four of five is anywhere from 38% to
  96%; fifteen of fifteen is at least 80%.
- **p against the baseline:** Fisher's exact test of the trial's answers
  against the baseline's most common one, then Holm's adjustment across the
  input's trials. A small value says the trial moved the answer.
- **At most this share differ:** for a repeat, a presentation, a placement
  or a sham, the trials that should hold the answer, the upper end of the 95%
  interval of answers unlike the baseline's. "Held" with fifteen calls means
  at most 20% differ; with five, at most 43%.
- **Drawn again:** each run's verdict, read by the same fixed rules after
  every trial's calls are drawn again, with replacement, as many as it had.
  The draws are seeded by the frame's hash, so the same records always give
  the same shares, and `--resamples` sets how many there are. A run whose
  trials were each asked once has nothing to draw again, and says so.

---

### A verdict that rests on one call

Rung 19 is carried in all three of its runs. In the first, one of the five
ablation calls answered `waist` where the others said `adapter`, and four of
five is exactly the `agree` it needs:

```text
$ uv run gadfly stats examples/19-router-waist.json \
    examples/runs/19-router-waist/1.jsonl \
    examples/runs/19-router-waist/2.jsonl \
    examples/runs/19-router-waist/3.jsonl
frame: router-waist (e881f5975ceb46ed93fb272e1bca4d8bc365ad08bac7b561cc53c238fa91562b)
records: 3 runs, 90 calls
agreement: 99% of calls give their trial's most common answer in their own run
power: at 99% agreement, a trial reaches a level of 4 of 5 100% of the time, and all 6 trials the plan asks of an input 99%
input review
  baseline       15 calls  waist 15  top 100% (80%-100%)
  repeat         15 calls  waist 15  top 100% (80%-100%), at most 20% differ from waist
  ablation       15 calls  adapter 14, waist 1  top 93% (70%-99%), p 2.1e-07 against waist (Holm 8.3e-07)
  sham-1         15 calls  waist 15  top 100% (80%-100%), at most 20% differ from waist
  presentation   15 calls  waist 15  top 100% (80%-100%), at most 20% differ from waist
  control        15 calls  adapter 15  top 100% (80%-100%), p 1.3e-08 against waist (Holm 6.4e-08)
verdicts, each run's calls drawn again 200 times
  run 1, review  carried; drawn again carried 70%, unresolved 30%, cooled under 1%
  run 2, review  carried; drawn again carried 100%
  run 3, review  carried; drawn again carried 100%
```

Drawn again, the first run's verdict is carried seven times in ten and
otherwise mostly unresolved, while the other two runs are carried every time. The
three verdicts agree; the first rests on a call or two.

---

### Power before a run

`gadfly plan --agreement` says, before a call, how often the quorum can
resolve a frame for a reader that gives its usual answer that often. Take it
from an earlier run's `stats`, or guess it:

```text
$ uv run gadfly plan examples/19-router-waist.json \
    --agreement 0.88
router-waist (e881f5975ceb46ed93fb272e1bca4d8bc365ad08bac7b561cc53c238fa91562b): 30 calls
power: at 88% agreement, a trial reaches a level of 4 of 5 89% of the time, and all 6 trials the plan asks of an input 49%
  baseline     body 46ae3eca5bb5  nothing
  repeat       body 46ae3eca5bb5  nothing, asked again
  ablation     body 41586bad7f3b  cuts gadfly
  sham-1       body e4bb2857f327  cuts records
  presentation body 214397bd1128  renames codex-unified-model-router to unified-model-router
  control      body 3cb1c7c68465  cuts summary, provider, gadfly
```

At 88% agreement, the choice of `quorum` and `agree` decides most of what a
run can say. A larger quorum resolves more inputs, and a lower `agree` admits
more levels that are chance:

| `quorum` and `agree` | One trial reaches a level | All six trials do |
| --- | --- | --- |
| 5 and 4 | 89% | 49% |
| 7 and 5 | 96% | 77% |
| 9 and 6 | 98% | 91% |
| 9 and 7 | 92% | 59% |

---

### Pooling calls across frames

Two frames that send the same reader the same prompt make the same call, so
`--pool FRAME RECORDS` adds the other frame's calls to the counts. Gadfly
pools a call only when the battery line, the instruction and the labels are
the same and its prompt's hash is one of this frame's, and refuses a frame
that asks another reader.

A call keeps its own input, and one whose prompt two inputs share, under an
input named otherwise, is left out. Pooled calls are counted, never judged,
since their frame's plan is not this one's.

---

### From Python

The same numbers come from `midwife.stats`, read from records a caller keeps:

```python
from midwife import stats

compared = stats.compare(frame, runs)
shares = stats.stability(frame, runs, resamples=200)
power = stats.power(frame, stats.agreement(runs))
```

`compare` gives each input's trials, `stability` each run's share of each
category, and `power` the chance of reaching a level. `pooled(frame, others)`
returns other frames' calls on the same prompts, to pass to `compare`.
