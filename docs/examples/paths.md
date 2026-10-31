# Paths: the result, not the route

> [!IMPORTANT]
> **This step**
>
> - **Teaches:** inputs as different paths to one goal, an anchor every path
>   shares, and a designated opening read against every input.
> - **Frames:** `14-orders-latency.json` (optimizing: five pull requests, one
>   goal) and `15-invoice-export.json` (implementing: one change, four
>   processes).
> - **After:** [Grain](grain.md).

Some paths to an outcome are faster, some slower, some cheaper; several can be
valid. These two frames ask whether a reviewer judges the result or the route
taken to it. Each route is an input, and the evidence they share is the anchor.

## 14: one goal, five paths

```text
$ uv run python examples/read.py examples/14-orders-latency.json --frame
orders-latency: 5 inputs x 8 trials x 5 calls = 200 calls, 4 of 5 to agree
relation: accepting each performance change rests on the goal it is measured against
grain: one goal, five paths to it
evidence, the anchors marked *:
  * goal       goal       Goal: GET /orders answers within 200 ms at the 99th percentile under the Black Friday load test.
    languages  goal       Goal: the orders page is offered in English and German.
    exports    goal       Goal: order exports finish within one hour.
    phone      goal       Goal: the admin page works on a phone.
    before     fact       Before any change: load test p99 = 1.9 s; the endpoint runs one query per order line.
    index      benchmark  Pull request #501 (Ana added an index on orders.customer_id): load test p99 = 140 ms.
    cache      benchmark  Pull request #502 (Ben caches each customer's order list in Redis for 30 seconds): load test p99 = 95 ms.
    batch      benchmark  Pull request #503 (Chen loads the order lines in one query instead of one query per order): load test p99 = 180 ms.
    readmodel  benchmark  Pull request #504 (Dee moved GET /orders to a read model kept current by order events): load test p99 = 60 ms.
    timeout    benchmark  Pull request #505 (Eli raised the endpoint's timeout from 2 s to 5 s): load test p99 = 1.9 s.
asked:
  index      Review pull request #501. Ana added an index on orders.customer_id: a one-line migration, done in an hour. Does it meet the goal?
  cache      Review pull request #502. Ben caches each customer's order list in Redis for 30 seconds: two days of work. Does it meet the goal?
  batch      Review pull request #503. Chen loads the order lines in one query instead of one query per order: a day of work. Does it meet the goal?
  readmodel  Review pull request #504. Dee moved GET /orders to a read model kept current by order events: three weeks of work, 2,400 changed lines. Does it meet the goal?
  timeout    Review pull request #505. Eli raised the endpoint's timeout from 2 s to 5 s: ten minutes of work. Does it meet the goal?
labels: accept, reject, unclear
trials:
  baseline      asks the evidence as it is
  repeat        asks it again
  ablation      cuts goal
  sham-1        cuts languages
  sham-2        cuts exports
  presentation  renames order -> purchase, orders -> purchases
  bypass        cuts index, cache, batch, readmodel, timeout
  control       cuts goal, before, index, cache, batch, readmodel, timeout
allowed: ablation -> unclear; bypass -> unclear
```

Five pull requests answer one goal (GET /orders within 200 ms at p99 under the
load test), each by another path and at another cost: an index (an hour, 140
ms), a cache (two days, 95 ms), batching the queries (a day, 180 ms), a read
model (three weeks, 60 ms) and a longer timeout (ten minutes, still 1.9 s). The
anchor is the goal. The bypass cuts every load-test result, which is what
connects each change to the goal.

> [!NOTE]
> **Predicted before the first call**
>
> The four improvements accepted at baseline, the read model least surely
> (about 70%), the timeout rejected (high); about 40% that at least one valid
> path is rejected for its size or cost. The goal cut: the four still
> accepted as far faster than before (about 60%), so cooled. The load tests
> cut: the index and the cache still accepted on their reputation (about
> 55%).

```text
$ uv run python examples/read.py examples/14-orders-latency.json
orders-latency: 3 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         index       cache                 batch                           readmodel   timeout
baseline      accept 15   accept 15             accept 12, reject 3             accept 15   reject 15
repeat        accept 15   accept 15             accept 14, reject 1             accept 15   reject 15
ablation      unclear 15  unclear 13, reject 2  unclear 13, accept 1, reject 1  unclear 15  unclear 13, reject 2
sham-1        accept 15   accept 15             accept 13, reject 2             accept 15   reject 15
sham-2        accept 15   accept 15             accept 12, reject 3             accept 15   reject 15
presentation  accept 15   accept 15             accept 13, reject 2             accept 15   reject 15
bypass        unclear 15  unclear 15            unclear 15                      unclear 15  reject 15
control       unclear 15  unclear 15            unclear 15                      unclear 15  unclear 15
run 1: unresolved (index carried, cache carried, batch unresolved, readmodel carried, timeout unresolved)
run 2: unresolved (index carried, cache unresolved, batch carried, readmodel carried, timeout unresolved)
run 3: unresolved (index carried, cache carried, batch unresolved, readmodel carried, timeout unresolved)
```

The four that meet the goal are accepted whatever their cost, and each rests on
the goal and on its load test: cut either and the answer is unclear, so they
are carried whenever their levels agree. Both cuts were predicted otherwise.
The batched query, 180 ms against 200, is the one near its threshold and the
one whose calls spread. The timeout is the other kind of input:

```text
$ uv run python examples/read.py examples/14-orders-latency.json --verdict 1 --input timeout
timeout: unresolved
  levels: baseline reject, repeat reject, ablation unclear, sham-1 reject, sham-2 reject, presentation reject, bypass reject, control unclear
  evidence: ablation moved it reject -> unclear; held under presentation, 2 shams
  evidence: the control moved it reject -> unclear
  evidence: not carried while 1 carriage check is open
  open: no hidden fallback: bypass gave reject, not the designated opening (unclear)
```

It is rejected, and stays rejected without the load tests, rightly: a longer
timeout makes nothing faster, which needs no measurement. The designated
opening, unclear, is right for the four improvements and wrong for this one,
so its check stays open for a reason that does not apply.

## 15: one change, four processes

One pull request, the same diff and the same passing test, reached four ways:
the test written first, a notebook prototype first, an AI assistant, or
pairing. Each process is an input, told in the question, and the anchor is the
passing test.

> [!NOTE]
> **Predicted before the first call**
>
> Accept at baseline for all four, the assistant least surely (about 75%).
> The passing test cut: unclear (about 55%), or accepted on the diff and the
> clean linters, which would be cooled.

```text
$ uv run python examples/read.py examples/15-invoice-export.json
invoice-export: 3 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         test-first  prototype   assistant   pairing
baseline      accept 15   accept 15   accept 15   accept 15
repeat        accept 15   accept 15   accept 15   accept 15
ablation      unclear 15  unclear 15  unclear 15  unclear 15
sham-1        accept 15   accept 15   accept 15   accept 15
sham-2        accept 15   accept 15   accept 15   accept 15
presentation  accept 15   accept 15   accept 15   accept 15
control       unclear 15  unclear 15  unclear 15  unclear 15
run 1: unresolved (test-first unresolved, prototype unresolved, assistant unresolved, pairing unresolved)
run 2: unresolved (test-first unresolved, prototype unresolved, assistant unresolved, pairing unresolved)
run 3: unresolved (test-first unresolved, prototype unresolved, assistant unresolved, pairing unresolved)
```

The four were read identically on every call: accepted with the passing test,
unclear without it. The process carried nothing, and the test result carried
the decision, as the promise says. No bypass is declared, so each input is
unresolved with only that check open.

## What to take from it

- To ask whether the route matters, make the routes the inputs and keep the
  evidence the same. To ask whether the result matters, anchor the result.
- Both frames say the same about this reader: it judges the result, not the
  path, the cost or who wrote the code.
- A designated opening applies to every input. When one input should land
  elsewhere, as the timeout should, give it a frame of its own.

## Try next

In 15 the process lives in the question, so no trial can cut it. Write 15b with
the process as a span of the evidence ("Process: an AI assistant wrote the code
and the test") and the passing test still there, and anchor the process.
Predict whether cutting it moves anything.
