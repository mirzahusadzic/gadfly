# The branch with its step kept: predictions

Written before any call. With calls at once, the branch's time is lost to its maker, since every
reading waits for its step. These runs keep the step instead: each example's maker returns the step
its branch run A made for the same question (`kept-steps.json`, through `kept_step.py`). The reader
is unchanged, Sonnet 5.5 at `none`. The three frames are the branch frames but for the maker's line,
`{"kind": "kept-step-<example>-a"}`, so each is a new frame.

- **Runs:** for each of 19, 22 and 22c, one run one call at a time (`--parallel 1`), then one with
  24 at once (`--parallel 24`), both with `--output-tokens 4000`, each timed.
- **Verdicts:** as run A read with the same steps: 19 carried, 22 carried, 22c cooled. The reader
  draws anew, so one may move.
- **One reading, in seconds:** a run one call at a time, over its calls, takes 1 to 3 s a reading.
  The runs at 8 at once fitted about 1.5 s.
- **24 at once:** faster than one turn at 24 on every frame (10, 8 and 10 s), and under 6 s each.
- **Output tokens:** readings only, about 11 a reading; nothing for the making.
- **Stop rule:** a run that exits non-zero or holds an opening stops the rest.
- **Cost:** 6 runs, 172 Sonnet readings and no Muse calls. At most $0.50; hard cap these 6 runs.
