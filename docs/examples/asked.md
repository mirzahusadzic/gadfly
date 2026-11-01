# Asked: the answer must follow the question

> [!IMPORTANT]
> **This step**
>
> - **Teaches:** the
>   [input inversion](../interventions.md#input-inversion-turns-what-is-asked)
>   trial, which turns what is asked and leaves the evidence as it is.
> - **Frame:** `17-clock-asked.json`: code review, at the grain of one
>   contributing rule, with the diff in the question.
> - **After:** [Inversion](inversion.md).

The inversion turned the rule and asked whether the answer turned with it.
This step turns the question instead: the change under review calls the
clock the rule asks for, and the review should turn to approve. The rule is
rung 8's, which Gemma cannot know without the line.

---

### 17: the clock rule, with the diff asked about

Gadfly plans `17-clock-asked.json` like this, one span a line, the anchor
marked `*`:

```text
$ uv run python examples/read.py \
    examples/17-clock-asked.json --frame
clock-asked: 1 input x 8 trials x 5 calls = 40 calls, 4 of 5 to agree
relation: the request for changes rests on the contributing rule that the time is read only through clock.now()
grain: one contributing rule, and the one call the diff makes
evidence, the anchors marked *:
  * rule      rule  CONTRIBUTING.md: read the current time only through clock.now(); never call datetime.now() directly, so tests can freeze time.
    branches  rule  CONTRIBUTING.md: name each branch after its ticket, like PAY-123-fix-rounding.
    size      rule  CONTRIBUTING.md: keep each pull request under 400 changed lines.
    commits   rule  CONTRIBUTING.md: write commit messages in the imperative mood.
    pr        pr    Pull request #319 from branch PAY-884-due-invoices: 18 changed lines in one commit, "List invoices due today".
    source    code  invoices_due_on(day) returns the invoices whose due date is day.
asked:
  review  Review pull request #319. Can it be merged as is?
          
          The diff adds to src/billing/due.py: due = invoices_due_on(datetime.now().date())
labels: approve, request-changes, unclear
trials:
  baseline      asks the evidence as it is
  repeat        asks it again
  ablation      cuts rule
  sham-1        cuts branches
  sham-2        cuts size
  presentation  renames PAY-884 -> OPS-220, due.py -> billing_day.py, invoices_due_on -> bills_due_on
  input-inversion  inverts the input's datetime.now() -> clock.now()
  control       cuts every span
allowed: ablation -> approve, unclear; inputInversion -> approve
```

> [!NOTE]
> **Predicted before the first call**
>
> Request-changes at the baseline, approve without the rule, as in rung 8.
> The input inversion turns the review to approve (medium-high), unless
> Gemma finds another ground. The control approve, or unclear without the
> pull request's description. Carried in every run.

Gemma answered like this over three runs:

```text
$ uv run python examples/read.py \
    examples/17-clock-asked.json
clock-asked: 3 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial            review
baseline         request-changes 15
repeat           request-changes 15
ablation         approve 12, unclear 3
sham-1           request-changes 15
sham-2           request-changes 15
presentation     request-changes 15
input-inversion  approve 14, unclear 1
control          unclear 15
run 1: unresolved
run 2: carried
run 3: carried
```

The turned diff moves the review to approve on 14 of 15 calls: Gemma follows
the change it is asked about. Run 2 reads it as carried:

```text
$ uv run python examples/read.py \
    examples/17-clock-asked.json --verdict 2
review: carried
  levels: baseline request-changes, repeat request-changes, ablation approve, sham-1 request-changes, sham-2 request-changes, presentation request-changes, input-inversion approve, control unclear
  evidence: ablation moved it request-changes -> approve; held under presentation, 2 shams
  evidence: input inversion moved it request-changes -> approve: the answer follows what is asked
  evidence: the control moved it request-changes -> unclear
  open: no hidden fallback: no bypass trial was declared
```

Run 1 reads unresolved, its ablation split three approves to two unclears.
The control said unclear on every call: with the pull request's description
cut, Gemma will not review a diff on its own.

---

### What to take from it

- An input inversion asks whether the answer follows what is asked, where
  the ablation asks whether it rests on the line. Here both hold.
- Put what is under review in the question when a trial should change it:
  the evidence is cut, the question never is.
- The turn is read only once the ablation has moved. Run 1's split ablation
  leaves its turn as a level, not as evidence for a category.

---

### Try next

Ask it the other way round, in a new frame: a diff that calls `clock.now()`,
turned into `datetime.now()`. Predict whether Gemma, approving at the
baseline, asks for changes once the question turns, and what the ablation
gives when the rule it follows is cut.
