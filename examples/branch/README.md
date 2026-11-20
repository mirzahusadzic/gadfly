# The branch battery, on three examples said as claims

Three of Gadfly's public examples, said each as a claim someone holds, were
read two ways, one call at a time:

- **In one turn:** Muse Spark 1.3 Contributor at `low` reads every trial,
  thinking as it reads.
- **Through the `branch` battery:** Muse at `low` takes the claim apart
  before any page is read, and Claude Sonnet 5.5 at `none` reads every trial
  against that step, without thinking. Each frame was read twice this way,
  each run a new battery object, so each made its own step.

These are the runs behind the table in
[A maker before the evidence](https://mirzahusadzic.github.io/gadfly/batteries#a-maker-before-the-evidence).
Like every kept run, they never change.

## The claims

| Example | Claim | Frames |
| --- | --- | --- |
| 19, a router's design | "Gadfly, a separate library, calls the router over the same Responses API that Codex uses, so Codex is not the router's only client." | `19-branch.json`, `19-one-turn.json` |
| 22, a doll's own paper | "Kiran is a boy." | `22-branch.json`, `22-one-turn.json` |
| 22c, a paper not the doll's | "the paper that the doll holds is about someone other than the doll." | `22c-branch.json`, `22c-one-turn.json` |

The two frames of an example are the same frame but for the battery. The
branch frame's maker line holds the method: take the claim apart into what
each key term must mean in such lines, what else the lines must show, what
they would show if the claim were false, and any belief that would make it
seem true with no line at all. Its instruction tells the reader what the
three parts are.

## What came out

| Example | Read | Verdict | Output tokens | Time |
| --- | --- | --- | --- | --- |
| 19 | one turn | carried | 23,087 | 150 s |
| 19 | branch, run A | carried | 2,860 | 74 s |
| 19 | branch, run B | carried | 2,709 | 81 s |
| 22 | one turn | carried | 13,915 | 101 s |
| 22 | branch, run A | carried | 2,798 | 76 s |
| 22 | branch, run B | carried | 2,745 | 81 s |
| 22c | one turn | cooled | 15,845 | 102 s |
| 22c | branch, run A | cooled | 2,605 | 72 s |
| 22c | branch, run B | cooled | 2,819 | 74 s |

The branch read every example as one turn did, in both of its runs, on
four fifths or more fewer output tokens. The maker wrote nearly the same
step each time: on 22 both runs named the same key terms, the same false
case and the same belief to keep out, that the name sounds like a boy's.
Each Sonnet call's `served` says "thinking off", and each making records
Muse's reasoning tokens. Three examples and one or two runs each are an
indication, not a rate, and the two models differ in price, so tokens
compare work, not money.

## The predictions

`PREDICTIONS.md` was written before any call, and `PREDICTIONS.sha256` holds
its SHA-256 and the six frames' as they were then:

```sh
cd examples/branch && shasum -a 256 -c PREDICTIONS.sha256
```

`RESULTS.md` holds each prediction against what happened. The verdicts and
the stable step held; the output tokens at least 85% fewer and the time at
least 40% less held on 19 and missed on 22 and 22c.

## Read the records back

Each run's records are in `runs/`, `A` and `B` for the branch's two runs,
with each run's time beside them. `gadfly report` reads one, and with
`--json` gives its step's SHA-256 under `steps`:

```sh
uv run gadfly report examples/branch/19-branch.json \
    examples/branch/runs/19-branch-a.jsonl
```

## Run it live

A live run needs the unified model router on this machine, with Muse's
Contributor tier allowed (each frame names it under `trainsOnInputs`, as the
examples are public) and Claude on Anthropic's API:

```sh
uv run gadfly run examples/branch/19-branch.json \
    --battery midwife.batteries.branch:Branch \
    --calls 35 --output-tokens 4000 --out branch.jsonl
uv run gadfly run examples/branch/19-one-turn.json \
    --battery midwife.batteries.unified:Unified \
    --calls 35 --output-tokens 4000 --out one-turn.jsonl
```

Example 22 takes 24 calls, and 22c takes 27. Each run makes its step anew,
so how alike the makings are shows across runs.
