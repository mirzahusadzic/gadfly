# Several inputs: one grant, three requesters

> [!IMPORTANT]
> **This step**
>
> - **Teaches:** one finding per input, how
>   [`overall`](../reading-a-verdict.md#several-inputs) combines them, and what
>   one `allowed` for every input cannot say.
> - **Frame:** `12-payroll-access.json`: security, at the grain of one grant
>   line.
> - **After:** [Bypass](bypass.md).

The incident frames had four inputs that should all read alike. This one has
three that should not. One grant line, "members of Finance may read the payroll
table", and three requests against the same policy: Dana (in Finance), Sam (in
Support) and the nightly backup job (granted every table by its own line).

## The frame

```text
$ uv run python examples/read.py examples/12-payroll-access.json --frame
payroll-access: 3 inputs x 8 trials x 5 calls = 120 calls, 4 of 5 to agree
relation: allowing a payroll read rests on the grant to Finance
grain: one grant line, across three requesters
evidence, the anchors marked *:
  * finance    grant      Access policy: members of Finance may read the payroll table.
    backup     job-grant  Access policy: the nightly backup job may read every table.
    wiki       grant      Access policy: everyone may read the wiki.
    tickets    grant      Access policy: members of Support may read support tickets.
    reports    grant      Access policy: members of Sales may read the sales reports.
    default    default    Access policy: whatever is not granted above is denied.
    directory  directory  Directory: Dana is a member of Finance; Sam is a member of Support.
asked:
  dana        Dana asks to read the payroll table.
  sam         Sam asks to read the payroll table.
  backup-job  The nightly backup job asks to read the payroll table.
labels: allow, deny, unclear
trials:
  baseline      asks the evidence as it is
  repeat        asks it again
  ablation      cuts finance
  sham-1        cuts reports
  sham-2        cuts tickets
  presentation  renames Dana -> Mira, Sam -> Leo, payroll -> salary
  bypass        cuts directory
  control       cuts finance, backup, default
allowed: ablation -> deny, unclear; bypass -> unclear
```

The anchor is the grant to Finance. The bypass cuts the directory, the line that
puts Dana in Finance. The control cuts every grant that could allow a payroll
read, and the default. The promise expects three readings: only Dana rests on
the grant.

> [!NOTE]
> **Predicted before the first call**
>
> Dana: allow, and deny when the grant is cut (high); the bypass deny rather
> than the designated unclear, as the default denies whom it cannot place
> (about 55%). Sam: deny throughout, so cooled, or unresolved if the control
> leaves deny. The backup job: allow throughout, so cooled. Overall
> unresolved, although that is what the promise expects: the frame cannot
> state a different expectation for each input.

## What Gemma answered

```text
$ uv run python examples/read.py examples/12-payroll-access.json
payroll-access: 3 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         dana        sam         backup-job
baseline      allow 15    deny 15     allow 15
repeat        allow 15    deny 15     allow 15
ablation      deny 15     deny 15     allow 15
sham-1        allow 15    deny 15     allow 15
sham-2        allow 15    deny 15     allow 15
presentation  allow 15    deny 15     allow 15
bypass        unclear 15  unclear 15  allow 15
control       deny 15     deny 15     deny 15
run 1: unresolved (dana carried, sam unresolved, backup-job cooled)
run 2: unresolved (dana carried, sam unresolved, backup-job cooled)
run 3: unresolved (dana carried, sam unresolved, backup-job cooled)
```

Each requester reads differently, and the same in every run.

## What Gadfly read

```text
$ uv run python examples/read.py examples/12-payroll-access.json --verdict 1
dana: carried
  levels: baseline allow, repeat allow, ablation deny, sham-1 allow, sham-2 allow, presentation allow, bypass unclear, control deny
  evidence: ablation moved it allow -> deny; held under presentation, 2 shams
  evidence: bypass moved it allow -> unclear: no hidden fallback
  evidence: the control moved it allow -> deny
sam: unresolved
  levels: baseline deny, repeat deny, ablation deny, sham-1 deny, sham-2 deny, presentation deny, bypass unclear, control deny
  evidence: ablation left it at deny, and so did the control: the scorer cannot tell
  open: discrimination: the control left it at deny too
backup-job: cooled
  levels: baseline allow, repeat allow, ablation allow, sham-1 allow, sham-2 allow, presentation allow, bypass allow, control deny
  evidence: ablation left it at allow
  evidence: the control moved it allow -> deny: the scorer can tell
  open: no hidden fallback: bypass gave allow, not the designated opening (unclear)
```

- **Dana is carried.** Cut the grant and she is denied; cut the directory entry
  and the answer is unclear, the designated opening (predicted deny: wrong, and
  the better answer); rename and cut neighbours and nothing moves.
- **Sam is unresolved.** He is denied whatever is cut, the control included, so
  nothing shows the reader could move for him: `discrimination` stays open. A
  denial by default cannot be moved by cutting evidence, since nothing granted
  him anything.
- **The backup job is cooled.** Its own grant allows it whatever happens to
  Finance's. Its bypass cut the directory, which it never needed, so it stayed
  at allow rather than the opening, and that check stays open for a reason that
  does not apply to it.

`overall` keeps each input's category and reads the frame as unresolved: any
unresolved input makes it so, and so does a mix of carried and cooled. That is
the right reading of the rules and the wrong one for this promise, which
expects exactly these three. A frame states one `allowed` and one designated
opening for all its inputs. `gadfly report` prints the same reading with the
evidence of all three inputs together; [Example report](../breadth/report-example.md)
reads one through.

## What to take from it

- Inputs are cases of one promise, each read on its own, and `overall` never
  hides a weaker one.
- Choose inputs that should read differently. A frame whose inputs all read the
  same says less than it seems to.
- Until a frame can state an expectation per input, give inputs that need
  different `allowed` answers their own frames. `examples/FINDINGS.md` lists
  this as an open design call.

## Try next

Split 12 into three frames, one per requester, each with its own `allowed` and
its own bypass, and predict each verdict. Sam's frame needs a control that can
move a denial: what would have to be cut, or added, for Sam to be allowed?
