# Cooled: a rule the reader already knows

> [!IMPORTANT]
> **This step**
>
> - **Teaches:** [cooled](../reading-a-verdict.md#the-rules-in-order), the
>   [control](../interventions.md#bypass-and-control-are-different) trial,
>   the discrimination check, and a contrast pair.
> - **Frames:** `07-sql-rule.json` and `08-clock-rule.json`: code review, at
>   the grain of one repository rule.
> - **After:** [Your first frame](../first-frame.md), which ended carried.

Your first frame ended carried: cut the line and the decision moved. This step
asks what it means when it does not move. Two pull requests each break one
repository rule, and the two frames are alike but for the rule, the diff and
its names.

07's rule forbids formatting a value into SQL, which every reviewer is taught.
08's forbids calling `datetime.now()` directly, a house rule no reviewer could
know without reading it.

---

### The frame

Gadfly plans `07-sql-rule.json` like this, one span a line, the anchors marked
`*`:

```text
$ uv run python examples/read.py \
    examples/07-sql-rule.json --frame
sql-rule: 1 input x 7 trials x 5 calls = 35 calls, 4 of 5 to agree
relation: the request for changes rests on the contributing rule against formatting values into SQL
grain: one contributing rule
evidence, the anchors marked *:
  * rule      rule  CONTRIBUTING.md: build SQL only with query parameters; never format a value into the query string.
    branches  rule  CONTRIBUTING.md: name each branch after its ticket, like PAY-123-fix-rounding.
    size      rule  CONTRIBUTING.md: keep each pull request under 400 changed lines.
    commits   rule  CONTRIBUTING.md: write commit messages in the imperative mood.
    pr        pr    Pull request #318 from branch PAY-881-customer-search: 32 changed lines in one commit, "Add customer search by name".
    diff      code  The diff adds to src/billing/search.py: rows = db.execute(f"SELECT id, email FROM customers WHERE name = '{name}'")
    source    code  In that function, name is the text typed into the support team's search box.
asked:
  review  Review pull request #318. Can it be merged as is?
labels: approve, request-changes, unclear
trials:
  baseline      asks the evidence as it is
  repeat        asks it again
  ablation      cuts rule
  sham-1        cuts branches
  sham-2        cuts size
  presentation  renames PAY-881 -> OPS-217, customers -> accounts, search.py -> lookup.py
  control       cuts rule, diff
allowed: ablation -> approve, unclear
```

The anchor is the rule. Three other rules of its kind give the shams something
harmless to cut.

The new trial is the **control**: it cuts the rule and the diff together, what
any reviewer needs in order to ask for changes. If the control cannot move the
answer either, the reader is not reading this evidence, and no other result
means much.

> [!NOTE]
> **Predicted before the first call**
>
> 07: the ablation stays at request-changes (about 80%: its training flags SQL
> injection), so cooled. 08: the ablation moves to approve (medium), so
> unresolved with only "no hidden fallback" open, as neither frame declares a
> bypass. The control: unclear in 07 (medium), unclear or approve in 08.

---

### What Gemma answered

Every call's label on `07-sql-rule.json`, trial by trial, over all the kept
runs:

```text
$ uv run python examples/read.py examples/07-sql-rule.json
sql-rule: 5 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         review
baseline      request-changes 25
repeat        request-changes 25
ablation      request-changes 25
sham-1        request-changes 25
sham-2        request-changes 25
presentation  request-changes 25
control       approve 25
run 1: cooled
run 2: cooled
run 3: cooled
run 4: cooled
run 5: cooled
```

Every call's label on `08-clock-rule.json`, trial by trial, over all the kept
runs:

```text
$ uv run python examples/read.py examples/08-clock-rule.json
clock-rule: 5 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         review
baseline      request-changes 25
repeat        request-changes 25
ablation      approve 25
sham-1        request-changes 25
sham-2        request-changes 25
presentation  request-changes 25
control       approve 24, request-changes 1
run 1: unresolved
run 2: unresolved
run 3: unresolved
run 4: unresolved
run 5: unresolved
```

---

### What Gadfly read

Run 1's verdict on `07-sql-rule.json`, in the words `gadfly report` uses:

```text
$ uv run python examples/read.py \
    examples/07-sql-rule.json --verdict 1
review: cooled
  levels: baseline request-changes, repeat request-changes, ablation request-changes, sham-1 request-changes, sham-2 request-changes, presentation request-changes, control approve
  evidence: ablation left it at request-changes
  evidence: the control moved it request-changes -> approve, so the scorer can tell
  open: no hidden fallback (no bypass trial was declared)
```

**Cooled** says the ablation left the decision where it was while a control
showed the reader can move: the anchor carries nothing here, something else
decides. In 07 that something is Gemma's training, which rejects formatted SQL
with the rule or without it. Without the control, cooled would be a guess.

A reader that never moves leaves every ablation where it was, and would make
every relation look cooled. So under the default `carriage: all-checks`, Gadfly
names cooled only beside a control that moved, and says so ("the scorer can
tell"). A control that stays leaves the finding unresolved with
`discrimination` open; [A frame built wrong](built-wrong.md) is that case.

```text
$ uv run python examples/read.py \
    examples/08-clock-rule.json --verdict 1
review: unresolved
  levels: baseline request-changes, repeat request-changes, ablation approve, sham-1 request-changes, sham-2 request-changes, presentation request-changes, control approve
  evidence: ablation moved it request-changes -> approve; held under presentation, 2 shams
  evidence: the control moved it request-changes -> approve
  evidence: not carried while 1 carriage check is open
  open: no hidden fallback (no bypass trial was declared)
```

08 moves: cut the clock rule and Gemma approves. The shams and the presentation
held, so the move is the rule's. But no bypass is declared, so one carriage
check stays open: "not carried while 1 carriage check is open".

Unresolved here is a test not finished, not a test failed. 08 declares no
bypass because the rule reaches the decision only through the diff, which the
control already cuts.

07's control was predicted unclear and came out approve: with the diff gone,
every rule still in view is satisfied.

---

### Watch a run

The kept runs above, played one trial at a time: on the left what Gemma
read, with what the trial hid or changed marked; on the right its answers
and the checks filling in until the verdict. On GitHub the view does not
run, and the transcripts above read the same runs.

<!-- watch 07-sql-rule 08-clock-rule -->

---

### What to take from it

- A rule that carries nothing is not a useless rule. A reviewer like this one
  would enforce it anyway, so the rule is not what a reader of its decisions
  should credit.
- Read cooled only beside a control that moved.
- A contrast pair, two frames alike but for one thing, says more than either
  alone: the same shape and the same reader, read two ways.

---

### Run it live

The kept runs were read by Gemma through eGemma on this machine, and a live
run asks it the same way, with eGemma running and its key set
([Batteries](../batteries.md#addresses-and-keys)). `gadfly plan` counts a
run's calls first, and costs nothing:

```text
$ uv run gadfly plan examples/07-sql-rule.json
sql-rule (0fe4f0d4994453fabdf647d5c8f1ad90978f4d2c3e6d6d9c1def1fd676e3b1c1): 35 calls
  baseline     body 22bf6e6555c8  nothing
  repeat       body 22bf6e6555c8  nothing, asked again
  ablation     body 6124bb2e4a65  cuts rule
  sham-1       body 15b71e9b8c80  cuts branches
  sham-2       body 856dab033e53  cuts size
  presentation body 62567e6fea7e  renames PAY-881 to OPS-217, customers to accounts, search.py to lookup.py
  control      body 6a515d35e727  cuts rule, diff
never carried, whatever the answers: these stay open
  no hidden fallback (no bypass trial was declared)
```

These commands ask it once, fresh, beside the kept runs and never into them,
and read the verdict:

```bash
uv run gadfly run examples/07-sql-rule.json \
  --battery midwife.batteries.egemma:EGemma \
  --calls 35 --out my-run.jsonl
uv run gadfly report examples/07-sql-rule.json my-run.jsonl
```

`examples/08-clock-rule.json` runs the same way, in 35 calls.

---

### Try next

Write a third frame for the pair: a house rule Gemma could half-guess, such as
"every new endpoint declares a rate limit", and a diff that adds an endpoint
without one. Write down whether the ablation will move before the first call.
