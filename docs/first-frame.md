# Your first frame

Gadfly asks one question about one decision: **does the decision rest on the
evidence you think it rests on?** It cannot look inside the reader, so it
changes the evidence in fixed ways, asks again, and compares what comes back.

This page climbs one real experiment a step at a time. A dependency bot opens a
pull request that bumps a made-up library, quill, from 2.4.1 to 3.0.0. Our code
calls `quill.retry_after()`, and quill 3.0.0's changelog removes it. The reviewer
is Gemma 4 26B, served on this machine by eGemma. Does its decision to hold the
upgrade rest on that changelog line?

Each step below is a frame in `examples/` (`rung1.json` to `rung6.json`, each
the one before with one more trial), read in five fresh runs by Gemma. The
predictions were written in `examples/PREDICTIONS.md` before the first call, and
every record is kept in `examples/runs/`. So every output on this page is read
back from those records, and reading it needs no model.

## 1. The evidence and the question

The frame is the whole experiment, written down before any call:

```json
--8<-- "examples/upgrade.json"
```

- **`body.spans`** is the evidence, one sentence per span. The `kind` groups
  spans for the sham trial (section 4).
- **`anchors`** names the span the decision is supposed to rest on: the changelog
  line that removes `retry_after()`.
- **`inputs`** is the question. **`observe`** is what the reader may answer and
  what each answer means. Define every label in the instruction. A reader left to
  guess what a label means answers a different question.
- **`relation`**, **`grain`**, **`promise`** and the rest say what is being
  claimed, at which unit, and for whom. They are hashed with the rest, so a
  frame cannot be reworded after its runs: records from another wording are
  refused.

What Gemma receives per call is the instruction, then the spans one per line, a
line `---`, and the question. It must answer with one label. Each trial is asked
`quorum` times (5) and needs `agree` (4) answers alike; that answer is the
trial's **level**.

## 2. Cut the line: ablation

Rung 1 declares only the ablation, which removes the anchor.

```text
$ uv run python examples/read.py examples/rung1.json
quill-upgrade-rung-1: 5 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial     pr
baseline  hold 25
ablation  merge 25
run 1: unresolved
run 2: unresolved
run 3: unresolved
run 4: unresolved
run 5: unresolved
```

Every call held while the line was there, and merged once it was gone. That
move is necessary but not enough to call the line load-bearing. The verdict
says so, and lists what it still needs:

```text
$ uv run python examples/read.py examples/rung1.json --verdict 1
pr: unresolved
  levels: baseline hold, ablation merge
  evidence: ablation moved it hold -> merge
  evidence: not carried while 3 carriage checks are open
  open: no hidden fallback: no bypass trial was declared
  open: presentation invariance: no presentation trial was declared
  open: specificity: no sham trial was declared
```

Each `open:` line is a check no trial has made yet. Under the default
`carriage: all-checks`, a finding is not carried while one is open.

## 3. Ask again: repeat

A level is worth comparing only if it is stable. Repeat asks the unchanged
evidence again; if it gives another level, the verdict is unresolved before
anything else is read.

```text
$ uv run python examples/read.py examples/rung2.json
quill-upgrade-rung-2: 5 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial     pr
baseline  hold 25
repeat    hold 25
ablation  merge 25
run 1: unresolved
run 2: unresolved
run 3: unresolved
run 4: unresolved
run 5: unresolved
```

Gemma gave the same answer on all 25 calls. On clear evidence this reader is
close to deterministic; [Quorum](examples/quorum.md) shows where it is not.

## 4. Cut something harmless: shams

Perhaps any cut moves the reader. A sham removes a span of the anchor's kind
instead (here another changelog line, the closest in length), which should
change nothing. Two shams are drawn.

```text
$ uv run python examples/read.py examples/rung3.json
quill-upgrade-rung-3: 5 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial     pr
baseline  hold 25
repeat    hold 25
ablation  merge 25
sham-1    hold 25
sham-2    hold 25
run 1: unresolved
run 2: unresolved
run 3: unresolved
run 4: unresolved
run 5: unresolved
```

Both held, so the move is specific to the line: two checks remain open.

## 5. Rename: presentation

A reader might react to names rather than meaning. Presentation renames
`quill` to `heron`, `retry_after` to `wait_hint` and `backoff` to `pause`, in
one pass, in the evidence and the question alike.

```text
$ uv run python examples/read.py examples/rung4.json
quill-upgrade-rung-4: 5 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         pr
baseline      hold 25
repeat        hold 25
ablation      merge 25
sham-1        hold 25
sham-2        hold 25
presentation  hold 25
run 1: unresolved
run 2: unresolved
run 3: unresolved
run 4: unresolved
run 5: unresolved
```

It held. One check is left: whether something else would give the same answer
without the line's connection to our code.

## 6. Cut the connection: bypass

The line matters only because our code calls the function it removes. The
bypass cuts our call to `retry_after()` and keeps the line. A reader that reacts
to the word "Breaking" would still hold, a hidden fallback; one that follows the
connection would merge or say unclear.

```text
$ uv run python examples/read.py examples/rung5.json --verdict 1
pr: carried
  levels: baseline hold, repeat hold, ablation merge, sham-1 hold, sham-2 hold, presentation hold, bypass merge
  evidence: ablation moved it hold -> merge; held under presentation, 2 shams
  evidence: bypass moved it hold -> merge: no hidden fallback
```

The prediction was a fallback, at about 55%. It was wrong: Gemma merged on
every call. Every carriage check has passed, so the finding is **carried**.

## 7. Can it move at all: the control

Carried does not need a control; cooled does. A reader that never moves would
make every relation look cooled, so the control removes what any reader needs
(here the line and our call together) to show that this one can move.

```text
$ uv run python examples/read.py examples/rung6.json --verdict 1
pr: carried
  levels: baseline hold, repeat hold, ablation merge, sham-1 hold, sham-2 hold, presentation hold, bypass merge, control merge
  evidence: ablation moved it hold -> merge; held under presentation, 2 shams
  evidence: bypass moved it hold -> merge: no hidden fallback
  evidence: the control moved it hold -> merge
```

The next step of the ladder, [Cooled](examples/cooled.md), is where a control
decides a verdict.

## 8. What "carried" says here

On this evidence, at this grain, for this model at this revision, the decision
to hold rests on the changelog line, through our call to the function it
removes: cut the line or the call and the decision changes; cut a neighbour or
rename the names and it does not. It does not say that Gemma reviews upgrades
well, or that it would on other evidence.

## 9. Read it fresh, and write your own

With eGemma on this machine (its key in `EGEMMA_API_KEY` or
`EGEMMA_API_KEY_FILE`):

```bash
uv run gadfly check-frame examples/upgrade.json   # the shape, then the parser; no call
uv run gadfly plan examples/upgrade.json          # the trials and the call count; no call
uv run gadfly run examples/upgrade.json --battery gadfly.batteries.egemma:EGemma \
    --calls 40 --out my-run.jsonl
uv run gadfly report examples/upgrade.json my-run.jsonl
```

To test your own decision, copy `upgrade.json`, replace the situation, body,
anchor, question and labels, and run `check-frame` until it is accepted. Then
write down what you expect each trial to give, before the first call.

## Common refusals

| Message | Fix |
|---|---|
| `unknown keys: [...]` | every top-level key is checked; remove the typo rather than hoping it is ignored |
| `presentation renames nothing X reads` | map a word present in the body or every input |
| `bypass removes exactly the anchors` | choose the separate connection whose removal should expose the opening |
| `cumulative adds no span to the anchors` | cumulative must remove at least one additional span |
| `two inputs share an id` | input ids are record keys and must be unique |
| `allowed 'lower' needs observe.order` | declare the full label order before using a direction |
| `the frame does not say its baseline` | pin $B_0$; do not leave the comparison implicit |
| `the frame asks for the X battery, not Y` | make `battery.kind` and the battery class's `name` the same string |
| `carriage is all-checks or listed` | the policy is one of the two words, or left out for `all-checks` |
| `scopeCheck checks an outsideScope exclusion` | record the owner's check only beside the exclusion it checks |
| `placement leaves the order as it is` | move the span after one it does not already follow |

`uv run gadfly check-frame my-frame.json` shows these before any call, with the
schema's findings first when `jsonschema` is installed.

Next: the [examples](examples/index.md) climb on from here, one capability a
step, starting with [Cooled](examples/cooled.md). [Write a frame](write-a-frame.md)
is the complete field reference.

