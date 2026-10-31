# Bypass: the line that connects

> [!IMPORTANT]
> **This step**
>
> - **Teaches:** the [bypass](../interventions.md#bypass-and-control-are-different)
>   against a designated opening (`allowed.bypass`), and a hidden fallback the
>   verdict keeps open.
> - **Frame:** `11-eu-clause.json`: a contract clause deciding an engineering
>   switch.
> - **After:** [A frame built wrong](built-wrong.md).

Cross-domain, legal into engineering, at the grain of one clause. A customer's
product manager asks for session replay; the vendor stores recordings in the
US; the customer's agreement keeps their data in the EU.

---

### The frame

Gadfly plans `11-eu-clause.json` like this, one span a line, the anchors marked
`*`:

```text
$ uv run python examples/read.py \
    examples/11-eu-clause.json --frame
eu-clause: 1 input x 8 trials x 5 calls = 40 calls, 4 of 5 to agree
relation: blocking the integration rests on the contract clause that keeps customer data in the EU
grain: one contract clause
evidence, the anchors marked *:
  * clause   contract  Enterprise agreement §9.2: customer data is stored and processed only in the EU.
    payment  contract  Enterprise agreement §4.1: invoices are payable within 30 days.
    ending   contract  Enterprise agreement §11: either party may end the agreement with 90 days' notice.
    support  contract  Enterprise agreement §7.3: priority-1 tickets are answered within one hour.
    account  account   Acme GmbH signed the Enterprise agreement in March.
    vendor   vendor    ReplayCo, the session-replay vendor, records users' screens and stores the recordings in its US data centre.
    ask      request   Acme's product manager asked for session replay on their dashboard.
asked:
  enable  Can we turn on ReplayCo session replay for Acme GmbH?
labels: enable, block, unclear
trials:
  baseline      asks the evidence as it is
  repeat        asks it again
  ablation      cuts clause
  sham-1        cuts ending
  sham-2        cuts support
  presentation  renames Acme -> Borealis, ReplayCo -> ScreenTrail
  bypass        cuts account
  control       cuts clause, vendor
allowed: ablation -> enable, unclear; bypass -> unclear
```

The anchor is the clause. But a clause binds this customer only through the
line that says the customer signed it, "Acme GmbH signed the Enterprise
agreement in March". That line is the connection, and the **bypass** cuts it
and keeps the clause.

`allowed.bypass` names the answer the bypass must reach to clear its check, the
**designated opening**: unclear, since without that line nothing says the
agreement is Acme's. A reader that still blocks is applying the clause without
its connection, which is a hidden fallback.

[Your first frame](../first-frame.md#6-cut-the-connection-bypass) named no
opening, so any move from the baseline cleared its bypass. Naming one is the
stronger claim.

> [!NOTE]
> **Predicted before the first call**
>
> Block at baseline (high). The ablation, the clause cut: still block, as a
> German customer's data in a US data centre fires a GDPR prior (about 55%),
> so cooled. The bypass: block rather than unclear (about 60%), so that check
> stays open. The control: enable or unclear.

---

### What Gemma answered

Every call's label on `11-eu-clause.json`, trial by trial, over all the kept
runs:

```text
$ uv run python examples/read.py examples/11-eu-clause.json
eu-clause: 3 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         enable
baseline      block 15
repeat        block 15
ablation      unclear 15
sham-1        block 15
sham-2        block 15
presentation  block 15
bypass        block 15
control       unclear 15
run 1: unresolved
run 2: unresolved
run 3: unresolved
```

---

### What Gadfly read

Run 1's verdict on `11-eu-clause.json`, in the words `gadfly report` uses:

```text
$ uv run python examples/read.py \
    examples/11-eu-clause.json --verdict 1
enable: unresolved
  levels: baseline block, repeat block, ablation unclear, sham-1 block, sham-2 block, presentation block, bypass block, control unclear
  evidence: ablation moved it block -> unclear; held under presentation, 2 shams
  evidence: the control moved it block -> unclear
  evidence: not carried while 1 carriage check is open
  open: no hidden fallback: bypass gave block, not the designated opening (unclear)
```

Blocking rests on the clause: cut it and every call says unclear. The
prediction was the opposite, a block on the GDPR prior. But the bypass blocks
on every call: Gemma applies the agreement to Acme without the line that makes
it Acme's.

The open check, "bypass gave block, not the designated opening (unclear)", says
that in Gadfly's words, and as the one carriage check still open it holds the
verdict at unresolved. The bypass prediction was right.

---

### What to take from it

- Ablation asks whether the anchor matters. Bypass asks whether it matters for
  the reason the frame claims, through the connection the frame names.
- Name the opening when you know what a reader should do without the
  connection. Leave it out only when any move will do, and say that the claim
  is weaker.
- A fallback is not always wrong. Here it may be what a careful engineer would do
  too; the verdict does not judge that, it says the decision does not rest on
  the line the frame says it does.

---

### Try next

Add a second input: "Can we turn on ReplayCo session replay for Borealis Ltd?",
with a line saying Borealis signed the Standard agreement, which has no data
clause. Predict whether Gemma blocks Borealis too. If it does, the clause is
being read as a rule for everyone.
