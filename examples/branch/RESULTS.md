# The branch as designed, on three public examples as claims: the result

PREDICTIONS.md was hashed with every frame before any call (all OK after).
Nine runs, every exit 0, no opening; every Sonnet reading says "thinking off",
and every making records Muse's reasoning tokens (857 to 1,375).

| Example, as a claim | Readings | Muse, thinking, one turn | Branch run A | Branch run B |
| --- | --- | --- | --- | --- |
| 19, "Gadfly calls the router over the same Responses API that Codex uses" | 35 | carried, 23,087 out, 150 s | carried, 2,860, 74 s | carried, 2,709, 81 s |
| 22, "Kiran is a boy" | 24 | carried, 13,915, 101 s | carried, 2,798, 76 s | carried, 2,745, 81 s |
| 22c, "the paper that the doll holds is about someone other than the doll" | 27 | cooled, 15,845, 102 s | cooled, 2,605, 72 s | cooled, 2,819, 74 s |

Input tokens a reading: one turn 451, 353, 275; branch 1,044, 880, 746.

Against the predictions:

- **Verdicts:** held, all nine (19 carried, 22 carried, 22c cooled, on both
  sides and in both branch runs).
- **A stable maker:** held. On each frame the two runs' steps name the same
  key terms, the same false case and the same belief to keep out (22: "name
  sound bias" and "Kiran sounds male bias"; 22c: "held notes concern other
  people" both times), and their verdicts match.
- **Output tokens at least 85% fewer:** held on 19 (88%); missed on 22 (80%)
  and 22c (83%).
- **Time at least 40% less:** held on 19 (48%); missed on 22 (22%) and 22c
  (28%). A call's time is not only what it writes, and the frames with fewer
  readings carry the two makings over fewer calls.
- **Thinking off, makings that think:** held.

Cells moved within a verdict: 22c run A's ablation supports 2 of 3, run B's
cumulative supports 2 of 3 and control does-not-support 3 of 3, where one turn
read unclear; the category stayed cooled.
