# The branch with every call at once: predictions

Written before any call. The runs at `--parallel 8` still queued their calls in about five rounds, so
they did not show every call at once. The six frames are unchanged, and only `--parallel` differs.

- **Runs:** for each of 19, 22 and 22c, one run through the branch, then one in one turn, both with
  `--output-tokens 4000 --parallel 35`, each timed. No frame has more than 35 calls, so every call
  starts at once, and a larger number would change nothing.
- **Verdicts:** 19 carried, 22 carried, 22c cooled, in both ways.
- **Output tokens:** within a fifth of each frame's kept run of the same way.
- **Time, each run:** no slower than its run at `--parallel 8`.
- **The branch slower than one turn on every frame.** One turn takes about as long as its slowest
  thinking call. The branch takes its making and then a reading, since every reading waits for its
  step. This is argued from times fitted to the runs at 8, and the run is what decides it.
- **Stop rule:** a run that exits non-zero or holds an opening stops the rest, and a refusal for
  calls at once counts as an opening.
- **Cost:** 6 runs, 86 Muse calls in one turn, 86 Sonnet readings and about 6 Muse makings, the
  same as the runs at 8. At most $0.50; hard cap these 6 runs.
