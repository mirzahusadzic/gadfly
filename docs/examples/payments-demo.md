# Payments demo

[Tendora](https://github.com/mirzahusadzic/tendora) answers questions from
a corpus of plain-language statements, naming every statement an answer rests
on. Its public demo, Payments On-Call, asks 31 questions of 30 statements,
each read here by Tendora's engine and by Gemma 4 (26B-A4B,
instruction-tuned) served by eGemma, at temperature 0.7 and at 0. Pick a
question, then a reader in place of a run, to watch the same trials through
each reader's answers.

Each trial was asked once (`quorum` 1, `agree` 1), where the ladder's steps
ask five times. [Inversion](inversion.md) and
[Each anchor alone](each-anchor.md) read the same statements in frames of
their own.

<!-- watch group payments-demo -->

The view plays the runs kept in `examples/payments-demo/`, written for it by
`tools/watch_data.py`, and every prompt it shows is checked against the
digest its records carry. On GitHub the view does not run, and `gadfly
report` reads the same runs back as text.

---

### How each reader read them

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
