# Results, against PREDICTIONS.md

Every run is kept under `runs/<frame>/`: five per frame for rungs 1-8 and the full
upgrade frame, three for rungs 9-16. Each trial is asked 5 times, with 4 to agree.
The reader is eGemma's google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be.

## Rungs 1-6: one pull request, one trial added at a time (`upgrade.json`)

| rung | adds | verdict, all 5 runs | checks still open |
|---|---|---|---|
| 1 | ablation | unresolved | bypass, presentation, sham |
| 2 | repeat | unresolved | bypass, presentation, sham |
| 3 | 2 shams | unresolved | bypass, presentation |
| 4 | presentation | unresolved | bypass |
| 5 | bypass | carried | none |
| 6 | control | carried | none |

Every trial gave one answer on all 25 of its calls. Missed prediction: the bypass
(our call to `retry_after()` cut) was predicted hold, a fallback on the word
"Breaking", but it merged on every call.

The full frame, `upgrade.json`, run on its own five times after the rungs: carried
in all five, every trial one answer on all 25 calls, as rung 6. Its prediction
(unresolved, the bypass open) was the same miss.

## Rungs 7 and 8: a rule the model already knows, and one it cannot

| trial | 07-sql-rule | 08-clock-rule |
|---|---|---|
| baseline, repeat, shams, presentation | request-changes (all 125 calls) | request-changes (all 125 calls) |
| ablation (the rule cut) | request-changes, 25/25 | approve, 25/25 |
| control (the rule and the diff cut) | approve, 25/25 | approve 24, request-changes 1 |
| verdict, all 5 runs | cooled | unresolved, only "no hidden fallback" open |

Both verdicts were predicted. Gemma rejects formatted SQL whether or not the
repository forbids it, so that rule carries nothing; the clock rule is the only
reason it rejects `datetime.now()`. Missed prediction: the 07 control was predicted
unclear and came out approve. With the diff gone, every rule still in view is
satisfied, so approve can be read from what is left.

One call in 1,125 differed from its trial's majority. At eGemma's default
settings this reader is close to deterministic on clear evidence; the spread
comes later, with ambiguous evidence (rungs 9 and 10).

## Rung 9: a synchronous call in checkout (architecture, one requirement)

| trial | calls (3 runs) |
|---|---|
| baseline, repeat, shams, presentation | revise, all 75 |
| ablation (the 300 ms requirement cut) | revise 14, unclear 1 |
| bypass (the provider's 400-900 ms cut) | revise 10, unclear 5 |
| control (the design and the provider cut) | unclear 15 |
| verdict | cooled, unresolved, cooled |

Predicted: cooled. Right. Gemma asks to revise a design that waits on an SMS
provider inside checkout whether or not the 300 ms requirement is there: the
requirement carries nothing, its training does. Run 2 is unresolved only
because its bypass had no agreed level (three revise, two unclear). This is the
first trial here with real spread, and it is the one with the least
evidence: without the provider's latency, whether the wait matters is a guess.

## Rung 10: one incident, two routes, four tasks

The incident: API p99 rose from 180 ms to 2.4 s, with a deploy of the API and a
database failover in the same minute. The fast route to the cause is one
experiment, the rollback that left the latency as it was; the slow route is the
database's metrics, its cache hit rate and its slow queries. Four tasks read the
same timeline: debug, fix, optimize, alert.

| frame | routes present | anchors | read, per run |
|---|---|---|---|
| 10a | fast | the rollback | unresolved, misaligned, misaligned |
| 10b | slow | the two metrics | misaligned ×3 |
| 10c | both | the rollback | unresolved ×3: its control could not move (built wrong) |
| 10c2 | both | the rollback | unresolved ×3: cooled on 8 of 12 task-runs, each other one a trial without an agreed level |
| 10d | both | the two metrics | unresolved, unresolved, misaligned |

Calls at baseline, all runs:

| task | fast route only (10a) | slow route only (10b) | both (10c, 10c2, 10d) |
|---|---|---|---|
| debug | unclear 10, database 4, api 1 | database 15 | database 45 |
| fix | database 15 | database 15 | database 45 |
| optimize | database 12, api 2, unclear 1 | database 15 | database 45 |
| alert | api 8, database 7 | database 15 | database 45 |

**Two valid routes are not equal to this reader.** The metrics (direct evidence)
decide every task on every call. The rollback (an elimination: it was not the
API) decides where the fix goes on every call, mostly what to optimize, a coin
toss for the alert, and for the cause itself, unclear more often than not. 10a's
prediction (database on all four, medium-high) was wrong for debug and alert.

**Cut the only route and it blames the API.** 10a's and 10b's ablations leave
the same body, and it drew api on 98 of 120 calls, database on 14 and unclear on
8. With the deploy and the failover in the same minute, unclear is the answer
the frame allows; Gemma names the service in the symptom instead, so 10b is misaligned in every run and 10a where
its levels agree. Predicted for 10a at about 50%; for 10b "as 10a".

**With both routes, either one can go.** Cut the rollback and every task still
says database on every call (10c and 10c2, 120 of 120): the rollback is cooled,
"carried elsewhere too", for the cumulative (both routes cut) moves it to api.
Cut the metrics instead (10d) and the answers fall back to the fast route's
pattern: 10d's ablation is 10a's baseline body, and they agree within a call or
two
(debug unclear 11 and 10, fix database 15 and 15, optimize database 13 and 12,
alert 8 to 7 both ways). So at the grain of the two metrics, the diagnosis rests
on them (unclear without them, carried but for the undeclared bypass); the fix
and the optimizing do not (cooled: the rollback carries them alone). 10d's
predictions held task by task: fix cooled (two runs; the first had no agreed
cumulative), optimize cooled (three), debug unresolved with only the bypass open
where its ablation agreed (two), and alert unresolved or misaligned (one each),
though its first run agreed on database and read cooled, which was not
predicted.

**The control that could not move.** 10c's control cut the deploy and the
failover and kept the metrics, which name the database's new primary: database
on all 60 calls, and Gadfly rightly refused to call 10c cooled. 10c2 is 10c
with a control that cuts all five lines that point anywhere. Its control moved
on every task, and to api, not unclear (debug 13 of 15 api): predicted unclear
for debug, wrong. With nothing pointing anywhere, Gemma still blames the API.

**Why no 10 frame reads cooled overall.** Each frame has four inputs, and in
each run one of them tends to land a trial without an agreed level: the fix's
cumulative (api 9, database 6 in 10c2) or the alert's. 10c2 predicted cooled
overall in about one run in three; it was none.

## Rungs 11-15: other domains, other grains

| frame | domain, grain | predicted | read, per run |
|---|---|---|---|
| 11 eu-clause | legal into engineering, one clause | cooled | unresolved ×3: the clause carries; the bypass is open |
| 12 payroll-access | security, one grant line, three requesters | unresolved overall | unresolved ×3: Dana carried, Sam unresolved, the backup job cooled |
| 13 drop-table-section | data, a whole status section | unresolved, no bypass declared | unresolved ×3, only "no hidden fallback" open |
| 13b drop-table-reads | data, one status line | cooled or keep (low confidence) | cooled, unresolved, cooled |
| 14 orders-latency | optimizing, one goal, five paths | cooled | unresolved ×3: four paths carried in most runs, the timeout unresolved |
| 15 invoice-export | implementing, one test result, four processes | unclear on ablation (55%) | unresolved ×3, only "no hidden fallback" open |

**11.** Blocking session replay for Acme rests on the EU clause: cut it and Gemma
says unclear on all 15 calls. The prediction (block anyway, on a GDPR prior) was
wrong. The bypass, "Acme GmbH signed the Enterprise agreement" cut, still blocked
on all 15 calls, where unclear was designated: Gemma applies the agreement's
clause to Acme without the line that says Acme signed it. That is the one open
check, so the verdict is unresolved. The bypass prediction (block, 60%) was right.

**12.** One frame, three requesters, three readings, the same in all three runs.
Dana is carried: cut the Finance grant and she is denied; cut the directory that
says she is in Finance and the answer is unclear (predicted deny, 55%: wrong, and
the better answer). Sam is denied throughout, and the control (the grant, the
backup grant and the default cut) leaves him denied too, so Gadfly cannot tell
the reader can move for him: unresolved. The backup job is allowed throughout by
its own grant: cooled, with the bypass open, as the directory does not concern
it. The promise expects exactly this: only Dana rests on the grant. But the frame
states one `allowed` for all inputs, and `overall` reads the three as unresolved.
See [FINDINGS.md](FINDINGS.md), design call A.

**13 and 13b**, the same evidence at two grains. Cut the whole status section
(backfill done, writes stopped, no reads in 30 days) and Gemma says unclear on
every call: the section carries the drop. Cut only "no reads in 30 days" and it
still drops the table on every call: that line carries nothing. The instruction
says to drop only "without losing data or breaking a reader", and no other line
shows the readers are gone. Predicted keep at low confidence, with this as the
alternative. 13b's run 2 is unresolved because its control (the change request
cut) split three to two.

**14**, five pull requests against one latency goal, one each per input. The
baselines were predicted: the index (140 ms), the cache (95 ms), the batched query
(180 ms) and the read model (60 ms, three weeks of work) accepted, the timeout
(1.9 s) rejected. No valid path was rejected for its cost or size. The only
baseline spread is the batched query, 180 ms against a 200 ms goal: reject on 3
of 15 calls, so two of its runs had no agreed baseline or ablation level. Cut the
goal and every path goes to unclear (predicted: accepted anyway, as each is far
faster than before; wrong). Cut every load test (the bypass) and the four
improvements go to unclear as well (predicted: the index and the cache accepted
on their reputation; wrong). So the four improvements are carried whenever their
levels agree. The timeout is the other kind of input: rejected at baseline,
unclear without the goal, still rejected without the load tests (a longer
timeout does not make anything faster, which needs no measurement). The frame's
designated bypass opening, unclear, is right for four inputs and wrong for this
one. Design call A again.

**15**, one change reached by four processes: test first, a notebook prototype,
an AI assistant, pairing. Gemma treated them identically on every call: accept
with the passing test, unclear without it (predicted, 55%). The process carried
nothing and the test result carried the decision. No bypass was declared, so each
is unresolved with only that check open.

## Rung 16: inversion, where the answer must move

**16**, "May Jordan, the database administrator, restore the database from a
backup?" on Tendora's demo statements, with the incident commander's approval and
without. Calls per trial over the three runs:

| trial | approved | not approved |
|---|---|---|
| baseline | Yes 14, No 1 | No 15 |
| repeat | Yes 13, No 2 | No 15 |
| ablation (the restore rule) | No 15 | No 15 |
| sham-1 (Jordan may fail over) | Yes 15 | No 15 |
| sham-2 (Jordan keeps break-glass credentials) | Yes 10, No 5 | No 15 |
| inversion | No 15 | Yes 15 |
| control (every statement) | Yes 15 | No 15 |

The inversion turned both answers on every call, as predicted (approved No,
medium-high; not approved Yes, medium): Gemma follows the rule's sense when the
rule is turned around. The verdicts did not reach it. Approved read unresolved in
every run: sham-2 had no agreed level in runs 1 and 2 (cutting the break-glass
credentials, which share the anchor's role, moved it to No on 5 of 15 calls), and
run 3's baseline and repeat split. Its ablation went to No, not open as predicted,
still a move; its control stayed at Yes, answering from the case alone (the
predicted alternative), so monotonicity is open beside it. Not approved read
unresolved in every run: the ablation kept No, and so did the control, so the
scorer cannot tell; the No rests on the absence of leave, not on the rule. Its
inversion still moved it to Yes, read as evidence. Predicted: approved carried and
not approved carried or cooled; both wrong.

## Rung 17: the clock rule, with the diff asked about

**17**, rung 8's review with the diff moved into the question, and its
`datetime.now()` turned into `clock.now()` by the input inversion. Calls per
trial over the three runs:

| trial | review |
|---|---|
| baseline | request-changes 15 |
| repeat | request-changes 15 |
| ablation (the clock rule) | approve 12, unclear 3 |
| sham-1, sham-2 (another contributing rule) | request-changes 15 each |
| presentation | request-changes 15 |
| input-inversion (`clock.now()` in the diff) | approve 14, unclear 1 |
| control (every span) | unclear 15 |

The input inversion turned the review to approve, as predicted
(medium-high): the answer follows the change under review. Carried in runs 2
and 3, as predicted; run 1 read unresolved, its ablation split approve 3 to
unclear 2. The control said unclear, not approve: with the pull request's
description cut, Gemma will not review the diff alone, the alternative
predicted. Moving the diff into the question did not move the baseline.

## Rung 18: each anchor alone

Four frames over rung 16's statements, each declaring `eachAnchor`. Calls per
trial over the three runs of each:

| trial | 18, chain | 18b, two routes | 18b2, with a case | 18c, idle citation |
|---|---|---|---|---|
| baseline | Sam 15 | No 15 | Yes 12, No 3 | Yes 13, No 2 |
| repeat | Sam 15 | No 15 | Yes 11, No 4 | Yes 13, No 2 |
| ablation (both anchors) | Sam 9, open 6 | No 15 | No 15 | No 15 |
| first anchor alone | Sam 15 (s22) | No 15 (s16) | No 9, Yes 6 (s16) | No 15 (s15) |
| second anchor alone | Sam 15 (s23) | No 15 (s24) | Yes 13, No 2 (s24) | Yes 9, No 6 (s14) |
| sham-1 | Sam 15 | No 15 | No 9, Yes 6 | Yes 15 |
| sham-2 | Sam 15 | No 15 | Yes 10, No 5 | (one draw) |
| control (every statement) | open 15 | No 15 | No 15 | Yes 15 |
| per run | unresolved, unresolved, cooled | unresolved in all three | unresolved in all three | unresolved, unresolved, carried |

**18, the chain.** Predicted carried, with each anchor carrying it; wrong.
Either rule cut alone left Sam on every call, and both cut left Sam on 9 of
15: Gemma reaches Sam another way, through "Sam posts customer updates", the
alternative the prediction named. Runs 1 and 2 had no agreed ablation; run 3
agreed on Sam and read cooled, the control moving it to open.

**18b, two routes.** Predicted carried, with either route enough; wrong.
Gemma answered No on all 120 calls, whatever was cut, so the control could
not move it and every run read unresolved: the scorer cannot tell. No is its
default for a question with no case.

**18b2, with a case both routes reach.** Predicted carried, with either
route enough; wrong. Its Yes is not steady: the baseline and repeat split
in every run, and so did a sham. Cutting Priya's route moved it to No on 9
of 15 calls, cutting Alex's on 2: Gemma leans on the route the exposed key
reaches.

**18c, an idle citation.** Predicted carried with "s15 carries it; s14 adds
nothing alone" where the baseline holds, unresolved where it splits, and
monotonicity open: right on all three. Run 3 carried, reading "s15 carries
it" and "s14 alone has no agreed level" (Yes 3 to No 2 in that run); runs 1
and 2 split at the baseline or repeat. Monotonicity is open in runs 1 and 3,
the control answering Yes from the case alone.
