# Grain: how much to cut

> [!IMPORTANT]
> **This step**
>
> - **Teaches:** several anchors cut together, and the same evidence read at
>   two grains.
> - **Frames:** `13-drop-table-section.json` and `13b-drop-table-reads.json`:
>   a data migration, a whole section and then one line.
> - **After:** [Several inputs](inputs.md).

A change request drops the table `orders_v1`. The migration's status section
says three things: the backfill copied every row and the counts match, writes
stopped on 1 October, and the query log shows no reads in 30 days. The
instruction allows a drop only "without losing data or breaking a reader".

## The frame

```text
$ uv run python examples/read.py examples/13-drop-table-section.json --frame
drop-table-section: 1 input x 7 trials x 5 calls = 35 calls, 4 of 5 to agree
relation: approving the drop rests on the migration's status section
grain: the migration's whole status section
evidence, the anchors marked *:
  * backfill   status   Migration status: the backfill copied every orders_v1 row into orders_v2, and the row counts match.
  * dualwrite  status   Migration status: writes to orders_v1 stopped on 1 October.
  * reads      status   Migration status: the query log shows no reads of orders_v1 in the last 30 days.
    invoices   status   Migration status: invoices_v2 went live in August.
    index      status   Migration status: the customers index rebuild is set for November.
    replica    status   Migration status: the old reporting replica was retired in July.
    sessions   status   Migration status: sessions moved to Redis in June.
    audit      status   Migration status: the audit log table is now partitioned by month.
    search     status   Migration status: the search cluster was upgraded in September.
    request    request  Change request #77: DROP TABLE orders_v1.
asked:
  drop  Can change request #77 go ahead?
labels: drop, keep, unclear
trials:
  baseline      asks the evidence as it is
  repeat        asks it again
  ablation      cuts backfill, dualwrite, reads
  sham-1        cuts audit, index, search
  sham-2        cuts invoices, replica, sessions
  presentation  renames orders_v1 -> sales_old, orders_v2 -> sales_new
  control       cuts request
allowed: ablation -> keep, unclear
```

The anchors are the whole section, three spans, and the ablation cuts them
together. A sham cuts as many spans as the anchors, each of an anchor's kind and
the closest to it in length, and no span is drawn twice. So each sham here cuts
three unrelated status lines, and the six in the body are just enough for two
draws. The control cuts the change request itself. 13b is the same frame with a
single anchor, the reads line; its `grain` says so, and that makes it another
frame.

> [!NOTE]
> **Predicted before the first call**
>
> 13: drop at baseline (high); keep or unclear with the section cut (high);
> unresolved, as no bypass is declared. 13b: keep with the reads line cut, at
> low confidence, as Gemma is cautious about dropping tables. If it stays at
> drop, it is cooled at the line's grain while the section carries.

## What Gemma answered

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

## What Gadfly read

```text
$ uv run python examples/read.py examples/13b-drop-table-reads.json --verdict 1
drop: cooled
  levels: baseline drop, repeat drop, ablation drop, sham-1 drop, sham-2 drop, presentation drop, control unclear
  evidence: ablation left it at drop
  evidence: the control moved it drop -> unclear: the scorer can tell
  open: no hidden fallback: no bypass trial was declared
```

Cut the section and every call says unclear: the drop rests on the section,
and 13 is unresolved only because it declares no bypass. Cut only "no reads in
30 days" and Gemma still drops the table on every call: cooled, that line
carries nothing. The instruction says to drop only without breaking a reader,
and no other line shows the readers are gone. At the coarser grain the review
looks sound; at the finer one it skips the check that protects a reader. The
prediction (keep) was wrong, and the alternative it named came true.

13b's run 2 is unresolved because its control split three to two.

## What to take from it

- Anchors are a set, cut together. A coarse anchor can show that the decision
  rests on the section; it cannot show which line it rests on.
- Go finer where one line carries the risk. Each grain is its own frame.
- A cooled at the fine grain can be the most useful finding of all. Here it is
  a review skipping a check its own instruction asks for.

## Try next

Write 13c, anchored on the writes line alone ("writes to orders_v1 stopped on 1
October"), and predict it. Then decide which of the three lines a reviewer must
not drop without, and whether Gemma agrees.
