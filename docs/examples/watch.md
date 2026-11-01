# Watch a run

Gadfly checks whether an answer really rests on one line of evidence: it
hides or changes the evidence in a few fixed ways, asks again each time, and
compares the answers with the first one. Here is a real run, played one trial
at a time: on the left, exactly what the reader read in that trial; on the
right, what it answered, what that shows, and the checks filling in until the
verdict. Pick an example, press play, or click any trial.

<div class="gadfly-watch" data-frames="upgrade,16-restore-inversion,17-clock-asked,18c-restore-cited,07-sql-rule,09-sync-sms,11-eu-clause,12-payroll-access,10c2-incident-both" data-group="payments-demo"></div>

The view plays the runs kept in `examples/runs/` and `examples/payments-demo/`,
written for it by `tools/watch_data.py`, and every prompt it shows is checked
against the digest its records carry. On GitHub the view does not run;
`examples/read.py` and `gadfly report` read the same runs back as text.

---

### The payments demo

The last group of examples is Tendora's payments demo: 31 questions of 30
statements, each read by Tendora's engine and by Gemma 4 (26B-A4B,
instruction-tuned) served by eGemma, at temperature 0.7 and at 0. Pick a
question, then a reader in place of a run, to watch the same trials through
each reader's answers.

| Reader | Carried | Unresolved | Coupled but misaligned | Cooled |
|---|---|---|---|---|
| Tendora's engine | 31 | 0 | 0 | 0 |
| Gemma 4 at temperature 0.7 | 10 | 18 | 1 | 2 |
| Gemma 4 at temperature 0 | 14 | 11 | 3 | 3 |

Carried here means carried under the trials run: the cited statements cut,
other statements cut at random twice, the material reordered where a frame
asks it, and a control. The bypass and presentation checks were not run, so
every verdict lists them as still open. At temperature 0.7 the read shows how
steadily Gemma answers; at 0 its repeats agree almost by construction, and the
read shows whether a cut moves its answer.
