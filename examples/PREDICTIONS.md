# Predictions, written before any call

Frame: `examples/upgrade.json` (569c7169…), read by eGemma's Gemma.
Each rung adds one trial to the one before it, and each rung's runs are fresh calls.

| trial | cuts or changes | predicted answer | confidence |
|---|---|---|---|
| baseline | nothing | hold | high |
| repeat | nothing, asked again | hold | high |
| ablation | the Breaking line | merge; some calls may hold on the major version alone | medium (a cooled read is about one in three) |
| sham-1, sham-2 | a neutral changelog line | hold | high |
| presentation | quill → heron, retry_after → wait_hint, backoff → pause | hold | high |
| bypass | our call to retry_after() | hold: it reads the word Breaking, not whether our code calls the function (a hidden fallback) | low, about 55% |
| control | the Breaking line and our call | merge | medium-high |

Predicted verdict for the full frame: unresolved, with "no hidden fallback: bypass
left it at hold" open. If the bypass merges or says unclear, the verdict is carried.

None of this is changed after a run. A frame that turns out to be wrong gets a new
version, with the reason, and its old runs are kept.

## Rungs 7 and 8: a rule the model already knows, and one it cannot

Same pull request shape, same trials (no bypass: the rule reaches the decision
only through the diff, which the control cuts). Written before any call.

| trial | 07-sql-rule (f-string SQL) | 08-clock-rule (datetime.now()) |
|---|---|---|
| baseline | request-changes, high | request-changes, high |
| repeat | request-changes, high | request-changes, high |
| ablation (the rule cut) | request-changes: its training flags SQL injection, about 80% | approve, medium: it may still flag a naive datetime |
| sham-1, sham-2 | request-changes, high | request-changes, high |
| presentation | request-changes, high | request-changes, high |
| control (the rule and the diff cut) | unclear, medium | unclear or approve, medium |

Predicted verdicts: 07 cooled (the rule is not what decides; the training does).
08 unresolved with only "no hidden fallback" open (its ablation moves it).

## Rungs 9-15: other domains and grains, and several paths to one outcome

Written before any call to these frames. Three runs each: rungs 1-8 showed this
reader gives one answer per trial on clear evidence, so a third and later run
added nothing there.

**09 sync SMS in checkout** (architecture; grain: one requirement). Baseline
revise (high). Ablation, the 300 ms requirement cut: still revise, because a
synchronous external call in checkout is a known anti-pattern (about 55%), so
cooled. Bypass, the provider's latency cut: still revise, a fallback on the same
prior (about 60%). Control (the design and the provider cut): unclear.
Verdict: cooled; if the ablation moves, unresolved with the bypass open.

**10 one incident, two routes, four tasks** (debugging, implementing the fix,
optimizing, building an alert; grain: one test, or two metrics).
- 10a, the fast route only (rollback). Baseline database on all four tasks
  (medium-high). Ablation: no longer decided. Gemma names api for at least one
  task, blaming the deploy because it is recent and salient (about 50%): misaligned
  there. Otherwise unclear. Placement (the rollback moved up the timeline):
  database. Control: unclear.
- 10b, the slow route only (cache hit rate, slow queries). Baseline database
  (high). Ablation: as 10a.
- 10c, both routes. Ablation of the rollback alone: still database by the second
  route (about 70%), so cooled with "the cumulative ablation moved it: carried
  elsewhere too". This is the reading for "more than one valid path".

**11 EU data clause** (cross-domain, legal into engineering; grain: one clause).
Baseline block (high). Ablation, the clause cut: still block, because a German
customer's data sits in a US data centre and the GDPR prior fires (about 55%), so
cooled. Bypass, "Acme signed the Enterprise agreement" cut: block rather than the
designated unclear (about 60%), so that check stays open. Control: enable or unclear.

**12 payroll access** (security; grain: one grant line, three requesters).
- Dana: allow. Ablation deny (high). Bypass (the directory cut): deny rather than
  the designated unclear, as the default denies what it cannot place (about 55%).
- Sam: deny throughout; cooled, or unresolved if the control leaves deny.
- Backup job: allow throughout, so cooled.
- Overall: unresolved, although cooled is what the promise expects for Sam and
  the job. The frame cannot state a different expectation for each input.

**13 dropping orders_v1, at two grains** (data; grain: a whole status section, then
one line).
- 13: baseline drop (high). Ablation of the section: keep or unclear (high).
  Unresolved, as no bypass is declared.
- 13b: ablation of the "no reads in 30 days" line alone: keep, low confidence,
  because Gemma is cautious about dropping tables. If it stays drop, it is cooled
  at the line grain while the section carries.

**14 one latency goal, five paths** (optimizing; grain: one goal).
- Baselines: index accept, cache accept, batched query accept (180 ms against a
  200 ms goal, about 85%), read model accept (about 70%: its three weeks and 2,400
  lines may draw a reject), timeout reject (high). The chance that at least one
  valid path is rejected, a single-path bias, is about 40%.
- Ablation, the goal cut: the four improvements are still accepted, as each is far
  faster than before (about 60%), so cooled.
- Bypass, every load test cut: the index and the cache are still accepted on the
  approach's reputation (about 55%), so that check stays open.

**15 one change, four processes** (implementing; grain: one test result). Baseline
accept for test-first, prototype and pairing (high), and for the AI assistant
(about 75%). Ablation, the passing test cut: unclear (about 55%), otherwise accept
on the diff and the clean linters, which would be cooled. Control: unclear.

## Rungs 10c2 and 10d: the incident again, with a control that can move

Written after the runs of 10a-10c and before any call to these two frames, so
these predictions lean on those runs and say where.

**Why a new version.** 10c's control cut the deploy and the failover but kept
the cache and slow-query lines, which name "the new primary": it left the
answer at database on every call, so it could not show the reader can move, and
Gadfly read 10c as unresolved ("the control left it at database too"). The
frame was wrong, not the reader. 10c is kept as it ran. 10c2 is 10c with a
control that cuts all five lines that point anywhere (the deploy, the failover,
the two metrics and the rollback); nothing else changes.

**10d** asks the other half: with both routes present, does the answer rest on
the database's own metrics? Its anchors are the two metric lines; its cumulative
adds the rollback; its control is 10c2's.

Three trials repeat bodies already asked elsewhere, so they double as a check
that the reader answers the same prompt the same way in another frame:
10d's ablation is 10a's baseline body (39318fc1587d), the cumulative of 10c, 10c2
and 10d is 10a's ablation body (8257a99b4eac), and 10c2's ablation is 10b's
baseline body (af0877114f7c).

| trial | 10c2 (anchor: the rollback) | 10d (anchors: the two metrics) |
|---|---|---|
| baseline | database on all four tasks, high (10c: 60 of 60) | the same body: database, high |
| ablation | database on all four, high (10b's baseline: 60 of 60) | as 10a's baseline: debug unclear (about 2 in 3 runs agree), fix database (high), optimize database (about 4 in 5), alert split, so often no agreed level |
| cumulative | api on debug, optimize and alert; fix about 2 in 3 api, else no agreed level | the same body as 10c2's |
| shams, presentation | database, high | database, high |
| control | moves on every task: unclear for debug, api or unclear for the other three (the symptom names the API) | the same body as 10c2's |

Predicted verdicts.
- 10c2: cooled on debug, optimize and alert, each with "the cumulative ablation
  moved it to api: carried elsewhere too". Fix cooled in the runs where its
  cumulative agrees, unresolved where it does not. Overall: cooled in about one
  run in three, otherwise unresolved by fix.
- 10d: fix cooled (the rollback alone carries it, as in 10a); optimize mostly
  cooled; debug unresolved with only "no hidden fallback" open when its ablation
  agrees on unclear (no bypass is declared), unresolved by noise otherwise; alert
  unresolved (no agreed ablation level) or misaligned if api agrees. Overall:
  unresolved.

What the pair would say together: with both routes present, the fix rests on
neither alone, while the diagnosis leans on the metrics, the slower route.

## Rung 16: inversion, where the answer must move

Frame: `examples/16-restore-inversion.json` (43f14466…), read by eGemma's Gemma, 3
runs of 70 calls. The statements are Tendora's demo, Payments On-Call
(Apache-2.0); the question is "May Jordan, the database administrator, restore the
database from a backup?", once with the incident commander's approval and once
without. The anchor is the rule that Jordan may restore only after the incident
commander approves the restore; the inversion turns it into "only after the
incident commander does not approve the restore". Tendora's engine, measured
through its own route, turns both answers.

| trial | cuts or changes | approved | not approved | confidence |
|---|---|---|---|---|
| baseline | nothing | Yes | No | high |
| repeat | nothing, asked again | Yes | No | high |
| ablation | the restore rule | open; Yes if Gemma reads "tests a backup before restoring it" as leave to restore | open; No if the absence of leave reads as a refusal | medium, either way |
| sham-1, sham-2 | another of Jordan's statements | Yes | No | high |
| inversion | the rule's approval turned into its absence | No | Yes | medium-high (approved), medium (not approved: the turned rule is odd, and Gemma may say open or conditional) |
| control | every statement, leaving the case and the question | open; Yes if Gemma answers from the case alone | open; No from the case alone | medium |

Predicted verdicts.
- Approved: carried, the inversion moving it Yes -> No. If Gemma keeps Yes under
  the inversion, the reading drops the negation and the input reads coupled but
  misaligned, the very bug the trial is for. If the ablation keeps Yes, cooled.
- Not approved: carried in about half the runs; cooled in the rest, where the
  ablation keeps No because no statement grants the restore.
- Monotonicity open wherever the control keeps the baseline while the ablation
  moved (a model answering from the case alone).
- Overall: carried only in runs where both inputs carry, otherwise unresolved by
  "carried on some inputs and cooled on others".

## Rungs 17 and 18: what is asked turned, and each anchor alone

Written before the first call of either rung. Each frame runs 3 times, each
trial asked 5 times with 4 to agree.

### Rung 17: the clock rule, with the diff asked about

Frame: `examples/17-clock-asked.json` (153f8c20…), 3 runs of 40 calls. The
clock rule of rung 8, with the diff moved out of the evidence into what is
asked, so the ablation still cuts the rule and the call stays in view. The
input inversion turns the diff's `datetime.now()` into `clock.now()`: the
change then follows the rule, and the review should turn to approve.

| trial | cuts or changes | predicted | confidence |
|---|---|---|---|
| baseline | nothing | request-changes | high (rung 8: 25 of 25) |
| repeat | nothing, asked again | request-changes | high |
| ablation | the clock rule | approve | high (rung 8: 25 of 25) |
| sham-1, sham-2 | another contributing rule | request-changes | high |
| presentation | three names renamed | request-changes | high |
| input-inversion | the diff calls `clock.now()` instead | approve | medium-high: Gemma may still ask for changes on another ground, such as the `.date()` call or a missing test |
| control | every span, leaving the question and the diff | approve; unclear if Gemma will not review without the pull request's description | medium |

Predicted verdict: carried in every run, the input inversion moving it
request-changes -> approve, with no hidden fallback open (no bypass is
declared; `carriage: listed`). Moving the diff into the question may move
the baseline itself; if it does, that is the result.

### Rung 18: each anchor alone

Three frames over the same 30 statements as rung 16, Tendora's demo
(Apache-2.0), each question asked as the demo's own saved checks ask it.
Each declares two anchors and `eachAnchor`, so each anchor is also cut
alone.

**18, the notify chain** (`examples/18-notify-chain.json`, bf3e5d51…, 3 runs
of 40 calls). "Who notifies the customers?" with the case "A certificate
expires.": expiry makes Priya renew the certificate (s22), and the renewal
makes Sam notify the customers (s23).

| trial | cuts | predicted | confidence |
|---|---|---|---|
| baseline, repeat | nothing | Sam | high |
| ablation | s22 and s23 | open; Sam if Gemma reads "Sam posts customer updates" (s10) as notifying | medium |
| ablation-s22 | expiry makes Priya renew | open: nothing ties the expiry to a renewal | medium; Gemma may assume a renewal |
| ablation-s23 | the renewal makes Sam notify | open, or Priya (the one who acts) | medium |
| sham-1, sham-2 | statements of the anchors' roles | Sam | high |
| control | every statement | open | high |

Predicted: carried, with `each anchor carries it`. If s10 keeps Sam, the
ablation leaves it and the frame reads cooled: carried elsewhere.

**18b, two routes** (`examples/18b-access-logs.json`, b7dc8df6…, 3 runs of 40
calls). "Are access logs reviewed?", with no case: Priya reviews them when a
payment key is exposed (s16), and Alex after every rollback (s24).

| trial | cuts | predicted | confidence |
|---|---|---|---|
| baseline, repeat | nothing | conditional | medium; Yes is as likely if Gemma reads a rule that reviews them as a yes |
| ablation | s16 and s24 | open; conditional if Gemma leans on "If Priya reviews access logs, she files an audit note" (s29) | medium |
| ablation-s16 | Priya's route | the baseline's answer, through Alex's route | medium |
| ablation-s24 | Alex's route | the baseline's answer, through Priya's route | medium |
| sham-1, sham-2 | statements of the anchors' roles | the baseline's answer | high |
| control | every statement | open | high |

Predicted: carried, with `the anchors carry it independently; either
suffices`.

**18c, an idle citation built on purpose** (`examples/18c-restore-cited.json`,
4713844a…, 3 runs of 35 calls). Rung 16's approved case, with the
break-glass line (s14) declared an anchor beside the restore rule (s15) on
purpose: the demo's own saved check of this question cites s15 alone. In
rung 16, cutting s14 as a sham moved Gemma's Yes 5 times of 15.

| trial | cuts | predicted | confidence |
|---|---|---|---|
| baseline, repeat | nothing | Yes | high, though rung 16 split once in 15 and twice in 15 |
| ablation | s15 and s14 | No | high (rung 16: No 15 of 15 without s15) |
| ablation-s15 | the restore rule | No | high |
| ablation-s14 | the break-glass line | Yes in most runs; no agreed level in a run where it moves twice | medium |
| sham-1 | two more of Jordan's statements | Yes | medium-high |
| control | every statement | Yes, from the case alone | high (rung 16: 15 of 15) |

Predicted: carried with `s15 carries it; s14 adds nothing alone` where the
baseline and repeat hold, unresolved in a run where they split (`stable`);
monotonicity open in every run, as in rung 16. Where s14 alone has no agreed
level, the evidence says so and the category does not change.
