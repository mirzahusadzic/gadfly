# The branch with its step kept: results

Each prediction in `PREDICTIONS-kept-step.md` (sha256 136b5fae…, written before any call), against
the six runs in `runs/*-kept-step-*`. Every run exited 0 with no opening. Every record says "thinking
off", and each run read exactly run A's two steps for its example, by their SHA-256.

- **Verdicts: held.** 19 and 22 read carried and 22c cooled, in both runs, as run A did with the same
  steps.
- **One reading, in seconds: held.** One call at a time, the runs took 54.7, 53.5 and 59.1 s, that is
  1.56, 2.23 and 2.19 s a reading.
- **24 at once: held.** 5.6, 2.4 and 4.9 s, against one turn's 10, 8 and 10 s and the branch's 14, 10
  and 11 s with its step remade, at 24 at once.
- **Output tokens: held.** 375, 255 and 279, about 11 a reading, with nothing for a making.
- **Cost:** within the cap of these 6 runs.

With its step kept, the branch is faster than one turn at 24 at once, since its readings start at
once and need no thinking. A kept step no longer shows how alike its makings are: on these frames
two of nine remade runs gave a verdict other than one turn's.
