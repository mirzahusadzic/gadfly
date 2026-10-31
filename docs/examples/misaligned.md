# Misaligned: moving the wrong way

!!! abstract "This step"
    - **Teaches:** `allowed`,
      [coupled but misaligned](../reading-a-verdict.md#the-rules-in-order),
      several inputs in one frame, and the
      [placement](../interventions.md#placement-is-one-move) trial.
    - **Frames:** `10a-incident-fast.json` and `10b-incident-slow.json`: one
      incident, four tasks, one route to the cause in each.
    - **After:** [Quorum](quorum.md).

Not every decision is a diagnosis. These frames hold one incident (API latency
rose from 180 ms to 2.4 s, with a deploy and a database failover in the same
minute) and ask four tasks of it: debugging (which component caused it),
implementing the fix, optimizing, and building an alert. Two routes lead to the
database:

- the **fast route**, one experiment: the API was rolled back and the latency
  stayed, which rules the API out;
- the **slow route**, reading the metrics: the new primary's cache hit rate fell
  from 99% to 61%, and slow queries rose from 3 to 410 a minute.

10a holds only the fast route, and 10b only the slow one.

## The frame

```text
$ uv run python examples/read.py examples/10a-incident-fast.json --frame
incident-fast: 4 inputs x 8 trials x 5 calls = 160 calls, 4 of 5 to agree
relation: the answer 'database' rests on the rollback that left the latency as it was
grain: one test
evidence, the anchors marked *:
    deploy    event    14:02 the deploy of api v2.31 finished.
    failover  event    14:02 the primary database failed over to its replica.
    latency   symptom  14:03 API p99 latency rose from 180 ms to 2.4 s.
    requests  metric   14:06 the API's request rate stayed near 1,200 a second.
    disk      metric   14:07 the database volume was 48% full.
    queue     metric   14:08 the message queue's backlog stayed under 50.
    cron      metric   14:09 the scheduler ran every job on time.
    health    check    14:12 the load balancer's health checks all passed.
    dns       check    14:14 DNS for the API resolved correctly from three regions.
    cdn       check    14:16 the CDN's error rate was normal.
  * rollback  check    14:20 api was rolled back to v2.30; p99 latency stayed at 2.4 s.
asked:
  debug     Debugging: which component caused the latency rise?
  fix       Implementing the fix: the change goes into one component. Which one?
  optimize  Optimizing: which component should we work on first to bring p99 back under 200 ms?
  alert     Building: which component should get a new alert so this is caught sooner next time?
labels: api, database, unclear
trials:
  baseline      asks the evidence as it is
  repeat        asks it again
  ablation      cuts rollback
  sham-1        cuts dns
  sham-2        cuts health
  presentation  renames v2.30 -> v7.3, v2.31 -> v7.4
  placement     moves rollback after latency
  control       cuts deploy, failover
allowed: ablation -> unclear
```

Three things are new.

- **Four inputs.** Each task is an input with its own finding, read from the
  same trials. They are four cases of one promise, not four repetitions.
- **`allowed`.** The promise says that without the evidence that rules the API
  out, the engineer says unclear. `allowed.ablation` lists the answers an
  ablation may move to, here only unclear. A move anywhere else still shows the
  anchor matters, but it matters the wrong way.
- **Placement** moves the rollback up the timeline, right after the symptom,
  and changes no word. A reader that weighs a line by where it sits would move.

10b is the same timeline with the two metric lines in place of the rollback,
and those two lines are its anchors.

!!! note "Predicted before the first call"
    Database on all four tasks at baseline (10a medium-high, 10b high). The
    ablation: unclear, or api for at least one task, blaming the deploy because
    it is recent and salient (about 50%), which would read misaligned there.
    Placement: database.

## What Gemma answered

```text
$ uv run python examples/read.py examples/10a-incident-fast.json
incident-fast: 3 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         debug                          fix                 optimize                       alert
baseline      unclear 10, database 4, api 1  database 15         database 12, api 2, unclear 1  api 8, database 7
repeat        unclear 11, database 2, api 2  database 15         database 11, api 2, unclear 2  api 8, database 7
ablation      api 9, unclear 6               api 9, database 6   api 15                         api 12, database 3
sham-1        unclear 7, database 6, api 2   database 15         database 14, api 1             api 10, database 5
sham-2        unclear 11, database 3, api 1  database 15         database 6, api 5, unclear 4   api 14, database 1
presentation  unclear 10, api 4, database 1  database 15         database 12, unclear 2, api 1  api 10, database 4, unclear 1
placement     unclear 12, database 2, api 1  database 14, api 1  database 14, unclear 1         database 9, unclear 3, api 3
control       unclear 15                     api 10, unclear 5   api 13, unclear 2              api 15
run 1: unresolved (debug unresolved, fix unresolved, optimize unresolved, alert unresolved)
run 2: coupled but misaligned (debug unresolved, fix cooled, optimize coupled but misaligned, alert unresolved)
run 3: coupled but misaligned (debug unresolved, fix coupled but misaligned, optimize unresolved, alert unresolved)
```

```text
$ uv run python examples/read.py examples/10b-incident-slow.json
incident-slow: 3 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         debug              fix                 optimize     alert
baseline      database 15        database 15         database 15  database 15
repeat        database 15        database 15         database 15  database 15
ablation      api 13, unclear 2  api 10, database 5  api 15       api 15
sham-1        database 15        database 15         database 15  database 15
sham-2        database 15        database 15         database 15  database 15
presentation  database 15        database 15         database 15  database 15
control       database 15        database 15         database 15  database 15
run 1: coupled but misaligned (debug coupled but misaligned, fix unresolved, optimize coupled but misaligned, alert coupled but misaligned)
run 2: coupled but misaligned (debug coupled but misaligned, fix coupled but misaligned, optimize coupled but misaligned, alert coupled but misaligned)
run 3: coupled but misaligned (debug unresolved, fix coupled but misaligned, optimize coupled but misaligned, alert coupled but misaligned)
```

With one route each, the baselines already differ. The metrics decide every
task on every call. The rollback, an elimination (it was not the API), decides
where the fix goes on every call, and the cause itself mostly not: unclear on
ten calls of fifteen. Both routes are valid and lead an engineer to the same
answer; to this reader the elimination is enough to act on, not enough to
explain. The 10a prediction was wrong for debug and for the alert.

## What Gadfly read

```text
$ uv run python examples/read.py examples/10b-incident-slow.json --verdict 2 --input debug
debug: coupled but misaligned
  levels: baseline database, repeat database, ablation api, sham-1 database, sham-2 database, presentation database, control database
  evidence: ablation moved it database -> api, which the frame does not allow
  open: no hidden fallback: no bypass trial was declared
```

Cut the only route and the answers do not go to unclear: they go to api, the
service named in the symptom. That is **coupled but misaligned**. The ablation
moved, so the anchors do influence the decision, but to an answer the frame
does not allow. The rule is read before cooled and carried, and no later check
can clear it. 10b reads misaligned on every task whose ablation agreed, in every
run. Most of 10a's task-runs are unresolved: with only the elimination, the
debug and alert baselines split, and a trial without a level comes first. A
run's overall reading is misaligned when any input is, so two of 10a's three
runs read misaligned too.

Placement left every level it could be compared with where it was: where the
rollback sits did not matter.

## What to take from it

- `allowed` is the frame's promise put in labels. Write it from the promise,
  before the run.
- Misaligned is the finding to act on: the evidence matters, and without it the
  reader goes where the promise forbids. Here, with no route left, this reader
  blames the API rather than say it cannot tell, on 98 of the 120 calls of the
  two ablations, which ask the same timeline.
- Inputs share one plan and one `allowed`, and each gets its own finding.

## Try next

Change 10b's instruction to say "answer unclear unless the evidence rules a
component in or out", and predict whether its ablation still goes to api. The
instruction is hashed with the frame, so it is a new frame: name it 10b2.
