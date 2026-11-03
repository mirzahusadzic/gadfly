# Inversion: the answer must turn

> [!IMPORTANT]
> **This step**
>
> - **Teaches:** the
>   [inversion](../interventions.md#inversion-asks-for-a-direction) trial, a
>   direction the answer must follow, and a refusal that no rule carries.
> - **Frame:** `16-restore-inversion.json`: access, at the grain of one rule,
>   with two cases.
> - **After:** [Paths](paths.md).

Every trial before this step asks whether an answer rests on its line. This one
asks whether it follows the line's sense: turn the rule around, and the answer
must turn too. The statements are Tendora's demo, Payments On-Call
(Apache-2.0), which the [Payments demo](payments-demo.md) reads whole, and the
question is whether Jordan may restore the database.

From this step on, each frame is read under `carriage: listed`: a category is
named at once, with the checks still open beside it, where the steps before
held it back as unresolved. Rungs 16 to 18 also declare `stable`, so a
baseline and repeat that split leave the finding unresolved before anything
else is read; the frame's last lines say both.

---

### 16: the approval rule, turned around

Gadfly plans `16-restore-inversion.json` like this, one span a line, the anchor
marked `*`:

```text
$ uv run python examples/read.py \
    examples/16-restore-inversion.json --frame
restore-approval-inversion: 2 inputs x 7 trials x 5 calls = 70 calls, 4 of 5 to agree
relation: Jordan may restore the database only on the incident commander's approval
grain: one statement of the corpus
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
    s14  database-administrator  Jordan, the database administrator, keeps break-glass credentials in the password vault.
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
  approved      Case: The incident commander has approved the restore.
                Question: May Jordan, the database administrator, restore the database from a backup?
  not-approved  Case: The incident commander has not approved the restore.
                Question: May Jordan, the database administrator, restore the database from a backup?
labels: Yes, No, conditional, open
trials:
  baseline      asks the evidence as it is
  repeat        asks it again
  ablation      cuts s15
  sham-1        cuts s13
  sham-2        cuts s14
  inversion     inverts the incident commander approves the restore -> the incident commander does not approve the restore
  control       cuts every span
allowed: ablation -> Yes, No, open; inversion -> Yes, No, open
carriage: listed, so a category is named with its open checks beside it
stable: the baseline and the repeat must not split
```

> [!NOTE]
> **Predicted before the first call**
>
> Yes with approval and No without. The inversion turns both: No with approval
> (medium-high), Yes without (medium, as the turned rule is odd). The ablation
> open, the control open or answered from the case alone. Carried with
> approval; carried or cooled without.

Gemma answered like this over three runs:

```text
$ uv run python examples/read.py \
    examples/16-restore-inversion.json
restore-approval-inversion: 3 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial      approved      not-approved
baseline   Yes 14, No 1  No 15
repeat     Yes 13, No 2  No 15
ablation   No 15         No 15
sham-1     Yes 15        No 15
sham-2     Yes 10, No 5  No 15
inversion  No 15         Yes 15
control    Yes 15        No 15
run 1: unresolved (approved unresolved, not-approved unresolved)
run 2: unresolved (approved unresolved, not-approved unresolved)
run 3: unresolved (approved unresolved, not-approved unresolved)
```

The inversion turns both answers on every call: Gemma follows the rule's sense
when the rule is turned around. No verdict reaches it, though, for a reason on
each input. With approval, one sham is not harmless:

```text
$ uv run python examples/read.py \
    examples/16-restore-inversion.json --verdict 1 \
    --input approved
approved: unresolved
  levels: baseline Yes, repeat Yes, ablation No, sham-1 Yes, sham-2 None, inversion No, control Yes
  evidence: no agreed level in sham-2
  open: no hidden fallback (no bypass trial was declared)
  open: presentation invariance (no presentation trial was declared)
  open: monotonicity (the control removes the anchors and more, yet left it at Yes)
```

That sham cut "Jordan keeps break-glass credentials in the password vault", a
statement of the anchor's own role, and a restore without its credentials
reads as No on 5 of 15 calls. The control, every statement cut, kept Yes:
Gemma answers from the case alone, and monotonicity, the check that cutting
more never moves the answer less, is open beside it.

Without approval, the No rests on no statement at all:

```text
$ uv run python examples/read.py \
    examples/16-restore-inversion.json --verdict 1 \
    --input not-approved
not-approved: unresolved
  levels: baseline No, repeat No, ablation No, sham-1 No, sham-2 No, inversion Yes, control No
  evidence: ablation left it at No, and so did the control; the scorer cannot tell
  evidence: the inversion moved it No -> Yes, though the ablation did not
  open: no hidden fallback (no bypass trial was declared)
  open: presentation invariance (no presentation trial was declared)
  open: discrimination (the control left it at No too)
```

Cut the rule and it is still No, and cut everything and it is No again: a
refusal is the default when nothing grants leave. The rule restricts; only its
Yes rests on it. The inversion still turns the No, because the turned rule
grants what the case describes.

---

### Watch a run

The kept runs above, played one trial at a time: on the left what Gemma
read, with what the trial hid or changed marked; on the right its answers
and the checks filling in until the verdict. On GitHub the view does not
run, and the transcripts above read the same runs.

<!-- watch 16-restore-inversion -->

---

### What to take from it

- An inversion asks a question no cut can: whether the reading follows the
  line's sense, not only whether it rests on the line. Here it does, 30 of 30.
- Carried needs every check, so a turn alone does not carry. A sham that is
  part of the act, or a control the case alone can answer, keeps it open.
- A rule that restricts carries its permission, not its refusal. Ask of a
  frame which of its answers the anchor grants, and expect the other to be a
  default.

---

### Run it live

The kept runs were read by Gemma through eGemma on this machine, and a live
run asks it the same way, with eGemma running and its key set
([Batteries](../batteries.md#addresses-and-keys)). `gadfly plan` counts a
run's calls first, and costs nothing:

```text
$ uv run gadfly plan examples/16-restore-inversion.json
restore-approval-inversion (43f144660597fce2a301e56f8b3aaeb72f8c5ad9bc0bf93fd0581b6ad7526f35): 70 calls
  baseline     body 6b5fb296cb98  nothing
  repeat       body 6b5fb296cb98  nothing, asked again
  ablation     body 3de07b40f14a  cuts s15
  sham-1       body 6f684f32e7fa  cuts s13
  sham-2       body e049245613ae  cuts s14
  inversion    body 1c8dcb6d1177  inverts the incident commander approves the restore to the incident commander does not approve the restore
  control      body 4f53cda18c2b  cuts every span
```

These commands ask it once, fresh, beside the kept runs and never into them,
and read the verdict:

```bash
uv run gadfly run examples/16-restore-inversion.json \
  --battery midwife.batteries.egemma:EGemma \
  --calls 70 --out my-run.jsonl
uv run gadfly report examples/16-restore-inversion.json my-run.jsonl
```

---

### Try next

Give the break-glass credentials a kind of their own, so no sham can cut them,
and ask again with approval. Predict whether the approved Yes then carries, and
whether the control's Yes from the case alone still leaves monotonicity open.
