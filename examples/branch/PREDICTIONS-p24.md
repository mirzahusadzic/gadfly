# The branch with 24 calls at once: predictions

Written before any call. With every call at once, Anthropic refused 5 of 30 readings: its organization
allows 25 requests in flight across all models, by its own 429 ("Number of concurrent requests across
all models has exceeded your organization's limit"). So these runs make at most 24 at once, one under
the limit. That is every call of 22, and all but 3 of 22c's and 11 of 19's. The six frames are
unchanged, and only `--parallel` differs.

- **Runs:** for each of 19, 22 and 22c, one run through the branch, then one in one turn, both with
  `--output-tokens 4000 --parallel 24`, each timed.
- **Verdicts:** 22 carried and 22c cooled, both ways, and 19 carried in one turn. 19 through the
  branch may read otherwise: two of its four makings so far moved the ablation off unclear.
- **Output tokens:** within a fifth of each frame's kept run of the same way.
- **Time, each run:** no slower than its run at `--parallel 8`.
- **The branch slower than one turn on every frame.** Every reading waits for its step, which takes
  about 12 s to make, while one turn's calls take about 4 s each and overlap. These times are fitted
  to the runs at 8, and the run is what decides it.
- **Stop rule:** a run that exits non-zero or holds an opening stops the rest.
- **Cost:** 6 runs, 86 Muse calls in one turn, 86 Sonnet readings and about 6 Muse makings, as
  before. At most $0.50; hard cap these 6 runs.
