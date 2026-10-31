# Extending Gadfly

The core is deliberately small. These extensions widen who can use the method,
each with the need it answers and the contracts it keeps.

| Capability | Use it | What it keeps |
|---|---|---|
| Command line and report | `gadfly plan`, `run`, `report` | records as JSON Lines, an explicit budget, evidence apart from obligations |
| Frame schema and authoring check | `gadfly/frame.schema.json`, `gadfly check-frame` | the parser as the authority |
| Portfolio summary | `gadfly portfolio` | no verdict across frames |
| `placement` intervention | `"placement": {"span": id, "after": id}` | old frames' hashes and categories |
| `local-json` battery | `"battery": {"kind": "local-json", "url": ...}` | loopback, no credentials, a whole-call deadline |

## Command line and report

Need: the essay requires retained evidence and visible obligations. Without the
command line a reader writes Python to keep records, then joins
`evidence + obligations` in an ad-hoc print loop.

```bash
gadfly plan examples/refund.json
gadfly run examples/refund.json --battery examples.refund:RuleReader --calls 8 --out records.jsonl
gadfly report examples/refund.json records.jsonl
```

`run` uses only the public pipeline, writes each `Record.as_dict()` as one JSON
object per line the moment it exists, refuses to overwrite an output file,
requires an explicit call budget and says when it stopped early; `--kept`
finishes a stopped run. The battery, `module:Class`, is imported from the
current directory. `report` keeps a finding's levels, evidence and obligations on
separate lines (see the [example report](breadth/report-example.md)), or prints
them as JSON with `--json`. `python -m gadfly` is the same command.

## Frame schema and authoring check

Need: declaration errors should be visible in an editor before a run. The
parser remains the authority, because cross-field rules (anchor ids, label
order, a presentation map that renames something, a placement that moves
something, stable requiring repeat) are not all expressible in JSON Schema.

`gadfly/frame.schema.json` (draft 2020-12, published at the site's root, where
its `$id` points) describes every key and every trial's shape. Then:

```bash
gadfly check-frame path/to/frame.json --json
```

runs the schema, when `jsonschema` is installed, then `situate()`, and names
where each problem is. It never invents defaults or rewrites the frame. A parity
test holds the schema and the parser to the same answer on every shipped frame.

## Portfolio summary

Need: `overall()` reads one frame over its inputs. There is no fixed rule for
combining different relations, promises and recipients, so a portfolio verdict
would be a category error.

```bash
gadfly report --json frame-a.json records-a.jsonl > a.json
gadfly report --json frame-b.json records-b.jsonl > b.json
gadfly portfolio a.json b.json
```

It counts frames by category, lists the obligations two or more frames share,
and names the frames whose inputs disagree. It emits **no portfolio category**.

## Placement

Need: presentation invariance does not test whether a clause's structural place
matters. See [Placement intervention](breadth/placement-intervention.md).

## Local JSON battery

Need: a local evaluator should get the same privacy and deadline treatment as
the shipped batteries without an adapter of its own. See
[Local JSON battery](breadth/local-json-battery.md).

## Deliberately left out

- A single score across categories. The method returns distinctions, not a
  quality metric; collapsing them would hide exactly what the essay asks to retain.
- Automatic consent to training-tier providers. Consent remains an explicit exact
  model slug in the frame.
- A hosted record store. Gadfly's no-state property is a boundary, and storage
  retention is a separate decision.
