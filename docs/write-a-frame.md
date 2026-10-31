# Write a frame

A frame is plain JSON. Gadfly checks it before any call and hashes the checked
value; a changed frame is a different frame.

<!-- copy README.md:frame -->
The top-level keys are all checked before a call:

| Key | What you write |
|---|---|
| `name` | a short label for this frame |
| `relation`, `locus`, `body` | the premise, where it acts, and `body.spans` carrying it |
| `role`, `grain`, `purpose` | whose reading, at which unit, for what |
| `trajectory`, `baseline`, `crossing`, `promise` | the path to the recipient, everything pinned, the boundary, and what must cross it |
| `anchors` | span ids the relation rests on; at least one |
| `inputs` | the finite test domain, each `{id, text}` with distinct ids |
| `observe` | `labels`, `instruction`, and `order` when labels are ordered; other keys are your battery's |
| `interventions` | the trials; `ablation` is required |
| `allowed` | what `ablation` may produce, and optionally the opening `bypass` must expose |
| `standing` | `quorum`, `agree`, and optionally `stable` (which needs `repeat`) |
| `battery` | at least `kind`; shipped batteries use `model`, reasoning, schema or pins as documented below |
| `materialized` | `true` only when the observation is the form the recipient receives |
| `outsideScope` | the receiving owner's exclusion, in words; omit when there is none |
| `scopeCheck` | the owner's check of that exclusion: `owner`, `statement`, `source`, `encounter` |
| `carriage` | `all-checks` (the default) or `listed`: whether an open check holds a category back |

`body.spans` are `{id, text}` with an optional `kind` used to match sham spans.
`allowed` lists labels, or uses `lower`/`higher` along `observe.order`.
`allowed.bypass` is the label or labels a bypass must expose.

The frame is hashed whole. Rewording the promise, changing the grain or swapping
the battery makes a new frame, and records from the old hash will be refused.
`gadfly/frame.schema.json` gives editors the shape; `uv run gadfly check-frame`
runs it and then the parser, which has the last word.
<!-- end copy -->

## Required and optional fields

Required top-level keys are `name`, `relation`, `locus`, `role`, `grain`,
`purpose`, `trajectory`, `crossing`, `promise`, `baseline`, `body`, `anchors`,
`inputs`, `observe`, `interventions`, `allowed`, `standing` and `battery`.
`materialized`, `outsideScope`, `scopeCheck` and `carriage` are optional.

The shapes are exact:

| Path | Shape |
|---|---|
| `name`, the eight situation strings | non-empty strings; `name` is a label, while the other eight are prose |
| `baseline` | non-empty string or object |
| `body.spans` | non-empty list of `{id, text, kind?}`; ids are unique; `kind` defaults to `text` |
| `anchors` | non-empty list of span ids; at least one |
| `inputs` | non-empty list of `{id, text}`; both non-empty; ids are unique |
| `observe.labels` | at least two distinct non-empty strings |
| `observe.instruction` | non-empty string |
| `observe.order` | optional permutation of exactly `labels` |
| `observe.*` | any other key is your battery's to read |
| `interventions` | object with `ablation: true`; other keys appear in the table below |
| `allowed.ablation` | non-empty list of labels, or `lower`/`higher` with `order` |
| `allowed.bypass` | optional label list, or `lower`/`higher`; requires a bypass trial |
| `standing.quorum`, `agree` | integers, `1 <= agree <= quorum` |
| `standing.stable` | optional boolean; requires `repeat` |
| `battery.kind` | non-empty string matching the battery's `name` |
| `materialized` | optional boolean, default `false` |
| `outsideScope` | optional non-empty exclusion in the owner's words |
| `scopeCheck` | optional `{owner, statement, source, encounter}`, all non-empty; needs `outsideScope` |
| `carriage` | optional `all-checks` (the default) or `listed` |

The exact error strings are the public parser contract. If a frame is refused,
fix the declaration rather than adding an ignored key.

## Intervention shapes

| Key | Shape and rule |
|---|---|
| `repeat` | boolean |
| `ablation` | must be `true` |
| `cumulative` | non-empty span-id list that adds at least one non-anchor span |
| `sham` | `true`, or `{"draws": n}` with an integer `n >= 1` |
| `presentation` | non-empty object of non-empty word-to-replacement strings; no key repeated case-insensitively; must rename something read |
| `placement` | `{"span": id, "after": id}`: two different spans; the move must change the order |
| `bypass` | non-empty span-id list, not exactly the anchors |
| `control` | non-empty span-id list, not exactly the anchors |

Spans are removed by id. The trial that removes the anchors is the ablation; a
bypass that removed exactly the anchors would repeat it, and a presentation map
that touched nothing would produce a baseline. Gadfly refuses those degenerate
trials before spending calls.

## Choose a test domain

Inputs are cases, not trial repetitions. If one promise has several independent
cases, list each with a stable id. `judge` returns one finding per input and
`overall` combines them: any misaligned input makes the overall category
misaligned; any unresolved input keeps it unresolved; carried and cooled may
combine only when all inputs agree.

If the receiving owner excludes this relation entirely, say so in `outsideScope`.
Do not use that key to silence a failed test: it is a declaration about scope,
and the essay requires a separate scope check. Record the owner's check under
`scopeCheck`; until then the finding is unresolved (under `carriage: listed`,
outside scope with the check listed as open).

## Check before you run

`gadfly/frame.schema.json` is the frame's JSON Schema (draft 2020-12): point
your editor at it for completion and inline errors.
`uv run gadfly check-frame frame.json` runs the schema, when `jsonschema` is installed, and then the
parser, which has the last word on what only code can check (anchors in the
body, a presentation map that renames something, a placement that moves
something).

## A minimal valid skeleton

`examples/upgrade.json` is a complete working frame, and every other frame in
`examples/` was read by a live model. For a new relation, keep the shape and
replace the situation, body, anchor, input and observation labels.
Run `situate()` before making any calls so parser errors cost nothing.

## Troubleshooting

See [Your first frame § Common refusals](first-frame.md#common-refusals). For
problems after a run, see [Reading a verdict § Refused records](reading-a-verdict.md#refused-records).

