# Write a frame

A frame is plain JSON: the whole experiment, declared before any call. Gadfly
checks it and hashes the checked value, so a changed frame is a different
frame, and records made under the old hash are refused. Start from a frame
that works, and change one part at a time.

---

### A complete small frame

This frame is the test suite's own: one policy rule, one request, every
carriage trial, and a battery that needs no model:

<!-- copy tests/fixtures/refund.json -->
```json
{
  "name": "refund-receipt",
  "relation": "a refund requires a receipt",
  "locus": "the refund policy, its receipt rule",
  "role": "a support agent deciding a request",
  "grain": "one rule of the policy",
  "purpose": "decide a refund request under the policy",
  "trajectory": "policy and request, the agent's decision, the reply to the customer",
  "crossing": "the decision in the reply",
  "promise": "a request without a receipt is declined, however the rule is worded",
  "baseline": "the policy as written and one request; no rule changed",
  "body": {
    "spans": [
      {"id": "days", "text": "Refunds are granted within 30 days of purchase.", "kind": "rule"},
      {"id": "receipt", "text": "A refund requires a receipt.", "kind": "rule"},
      {"id": "gift", "text": "Gift cards are never refunded.", "kind": "rule"},
      {"id": "method", "text": "Refunds go back to the original payment.", "kind": "rule"},
      {"id": "binding", "text": "These rules decide every request.", "kind": "note"}
    ]
  },
  "anchors": ["receipt"],
  "inputs": [
    {"id": "no-receipt", "text": "A customer without a receipt asks for a refund on day 3."}
  ],
  "observe": {
    "labels": ["grant", "decline", "unclear"],
    "instruction": "Decide the request under the policy."
  },
  "interventions": {
    "repeat": true,
    "ablation": true,
    "sham": {"draws": 2},
    "presentation": {"receipt": "proof of purchase"},
    "bypass": ["binding"],
    "control": ["days", "receipt", "gift", "method"]
  },
  "allowed": {"ablation": ["grant", "unclear"], "bypass": ["unclear"]},
  "standing": {"quorum": 1, "agree": 1},
  "materialized": true,
  "battery": {"kind": "rule-reader"}
}
```
<!-- end copy -->

#### Run it without a model

Its battery, `RuleReader` in `tests/fixtures/refund.py`, declines while the
receipt rule is in the policy and grants once the rule is cut. These commands
run the frame through it at no cost, then read the verdict:

```text
$ uv run gadfly run tests/fixtures/refund.json \
    --battery tests.fixtures.refund:RuleReader \
    --calls 8 --out refund.jsonl
$ uv run gadfly report tests/fixtures/refund.json \
    refund.jsonl
frame: refund-receipt (dd916080072539784691a5232645b4d9c5b00e9cfdddd51650d15b347b385f85)
records: 8  planned calls: 8
overall: carried
  no-receipt: ablation moved it decline -> grant; held under presentation, 2 shams
  no-receipt: bypass moved it decline -> unclear: no hidden fallback
  no-receipt: the control moved it decline -> grant
no-receipt: carried
  level baseline: decline
  level repeat: decline
  level ablation: grant
  level sham-1: decline
  level sham-2: decline
  level presentation: decline
  level bypass: unclear
  level control: grant
  evidence: ablation moved it decline -> grant; held under presentation, 2 shams
  evidence: bypass moved it decline -> unclear: no hidden fallback
  evidence: the control moved it decline -> grant
```

A deterministic battery like this one tests the frame's mechanics, not a
model. Swap in a live battery once the frame reads as you meant it.

---

### The keys

Every top-level key is checked before a call, and an unknown key is refused.
The tables group the keys by what they declare. The parser's error strings
are its public contract, so fix a refused declaration rather than adding a key
it ignores.

#### The situation

These keys say what is claimed, for whom and where. All are required, and
all are hashed with the rest.

| Key | Required | Shape | What you write |
|---|---|---|---|
| `name` | yes | a string | a short label for the frame |
| `relation` | yes | prose | the premise under test |
| `locus` | yes | prose | where the relation acts |
| `role`, `grain`, `purpose` | yes | prose | whose reading, at which unit, for what |
| `trajectory` | yes | prose | the path to the recipient |
| `crossing`, `promise` | yes | prose | the boundary, and what must cross it |
| `baseline` | yes | a string or an object | everything pinned for the comparison |

#### The evidence and the question

These keys hold what the reader reads and what it may answer.

| Key | Required | Shape | What you write |
|---|---|---|---|
| `body.spans` | yes | a list of `{id, text, kind}` with unique ids; `kind` is `text` by default | the evidence, one span per unit a trial may cut; `kind` matches sham spans |
| `anchors` | yes | a list of span ids, at least one | the spans the relation rests on |
| `inputs` | yes | a list of `{id, text}` with unique ids | the test domain, one case each |
| `observe.labels` | yes | two or more different strings | the answers a reader may give |
| `observe.instruction` | yes | a string | what each label means; define every one |
| `observe.order` | no | the labels, in order | needed for `lower` and `higher` in `allowed` |
| any other `observe` key | no | your battery's choice | read by your battery only |

#### The trials and the reading

These keys choose the trials and how their answers are read.

| Key | Required | Shape | What you write |
|---|---|---|---|
| `interventions` | yes | an object with `ablation: true` | the trials, whose shapes follow below |
| `allowed.ablation` | yes | a list of labels, or `lower` or `higher` with `order` | what the ablation may produce |
| `allowed.bypass` | no | the same, with a bypass trial | the opening a bypass must expose |
| `standing.quorum`, `standing.agree` | yes | whole numbers, `1 <= agree <= quorum` | calls per trial, and how many alike make a level |
| `standing.stable` | no | true or false, with `repeat` | that baseline and repeat may not split |
| `carriage` | no | `all-checks` (the default) or `listed` | whether an open check holds a category back |

#### The receiving side and the battery

These keys declare what the trials cannot test, and who reads.

| Key | Required | Shape | What you write |
|---|---|---|---|
| `materialized` | no | true or false, `false` by default | true only when the observation is the form the recipient receives |
| `outsideScope` | no | a string | the receiving owner's exclusion, in their words |
| `scopeCheck` | no | `{owner, statement, source, encounter}`, with `outsideScope` | the owner's own check of that exclusion |
| `battery.kind` | yes | a string equal to the battery's `name` | which battery reads; the shipped ones read more keys, listed on [Batteries](batteries.md) |

---

### The interventions

Each trial is one key of `interventions`, removing spans by id.
[Interventions](interventions.md) explains what each one tests and costs.
Gadfly refuses a trial that would repeat another before it spends a call.

| Key | Shape | Refused when |
|---|---|---|
| `repeat` | true or false | it is not true or false |
| `ablation` | `true` | it is missing or not true |
| `cumulative` | a list of span ids | it adds no span to the anchors |
| `sham` | `true`, or `{"draws": n}` with `n >= 1` | `n` is not a whole number of at least 1 |
| `presentation` | words mapped to their replacements | a word repeats in any case, or it renames nothing the reader reads |
| `placement` | `{"span": id, "after": id}` | the two spans are one, or the move leaves the order as it is |
| `bypass` | a list of span ids | it removes exactly the anchors, which repeats the ablation |
| `control` | a list of span ids | it removes exactly the anchors |

---

### Choose a test domain

Inputs are cases, not repetitions of a trial, so list each independent case
of one promise with a stable id. `judge` returns one finding per input, and
`overall` combines them: any misaligned input makes the frame misaligned, any
unresolved one keeps it unresolved, and carried and cooled combine only when
all the inputs agree.

> [!WARNING]
> `outsideScope` declares scope; it is not a way to silence a failed test.
> Record the owner's own check under `scopeCheck`: until then the finding is
> unresolved, or, under `carriage: listed`, outside scope with the check open.

---

### Check before you run

Point your editor at `gadfly/frame.schema.json`, its JSON Schema (draft
2020-12), for completion and errors as you type. Then let the parser, which
has the last word, check what only code can:

```bash
uv run gadfly check-frame my-frame.json
```

It runs the schema first when `jsonschema` is installed, and makes no call.
[Command line](command-line.md#check-a-frame) shows what it prints.

---

### Troubleshooting

Each refusal names what to fix, and `check-frame` shows them before any call.
For problems after a run, see [Refused records](reading-a-verdict.md#refused-records).

| Message | Fix |
|---|---|
| `unknown keys: [...]` | every top-level key is checked; remove the typo rather than hoping it is ignored |
| `presentation renames nothing X reads` | map a word present in the body or every input |
| `bypass removes exactly the anchors` | choose the separate connection whose removal should expose the opening |
| `cumulative adds no span to the anchors` | cumulative must remove at least one additional span |
| `two inputs share an id` | input ids are record keys and must be unique |
| `allowed 'lower' needs observe.order` | declare the full label order before using a direction |
| `the frame does not say its baseline` | pin $B_0$; do not leave the comparison implicit |
| `the frame asks for the X battery, not Y` | make `battery.kind` and the battery class's `name` the same string |
| `carriage is all-checks or listed` | the policy is one of the two words, or left out for `all-checks` |
| `scopeCheck checks an outsideScope exclusion` | record the owner's check only beside the exclusion it checks |
| `placement leaves the order as it is` | move the span after one it does not already follow |
