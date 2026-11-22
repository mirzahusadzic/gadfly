# The branch with calls at once: results

Each prediction in `PREDICTIONS-parallel.md` (sha256 330bb8a2…, written before any call), against
the six runs in `runs/*-p8.*`. Every run exited 0 with no opening. Every Sonnet record says
"thinking off", and every making records reasoning tokens.

- **Verdicts: held on 22 and 22c, broke on 19 through the branch.** 22 read carried and 22c cooled
  both ways, and 19 carried in one turn. 19 through the branch read unresolved: its ablation split 3
  unclear and 2 does-not-support, short of the 4 of 5 the frame needs. All five ablation calls carried
  one prompt and one step, so the split is the reader's on that step. The kept runs A and B, each with
  a step of its own, read the ablation unclear 5 of 5.
- **Output tokens: held.** Each is within a fifth of the kept run of the same way. Branch 3,187, 3,008
  and 2,698 against 2,860, 2,798 and 2,605 (run A); one turn 24,064, 16,568 and 14,726 against
  23,087, 13,915 and 15,845.
- **Time, each run: held.** Branch 20, 17 and 16 s against 74, 76 and 72 s (run A); one turn 20, 18
  and 15 s against 150, 101 and 102 s.
- **Time saved by the branch: held, and there is none.** 19 took 20 s both ways, 22 took 17 s against
  18, and on 22c the branch was 7% slower, 16 s against 15. One call at a time it saved 48%, 22% and
  28%.
- **Cost:** within the cap of these 6 runs.

With eight calls at once, the branch keeps its saving in output tokens and loses its saving in time.
A step is made before its input's readings start, while one turn's thinking calls overlap. These are
one run each way, an indication and not a rate, and each time is the whole command's wall time.
