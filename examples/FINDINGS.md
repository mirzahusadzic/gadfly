# Findings

What the examples showed about the reader, the service that serves it, and Gadfly
itself. Every claim points at frames whose runs are kept under `runs/`, and each
can be read back with `read.py`, without a model.

## The reader: Gemma 4 26B through eGemma

1. **On clear evidence it gives one answer.** 158 of 5,495 calls differed
   from their trial's majority, at eGemma's default temperature of 0.7. 134
   of them are in the incident frames (10), most on the trials where the cause
   rests on an elimination or on nothing at all. The rest sit where the
   evidence leaves room: the SMS design without the provider's latency (09
   bypass), a batched query at 180 ms against a 200 ms goal (14), a drop request
   with no change request in view (13b control). A trial with no agreed level is
   that room showing, not a fault.

2. **The same prompt in another frame gets the same answers.** Some trials in
   different frames leave the same body, so Gemma got the identical prompt from
   another frame. Their answers mostly match within a call or two: 10d's
   ablation and 10a's baseline (debug unclear on 11 and 10 of 15, fix database
   on 15 and 15, alert split 8 to 7 both times, once each way), and the body
   that is 10a's and 10b's ablation and the cumulative of 10c, 10c2 and 10d
   (optimize api on 15, 15, 15, 14 and 14 of 15). The widest gap is on that
   last body's debug task: api on 9 of 15 calls in 10a, and on 13, 13, 13 and
   14 in the other four. The reader never sees the frame, only the prompt, so
   a gap like that is sampling at temperature 0.7, and fifteen calls do not
   pin a rate closer than that.

3. **It mostly reads what it is given.** Cut the line a decision should rest on
   and it says unclear: the EU clause (11), the migration's status section (13),
   the latency goal and the load tests (14), the passing test (15), the directory
   entry that puts Dana in Finance (12), our call to the removed function (the
   upgrade's bypass). Where its training decides instead, the frame shows it as
   cooled: formatted SQL (07), a synchronous provider call in checkout (09), and
   dropping a table with no line showing nobody reads it (13b). The last is the
   one a reviewer should worry about: the instruction asks for exactly that line.

4. **It applies a rule without checking that the rule reaches the case.** Cut
   "Acme GmbH signed the Enterprise agreement" and it still blocks Acme on the
   agreement's clause (11, 15 of 15 calls). In the other bypasses it followed the
   connection (the upgrade, Dana, the load tests).

5. **With the evidence for one cause gone, it names the component in the
   symptom.** Cut the database's metrics (10b) or the rollback (10a) and it
   answers api on 98 of 120 calls, the service named in "API p99 latency rose",
   rather than unclear, although a deploy and a failover happened in the same
   minute. With every line that points anywhere cut (the control of 10c2 and
   10d), it still answers api, even for the cause (27 of 30 calls).

6. **It trusts direct evidence more than an elimination.** With the database's metrics in view it names the
   database on every call, whatever the task (10b, and every frame with both
   routes). With only the rollback that ruled the API out (10a), it names the
   database for where the fix goes on every call, for what to optimize on most,
   for the alert on half, and for the cause itself it says unclear on two calls
   in three. Both routes are valid, and lead a human engineer to the same
   answer; to this reader the elimination is enough to act on and not enough to
   explain. With both routes present either can be cut and the answer holds
   (10c2, 10d), which Gadfly reads as cooled, "carried elsewhere too".

7. **It judges the result, not the path to it.** Four valid optimizations, from
   a one-hour index to a three-week read model, were accepted alike; the timeout
   that changed nothing was rejected (14). One change reached four ways (test
   first, a prototype, an AI assistant, pairing) was read identically on every
   call (15). The one path-dependent spread is a result near its threshold.

## The service: eGemma

- **No call failed.** 5,495 calls: no error, no
  refusal and no answer outside the schema. Every raw answer was the one-key JSON
  object the schema allows, in three whitespace variants (`{ "label": "…"}` on
  93%).
- **The rate limit sets the pace, not the model.** The judge budget is 60 calls
  per 60 s. A 40-call frame takes 9 s inside the budget and 69 s once it has to
  wait; a 160-call frame takes 2 to 5 minutes. Unpaced, the model answers about
  four of these calls a second. For short prompts with one-label answers, a
  larger budget for loopback callers, or a batch call, would cut a run several
  times over. That is eGemma's decision, not Gadfly's.
- **Small calls.** Median 262 input tokens (118 to 361) and 8 output tokens (6
  to 11); 1.43 million input tokens in all.
- **Provenance holds.** Every record names the served model and its revision,
  and one revision served every example, so a reader of the records knows
  what answered.
- **Temperature.** A frame that names no temperature gets eGemma's default,
  0.7. Every frame here left it to the default; point 1 is what that gave.

## Gadfly

### Fixed, each with a guard test that failed before the fix

| commit | what a finding failed to say |
|---|---|
| 0188e02 | an undeclared sham read as "0 sham trial(s), 0 declared" instead of as the other undeclared checks do |
| 019d668 | a sham that moved the answer was hidden whenever the category was not carried |
| b450c28 | a carried finding did not name the bypass and the control that settled it, so two different runs read the same |
| 4d0d757 | an unresolved finding whose control stayed put dropped the cumulative trial that moved it (10c) |

### It caught a frame built wrong

10c's control cut the deploy and the failover but kept the two lines that name
the database's new primary, so it could not move the answer, and it did not.
Gadfly refused to call 10c cooled: "the control left it at database too". That
check exists for a reader that cannot move; here it caught the frame's author.
10c2 is the corrected frame, and 10c stays as it ran.

### Design calls

Each is a question for the owner, with a recommendation; none is implemented.

**A. One expectation for every input.** `allowed` holds for all inputs of a
frame, but the inputs of 12 and 14 differ on purpose. The backup job does not
need the directory, so its bypass should leave it at allow; the timeout is
rejected without any load test, so its bypass should leave it at reject. Both
read as "bypass gave X, not the designated opening". Recommended: an optional
`allowed` on an input, used in place of the frame's for that input.

**B. `overall` cannot say "each input as promised".** 12 reads unresolved
overall in every run, though Dana carried, the backup job cooled and Sam was
denied, which is what the promise describes. Recommended: an optional expected
category per input; `overall` then reports whether each input met its own,
and keeps today's reading when none is given. The same reading also grows
stricter with every input: one trial without an agreed level anywhere makes the
whole frame unresolved, so no run of 10c2 read cooled overall although 9 of its
12 task-runs did. A per-input expectation would let the report say how many
inputs met theirs, not only whether all did.

**C. The baseline is never compared with the promise.** 10a's debugging
baseline was unclear on 10 of 15 calls although the promise expects database.
Here the trials around it lacked agreed levels, so it read unresolved anyway,
but a baseline that agreed on the wrong answer would have been read as if it
were the decision the frame is about. Recommended: an optional expected baseline
label per input; a baseline that differs becomes an open check, "the baseline
gave X, the promise expects Y".

**D. The cumulative answer is not read against `allowed`.** In 10c, 10c2 and
10d, cutting both routes moved the answer to api, which the frame allows the ablation
only as unclear. Recommended: read the cumulative against the ablation's
allowed answers, and record a disallowed move as an open check, not a demotion.

**E. Sam cannot move.** A decision that is the default (denied when nothing
grants it) cannot be moved by cutting evidence: Sam stays denied whatever is
cut, so his control cannot show the reader can move, and he reads unresolved.
Every trial in Gadfly removes or rewrites; none adds. Recommended: leave it, and
say in the docs that a default decision is tested from the input that has a
grant (Dana); an added-span trial is a larger change than this needs.

**F. A moved sham under all-checks.** The fix in 019d668 lists a moved sham as
an open check under every category, but only carried is demoted by it. Should a
moved sham also demote cooled and misaligned? Recommended: no for misaligned
(its finding stands on the presentation or the ablation), yes for cooled, which
like carried claims something about the anchors.
