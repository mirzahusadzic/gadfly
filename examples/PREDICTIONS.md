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
