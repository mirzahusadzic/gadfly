# Your first frame

Gadfly asks one question about one decision: **does the decision rest on the
evidence you think it rests on?** It cannot look inside the reader, so it
changes the evidence in fixed ways, asks again, and compares what comes back.

This page climbs one real experiment a step at a time. A dependency bot opens a
pull request that bumps a made-up library, quill, from 2.4.1 to 3.0.0. Our code
calls `quill.retry_after()`, and quill 3.0.0's changelog removes it.

The reviewer is Gemma 4 26B, served on this machine by eGemma. Does its
decision to hold the upgrade rest on that changelog line?

Each step below is a frame in `examples/` (`rung1.json` to `rung6.json`, each
the one before with one more trial), read in five fresh runs by Gemma. The
predictions were written in `examples/PREDICTIONS.md` before the first call, and
every record is kept in `examples/runs/`. So every output on this page is read
back from those records, and reading it needs no model.

---

### 1. The evidence and the question

The frame is the whole experiment, written down before any call. Here it is in
words, each span linked to its line in the file:

<!-- frame examples/upgrade.json -->

**The relation**

- **Relation:** the decision to hold the upgrade rests on the changelog line that removes retry_after()
- **Locus:** the evidence a reviewer has on the pull request: our code, the library's changelog, the CI result
- **Role:** the reviewer of dependency upgrades
- **Grain:** one changelog line
- **Purpose:** merge an upgrade only when our code needs no change for it
- **Trajectory:** pull request, evidence, the reviewer's decision, the merge button
- **Crossing:** the decision posted on the pull request
- **Promise:** the reviewer holds the upgrade while the changelog removes a function our code calls; without that line they merge or say unclear, never hold for another reason
- **Baseline:** the pull request's evidence as it stands; nothing changed

**The evidence**, the anchor marked `*`:

| Span | Kind | Text |
|---|---|---|
| [`use`](../examples/upgrade.json#L14) | code | src/billing/retry.py calls quill.retry_after(response) to wait before retrying a 429 response. |
| [`get`](../examples/upgrade.json#L15) | code | src/billing/client.py calls quill.get(url, timeout=10) for every request. |
| [`removed`](../examples/upgrade.json#L16) `*` | changelog | quill 3.0.0 changelog, Breaking: retry_after() is removed; use Response.backoff() instead. |
| [`http3`](../examples/upgrade.json#L17) | changelog | quill 3.0.0 changelog, Added: HTTP/3 support. |
| [`leak`](../examples/upgrade.json#L18) | changelog | quill 3.0.0 changelog, Fixed: a memory leak in the connection pool. |
| [`typos`](../examples/upgrade.json#L19) | changelog | quill 3.0.0 changelog, Docs: corrected typos in the README. |
| [`ci`](../examples/upgrade.json#L20) | ci | CI on this pull request: all 214 tests passed; no test exercises the retry path. |

**The question**

- **Asked, `pr`:** Dependabot opened pull request #212: bump quill from 2.4.1 to 3.0.0 in requirements.txt. Can it be merged as is?
- **Answers:** `merge`, `hold` or `unclear`
- **Instruction:** You review dependency upgrade pull requests for this repository. Use only the evidence given. Answer merge if the upgrade can be merged without changing our code, hold if our code must change before it can be merged, unclear if the evidence does not decide.

**The trials**, each asked 5 times, 40 calls in all:

- **`baseline`:** asks the evidence as it is
- **`repeat`:** asks the same again
- **`ablation`:** cuts `removed`
- **`sham-1`:** cuts `leak`
- **`sham-2`:** cuts `typos`
- **`presentation`:** renames `backoff` to `pause`, `quill` to `heron`, `retry_after` to `wait_hint`
- **`bypass`:** cuts `use`
- **`control`:** cuts `removed`, `use`

**The reading**

- **Without the anchor:** `merge` or `unclear` may come back
- **A level:** 4 of 5 answers alike
- **Carriage:** `all-checks`, so a category waits for the checks it needs
- **Materialized:** the answer is the form the recipient receives
- **Battery:** `egemma`

[The frame as written ↗](../examples/upgrade.json)
<!-- end frame -->

- **The evidence** (`body.spans`) is one sentence per span. Its `kind` groups
  spans for the sham trial (section 4).
- **The anchor** (`anchors`), marked `*`, is the span the decision is supposed
  to rest on: the changelog line that removes `retry_after()`.
- **The question** (`inputs`) is what the reader is asked, and the answers and
  the instruction (`observe`) say what each answer means. Define every label in
  the instruction. A reader left to guess what a label means answers a
  different question.
- **The relation** and the words under it (`relation`, `grain`, `promise` and
  the rest) say what is being claimed, at which unit, and for whom. They are
  hashed with the rest, so a frame cannot be reworded after its runs: records
  from another wording are refused.

What Gemma receives per call is the instruction, then the spans one per line, a
line `---`, and the question. It must answer with one label. Each trial is asked
`quorum` times (5) and needs `agree` (4) answers alike; that answer is the
trial's **level**.

---

### 2. Cut the line: ablation

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
$ uv run python examples/read.py \
    examples/rung1.json --verdict 1
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

---

### 3. Ask again: repeat

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

---

### 4. Cut something harmless: shams

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

---

### 5. Rename: presentation

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

---

### 6. Cut the connection: bypass

The line matters only because our code calls the function it removes. The
bypass cuts our call to `retry_after()` and keeps the line. A reader that reacts
to the word "Breaking" would still hold, a hidden fallback; one that follows the
connection would merge or say unclear.

```text
$ uv run python examples/read.py \
    examples/rung5.json --verdict 1
pr: carried
  levels: baseline hold, repeat hold, ablation merge, sham-1 hold, sham-2 hold, presentation hold, bypass merge
  evidence: ablation moved it hold -> merge; held under presentation, 2 shams
  evidence: bypass moved it hold -> merge: no hidden fallback
```

The prediction was a fallback, at about 55%. It was wrong: Gemma merged on
every call. Every carriage check has passed, so the finding is **carried**.

---

### 7. Can it move at all: the control

Carried does not need a control; cooled does. A reader that never moves would
make every relation look cooled, so the control removes what any reader needs
(here the line and our call together) to show that this one can move.

```text
$ uv run python examples/read.py \
    examples/rung6.json --verdict 1
pr: carried
  levels: baseline hold, repeat hold, ablation merge, sham-1 hold, sham-2 hold, presentation hold, bypass merge, control merge
  evidence: ablation moved it hold -> merge; held under presentation, 2 shams
  evidence: bypass moved it hold -> merge: no hidden fallback
  evidence: the control moved it hold -> merge
```

The next step of the ladder, [Cooled](examples/cooled.md), is where a control
decides a verdict.

---

### 8. What "carried" says here

On this evidence, at this grain, for this model at this revision, the decision
to hold rests on the changelog line, through our call to the function it
removes: cut the line or the call and the decision changes; cut a neighbour or
rename the names and it does not. It does not say that Gemma reviews upgrades
well, or that it would on other evidence.

---

### 9. Read it fresh, and write your own

With eGemma on this machine and its key in `EGEMMA_API_KEY` or
`EGEMMA_API_KEY_FILE`, these commands check the frame, plan it, run it fresh
and read the verdict:

```bash
uv run gadfly check-frame examples/upgrade.json
uv run gadfly plan examples/upgrade.json
uv run gadfly run examples/upgrade.json \
  --battery midwife.batteries.egemma:EGemma \
  --calls 40 --out my-run.jsonl
uv run gadfly report examples/upgrade.json my-run.jsonl
```

`check-frame` checks the frame's shape and then the parser, and `plan` shows
the trials and the call count; neither makes a call.

To test your own decision, copy `upgrade.json`, replace the situation, body,
anchor, question and labels, and run `check-frame` until it is accepted. Then
write down what you expect each trial to give, before the first call.
[Write a frame](write-a-frame.md) has every key, and what each refusal means.

---

### Next

The [examples](examples/index.md) climb on from here, one capability a step,
starting with Cooled, where a control decides the verdict.
