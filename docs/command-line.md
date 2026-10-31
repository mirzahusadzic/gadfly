# Command line

`gadfly` checks, plans, runs and reports frames from a terminal, using only
the public pipeline. Each command takes a frame file, and `run` and `report`
also take a file of records, one JSON object per line. `uv run python -m
gadfly` is the same command.

---

### Commands

Every command but `portfolio` also takes `--json`, which prints the same as
JSON. A refusal, such as a missing file, an existing `--out` file or a battery
that cannot be imported, prints `gadfly:` and the reason, and exits with 2.

| Command | Calls a model | Prints | Exit status |
| --- | --- | --- | --- |
| `check-frame FRAME` | no | `ok`, the frame's hash and its calls, or each problem and where it is | 0 when accepted, 1 when not |
| `plan FRAME` | no | each trial, its kind and its body's hash, and the call count | 0 |
| `run FRAME` | yes, up to `--calls` | the calls written, how many came back as openings and why, and why it stopped early | 0 |
| `report FRAME RECORDS` | no | the overall category, then each input's levels, evidence and open obligations | 0 |
| `portfolio REPORT...` | no | frames counted by category, the obligations they share, and frames whose inputs disagree | 0 |

---

### Check a frame

`check-frame` runs the frame's JSON Schema when `jsonschema` is installed,
then the parser, which has the last word. It never invents a default or
rewrites the frame:

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
  baseline     baseline     body b3b0e45a1db0
  repeat       repeat       body b3b0e45a1db0
  ablation     ablation     body f55c89aeef47
  sham-1       sham         body 38181aba8284
  sham-2       sham         body 67327300286d
  presentation presentation body 5d71afdd24d7
  bypass       bypass       body 429d3f15741d
  control      control      body 0b3f0f01c0fa
```

Each line is a trial, its kind and the hash of the body the reader gets. The
count is the inputs times the trials times `quorum`.

---

### Run a frame

`run` makes the calls the budget covers and keeps each record as one JSON line
the moment it exists. It needs an explicit budget, never writes over a file,
and makes no file until its first record:

```bash
uv run gadfly run examples/upgrade.json \
  --battery midwife.batteries.egemma:EGemma \
  --calls 40 --out records.jsonl
```

It prints the calls it wrote. When some came back as openings, it also prints
how many and the most common reason, such as `eGemma could not be reached`:
[Troubleshooting](troubleshooting.md) says what each one means.

| Flag | Value | Effect |
| --- | --- | --- |
| `--battery` | `module:Class`, required | The battery, imported from the current directory. |
| `--out` | a new file, required | Where the records go, one JSON line each. |
| `--calls` | a whole number, required | The most calls to make. |
| `--output-tokens` | a whole number, 64 by default | Each answer's cap. |
| `--token-budget` | a whole number, none by default | The most output tokens in all. |
| `--only` | a trial id, repeatable | Runs only those trials: a partial run, for diagnosis. |
| `--kept` | a records file | Records already made, whose calls are not made again, so a stopped run finishes. The new file holds them first, so it is the whole run. |
| `--json` | flag | Prints the calls planned and made, the openings by reason, and why it stopped, as JSON. |

---

### Report a verdict

`report` reads the verdict from kept records by the fixed rules, so it calls
no model. It keeps a finding's levels, evidence and open obligations on lines
of their own:

```text
$ uv run gadfly report examples/upgrade.json \
    examples/runs/upgrade/1.jsonl
frame: quill-upgrade (569c71692864ab0fcfbfcd41baaa0011ee213bc0b90ca9bcb95dd40b7f085679)
records: 40  planned calls: 40
overall: carried
  pr: ablation moved it hold -> merge; held under presentation, 2 shams
  pr: bypass moved it hold -> merge: no hidden fallback
  pr: the control moved it hold -> merge
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
  evidence: bypass moved it hold -> merge: no hidden fallback
  evidence: the control moved it hold -> merge
```

It opens with the frame, the records and the overall category, then each
input's finding; the [example report](breadth/report-example.md) reads one
with three inputs.

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
share, and names the frames whose inputs disagree.
