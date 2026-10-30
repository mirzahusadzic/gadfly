# Extending Gadfly

The core is deliberately small. These are concrete extensions in order of the
need they answer, with the contracts each must keep. Priorities and effort are
relative to this repository at `306537f`.

| ID | Capability | Priority | Effort | What it replaces | Artifact |
|---|---|---|---|---|---|
| E1 | CLI runner and human report | high | medium | ad-hoc `examples/*.py` command wrappers | `breadth/gadfly_cli.py`, `breadth/report-example.md` |
| E2 | Frame JSON Schema and authoring check | high | small | prose-only field table for editor validation | `breadth/frame.schema.json` |
| E3 | Portfolio summary without a synthetic verdict | medium | medium | manually combining `Overall` records in a spreadsheet | `breadth/portfolio.py` |
| E4 | `placement` intervention | medium | large | a second frame made only to move one span | `breadth/placement-intervention.md` |
| E5 | `local-json` battery | medium | medium | copy-pasted loopback HTTP batteries | `breadth/local-json-battery.md` |

## E1: CLI and report

Need: the essay requires retained evidence and visible obligations. Today a
reader must write Python to keep records and then join `evidence + obligations`
in an ad-hoc print loop.

Interface:

```bash
gadfly plan examples/refund.json
gadfly run examples/refund.json --battery examples.refund:RuleReader --calls 7 --out records.jsonl
gadfly report examples/refund.json records.jsonl
```

The prototype is `breadth/gadfly_cli.py`. It uses only the public pipeline,
writes each `Record.as_dict()` as one JSON object per line, refuses to overwrite
an output file, requires an explicit call budget, and never hides a stopped run.
The human report keeps evidence and obligations separate.

Contracts kept: no runtime dependencies; JSON Lines record keys unchanged;
frame/hash computed by `situate`; no state beyond the output file; no live call
unless `run` is invoked with a battery. Cost: roughly 200 lines plus subprocess
tests for exit codes and partial runs.

## E2: JSON Schema and authoring check

Need: declaration errors should be visible in an editor before a run. The code's
parser remains the authority because cross-field rules (anchor ids, label order,
non-vacuous presentation, stable requiring repeat) are not all expressible in
JSON Schema.

`breadth/frame.schema.json` is the structural draft. A follow-on command should be:

```bash
gadfly check-frame path/to/frame.json --format json
```

It runs the schema for field suggestions, then `situate()` for the authoritative
error. Output names the path and the smallest fix. It must not invent defaults or
rewrite the frame. Cost: small schema maintenance plus a parser-to-schema parity
test for every example.

## E3: portfolio summary

Need: `overall()` is defined over one frame's inputs. There is no fixed rule for
combining different relations, promises and recipients, so a synthetic portfolio
verdict would be a category error.

Interface:

```bash
gadfly report --json frame-a records-a.jsonl > a.json
gadfly report --json frame-b records-b.jsonl > b.json
python breadth/portfolio.py a.json b.json
```

The prototype reports frame counts by category, shared obligations, and frames
whose inputs disagree. It deliberately emits **no portfolio category**. Cost:
about 150 lines and tests for duplicate names, empty lists and disagreement.

## E4: placement intervention

Need: presentation invariance does not test whether a clause's structural place
matters. The interface and verdict branch are specified in
`breadth/placement-intervention.md`. It adds one additively declared trial and a
new evidence branch before ablation. It changes the frame schema and tests but
leaves old hashes and replays unchanged. Cost: large because it touches every
layer and needs a contract test that old records still reach old categories.

## E5: local JSON battery

Need: a local evaluator should get the same privacy and deadline treatment as
the shipped batteries without a provider adapter. The wire contract is in
`breadth/local-json-battery.md`. It reuses the loopback opener, timeout and size
caps, and the existing schema/label pointer. Cost: medium, mostly negative
security and malformed-response tests.

## Deliberately not proposed

- A single score across categories. The method returns distinctions, not a
  quality metric; collapsing them would hide exactly what the essay asks to retain.
- Automatic consent to training-tier providers. Consent remains an explicit exact
  model slug in the frame.
- A hosted record store. Gadfly's no-state property is a boundary, and storage
  retention is a separate decision.

