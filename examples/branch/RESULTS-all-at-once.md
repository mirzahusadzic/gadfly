# The branch with every call at once: results

Against `PREDICTIONS-all-at-once.md` (sha256 4ba2b210…, written before any call). The stop rule
ended it after the first run, so only `runs/19-branch-p35.*` exists, and no prediction about time was
tested.

- **The stop rule:** in 19 through the branch, 5 of its 30 readings of the first step came back as
  openings, "the router answered 429". The 30 readings waited for their step and then went out
  together. The router passes a provider's rate limit on with its retry-after, and Gadfly keeps a
  refused call as an opening, never retried.
- **What it shows:** every call at once meets the provider's rate limit before it meets Python. Here
  that limit fell between the 8 calls at once that ran clean and 30.
- **The verdict:** unresolved, as the inversion kept only 3 labels. Its ablation read
  does-not-support 5 of 5, which the frame does not allow.
- **The ablation on 19, over four makings:** unclear 5 of 5 in runs A and B, 3 unclear and 2
  does-not-support at 8 at once, and does-not-support 5 of 5 here. Each run's five ablation calls read
  one step, so the answer to the cut page moved with the step drawn.
- **Cost:** one run of 35 calls, 5 of them refused, within the cap.
