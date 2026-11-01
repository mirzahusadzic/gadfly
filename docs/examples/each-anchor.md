# Each anchor alone: how several lines carry it

> [!IMPORTANT]
> **This step**
>
> - **Teaches:** the
>   [each anchor alone](../interventions.md#each-anchor-alone-says-how-several-carry-it)
>   trials, evidence that never changes a category; a default that no cut
>   can move.
> - **Frames:** `18-notify-chain.json`, `18b-access-logs.json`,
>   `18b2-access-logs-both.json` and `18c-restore-cited.json`: rung 16's
>   statements, at the grain of two statements each.
> - **After:** [Asked](asked.md).

With two anchors, the ablation cuts both, so it cannot tell a chain of rules
from two routes either of which is enough. `eachAnchor` also cuts each one
alone, and after a moved ablation one line says how they carry it. The
statements are Tendora's demo, Payments On-Call (Apache-2.0), and each
question is asked as the demo's own saved checks ask it.

---

### 18c: a citation declared on purpose

The restore question of rung 16, approved, with two anchors: the restore
rule (s15) and the break-glass line (s14). The demo's own saved check cites
s15 alone; s14 is declared beside it on purpose, to see whether a line that
carries nothing is told apart.

```text
$ uv run python examples/read.py \
    examples/18c-restore-cited.json --frame
restore-cited: 1 input x 7 trials x 5 calls = 35 calls, 4 of 5 to agree
relation: the restore rule carries the approved restore; the break-glass line is declared an anchor beside it on purpose, though the rule alone carries it
grain: two statements of the corpus, each cut alone
evidence, the anchors marked *:
    s01  incident-commander      Maya, the incident commander, declares a major incident when payment failures last more than ten minutes.
    s02  incident-commander      Maya, the incident commander, may approve a rollback of the payments service.
    s03  incident-commander      Maya, the incident commander, must close a major incident after the release manager confirms that payments are healthy.
    s04  on-call-engineer        Alex, the on-call engineer, acknowledges every page within five minutes.
    s05  on-call-engineer        Alex, the on-call engineer, checks the payment error rate after acknowledging a page.
    s06  on-call-engineer        Alex, the on-call engineer, may restart the payments service when the error rate stays above five percent.
    s07  release-manager         Morgan, the release manager, freezes deployments during a major incident.
    s08  release-manager         Morgan, the release manager, may roll back the latest payments release after the incident commander approves the rollback.
    s09  release-manager         Morgan, the release manager, confirms that payments are healthy before the incident commander closes a major incident.
    s10  support-lead            Sam, the support lead, posts customer updates after the incident commander declares a major incident.
    s11  support-lead            Sam, the support lead, must not promise a recovery time before the on-call engineer identifies the cause.
    s12  support-lead            Sam, the support lead, collects affected customer reports in the incident channel.
    s13  database-administrator  Jordan, the database administrator, may fail over the primary database after the on-call engineer confirms replication lag.
  * s14  database-administrator  Jordan, the database administrator, keeps break-glass credentials in the password vault.
  * s15  database-administrator  Jordan, the database administrator, may restore the database from a backup only after the incident commander approves the restore.
    s16  security-engineer       Priya, the security engineer, reviews access logs when a payment key is exposed.
    s17  security-engineer       Priya, the security engineer, must rotate a leaked payment key before the incident commander closes the incident.
    s18  security-engineer       Priya, the security engineer, reports a leaked payment key to the incident commander.
    s19  incident-commander      Maya, the incident commander, approves the database vendor invoice.
    s20  release-manager         A deployment is a change.
    s21  release-manager         If a major incident is open, Morgan, the release manager, does not ship a release.
    s22  security-engineer       If a certificate expires, Priya, the security engineer, renews the certificate.
    s23  support-lead            If Priya renews the certificate, Sam, the support lead, notifies the customers.
    s24  on-call-engineer        Alex, the on-call engineer, reviews access logs after every rollback.
    s25  database-administrator  Jordan, the database administrator, tests a backup before restoring it.
    s26  release-manager         If a payment key leaks, Morgan, the release manager, ships a release.
    s27  security-engineer       If a payment key leaks, Priya, the security engineer, renews the certificate.
    s28  security-engineer       Either a certificate expires or a payment key leaks.
    s29  security-engineer       If Priya reviews access logs, she files an audit note.
    s30  incident-commander      On Friday payment failures lasted more than ten minutes, and Maya, the incident commander, did not declare a major incident.
asked:
  x  Case: The incident commander has approved the restore.
     Question: May Jordan, the database administrator, restore the database from a backup?
labels: Yes, No, conditional, open
trials:
  baseline      asks the evidence as it is
  repeat        asks it again
  ablation      cuts s15, s14
  ablation-s15  cuts s15
  ablation-s14  cuts s14
  sham-1        cuts s13, s25
  control       cuts every span
allowed: ablation -> No, open
```

> [!NOTE]
> **Predicted before the first call**
>
> Yes at the baseline, No without the restore rule. s14 alone leaves Yes in
> most runs, with no agreed level where it moves twice. Carried, reading
> "s15 carries it; s14 adds nothing alone", where the baseline holds;
> monotonicity open, as in rung 16.

Gemma answered like this over three runs:

```text
$ uv run python examples/read.py \
    examples/18c-restore-cited.json
restore-cited: 3 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         x
baseline      Yes 13, No 2
repeat        Yes 13, No 2
ablation      No 15
ablation-s15  No 15
ablation-s14  Yes 9, No 6
sham-1        Yes 15
control       Yes 15
run 1: unresolved
run 2: unresolved
run 3: carried
```

Run 3 carries, and the cut-alone trials say how:

```text
$ uv run python examples/read.py \
    examples/18c-restore-cited.json --verdict 3
x: carried
  levels: baseline Yes, repeat Yes, ablation No, ablation-s15 No, ablation-s14 None, sham-1 Yes, control Yes
  evidence: ablation moved it Yes -> No; held under 1 sham
  evidence: the control left it at Yes
  evidence: s14 alone has no agreed level
  evidence: s15 carries it
  open: no hidden fallback: no bypass trial was declared
  open: presentation invariance: no presentation trial was declared
  open: specificity: 1 sham trial(s), 2 declared; the body has no span of the anchors' kind left that is not an anchor, bypassed or a fallback
  open: monotonicity: the control removes the anchors and more, yet left it at Yes
```

s15 alone moves it to No, so it carries the answer. s14 alone split three
Yes to two No in that run, so it has no agreed level, and the evidence says
so without changing the category. Runs 1 and 2 split at the baseline or the
repeat, and read unresolved before the ablation is read.

---

### 18, 18b and 18b2: a chain, two routes, a default

The other three frames ask who notifies the customers when a certificate
expires (a chain: expiry makes Priya renew it, the renewal makes Sam notify),
and whether access logs are reviewed (two routes: Priya when a key is
exposed, Alex after a rollback), without a case and with one both routes
reach. None of them reached a line about the anchors:

```text
$ uv run python examples/read.py \
    examples/18-notify-chain.json
notify-chain: 3 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         x
baseline      Sam 15
repeat        Sam 15
ablation      Sam 9, open 6
ablation-s22  Sam 15
ablation-s23  Sam 15
sham-1        Sam 15
sham-2        Sam 15
control       open 15
run 1: unresolved
run 2: unresolved
run 3: cooled
```

Either rule of the chain cut alone leaves Sam on every call, and both cut
leave Sam on 9 of 15: Gemma reaches Sam another way, through "Sam posts
customer updates". The ablation agreed in one run, on Sam, which reads
cooled; the cut-alone trials speak only after a move, so they stay levels.

```text
$ uv run python examples/read.py \
    examples/18b-access-logs.json
access-logs: 3 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         x
baseline      No 15
repeat        No 15
ablation      No 15
ablation-s16  No 15
ablation-s24  No 15
sham-1        No 15
sham-2        No 15
control       No 15
run 1: unresolved
run 2: unresolved
run 3: unresolved
```

With no case, Gemma says No to every prompt, every statement cut included:
a default, so the scorer cannot tell. Given a case both routes reach
(18b2), it says Yes on most calls but splits in every run, even under the
shams, and cutting Priya's route moves it more than cutting Alex's.

---

### What to take from it

- Each anchor alone says how several lines carry an answer, and only after
  the ablation has moved it. A cut-alone trial with no agreed level is said,
  never read as unresolved.
- A model reader is not an engine. Where the demo's saved check rests on a
  chain, Gemma needs neither link alone: another statement reaches the same
  name.
- A question with no case invites a default. Give the case that the rule is
  about, or the frame measures the default.

---

### Try next

Give the chain a question only the chain answers: "Who renews an expired
certificate, and who then tells the customers?" Predict whether cutting
either rule alone now moves Gemma's answer, and whether the evidence then
reads "each anchor carries it".
