# Troubleshooting

Each problem is listed by what Gadfly prints. A refusal prints what the last
line of a Python traceback would, its class and what went wrong, and on the
next line, when it can, what to do; the class says what to fix and gives the
exit status. With `--json`, the same goes to standard error as one object, and
on the site each table below can show its rows that way.

---

### Exit statuses

The status says what happened without a word read, and the first line of a
refusal says it in words, so a script, a person and another model read it
alike.

| Exit | Type | What it means |
| --- | --- | --- |
| 0 | none | done |
| 1 | none | nothing was read: every call came back as an opening, or `check-frame` did not accept the frame |
| 2 | `UsageError` | the command or the call asks for what cannot be done, and nothing was spent |
| 3 | none | the run stopped early, so its records are partial; `--kept` finishes them |
| 4 | `FrameError` | the frame is refused |
| 5 | `RecordsError` | records or a report are not this frame's run |
| 6 | `BatteryError` | the battery cannot be made, set up or reached |
| 7 | `FileNotFoundError`, `FileExistsError`, `PermissionError` | a file or a folder cannot be read or written |
| 70 | any other | a bug in Gadfly, which prints its traceback |
| 130 | `KeyboardInterrupt` | stopped by Ctrl-C |
| 141 | none | the program reading its output stopped reading (`\| head`), so the command ended quietly, as any Unix tool does |

---

### UsageError

The command or the call asks for what cannot be done, and nothing was spent.
When Gadfly prints what to do, it opens the second column.

| You see | What to do |
| --- | --- |
| `UsageError: the plan needs 40 calls; the budget allows 10` | `gadfly plan shows the calls a whole run needs`. `--calls` is below the plan, so no file was made. |
| `UsageError: unrecognized arguments --stop` | `gadfly run --help shows its arguments`. Flags are named in full, since a shortened one would change meaning when a longer one is added. |
| `UsageError: --battery is module:Class (for example midwife.batteries.egemma:EGemma)` | Name the class after a colon. |
| `UsageError: the plan has no trial 'controll'` | `gadfly plan lists its trials`. Name one of them with `--only`. |
| `UsageError: battery 'egemma' does not take calls at once` | Leave out `--parallel`, as this battery takes one call at a time. |
| `UsageError: - reads standard input, which is a terminal` | `pipe the file in, or name it`. |
| `UsageError: standard input is read once` | `name - for one file at most`. |
| `UsageError: --json and --out - both print to standard output` | `choose a file for --out`. |

---

### FrameError

The frame is refused as written, and Gadfly never repairs it.
`gadfly check-frame` names each refusal and where it is, without a call, and
[Write a frame](write-a-frame.md#troubleshooting) lists the common ones.

| You see | What to do |
| --- | --- |
| `FrameError: file 'frame.json' is not JSON at line 2, column 1 (Expecting value)` | Correct the file at that place; a frame is plain JSON. |
| `FrameError: file 'frame.json' is not UTF-8 text` | Save the file as UTF-8. |
| `FrameError: the body has no span 'r9'` | `anchors name spans of the body`. Name as anchors only the ids of its spans. |
| `FrameError: required influence is tested by ablation, and none is declared` | `set ablation to true`. |

---

### RecordsError

The records, or a report, are not what this frame's run made, so no verdict is
read from them.

| You see | What to do |
| --- | --- |
| `RecordsError: a record belongs to another frame` | The records were made under another frame: another file, or this one edited after the run, since any change makes a new hash. Read them with the frame they were made under. |
| `RecordsError: a record of trial 'baseline' was made on another body` | The trial's text differs from the one the record was made on. The frame, or the way Gadfly plans it, changed after the run. |
| `RecordsError: a record is a JSON object` or `RecordsError: a record's trial is not a str` | A line of the records file is not a record Gadfly wrote: another file, or one edited by hand. |
| `RecordsError: file 'records.jsonl' is not JSON at line 3, column 1 (Expecting value)` | That line is not a record; the file was cut short or edited. |
| `RecordsError: two records for input 'pr', trial 'baseline', run 2` | The same call is kept twice, usually from two files joined into one. Keep one of them. |
| `RecordsError: a kept record of trial 'baseline' was made from another prompt` | A record passed as `--kept` was made with a prompt this frame does not plan for that call. Resume only from the records this frame's own run made. |
| `RecordsError: file 'kept.jsonl' holds a lone surrogate at line 3` | `no file can hold it; correct or drop that record, then run again`. That record holds text, often from another tool, that cannot be written back, and nothing was spent. |
| ``RecordsError: a portfolio reads `gadfly report --json` documents, and this is not one`` | Each file `portfolio` reads is the output of `gadfly report --json`. |

---

### BatteryError

The battery cannot be made, cannot serve this frame as it is set up, or cannot
reach what it needs, and no call was made.

| You see | What to do |
| --- | --- |
| `BatteryError: no eGemma key` | `name a file that holds it in the environment variable EGEMMA_API_KEY_FILE, or set EGEMMA_API_KEY`. |
| `BatteryError: file '/Users/you/.egemma/key' is empty` | `the environment variable EGEMMA_API_KEY_FILE names it; write eGemma's key into it`. |
| `BatteryError: no router token` | `set the environment variable CODEX_ROUTER_TOKEN, or install the router`. The `unified` battery found no token in the variable or in the router's settings file, `~/.codex/unified-router/openrouter.env`. |
| `BatteryError: this frame asks for battery 'egemma', not 'unified'` | A frame names its battery in `battery.kind`, and another battery is another frame. Pass the one it names. |
| `BatteryError: 'midwife.frame:parse' is not a battery` | `a battery has a name, check() and observe()`. The name after the colon is found, but it is not a battery class or object. |
| `BatteryError: module 'tests.fixtures.refund' has no 'NoSuchReader'` | The module was found, but not the class named after the colon. Check its spelling and case. |
| `BatteryError: No module named '...'` | The battery's module is imported from the current directory. Run from the folder that holds it, or check its name. |
| `BatteryError: the evaluator's address must not hold a user or password` | A battery's address names a user or a password. Gadfly refuses it without repeating it; take the credentials out of the address. |
| `BatteryError: the evaluator's address 'http://127.0.0.1:99999' has no valid port` | `a port is a number from 0 to 65535`. |
| `BatteryError: battery.timeout is a number of seconds, up to 3600` | The `local-json` battery's whole-call deadline is missing a positive number, or asks for more than an hour. |

---

### File errors

A file or a folder the command names cannot be read or written, and nothing
was spent. These are Python's own errors, said in plain words.

| You see | What to do |
| --- | --- |
| `FileNotFoundError: file 'frame.json' does not exist` | Check the path, or the file that the environment variable `EGEMMA_API_KEY_FILE` names. |
| `FileNotFoundError: folder 'runs' does not exist` | `make it, or choose another --out`. |
| `PermissionError: folder 'runs' cannot be written` | `choose another --out`. The folder is not yours to write. |
| `FileExistsError: file 'records.jsonl' exists already` | `kept records are never written over; choose a new --out, or finish it with --kept`. To finish a stopped run, pass its file as `--kept` with a new `--out`. |

---

### KeyboardInterrupt

Ctrl-C stops a run, and every record made so far is already in its file.

| You see | What to do |
| --- | --- |
| `KeyboardInterrupt: stopped by Ctrl-C after 12 calls; they are in file 'records.jsonl'` | `finish with --kept 'records.jsonl' and a new --out`. Only the missing calls are made, and the new file holds the whole run, to report as one. A crash leaves the file the same way. |

---

### Openings and early stops

A call that comes back without an answer is an opening, which `run` counts and
names. Neither is an error: the run goes on, and says so when it ends.

| You see | What it means, and what to do |
| --- | --- |
| `openings: 10 of 10 calls, most often "eGemma could not be reached (ConnectionRefusedError)" (10)` | Nothing answers at `EGEMMA_URL`, by default `http://127.0.0.1:8000`. Start eGemma, or point the variable at it. The calls were spent, and `run` exits with 1, so run again into a new file. |
| `"the router could not be reached (...)"` or `"the evaluator could not be reached (...)"` | The same for the router, at `http://127.0.0.1:18766`, or for your evaluator, at the frame's `battery.url`. |
| `"eGemma answered 401"` or `"the router answered 401"` | The key or the token is wrong. |
| `"eGemma answered 503 after 3 retries"` | eGemma stayed busy or has no model loaded; the battery waits and retries before it gives up. Check eGemma's own log. |
| `"the router reports 'openrouter-data-policy'"` | No OpenRouter endpoint for that model keeps no data, and the frame does not consent to one that trains on its inputs. Choose another model, or pin endpoints with `battery.endpoints`. |
| `stopped: the token budget (30) is spent` | The run stopped before its last call, so its records are partial, and `run` exits with 3. Finish with `--kept` and a new `--out`. |
| `stopped: the battery reported 900 output tokens for a call capped at 64` | The battery spent more output tokens on one call than `--output-tokens` allows, so the run stopped after that call, and its record is kept. A battery that writes before it answers spends tokens on the whole call: set `--output-tokens` to what a whole call may spend, and finish with `--kept`. |

---

### Reading a verdict

A verdict that reads unresolved is a finding, not an error, and `report` exits
with 0.

| You see | What it means, and what to do |
| --- | --- |
| `unresolved`, with `no agreed level in ...` | Fewer than `agree` answers matched in those trials: the reader split, or the calls came back as openings. The `openings` line of `run` says which. |
| `unresolved`, with only open checks beside it | Every trial agreed, but a check the category needs is still open. [Reading a verdict](reading-a-verdict.md) explains `carriage` and each check. |

---

### Developing Gadfly

| You see | What it means, and what to do |
| --- | --- |
| `1 transcript(s), copies or references differ` | A page quotes output the code no longer prints, or a copy, frame view or API section is stale. Run `uv run python tools/doc_outputs.py --write`. |
| `tests/test_kept_runs.py` fails | A change to the verdict rules changed a kept run's category. That is a method change: say so in the docs, and never edit the kept runs. |
| `npm run docs:build` fails on a dead link | A link names a page that does not exist. `test_every_link_lands` finds it, with any heading anchor that does not. |
