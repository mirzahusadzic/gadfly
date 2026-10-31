# Examples

Every example here is an experiment, not a demonstration. Each is a frame, the
predictions written before its first call (`examples/PREDICTIONS.md`), and the
records of every run (`examples/runs/`). The reader is Gemma 4 26B (the QAT
q4_0 GGUF build, revision `d1c082be`), served by eGemma on one machine. A wrong
prediction stays in, and so does a frame that turned out to be built wrong: a
frame is never edited after its runs, and a corrected one is a new frame beside
it. Reading an example back needs no model.

--8<-- "README.md:examples"

The scale is small on purpose: one model, one machine, three to five runs a
frame, each trial asked five times with four to agree. What each result says is
narrow, and the text under each transcript says how narrow.
`examples/RESULTS.md` sets every result against its prediction, and
`examples/FINDINGS.md` gathers what they showed about the reader, the
service and Gadfly.

Each transcript prints the frame, how many kept runs it has and what read them;
then a table of the answers each trial got, all runs together; then each run's
verdict. A trial whose five answers do not agree four to one has no level, and
a verdict that needs it is unresolved.

## 1-6: One pull request, one trial at a time

A dependency bot bumps a library whose changelog removes a function our code
calls. [Your first frame](first-frame.md) climbs this frame one trial at a
time, from a bare ablation (unresolved, three checks open) to every check
passed (carried).

## 07, 08: A rule the model knows, and one it cannot

The same pull-request review twice. In 07 the repository's rules forbid
building SQL by formatting a value into the query, and the diff does exactly
that. In 08 they forbid calling `datetime.now()` directly, and the diff does
that. The question is whether the request for changes rests on the rule.

```text
$ uv run python examples/read.py examples/07-sql-rule.json
sql-rule: 5 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         review
baseline      request-changes 25
repeat        request-changes 25
ablation      request-changes 25
sham-1        request-changes 25
sham-2        request-changes 25
presentation  request-changes 25
control       approve 25
run 1: cooled
run 2: cooled
run 3: cooled
run 4: cooled
run 5: cooled
```

```text
$ uv run python examples/read.py examples/08-clock-rule.json
clock-rule: 5 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         review
baseline      request-changes 25
repeat        request-changes 25
ablation      approve 25
sham-1        request-changes 25
sham-2        request-changes 25
presentation  request-changes 25
control       approve 24, request-changes 1
run 1: unresolved
run 2: unresolved
run 3: unresolved
run 4: unresolved
run 5: unresolved
```

Both verdicts were predicted. Gemma rejects formatted SQL whether or not the
repository forbids it: its training decides, and the rule carries nothing
(**cooled**, which needs the control to show the reader can move; it did). The
clock rule is the only reason it rejects `datetime.now()`: cut it and Gemma
approves. 08 stops short of carried only because it declares no bypass. The
rule reaches the decision only through the diff, which the control already cuts.

A rule that carries nothing is not a useless rule. It means a reviewer like this
one would enforce it anyway, so the rule is not what a reader of its decisions
should credit.

## 09: A synchronous call in checkout

An architecture review at the grain of one requirement. The proposal sends the
order confirmation by SMS inside the checkout request and waits for the
provider; the requirements say checkout answers within 300 ms; the provider
takes 400 to 900 ms.

```text
$ uv run python examples/read.py examples/09-sync-sms.json
sync-sms-design: 3 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         review
baseline      revise 15
repeat        revise 15
ablation      revise 14, unclear 1
sham-1        revise 15
sham-2        revise 15
presentation  revise 15
bypass        revise 10, unclear 5
control       unclear 15
run 1: cooled
run 2: unresolved
run 3: cooled
```

Predicted cooled, and cooled it is in two runs of three: the request to revise
does not rest on the 300 ms requirement, because a synchronous provider call in
checkout is something this reader rejects anyway. The third run is unresolved by
noise. With the provider's latency cut (the bypass), whether the wait matters is
a guess, and the calls split ten to five: the first real spread in these examples,
where the evidence is thinnest.

## 10: One incident, two routes, four tasks

Not every decision is a diagnosis, and no single route to one is the valid one.
These frames hold one incident (API latency rose from 180 ms to 2.4 s, a deploy
and a database failover in the same minute) and ask four different tasks of it:
debugging (which component caused it), implementing the fix, optimizing, and
building an alert. Two routes lead to the database:

- the **fast route**, one experiment: the API was rolled back and the latency
  stayed, which rules the API out;
- the **slow route**, reading the metrics: the new primary's cache hit rate fell
  from 99% to 61%, and slow queries rose from 3 to 410 a minute.

10a holds only the fast route, 10b only the slow one, and 10c, 10c2 and 10d both.

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
ten calls of fifteen. Both are valid routes, and lead a human engineer to the
same answer; to this reader the elimination is enough to act on, not enough to
explain. Cut the only route (each frame's ablation) and the answers do not go
to unclear, the one answer the frames allow: they go to api, the service named
in the symptom, so 10b is **misaligned** in every run and 10a where its levels
agree.

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

With both routes present, either can go. 10c2 cuts the rollback and every task
still says database on every call; its cumulative trial cuts the metrics too and
the answer moves. That is **cooled**, with "the cumulative ablation moved it to
api: carried elsewhere too": the rollback is a valid route the decision does not
need. 10d cuts the metrics instead and the answers fall back to 10a's baseline,
which is the same body, within a call or two of fifteen: the diagnosis rests on the metrics
(unclear without them), the fix and the optimizing do not (cooled: the rollback
alone carries them). Where a task-run reads unresolved, one of its trials split.
With four inputs a run, one usually does, so no run reads cooled overall.

10c2 is a second version. 10c, kept as it ran, had a control that cut the deploy
and the failover but kept the metrics, which name the database's new primary;
it could not move the answer, and Gadfly refused to call 10c cooled: "the control
left it at database too". The check that exists for a reader that cannot move
caught the frame's author. 10c2's control cuts every line that points anywhere,
and it moved on every task, to api again.

## 11: A contract clause

Cross-domain, legal into engineering, at the grain of one clause. A customer's
product manager asks for session replay; the vendor stores recordings in the US;
the customer's agreement keeps their data in the EU.

```text
$ uv run python examples/read.py examples/11-eu-clause.json
eu-clause: 3 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         enable
baseline      block 15
repeat        block 15
ablation      unclear 15
sham-1        block 15
sham-2        block 15
presentation  block 15
bypass        block 15
control       unclear 15
run 1: unresolved
run 2: unresolved
run 3: unresolved
```

Blocking rests on the clause: cut it and every call says unclear. The prediction
was the opposite (a GDPR prior blocks anyway). But cut "Acme GmbH signed the
Enterprise agreement", the line that makes the clause Acme's, and Gemma still
blocks on every call: it applies the agreement without the line that connects it
to this customer. That is the one open check, so each run is unresolved.

## 12: One grant, three requesters

Security, at the grain of one grant line: "members of Finance may read the
payroll table". Three requests read the same policy: Dana (in Finance), Sam (in
Support) and the nightly backup job (granted every table by its own line).

```text
$ uv run python examples/read.py examples/12-payroll-access.json
payroll-access: 3 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         dana        sam         backup-job
baseline      allow 15    deny 15     allow 15
repeat        allow 15    deny 15     allow 15
ablation      deny 15     deny 15     allow 15
sham-1        allow 15    deny 15     allow 15
sham-2        allow 15    deny 15     allow 15
presentation  allow 15    deny 15     allow 15
bypass        unclear 15  unclear 15  allow 15
control       deny 15     deny 15     deny 15
run 1: unresolved (dana carried, sam unresolved, backup-job cooled)
run 2: unresolved (dana carried, sam unresolved, backup-job cooled)
run 3: unresolved (dana carried, sam unresolved, backup-job cooled)
```

Each requester reads differently, and the same in every run. Dana is carried:
cut the grant and she is denied, cut the directory entry that puts her in Finance
and the answer is unclear. Sam is denied whatever is cut, so the control cannot
show the reader can move for him: unresolved. The backup job rests on its own
grant: cooled. That is what the frame's promise expects, but a frame states one
set of allowed answers and one designated opening for all its inputs, so the
overall verdict is unresolved. This is a limit of Gadfly, not of the reader; see
`examples/FINDINGS.md`.

## 13, 13b: The same evidence at two grains

A change request drops the table `orders_v1`. The migration's status section
says the backfill is done and the counts match, writes stopped on 1 October,
and the query log shows no reads in 30 days. 13 tests the whole section; 13b
tests the last line alone.

```text
$ uv run python examples/read.py examples/13-drop-table-section.json
drop-table-section: 3 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         drop
baseline      drop 15
repeat        drop 15
ablation      unclear 15
sham-1        drop 15
sham-2        drop 15
presentation  drop 15
control       unclear 15
run 1: unresolved
run 2: unresolved
run 3: unresolved
```

```text
$ uv run python examples/read.py examples/13b-drop-table-reads.json
drop-table-reads: 3 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         drop
baseline      drop 15
repeat        drop 15
ablation      drop 15
sham-1        drop 15
sham-2        drop 15
presentation  drop 15
control       unclear 13, drop 2
run 1: cooled
run 2: unresolved
run 3: cooled
```

Cut the section and every call says unclear: the drop rests on the section (13
is unresolved only because it declares no bypass). Cut only "no reads in 30
days" and Gemma still drops the table on every call (cooled): that line carries
nothing, although the instruction says to drop only "without breaking a reader",
and no other line shows the readers are gone. At the coarser grain the review
looks sound; at the finer one it skips the check that protects a reader.

## 14: One goal, five paths

Optimizing. Five pull requests answer one goal (GET /orders within 200 ms at
p99 under the load test), each by another path and at another cost: an index
(an hour, 140 ms), a cache (two days, 95 ms), batching the queries (a day,
180 ms), a read model (three weeks, 60 ms) and a longer timeout (ten minutes,
still 1.9 s).

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
the goal and on its load test: cut either and the answer is unclear (carried
whenever its levels agree). Both were predicted otherwise: that the
improvements would be accepted without the goal as "far faster than before",
and the index and the cache without a measurement, on their reputation. The
batched query, 180 ms against 200, is the one near its threshold and the one
whose calls spread. The timeout is rejected, and stays rejected without the load
tests, rightly: a longer timeout makes nothing faster. The frame's designated
bypass opening is unclear for every input, which is wrong for this one.

## 15: One change, four processes

Implementing. One pull request, the same diff and the same passing test, reached
four ways: the test written first, a notebook prototype first, an AI assistant,
or pairing.

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
unclear without it. The process carried nothing, and the test result carried the
decision, as the promise says. No bypass was declared, so each input is
unresolved with that one check open.

## Run one yourself

Each kept run was made by `examples/climb.py`, which runs a frame against eGemma
and keeps the run beside the others. To read a frame fresh without adding to
them, run it to a file of your own and report it:

```bash
uv run gadfly plan examples/09-sync-sms.json   # 40 calls
uv run gadfly run examples/09-sync-sms.json --battery gadfly.batteries.egemma:EGemma \
    --calls 40 --out my-run.jsonl
uv run gadfly report examples/09-sync-sms.json my-run.jsonl
```

A reader that differs from the one recorded (another model, another revision,
another temperature) is a new experiment: write its predictions down first.
