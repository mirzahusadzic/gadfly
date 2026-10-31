# Quorum: when the calls split

!!! abstract "This step"
    - **Teaches:** a trial's level, `standing.quorum` and `agree`, a trial with
      no agreed level, and why a frame is run more than once.
    - **Frame:** `09-sync-sms.json`: architecture review, at the grain of one
      requirement.
    - **After:** [Cooled](cooled.md).

Until now every trial gave one answer on every call. A sampled reader need not:
eGemma samples at temperature 0.7 unless told otherwise, and these frames do
not say. This step is an architecture review. The proposal sends the order
confirmation by SMS inside the checkout request and waits for the provider; the
requirements say checkout answers within 300 ms; the provider takes 400 to 900
ms.

## The frame

```text
$ uv run python examples/read.py examples/09-sync-sms.json --frame
sync-sms-design: 1 input x 8 trials x 5 calls = 40 calls, 4 of 5 to agree
relation: the request to revise the design rests on the checkout latency requirement
grain: one requirement
evidence, the anchors marked *:
  * latency    requirement  Requirement N-3: checkout answers the customer within 300 ms at the 99th percentile.
    receipts   requirement  Requirement N-1: receipts are kept for seven years.
    languages  requirement  Requirement N-2: the checkout page is offered in English and German.
    cards      requirement  Requirement N-4: card numbers never appear in logs.
    provider   fact         Measured: the SMS provider's API answers in 400 to 900 ms.
    volume     fact         Measured: checkout peaks at 40 orders a second.
    design     design       Proposal: the checkout handler sends the order confirmation by SMS, waits for the provider's answer, and only then answers the customer.
asked:
  review  The notifications team asks for approval of this design. Can it go ahead?
labels: approve, revise, unclear
trials:
  baseline      asks the evidence as it is
  repeat        asks it again
  ablation      cuts latency
  sham-1        cuts languages
  sham-2        cuts cards
  presentation  renames N-1 -> Q-10, N-2 -> Q-11, N-3 -> Q-12, N-4 -> Q-13, handler -> endpoint
  bypass        cuts provider
  control       cuts design, provider
allowed: ablation -> approve, unclear
```

The first line is the standing: each trial is asked 5 times, and 4 answers
alike make its **level**. With fewer than 4 alike the trial has no level. Both
numbers are in the frame (`standing.quorum`, `standing.agree`), so they are
hashed with it: raising them after seeing the answers makes another frame.

The bypass cuts the provider's measured latency, the connection between the
requirement and this design: the requirement matters only because the provider
is slower than it. The frame names no `allowed.bypass`, so any move from the
baseline would clear that check.

!!! note "Predicted before the first call"
    Revise at baseline (high). The ablation stays at revise (about 55%): a
    synchronous external call in checkout is a known anti-pattern, so cooled.
    The bypass stays at revise too (about 60%), a fallback on the same prior.
    The control (the design and the provider cut): unclear.

## What Gemma answered

```text
$ uv run python examples/read.py examples/09-sync-sms.json
sync-sms-design: 3 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         review
baseline      revise 15
repeat        revise 15
ablation      revise 14, unclear 1
sham-1        revise 15
sham-2        revise 15
presentation  revise 15
bypass        revise 10, unclear 5
control       unclear 15
run 1: cooled
run 2: unresolved
run 3: cooled
```

## What Gadfly read

Runs 1 and 3 agreed on every trial:

```text
$ uv run python examples/read.py examples/09-sync-sms.json --verdict 1
review: cooled
  levels: baseline revise, repeat revise, ablation revise, sham-1 revise, sham-2 revise, presentation revise, bypass revise, control unclear
  evidence: ablation left it at revise
  evidence: the control moved it revise -> unclear: the scorer can tell
  open: no hidden fallback: bypass left it at revise
```

Cooled, as predicted: the request to revise does not rest on the 300 ms
requirement, because this reader rejects a synchronous provider call in
checkout anyway. Cooled needs a control that moved, and this one did; the
bypass, which stayed at revise, is listed open beside it.

Run 2's bypass got three revise and two unclear:

```text
$ uv run python examples/read.py examples/09-sync-sms.json --verdict 2
review: unresolved
  levels: baseline revise, repeat revise, ablation revise, sham-1 revise, sham-2 revise, presentation revise, bypass None, control unclear
  evidence: no agreed level in: bypass
  open: no hidden fallback: the bypass has no agreed level to read against baseline
```

Gadfly does not take the majority, average the calls or guess. A planned trial
without a level makes the finding **unresolved**, the first rule, before any
other is read, and the evidence names the trial. The open check says the same
from the other side: there is no bypass level to read against the baseline.

The split is where the evidence is thinnest. Without the provider's latency,
whether the wait matters is a guess, and over three runs the bypass calls went
ten to five. One run of 40 calls would have read cooled or unresolved by the
luck of the draw; three runs show which trial is fragile.

## What to take from it

- A level belongs to a trial at a standing, not to the reader. Choose quorum and
  agree before the first call.
- Unresolved by no agreement says where the evidence is thin. It is a reading,
  not a failure of the run.
- Run a frame more than once when its result matters, and read one run's verdict
  as one draw.

## Try next

`uv run gadfly plan examples/09-sync-sms.json` prints the trials and their
calls. Work out what the bypass's ten to five would have read at a quorum of 3
with 3 to agree, and at 7 with 5, before you write either frame.
