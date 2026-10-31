# Examples

Every example here is an experiment, not a demonstration. Each is a frame, the
predictions written before its first call (`examples/PREDICTIONS.md`), and the
records of every run (`examples/runs/`). The reader is Gemma 4 26B (the QAT
q4_0 GGUF build, revision `d1c082be`), served by eGemma on one machine. A wrong
prediction stays in, and so does a frame that turned out to be built wrong: a
frame is never edited after its runs, and a corrected one is a new frame beside
it. Reading an example back needs no model.

## The ladder

The examples climb. Each step is one or two frames on a new domain or grain,
and it teaches one more thing Gadfly does, on top of the steps before it.
[Your first frame](../first-frame.md) is the first step.

| Step | Frames | Teaches | Domain, grain |
|---|---|---|---|
| [Your first frame](../first-frame.md) | `upgrade`, `rung1`-`rung6` | each trial in turn; levels; open checks; **carried** | dependencies, one changelog line |
| [Cooled](cooled.md) | 07, 08 | **cooled**; the control; discrimination; a contrast pair | code review, one repository rule |
| [Quorum](quorum.md) | 09 | quorum and agree; a trial with no level; runs | architecture, one requirement |
| [Misaligned](misaligned.md) | 10a, 10b | `allowed`; **coupled but misaligned**; several inputs; placement | an incident, four tasks, one route each |
| [Cumulative](cumulative.md) | 10c2, 10d | the cumulative trial; "carried elsewhere too"; two valid routes | the same incident, both routes |
| [A frame built wrong](built-wrong.md) | 10c | the control as a check on the frame; a new version, never an edit | the same incident |
| [Bypass](bypass.md) | 11 | `allowed.bypass`, the designated opening; a fallback left open | contract into engineering, one clause |
| [Several inputs](inputs.md) | 12 | one finding per input; `overall`; what one `allowed` cannot say | security, one grant, three requesters |
| [Grain](grain.md) | 13, 13b | several anchors; the same evidence at two grains | data migration, a section, then one line |
| [Paths](paths.md) | 14, 15 | inputs as paths to one goal; the result, not the route | optimizing; implementing |
| [Run your own](your-own.md) | yours | predictions first; plan, run, report; which trial answers which question | yours |

## How a step reads

Each step shows four things, each printed from the files in `examples/` by
`examples/read.py`, which calls no model:

1. **The frame**, as Gadfly plans it (`--frame`): the evidence one span a line,
   the anchors marked `*`, the question, and what each trial cuts, renames or
   moves.
2. **The prediction**, as it was written before the first call.
3. **The answers**: the labels each trial's calls gave, all runs together.
4. **The reading**: one run's verdict (`--verdict N`, one input with
   `--input`), its levels, its evidence and its open checks, in the words
   `gadfly report` uses.

Then what to take from it, and an experiment to try next. The scale is small on
purpose: one model, one machine, three to five runs a frame, each trial asked
five times with four to agree. What each result says is narrow, and each step
says how narrow. `examples/RESULTS.md` sets every result against its
prediction, and `examples/FINDINGS.md` gathers what they showed about the
reader, the service and Gadfly.

## Every result at a glance

<!-- copy README.md:examples -->
| Example | Domain, grain | Does the decision rest on… | Read by Gemma, per run |
|---|---|---|---|
| `upgrade.json`, `rung1`-`rung6` | dependencies, one changelog line | the line that removes a function our code calls? | carried; the rungs show each check closing |
| `07-sql-rule.json` | code review, one repository rule | the rule against formatted SQL? | cooled: its training decides |
| `08-clock-rule.json` | code review, one repository rule | the rule against `datetime.now()`? | the rule decides; unresolved, no bypass declared |
| `09-sync-sms.json` | architecture, one requirement | the 300 ms requirement? | cooled in two runs of three |
| `10a`-`10d` | debugging, fixing, optimizing, alerting; one test or two metrics | which of two routes to the cause? | the metrics decide every task; the rollback alone decides the fix, not the cause; with both, either can go (cooled) |
| `11-eu-clause.json` | contract into engineering, one clause | the clause keeping data in the EU? | the clause carries; applied without the line that makes it the customer's |
| `12-payroll-access.json` | security, one grant, three requesters | the grant to Finance? | Dana carried, Sam unresolved, the backup job cooled |
| `13`, `13b` | data migration, a section, then one line | the status saying the table is unused? | the section carries; "no reads in 30 days" carries nothing |
| `14-orders-latency.json` | optimizing, one goal, five paths | the latency goal? | four paths carried whatever their cost; the timeout rejected |
| `15-invoice-export.json` | implementing, one test, four processes | the passing test? | the test decides, never the process |
<!-- end copy -->
