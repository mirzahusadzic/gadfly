# The branch with 24 calls at once: results

Each prediction in `PREDICTIONS-p24.md` (sha256 0f274a2e…, written before any call), against the six
runs in `runs/*-p24.*`. Every run exited 0 with no opening. Every Sonnet record says "thinking off".

- **Verdicts: held but for 22c through the branch.** 19 and 22 read carried both ways, and 22c cooled
  in one turn. 22c through the branch read carried: with this run's step, cutting the anchor moved
  the reader to unclear in all 3 ablation calls, where one turn stayed at supports. 19 through the
  branch read carried, its ablation unclear 5 of 5.
- **Output tokens: held.** Each is within a fifth of the kept run of the same way. Branch 3,085,
  2,289 and 2,661 against 2,860, 2,798 and 2,605 (run A); one turn 23,628, 16,147 and 14,697 against
  23,087, 13,915 and 15,845.
- **Time, each run: held.** Branch 14, 10 and 11 s against 20, 17 and 16 s at 8 at once; one turn
  10, 8 and 10 s against 20, 18 and 15 s.
- **The branch slower than one turn on every frame: held.** 19 took 14 s against 10, 22 took 10 s
  against 8, and 22c took 11 s against 10.
- **Cost:** within the cap of these 6 runs.

The branch's verdict differed from one turn's in two of its nine whole runs. 19 read unresolved at
8 at once, and 22c carried here; each other run matched one turn. These are one run each way, an
indication and not a rate, and each time is the whole command's wall time.
