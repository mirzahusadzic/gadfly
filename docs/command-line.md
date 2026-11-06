# Command line

`gadfly` checks, plans, runs and reports frames from a terminal, and carries
recoil through them, using only the public pipeline. Most commands take a
frame file, `report` and `stats` its records, one JSON object per line, and
`portfolio` the reports of several frames.

`uv run python -m midwife` is the same command. `gadfly` alone prints its
help with examples, and `gadfly --version` its version.

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
| `plan FRAME` | no | each trial, its kind and its body's hash, and the call count; with `--agreement`, how often the quorum reaches a level; with `--most` or `--runs`, the most calls asking until firm can make | 0; a refusal's |
| `run FRAME` | yes, up to `--calls` | the calls written and how to read the verdict, then an `OpeningWarning` for calls that came back as openings and a `StoppedWarning` for an early stop | 0; 1 when every call came back as an opening, stopped early or not; 3 when stopped early, its records partial; 130 when stopped by Ctrl-C; 141 when its reader stops reading; a refusal's |
| `report FRAME RECORDS` | no | the overall category, then each input's levels, evidence and open obligations | 0; a refusal's |
| `stats FRAME RECORDS...` | no | each trial's answers over the kept runs, how firm they are and how far they moved or held, the quorum's power, and how often each run's verdict comes out the same when its calls are drawn again | 0; a refusal's |
| `walk FRAMES... --from FRAME` | no | the piece, each hole it fits in the order it would be asked, each whose fit defers, each frame that passed it on, each text it could not follow, and whether the walk is complete; with `--made`, the records that made each artefact it climbed through; with `--sideways`, which frames it reached aside; with `--vectors`, each fit's cosine or why it has none; with `--calls`, each fit's calls until firm and whether they are covered | 0; a refusal's |
| `successor FRAME --hole ID --from FRAME` | no | the drafted frame, checked, on standard output or in a new file, and whether it asks another question | 0; a refusal's |
| `firm FRAME --runs FOLDER` | yes, up to `--calls` | each run's category, kept or asked now, and whether the verdict is firm, then an `OpeningWarning` or a `StoppedWarning` as `run` says them | 0; 1 when every call came back as an opening; 3 when stopped before the verdict was firm; 130 when stopped by Ctrl-C; a refusal's |
| `gate BEFORE AFTER` | no | the gate, the successor's category, what climbs on from it, what a reframing changed, and the check still open | 0; a refusal's |
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
| `--calls` | a whole number or `auto`, required | The most calls to make; `auto` reserves a whole run's, which `plan` counts and `calls_needed` gives in Python. |
| `--output-tokens` | a whole number, 64 by default | Each call's cap, a battery's own drafting included. |
| `--token-budget` | a whole number, none by default | The most output tokens in all. |
| `--only` | a trial id, repeatable | Runs only those trials: a partial run, for diagnosis. |
| `--kept` | a records file | Records already made, whose calls are not made again, so a stopped run finishes. The new file holds them first, so it is the whole run. |
| `--settle` | flag | Stops asking a trial once its level cannot change, such as after four alike of five with four to agree. The verdict reads as a whole run's; under `stable` the baseline and repeat always run whole. |
| `--stop-unresolved` | flag | Asks the baseline, repeat, ablation, control, presentation and placement first, then stops asking an input once no answer its other trials could give would resolve it. The verdict reads the category a whole run would and names the trials not asked. |
| `--withhold` | a file, or `-` | Refuses, before any call and without making a file, a frame whose prompts hold text the set withholds, as [Withhold text](#withhold-text) says. |
| `--parallel` | a whole number, 1 by default | Makes that many calls at once, for a battery that takes them (the unified battery does; eGemma, with its rate limit, does not). A first Ctrl-C lets the calls already out end and keeps them; a second stops at once. |
| `--json` | flag | Prints the calls planned and made, the tokens they reported as `usage`, how many reported no reasoning as `unthought`, the openings by reason, why it stopped, its exit status and its warnings, as one JSON object. |

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

#### Withhold text

`--withhold FILE` on `run`, `firm` and `check-frame` names text that must not
leave this machine. The file has two parts, each listing `names` (whole words,
any case), `lines` (the SHA-256 of a line's words joined by single spaces) and
`patterns` (Python regular expressions):

```json
{"always": {"patterns": ["sk-[A-Za-z0-9]{20,}"]},
 "training": {"names": ["Kestrel"], "lines": []}}
```

`always` binds every call, and `training` binds a battery whose calls may train
on what it reads, which `trains` says. Every prompt the plan makes is read before
the first call; a line opening with a diff marker is also read without it, and
a refusal names the trial, the input and the kind, never the text.
`check-frame --withhold` reads both parts, since no battery is named, and with
`--json` lists every place under `withheld`; in a crossing, what the maker
writes is not read before the reader sees it.

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
with three inputs. With `--json` it also gives the records read, the tokens
they reported and the calls that reported no reasoning, as `records`, `usage`
and `unthought`, as `run` and `firm` do.

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

### Recoil through frames

Four commands carry a piece found deep in a chain of frames back up to the
frames it can answer, each a step of [Recoil](recoil.md) and the function of
the same name in `midwife.recoil`. `walk` and `gate` read files and call no
model, `successor` drafts a frame, and `firm` asks one run at a time; with
`--json`, each prints what its function returns, as one JSON object.

#### Walk a piece

`walk` climbs from the frame a piece was found in, `--from`, through the
frames given, and names each frame the piece fits, each whose fitting hole
defers, each that passed it on, and each quoted text no frame given holds.
The piece is one of that frame's spans, `--span`, or its decision read as a
label, `--decision`:

```text
$ uv run gadfly walk examples/dolls/1-amani.json \
    examples/dolls/2-kiran.json examples/dolls/3-sasha.json \
    examples/dolls/4-robin.json \
    --from examples/dolls/5-mirza.json --span says
piece: 'The paper says: "My name is Kiran, and I am a boy."', of kind kiran-paper, from Mirza (2502951a6892)
fits: Kiran (68efde28470c), hole paper
passed: Robin (4df473486555)
passed: Sasha (a3684beb68f9)
passed: Amani (f67c31b5a5df)
complete: yes
```

A walk that names a text it could not follow is not complete: the frame
that holds it was not given.

With `--calls N`, `walk` counts each fit before the first call: the most
calls asking its successor until firm can make, over at most `--most` runs,
5 by default. It covers the fits in order up to the first the calls left
cannot, and names that one and every one after it as not asked:

```text
$ uv run gadfly walk examples/dolls/1-amani.json \
    examples/dolls/2-kiran.json examples/dolls/3-sasha.json \
    examples/dolls/4-robin.json \
    --from examples/dolls/5-mirza.json --span says --calls 40
piece: 'The paper says: "My name is Kiran, and I am a boy."', of kind kiran-paper, from Mirza (2502951a6892)
fits: Kiran (68efde28470c), hole paper, at most 45 calls until firm, not asked, past the budget
passed: Robin (4df473486555)
passed: Sasha (a3684beb68f9)
passed: Amani (f67c31b5a5df)
complete: yes
budget: 40 calls cover 0 fits of 1, each fit at most 5 runs
```

`--made RECORDS` gives a crossing's run, and may repeat: a frame quoting an
artefact its maker made climbs to the crossing
([Recoil](recoil.md#artefacts-as-parents)), and each line it reaches so names
the trial and input of each record that made it.

`--sideways` offers the piece one step aside too, from the frame `--from`
names to each frame given that quotes a text it quotes; each line it
reaches so says `sideways`, and each sibling then climbs as usual.

`--vectors FILE` orders the fits by cosine, from whole-text vectors acquired
elsewhere ([Recoil](recoil.md#ordered-by-whole-text-vectors)), and
`--space ID` names the space to order by when the file holds several. Each
fit then says its cosine, or why it has none and keeps its place, and a last
line names the space and the SHA-256 of the file.

#### Draft a successor

`successor` drafts the frame a fit is asked again as: the piece a span in the
hole's place, quoting its text by SHA-256, and the frame's one anchor. It
checks the draft as any frame is checked, then prints it, or writes it to a
new file with `--out`, never over one:

```bash
uv run gadfly successor examples/dolls/2-kiran.json \
  --hole paper --from examples/dolls/5-mirza.json \
  --span says --out kiran.json
```

A piece found in no frame given, such as a statement from a store of its
own, is named with `--text` and `--kind` instead of `--from`; the same text
and kind draft the same successor as the span they came from.

`--after SPAN` places the piece right after that span, the line it amends,
for a reader that reads each span as a line; without it the piece comes last.
Either way its ablation gives back the frame's body byte for byte.

`--set KEY VALUE` sets any other key to a JSON value, such as the trials that
read the anchor, and may repeat. It says whether the draft asks another
question, which `gate` reads as a reframing: on standard error while the frame
has standard output, on standard output with `--out`, and as `reframes` in
the one document `--json` prints.

#### Ask until firm

`firm` asks a frame one whole run at a time, and stops once its verdict is
firm: every input's category read alike in at least `--firm` of the draws of
the latest run's calls, and the same as the run before. Its runs live in the
folder `--runs` names, one file each, `1.jsonl` and on; the kept ones count
as runs made, so a frame already firm is asked nothing:

```bash
mkdir kiran-runs
uv run gadfly firm kiran.json --runs kiran-runs \
  --battery midwife.batteries.unified:Unified \
  --calls 45 --output-tokens 8000
```

It prints each run's category, whether the verdict is firm, and the tokens
the calls made now reported, in and out, which `--json` gives as `usage`. It
ends with how many of the calls that reported reasoning reported none, which
`--json` gives as `unthought`, by trial too; nothing is resent, so a reflex
answer counts as any other, and the count is read against the reasoning the
frame asked for. A stop for the budget is a
`StoppedWarning`, and a run that a battery or Ctrl-C cut short is named by
its file, since it is never read as firm.

`--parallel N` makes up to N calls at once within each run, for a battery
that takes them, as `run --parallel` does. The runs stay one after another,
since each decides whether the next is asked.

`plan` counts a climb before its first call. With `--most N`, and `--runs`
for the runs already kept, it adds the most calls `firm` can make: a whole
run's for each run beyond the kept ones, and fewer once a run is firm.

```bash
uv run gadfly plan kiran.json --most 5 --runs kiran-runs
```

| Flag | Value | Effect |
| --- | --- | --- |
| `--battery` | `module:Class`, required | The battery, imported from the current directory. |
| `--runs` | a folder, required | The frame's runs, read in their order; each new run is added as the next file, record by record, never over one. |
| `--calls` | a whole number or `auto`, required | The most calls to make, over every run; no run starts that it cannot cover whole. `auto` reserves the most `--most` runs can take beyond the kept ones, `calls_until_firm` in Python. |
| `--output-tokens` | a whole number, 64 by default | Each call's cap, a battery's own drafting included. |
| `--token-budget` | a whole number, none by default | The most output tokens in all. |
| `--firm` | a share, 0.95 by default | The share of draws that must read each input's category alike. |
| `--most` | a whole number, the frame's `standing.most` or else 5 by default | The most runs read, kept ones included. A frame that declares `standing.most` is read so, and a different `--most` is refused. |
| `--parallel` | a whole number, 1 by default | Makes that many calls at once within each run, for a battery that takes them; the runs stay one after another. |
| `--withhold` | a file, or `-` | Refuses, before any call and without making a file, a frame whose prompts hold text the set withholds, as [Withhold text](#withhold-text) says. |
| `--json` | flag | Each run's file and category, whether the verdict is firm, the shares, the latest run's findings, the calls made, their `usage` and `unthought` counts, why it stopped, its exit status and its warnings. |

#### Read the gate

`gate` reads what a fit did, from the frame and its successor. A successor
that changed more than its evidence asks another question, a reframing read
against no category; any other is read from the runs `--runs` keeps, with
`--firm` and `--most` as `firm` asked it:

```text
$ uv run gadfly gate examples/dolls/2-kiran.json \
    examples/22-kiran-paper.json \
    --runs examples/runs/22-kiran-paper
successor: Kiran (6035528933c8), of Kiran (68efde28470c)
runs: 1 read, firm
gate: climbs
category: carried
climbs: 'Kiran reads boy', of kind role
```

When the gate climbs, `walk` carries each decision it names on from the
successor, with `--from` the successor and `--decision` the label.

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
