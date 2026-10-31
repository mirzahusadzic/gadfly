# A frame built wrong

> [!IMPORTANT]
> **This step**
>
> - **Teaches:** the discrimination check as a check on the frame's author,
>   and why a frame gets a new version instead of an edit.
> - **Frame:** `10c-incident-both.json`, kept as it ran, beside `10c2`.
> - **After:** [Cumulative](cumulative.md).

10c2 is a second version. The first, 10c, differs by its name and its control:

```text
$ git diff --no-index examples/10c-incident-both.json \
    examples/10c2-incident-both.json
diff --git a/examples/10c-incident-both.json b/examples/10c2-incident-both.json
index 19265ed..1fd822f 100644
--- a/examples/10c-incident-both.json
+++ b/examples/10c2-incident-both.json
@@ -1,5 +1,5 @@
 {
-  "name": "incident-both",
+  "name": "incident-both-v2",
   "relation": "the answer 'database' rests on the rollback that left the latency as it was",
   "locus": "the incident timeline the on-call engineer reads",
   "role": "the on-call engineer for the API",
@@ -123,7 +123,10 @@
     },
     "control": [
       "deploy",
-      "failover"
+      "failover",
+      "cache",
+      "slowq",
+      "rollback"
     ]
   },
   "allowed": {
```

10c's control cut the deploy and the failover. It kept the two metric lines,
which name the database's new primary, so it left a line pointing at the
database.

---

### What Gemma answered

Every call's label on `10c-incident-both.json`, trial by trial, over all the
kept runs:

```text
$ uv run python examples/read.py \
    examples/10c-incident-both.json
incident-both: 3 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         debug              fix                 optimize     alert
baseline      database 15        database 15         database 15  database 15
repeat        database 15        database 15         database 15  database 15
ablation      database 15        database 15         database 15  database 15
cumulative    api 13, unclear 2  api 10, database 5  api 15       api 14, database 1
sham-1        database 15        database 15         database 15  database 15
sham-2        database 15        database 15         database 15  database 15
presentation  database 15        database 15         database 15  database 15
control       database 15        database 15         database 15  database 15
run 1: unresolved (debug unresolved, fix unresolved, optimize unresolved, alert unresolved)
run 2: unresolved (debug unresolved, fix unresolved, optimize unresolved, alert unresolved)
run 3: unresolved (debug unresolved, fix unresolved, optimize unresolved, alert unresolved)
```

---

### What Gadfly read

Run 1's verdict for `debug` on `10c-incident-both.json`, in the words `gadfly
report` uses:

```text
$ uv run python examples/read.py \
    examples/10c-incident-both.json --verdict 1 \
    --input debug
debug: unresolved
  levels: baseline database, repeat database, ablation database, cumulative api, sham-1 database, sham-2 database, presentation database, control database
  evidence: ablation left it at database, and so did the control: the scorer cannot tell
  evidence: the cumulative ablation moved it to api: carried elsewhere too
  open: no hidden fallback: no bypass trial was declared
  open: discrimination: the control left it at database too
```

The ablation left it at database, and so did the control. A reader that never
moves would give exactly these levels, so Gadfly does not call it cooled: "the
scorer cannot tell", with `discrimination` open. The cumulative still moved,
and Gadfly says so either way, since that is where else the decision may rest.

The reader was fine. The control did not cut what any reader needs, and the
check that exists to catch a reader that cannot move caught the frame's author
instead.

---

### A new version, never an edit

The fix was not to change 10c's control. Every record names the hash of the
whole frame it was made under, so an edited frame refuses its old records
(`a record belongs to another frame`), and an edit made quietly after the runs
would leave nothing to show that it happened. So:

1. 10c stays as it ran, with its runs.
2. The corrected frame is a new file, 10c2, with its own name and hash.
3. The reason and the new predictions were written in
   `examples/PREDICTIONS.md` ("Why a new version") before 10c2's first call.

A reader of the examples sees both versions and which came first.

---

### What to take from it

- A control is a claim about the task: cut it and any reader must move. Check
  that it cuts everything that points to the answer.
- When a check fails, ask first whether the frame asked the right question.
- Correct a frame with a new version and its reason, and keep the old one.

---

### Try next

Copy 10c to a file of your own, change one word of its `crossing`, and report a
kept run against it:
`uv run gadfly report my-10c.json examples/runs/10c-incident-both/1.jsonl`.
Gadfly refuses the records: `a record belongs to another frame`.
