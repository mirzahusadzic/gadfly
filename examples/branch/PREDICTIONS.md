# The branch as designed, on three public examples as claims: predictions

Written before any call, at Mirza's yes. The method is in the maker: the
ladder's claim frames for examples 19, 22 and 22c, unchanged but for the
battery. Checked first: Muse 1.3 Contributor at `low` is a level the router
declares; Sonnet 5.5 at `none` is thinking off on Anthropic's API (the
router's code, and "thinking off" in earlier records). Every frame passed
check-frame and the battery's own check and check_cap.

- **Branch:** maker Muse at `low` (it thinks; reasoning is mandatory
  upstream), with the ladder's take-the-claim-apart instruction unchanged;
  reader Sonnet 5.5 at `none`, `fallback: none`. Two runs a frame, each a new
  battery object, so each makes its own steps.
- **One turn, the reference:** the same claim frames read by Muse at `low`,
  one run a frame.
- **Order, a frame at a time:** branch A, one turn, branch B; `--output-tokens
  4000 --parallel 1`, unpaced; each run timed.
- **Verdicts:** the branch reads as the ladder's branch did with a Sonnet
  maker: 19 carried, 22 carried, 22c cooled, in both runs. Muse in one turn:
  19 carried, 22 carried, 22c cooled.
- **A stable maker:** on each frame the two runs' steps name the same key
  terms and the same false case; their verdicts match.
- **Cost of work:** the branch's output tokens, maker included, at least 85%
  below Muse's in one turn, and its time at least 40% below; every Sonnet call
  says "thinking off", and every making records reasoning tokens.
- **Stop rule:** a run that exits non-zero or has an opening stops the rest.
- **Cost:** 9 runs, 172 Sonnet readings, 86 Muse calls in one turn and about
  12 Muse makings; about $0.25, at most $0.50; hard cap these 9 runs.
