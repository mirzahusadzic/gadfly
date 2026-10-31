# Cumulative: two routes to one answer

> [!IMPORTANT]
> **This step**
>
> - **Teaches:** the [cumulative](../interventions.md#what-each-trial-can-establish)
>   trial, "carried elsewhere too", and how to read a decision more than one
>   route supports.
> - **Frames:** `10c2-incident-both.json` and `10d-incident-metrics.json`: the
>   same incident, with both routes present.
> - **After:** [Misaligned](misaligned.md).

No single route is the valid one. A real timeline often holds both, the
rollback and the metrics, and an engineer may take either, one faster than the
other, to the same answer. Then cutting one route asks whether the decision
needs it, and cutting both asks whether it rests on the other.

## The frame

```text
$ uv run python examples/read.py examples/10c2-incident-both.json --frame
incident-both-v2: 4 inputs x 8 trials x 5 calls = 160 calls, 4 of 5 to agree
relation: the answer 'database' rests on the rollback that left the latency as it was
grain: one test, with a second route present
evidence, the anchors marked *:
    deploy    event    14:02 the deploy of api v2.31 finished.
    failover  event    14:02 the primary database failed over to its replica.
    latency   symptom  14:03 API p99 latency rose from 180 ms to 2.4 s.
    cache     metric   14:04 the new primary's buffer cache hit rate fell from 99% to 61%.
    slowq     metric   14:05 queries slower than one second on the new primary rose from 3 a minute to 410 a minute.
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
  cumulative    cuts cache, rollback, slowq
  sham-1        cuts dns
  sham-2        cuts health
  presentation  renames v2.30 -> v7.3, v2.31 -> v7.4
  control       cuts deploy, failover, cache, slowq, rollback
allowed: ablation -> unclear
```

The anchor is the rollback. The **cumulative** trial cuts the anchors and more:
here the rollback and both metrics, every route at once. That leaves the same
timeline the ablations of 10a and 10b asked, word for word. The control cuts
every line that points anywhere: the deploy, the failover, both metrics and the
rollback.

10d is the other half: the same timeline, with the two metrics as its anchors
and the rollback as its cumulative's extra cut.

> [!NOTE]
> **Predicted before the first call**
>
> 10c2: the ablation stays at database on all four tasks (high), and the
> cumulative moves to api, so cooled with "carried elsewhere too"; cooled
> overall in about one run in three. 10d: its ablation leaves only the
> rollback, so it answers as 10a's baseline did: debug mostly unclear, the fix
> database, optimize mostly database, the alert split.

## What Gemma answered

```text
$ uv run python examples/read.py examples/10c2-incident-both.json
incident-both-v2: 3 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         debug              fix                optimize           alert
baseline      database 15        database 15        database 15        database 15
repeat        database 15        database 15        database 15        database 15
ablation      database 15        database 15        database 15        database 15
cumulative    api 13, unclear 2  api 9, database 6  api 14, unclear 1  api 11, database 4
sham-1        database 15        database 15        database 15        database 15
sham-2        database 15        database 15        database 15        database 15
presentation  database 15        database 15        database 15        database 15
control       api 13, unclear 2  api 15             api 15             api 15
run 1: unresolved (debug unresolved, fix unresolved, optimize cooled, alert cooled)
run 2: unresolved (debug cooled, fix unresolved, optimize cooled, alert cooled)
run 3: unresolved (debug cooled, fix cooled, optimize cooled, alert unresolved)
```

```text
$ uv run python examples/read.py examples/10d-incident-metrics.json
incident-both-metrics: 3 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         debug                          fix                optimize                       alert
baseline      database 15                    database 15        database 15                    database 15
repeat        database 15                    database 15        database 15                    database 15
ablation      unclear 11, api 2, database 2  database 15        database 13, api 1, unclear 1  database 8, api 7
cumulative    api 14, unclear 1              api 8, database 7  api 14, unclear 1              api 12, database 3
sham-1        database 15                    database 15        database 15                    database 15
sham-2        database 15                    database 15        database 15                    database 15
presentation  database 15                    database 15        database 15                    database 15
control       api 14, unclear 1              api 15             api 15                         api 15
run 1: unresolved (debug unresolved, fix unresolved, optimize cooled, alert cooled)
run 2: unresolved (debug unresolved, fix cooled, optimize cooled, alert unresolved)
run 3: coupled but misaligned (debug unresolved, fix cooled, optimize cooled, alert coupled but misaligned)
```

## What Gadfly read

```text
$ uv run python examples/read.py examples/10c2-incident-both.json --verdict 3 --input optimize
optimize: cooled
  levels: baseline database, repeat database, ablation database, cumulative api, sham-1 database, sham-2 database, presentation database, control api
  evidence: ablation left it at database
  evidence: the control moved it database -> api: the scorer can tell
  evidence: the cumulative ablation moved it to api: carried elsewhere too
  open: no hidden fallback: no bypass trial was declared
```

The ablation left it at database, and the control moved it, so the reader can
tell. The cumulative moved it too, so the decision rests on what the cumulative
also cut. That last line is what the trial is for. Cooled alone says the
rollback is not needed; with the cumulative it says the decision is carried
elsewhere too, here by the metrics. The rollback is a valid route the decision
does not need while the metrics are there.

10d cuts the metrics instead, and its answers fall back to the fast route's: its
ablation asks the same body as 10a's baseline, and the two agree within a call
or two of fifteen. The diagnosis rests on the metrics:

```text
$ uv run python examples/read.py examples/10d-incident-metrics.json --verdict 1 --input debug
debug: unresolved
  levels: baseline database, repeat database, ablation unclear, cumulative api, sham-1 database, sham-2 database, presentation database, control api
  evidence: ablation moved it database -> unclear; held under presentation, 2 shams
  evidence: the control moved it database -> api
  evidence: not carried while 1 carriage check is open
  open: no hidden fallback: no bypass trial was declared
```

It is carried but for the bypass neither frame declares. The fix and the
optimizing do not rest on the metrics: cooled, as the rollback alone carries
them. Together the two frames say that with both routes present, where the fix
goes rests on neither alone, while the cause leans on the metrics, the slower
route.

No run of either frame reads cooled overall. With four inputs a run, one of them
usually has a trial whose calls split, such as the fix's cumulative in 10c2 (api
9, database 6), and one unresolved input makes the run unresolved. 10c2's
prediction, cooled overall in about one run in three, was wrong.

## What to take from it

- Declare a cumulative trial when a decision could rest on more than one route.
  Without it, cooled says only "not this"; with it, it also says "and here
  instead".
- Cooled does not say the evidence was useless, only that the decision did not
  need it while the rest was there.
- The same prompt gets much the same answers in another frame. Three trials
  here ask bodies other frames asked (`gadfly plan` prints each body's hash),
  and most counts match within a call or two. The widest gap is the debug task
  with every route cut: api on 9 of 15 calls in 10a, on 13 or 14 in each of the
  four other frames.

## Try next

Add a third route to 10c2's timeline, say "the API's CPU stayed near 30%", and
predict whether the cumulative still moves the diagnosis. It is a new frame,
with its own name and its own prediction.
