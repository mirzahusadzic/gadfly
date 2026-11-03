# Command line

`gadfly` checks, plans, runs and reports frames from a terminal, using only
the public pipeline. Each command takes a frame file, and `run` and `report`
also take a file of records, one JSON object per line. `uv run python -m
midwife` is the same command. `gadfly` alone prints its help with examples,
and `gadfly --version` its version.

---

### Commands

Every command also takes `--json`, which prints the same as JSON. A refusal
prints what Python's last traceback line would, its class and what went
wrong, then what to do, and exits with its class's status: 2 for the command,
4 the frame, 5 the records, 6 the battery and 7 a file.
Results go to standard output and messages to standard error, and any file
a command reads may be `-`, standard input, once in a command.

| Command | Calls a model | Prints | Exit status |
| --- | --- | --- | --- |
| `check-frame FRAME` | no | `ok`, the frame's hash and its calls, or each problem as a `FrameError` and where it is | 0 when accepted, 4 when not; a refusal's |
| `plan FRAME` | no | each trial, its kind and its body's hash, and the call count; with `--agreement`, how often the quorum reaches a level | 0; a refusal's |
| `run FRAME` | yes, up to `--calls` | the calls written and how to read the verdict, then an `OpeningWarning` for calls that came back as openings and a `StoppedWarning` for an early stop | 0; 1 when every call came back as an opening, stopped early or not; 3 when stopped early, its records partial; 130 when stopped by Ctrl-C; 141 when its reader stops reading; a refusal's |
| `report FRAME RECORDS` | no | the overall category, then each input's levels, evidence and open obligations | 0; a refusal's |
| `stats FRAME RECORDS...` | no | each trial's answers over the kept runs, how firm they are and how far they moved or held, the quorum's power, and how often each run's verdict comes out the same when its calls are drawn again | 0; a refusal's |
| `portfolio REPORT...` | no | frames counted by category, the obligations they share, and frames whose inputs disagree | 0; a refusal's |

---

### Check a frame

`check-frame` runs the frame's JSON Schema when `jsonschema` is installed,
then the parser, which has the last word. It never invents a default or
rewrites the frame; it prints each problem as a `FrameError` with where it is,
and exits with 4, or prints `ok`:

```text
$ uv run gadfly check-frame examples/upgrade.json
ok (schema and parser): quill-upgrade (569c71692864ab0fcfbfcd41baaa0011ee213bc0b90ca9bcb95dd40b7f085679), 40 calls
```

The parser also checks what a schema cannot: that anchors name spans in the
body, labels follow their order, a presentation map renames something, a
placement moves something, and `stable` comes with `repeat`. The schema is
`midwife/frame.schema.json` (draft 2020-12), published at the site's root where
its `$id` points, and a parity test holds it and the parser to the same answer
on every shipped frame.

---

### Plan a run

`plan` derives the trials from the frame and counts the calls a whole run
makes, without making any:

```text
$ uv run gadfly plan examples/upgrade.json
quill-upgrade (569c71692864ab0fcfbfcd41baaa0011ee213bc0b90ca9bcb95dd40b7f085679): 40 calls
  baseline     body b3b0e45a1db0  nothing
  repeat       body b3b0e45a1db0  nothing, asked again
  ablation     body f55c89aeef47  cuts removed
  sham-1       body 38181aba8284  cuts leak
  sham-2       body 67327300286d  cuts typos
  presentation body 5d71afdd24d7  renames backoff to pause, quill to heron, retry_after to wait_hint
  bypass       body 429d3f15741d  cuts use
  control      body 0b3f0f01c0fa  cuts removed, use
```

Each line is a trial, the hash of the body the reader gets, and what the
trial does to it, so the predictions can be written from here. The count is
the inputs times the trials times `quorum`.

`plan` also names what no answers can make the frame read, carried or cooled,
with the checks that keep it away. The verdict rules read every answer each
trial could give, so this frame, which declares no bypass, is never carried:

```text
$ uv run gadfly plan examples/07-sql-rule.json
sql-rule (0fe4f0d4994453fabdf647d5c8f1ad90978f4d2c3e6d6d9c1def1fd676e3b1c1): 35 calls
  baseline     body 22bf6e6555c8  nothing
  repeat       body 22bf6e6555c8  nothing, asked again
  ablation     body 6124bb2e4a65  cuts rule
  sham-1       body 15b71e9b8c80  cuts branches
  sham-2       body 856dab033e53  cuts size
  presentation body 62567e6fea7e  renames PAY-881 to OPS-217, customers to accounts, search.py to lookup.py
  control      body 6a515d35e727  cuts rule, diff
never carried, whatever the answers: these stay open
  no hidden fallback (no bypass trial was declared)
```

When an input has more than 200,000 answers to read, `plan` says it read
none rather than guess. A frame declared outside scope is never carried or
cooled, and `plan` gives the exclusion as the reason.

---

### Run a frame

`run` makes the calls the budget covers and keeps each record as one JSON line
the moment it exists. It needs an explicit budget, never writes over a file,
and makes none when it is refused, so a run with nothing left to ask still
makes its file, empty:

```bash
uv run gadfly run examples/upgrade.json \
  --battery midwife.batteries.egemma:EGemma \
  --calls 40 --out records.jsonl
```

It prints the calls it wrote, and in a terminal counts them as they are
made. Calls that came back as openings raise an `OpeningWarning`, and a stop
before the plan's end a `StoppedWarning`, each said on standard error with
what to do, as [Troubleshooting](troubleshooting.md) tables them. Stopped by
Ctrl-C, it says where the records made so far are and how to finish with
`--kept`, and a second Ctrl-C ends it at once, waiting for no call still out.

| Flag | Value | Effect |
| --- | --- | --- |
| `--battery` | `module:Class`, required | The battery, imported from the current directory. |
| `--out`, also `-o` or `--output` | a new file or `-`, required | Where the records go, one JSON line each; `-` sends them to standard output and what `run` prints to standard error. |
| `--calls` | a whole number, required | The most calls to make. |
| `--output-tokens` | a whole number, 64 by default | Each call's cap, a battery's own drafting included. |
| `--token-budget` | a whole number, none by default | The most output tokens in all. |
| `--only` | a trial id, repeatable | Runs only those trials: a partial run, for diagnosis. |
| `--kept` | a records file | Records already made, whose calls are not made again, so a stopped run finishes. The new file holds them first, so it is the whole run. |
| `--settle` | flag | Stops asking a trial once its level cannot change, such as after four alike of five with four to agree. The verdict reads as a whole run's; under `stable` the baseline and repeat always run whole. |
| `--stop-unresolved` | flag | Asks the baseline, repeat, ablation, control, presentation and placement first, then stops asking an input once no answer its other trials could give would resolve it. The verdict reads the category a whole run would and names the trials not asked. |
| `--parallel` | a whole number, 1 by default | Makes that many calls at once, for a battery that takes them (the unified battery does; eGemma, with its rate limit, does not). A first Ctrl-C lets the calls already out end and keeps them; a second stops at once. |
| `--json` | flag | Prints the calls planned and made, the openings by reason, why it stopped, its exit status and its warnings, as one JSON object. |

With `--out -` the records stream to standard output, and `report` reads
them from standard input when its records are `-`:

```bash
uv run gadfly run frame.json --battery mine:Reader \
  --calls 40 --out - | uv run gadfly report frame.json -
```

#### Run in slices

A run makes one call at a time unless its battery takes several and
`--parallel` asks for them, so a slow battery can take hours. Slices with no
trial in common can run side by side, each into its own file, and their
records together are the whole run:

```bash
uv run gadfly run frame.json --battery mine:Reader \
  --calls 20 --only baseline --only repeat \
  --out a.jsonl &
uv run gadfly run frame.json --battery mine:Reader \
  --calls 20 --only ablation --only control \
  --out b.jsonl &
wait
cat a.jsonl b.jsonl > slices.jsonl
```

`gadfly report` reads `slices.jsonl` as the whole run. To keep it as one
file, as a single run writes it, pass it as `--kept` with a new `--out`, and
no call is spent. A trial in two slices is refused when they are read
together: `two records for` that call.

---

### Report a verdict

`report` reads the verdict from kept records by the fixed rules, so it calls
no model. It keeps a finding's levels, evidence and open obligations on lines
of their own:

```text
$ uv run gadfly report examples/upgrade.json \
    examples/runs/upgrade/1.jsonl
frame: quill-upgrade (569c71692864ab0fcfbfcd41baaa0011ee213bc0b90ca9bcb95dd40b7f085679)
records: 40 of 40 planned calls
overall: carried
  in pr, ablation moved it hold -> merge; held under presentation, 2 shams
  in pr, bypass moved it hold -> merge, so no hidden fallback
  in pr, the control moved it hold -> merge
pr: carried
  level baseline: hold
  level repeat: hold
  level ablation: merge
  level sham-1: hold
  level sham-2: hold
  level presentation: hold
  level bypass: merge
  level control: merge
  evidence: ablation moved it hold -> merge; held under presentation, 2 shams
  evidence: bypass moved it hold -> merge, so no hidden fallback
  evidence: the control moved it hold -> merge
```

It opens with the frame, the records and the overall category, then each
input's finding; the [example report](breadth/report-example.md) reads one
with three inputs.

---

### How firm a verdict is

`stats` reads the kept runs of one frame and reports, beside each verdict,
how much its calls support it; [Statistics](statistics.md) explains each
number. It calls no model and changes no verdict:

```text
$ uv run gadfly stats examples/upgrade.json \
    examples/runs/upgrade/1.jsonl --resamples 0
frame: quill-upgrade (569c71692864ab0fcfbfcd41baaa0011ee213bc0b90ca9bcb95dd40b7f085679)
records: 1 run, 40 calls
agreement: 100% of calls give their trial's most common answer in their own run
power: at 100% agreement, a trial reaches a level of 4 of 5 100% of the time, and all 8 trials the plan asks of an input 100%
input pr
  baseline        5 calls  hold 5  top 100% (57%-100%)
  repeat          5 calls  hold 5  top 100% (57%-100%), at most 43% differ from hold
  ablation        5 calls  merge 5  top 100% (57%-100%), p 0.0079 against hold (Holm 0.056)
  sham-1          5 calls  hold 5  top 100% (57%-100%), at most 43% differ from hold
  sham-2          5 calls  hold 5  top 100% (57%-100%), at most 43% differ from hold
  presentation    5 calls  hold 5  top 100% (57%-100%), at most 43% differ from hold
  bypass          5 calls  merge 5  top 100% (57%-100%), p 0.0079 against hold (Holm 0.056)
  control         5 calls  merge 5  top 100% (57%-100%), p 0.0079 against hold (Holm 0.056)
  run 1, pr  carried
```

`--pool FRAME RECORDS` adds the calls another frame made with the same
reader on the same prompts, and `--resamples` sets how many times each run's
calls are drawn again, 0 for none.

---

### Count several reports

`portfolio` counts several frames' reports side by side. There is no fixed
rule for combining different relations, promises and recipients, so it names
no category across frames:

```bash
uv run gadfly report --json \
  frame-a.json records-a.jsonl > a.json
uv run gadfly report --json \
  frame-b.json records-b.jsonl > b.json
uv run gadfly portfolio a.json b.json
```

It counts the frames by category, lists the obligations two or more of them
share, and names the frames whose inputs disagree; `--json` prints the same as
JSON. A report whose categories are not the five a verdict reads is refused as
a `RecordsError`, as `gadfly report` did not write it.
