# The branch with calls at once: predictions

Written before any call, to give the table in "A maker before the evidence" its third number. The
kept runs went one call at a time (`--parallel 1`), so their time saved says nothing of runs that make
calls at once. The six frames are unchanged, and only `--parallel` differs.

- **Runs:** for each of 19, 22 and 22c, one run through the branch, then one in one turn, both with
  `--output-tokens 4000 --parallel 8`, each timed. Each branch run is a new battery object, so it
  makes its own step.
- **Verdicts:** as before, in both ways: 19 carried, 22 carried, 22c cooled.
- **Output tokens:** within a fifth of each frame's kept run of the same way, since the same calls are
  made.
- **Time, each run:** below its kept run's time one call at a time.
- **Time saved by the branch:** below its saving one call at a time on every frame (48% on 19, 22% on
  22, 28% on 22c), and it may be none or less. A step is made before its input's readings start, so
  with calls at once the making is the branch's floor, while one turn's thinking calls overlap. This
  is argued, not measured, and the run is what decides it.
- **Stop rule:** a run that exits non-zero or holds an opening stops the rest.
- **Cost:** 6 runs, 86 Muse calls in one turn, 86 Sonnet readings and about 6 Muse makings. The kept
  runs' prediction set at most $0.50 for twice the Sonnet readings, so at most $0.50; hard cap these
  6 runs.
