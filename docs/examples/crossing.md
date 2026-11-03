# Crossing: through what the maker writes

> [!IMPORTANT]
> **This step**
>
> - **Teaches:** a [crossing](../crossings.md), where a maker
>   writes what the reader reads, so the verdict says whether the evidence
>   survived the writing; the same evidence carried through one artefact
>   and cooled through another.
> - **Frames:** `20-incident-cause.json` and `20b-incident-status.json`:
>   one incident's six lines, written up as a cause section or as a status
>   update, then read for a rollback.
> - **After:** [Each anchor alone](each-anchor.md).

An incident commander rarely reads the signals themselves: someone writes
them up first. Both frames hold the same lines, question and reader, and
differ only in what the maker is told to write. Muse Spark 1.3 Contributor
writes and reads through the unified model router, each at reasoning `low`,
and the incident is invented.

---

### 20: the cause section

The frame, as Gadfly plans it; `made into` is the maker's instruction, and
the maker sees the lines alone, never the question:

```text
$ uv run python examples/read.py \
    examples/20-incident-cause.json --frame
incident-cause: 1 input x 6 trials x 5 calls = 30 calls, 4 of 5 to agree
relation: the rollback rests on the pool change in deploy 42, through the cause the report states
grain: one signal or one change
evidence, the anchors marked *:
    latency   signal  p99 latency of ledger-api rose from 120 ms to 900 ms and stayed there.
  * pool      change  Deploy 42, the only change before the rise, cut ledger-api's database connection pool from 50 to 5.
    errors    signal  The error rate held at 0.1%.
    cpu       signal  CPU use on the ledger-api hosts held near 40%.
    database  signal  The database reported normal query times throughout, with most of its 200 connections idle.
    logs      change  Deploy 41, two days earlier, changed only the format of ledger-api's logs.
asked:
  rollback  Should deploy 42 be rolled back now?
made into: You write the cause section of an incident report from the signals and changes given. In two or three sentences, say what most likely caused what the signals show, using only what is given. Do not recommend an action.
labels: rollback, investigate, keep
trials:
  baseline      asks the evidence as it is
  repeat        asks it again
  ablation      cuts pool
  sham-1        cuts logs
  presentation  renames deploy -> release
  control       cuts latency, pool
allowed: ablation -> investigate, keep
carriage: listed, so a category is named with its open checks beside it
```

> [!NOTE]
> **Predicted before the first call**
>
> Rollback at the baseline, investigate without the pool line, keep under
> the control. Carried in every run, with no hidden fallback open beside
> it.

Muse answered like this over three runs:

```text
$ uv run python examples/read.py \
    examples/20-incident-cause.json
incident-cause: 3 kept runs, made and read by meta/muse-spark-1.3-contributor
trial         rollback
baseline      rollback 15
repeat        rollback 15
ablation      investigate 15
sham-1        rollback 15
presentation  rollback 15
control       keep 15
run 1: carried
run 2: carried
run 3: carried
```

What the maker wrote in the first run, from the first call of each trial,
and what the reader answered from it:

```text
$ uv run python examples/read.py \
    examples/20-incident-cause.json --made 1
baseline, read as rollback
  The sustained rise in ledger-api p99 latency from 120 ms to 900 ms was
  most likely caused by Deploy 42, the only change before the rise,
  which cut ledger-api's database connection pool from 50 to 5. This is
  consistent with requests waiting for a connection while CPU use held
  near 40%, the error rate held at 0.1%, and the database reported
  normal query times with most of its 200 connections idle.
repeat, read as rollback
  Deploy 42 reduced ledger-api's database connection pool from 50 to 5
  immediately before p99 latency rose from 120 ms to 900 ms and stayed
  there. CPU use remaining near 40%, error rate holding at 0.1%, and the
  database reporting normal query times with most of its 200 connections
  idle indicates the delay was waiting for the reduced pool in
  ledger-api.
ablation, read as investigate
  The sustained rise in p99 latency from 120 ms to 900 ms is not
  explained by host overload, application errors, or database
  performance, since CPU held near 40%, error rate held at 0.1%, and
  database query times were normal with most of its 200 connections
  idle. Deploy 41 is also an unlikely cause because it occurred two days
  earlier and changed only the format of ledger-api's logs.
sham-1, read as rollback
  Deploy 42, the only change before the rise, cut ledger-api's database
  connection pool from 50 to 5, after which p99 latency rose from 120 ms
  to 900 ms and stayed there. The unchanged 0.1% error rate, steady 40%
  CPU use on ledger-api hosts, and normal database query times with most
  of its 200 connections idle show the delay was waiting for the reduced
  pool rather than slow queries or saturated hosts.
presentation, read as rollback
  The sustained rise in ledger-api p99 latency from 120 ms to 900 ms was
  most likely caused by Release 42 cutting ledger-api's database
  connection pool from 50 to 5. With far fewer connections to wait on,
  requests queued longer, which is consistent with the error rate
  holding at 0.1%, CPU use holding near 40%, and the database reporting
  normal query times with most of its 200 connections idle.
control, read as keep
  The signals show sustained normal operation with error rate held at
  0.1%, ledger-api CPU use near 40%, and normal database query times
  with most of its 200 connections idle. Deploy 41 occurred two days
  earlier and changed only the format of ledger-api's logs. No provided
  change accounts for a disruption in the reported signals.
```

Without the pool line, nothing given names a change in deploy 42, and the
cause section says that nothing given explains the rise; the commander
investigates. Renamed to a release, the section still names the change, and
the control leaves nothing to explain.

The first run's verdict is carried, with two checks open beside it, as
`carriage: listed` names them:

```text
$ uv run python examples/read.py \
    examples/20-incident-cause.json --verdict 1
rollback: carried
  levels: baseline rollback, repeat rollback, ablation investigate, sham-1 rollback, presentation rollback, control keep
  evidence: ablation moved it rollback -> investigate; held under presentation, 1 sham
  evidence: the control moved it rollback -> keep
  open: no hidden fallback (no bypass trial was declared)
  open: materialization (the frame does not say the observation is the form the recipient receives)
```

No bypass was declared, and the frame does not declare `materialized`: the
commander receives the cause section, not the reader's label.

---

### 20b: the status update

The same frame, but the maker is told to write "the customer-facing status
update for an incident from the signals and changes given. In one or two
sentences of plain words, say what customers experienced. Do not recommend an
action."

> [!NOTE]
> **Predicted before the first call**
>
> Investigate everywhere but under the control, which reads keep. Cooled in
> every run, at medium confidence: an update that names "a recent change"
> could carry enough for a rollback.

Muse answered like this over three runs:

```text
$ uv run python examples/read.py \
    examples/20b-incident-status.json
incident-status: 3 kept runs, made and read by meta/muse-spark-1.3-contributor
trial         rollback
baseline      investigate 15
repeat        investigate 15
ablation      investigate 15
sham-1        investigate 15
presentation  investigate 15
control       keep 14, investigate 1
run 1: cooled
run 2: cooled
run 3: cooled
```

The status updates of the first run:

```text
$ uv run python examples/read.py \
    examples/20b-incident-status.json --made 1
baseline, read as investigate
  Customers experienced slow responses when using the ledger API. The
  slowest requests took about 900 milliseconds instead of the usual 120
  milliseconds.
repeat, read as investigate
  Customers experienced slow responses from the ledger service, with
  delays growing from about a tenth of a second to nearly a second and
  staying high.
ablation, read as investigate
  A small share of requests were taking much longer than usual to
  complete, but they still went through successfully.
sham-1, read as investigate
  Customers experienced slow responses, with wait times rising to around
  900 ms from the usual 120 ms.
presentation, read as investigate
  Customers experienced slow responses from ledger-api, with some
  requests taking much longer than usual to complete.
control, read as keep
  Customers experienced normal service with requests completing as
  expected.
```

Each update says what customers saw, and none says what changed, so the
commander investigates with the pool line or without it. The control still
moves the answer to keep, so the reader can tell; what the anchor said was
lost at the crossing.

---

### How firm each reading is

Over the three runs, `gadfly stats` says how much each verdict rests on.
One control call of 20b's third run answered `investigate`:

```text
$ uv run gadfly stats examples/20b-incident-status.json \
    examples/runs/20b-incident-status/1.jsonl \
    examples/runs/20b-incident-status/2.jsonl \
    examples/runs/20b-incident-status/3.jsonl
frame: incident-status (20f39215d11cccf3c12fe64fc07f7430cd17c89f286a9ef416fc68703edc40fe)
records: 3 runs, 90 calls
agreement: 99% of calls give their trial's most common answer in their own run
power: at 99% agreement, a trial reaches a level of 4 of 5 100% of the time, and all 6 trials the plan asks of an input 99%
input rollback
  baseline       15 calls  investigate 15  top 100% (80%-100%)
  repeat         15 calls  investigate 15  top 100% (80%-100%), at most 20% differ from investigate
  ablation       15 calls  investigate 15  top 100% (80%-100%), p 1 against investigate (Holm 1)
  sham-1         15 calls  investigate 15  top 100% (80%-100%), at most 20% differ from investigate
  presentation   15 calls  investigate 15  top 100% (80%-100%), at most 20% differ from investigate
  control        15 calls  keep 14, investigate 1  top 93% (70%-99%), p 2.1e-07 against investigate (Holm 1e-06)
verdicts, each run's calls drawn again 200 times
  run 1, rollback  cooled; drawn again cooled 100%
  run 2, rollback  cooled; drawn again cooled 100%
  run 3, rollback  cooled; drawn again cooled 71%, unresolved 29%
```

The third run's verdict is cooled in seven draws of ten and otherwise
unresolved: the three runs agree, and the third rests on one call. 20's
three runs are carried in every draw.

---

### Watch a run

The kept runs above, played one trial at a time: on the left what Muse
was given, with what the trial hid or changed marked, and what it wrote
from it; on the right the answers read from what it wrote, and the checks
filling in until the verdict. On GitHub the view does not run, and the
transcripts above read the same runs.

<!-- watch 20-incident-cause 20b-incident-status -->

---

### What to take from it

- **The maker is inside the reading:** the same evidence and the same
  reader are carried through a cause section and cooled through a status
  update. A decision made from a report rests on its evidence only as far
  as the report carries it.
- **Cooled is not the reader's failure here:** the control moved, and the
  reader answered every update as told. The pool line never reached it.
- **Each call is two:** 180 kept calls made 360 calls to Muse, the maker's
  and the reader's, and each kept call spent 689 to 2,118 output tokens.

---

### Run it live

The kept runs were made and read by Muse through unified-model-router, with
the `crossing` battery, and a live run asks it the same way, with the router
running on this machine
([Batteries](../batteries.md#a-maker-before-the-reader)). `gadfly plan`
counts a run's calls first, and costs nothing:

```text
$ uv run gadfly plan examples/20-incident-cause.json
incident-cause (282805e302be793a78b7addbe303fd178c542d7e9584b54141d44196c6cf20ab): 30 calls
  baseline     body e6e21468ac74  nothing
  repeat       body e6e21468ac74  nothing, asked again
  ablation     body 9e49e1de2d55  cuts pool
  sham-1       body 691b1a0e73f7  cuts logs
  presentation body 1b7639c42a0c  renames deploy to release
  control      body fa671a8f00db  cuts latency, pool
```

These commands ask it once, fresh, beside the kept runs and never into them,
and read the verdict; each call both makes and reads, and Muse thinks before
it answers, so each is given up to 4,000 output tokens:

```bash
uv run gadfly run examples/20-incident-cause.json \
  --battery midwife.batteries.crossing:Crossing \
  --calls 30 --output-tokens 4000 --out my-run.jsonl
uv run gadfly report examples/20-incident-cause.json my-run.jsonl
```

`examples/20b-incident-status.json` runs the same way, in 30 calls.

---

### Try next

Have 20's maker write for an executive in one sentence, and see
whether the cause survives; or take the first run's cause section as a span
of its own, name its SHA-256 as its `source`, and read it alone.
