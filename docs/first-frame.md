# Your first frame

This tutorial tests one sentence from a cited source:

> The cobalt manifest records 40 crates.

We want to know whether an answer's crate count rests on source `S-2`, rather
than on the word *cobalt*. The complete frame is
`examples/citation.json`; the deterministic scorers are in
`examples/citation.py`.

## 1. Declare the situation

The first nine keys say what is being tested and whose consequence matters.

```json
{
  "name": "cited-source",
  "relation": "the answer's crate count rests on cited source S-2",
  "locus": "the answer, where the count is stated",
  "role": "a reader checking the answer against its cited sources",
  "grain": "one claim of the answer",
  "purpose": "the stated count is traceable to the source the answer cites",
  "trajectory": "sources and question, the answer, the reader's check",
  "crossing": "the reader's check of the answer",
  "promise": "the count is given only while S-2 is cited, however the source is worded",
  "baseline": "the sources as written and one question; nothing changed"
}
```

- **relation** is the premise under intervention.
- **locus** is where it acts.
- **grain** is the comparison unit. Do not mix answers and individual clauses.
- **crossing** is the recipient boundary where the promise must remain true.
- **promise** is the observable consequence, not a wish for the system overall.

The `baseline` is everything pinned for this comparison. A model, revision,
rubric hash or retrieval snapshot belongs here when the test depends on it.

## 2. Put the relation in a body

```json
{
  "body": {"spans": [
    {"id": "s1", "text": "Source S-1: the harbor ledger lists arrivals by date.", "kind": "source"},
    {"id": "s2", "text": "Source S-2: the cobalt manifest records 40 crates.", "kind": "source"},
    {"id": "s3", "text": "Source S-3: the tide table gives high water at noon.", "kind": "source"},
    {"id": "s4", "text": "Source S-4: the crew roll names twelve hands.", "kind": "source"},
    {"id": "rule", "text": "Answer the question using the cited source.", "kind": "rule"},
    {"id": "binding", "text": "These records decide every question.", "kind": "note"}
  ]},
  "anchors": ["s2"],
  "inputs": [
    {"id": "crates", "text": "How many crates does the cobalt manifest record?"}
  ]
}
```

The anchor is the span whose removal tests the relation. Other spans of the same
`kind` give the sham trial somewhere to cut. Do not pick an anchor that contains
the whole answer; pick the smallest declared unit that could carry the promise.

The input is the finite test case. Add inputs when the claim is meant to hold
across cases; Gadfly will return one finding per input and an overall category.

## 3. Say what the scorer can observe

```json
{
  "observe": {
    "labels": ["grounded", "ungrounded"],
    "instruction": "Answer the question from the cited source."
  },
  "allowed": {"ablation": ["ungrounded"], "bypass": ["ungrounded"]}
}
```

The labels are the entire comparison vocabulary. The comparison is exact label
equality: there is no undocumented similarity threshold and no hidden scalar.
Ordered outcomes additionally use `observe.order` with `allowed: "lower"` or
`"higher"`. The allowed relation says what a valid ablation may produce; a move
outside it is `coupled but misaligned`, not carriage. `allowed.bypass` names
the designated opening: what the reader must answer once the connection that
makes the relation operative (here the binding line, "These records decide
every question.") is cut. A reader that answers anything else there has a
hidden fallback.

## 4. Choose the interventions

```json
{
  "interventions": {
    "repeat": true,
    "ablation": true,
    "sham": {"draws": 2},
    "presentation": {"cobalt": "verdigris"},
    "bypass": ["binding"]
  },
  "standing": {"quorum": 1, "agree": 1},
  "materialized": true,
  "battery": {"kind": "citation-reader"}
}
```

`ablation` is required. The others answer separate questions:

| Question | Trial | If omitted |
|---|---|---|
| Is the level stable? | `repeat` | no stability comparison |
| Does wording drive the result? | `presentation` | presentation invariance remains open, so the finding cannot be `carried` |
| Does the structure drive it? | `placement` | nothing tests the span's place |
| Is the change specific? | `sham` | specificity remains open |
| Is there a hidden fallback? | `bypass` | no-hidden-fallback remains open |
| Can the scorer move at all? | `control` | discrimination remains open, so the finding cannot be `cooled` |

Under the default `carriage: all-checks`, a check left open keeps `carried` and
`cooled` unresolved. A frame that says `"carriage": "listed"` names the category
and lists the open checks beside it.

`quorum` is the number of scorer calls per trial; `agree` is the number of
identical observations needed for one level. Here one call is enough because the
battery is deterministic. A sampled model normally needs three or more.

## 5. Run the battery

The frame names `citation-reader`, so only a battery whose `name` is exactly
`citation-reader` may read it.

```python
--8<-- "examples/first_frame.py:7:"
```

```text
$ uv run python examples/first_frame.py
carried
ablation moved it grounded -> ungrounded; held under presentation, 2 shams
```

The relation moved the observation in the allowed direction, presentation and
the shams held, and cutting the binding line exposed the designated opening:
the reader answers `ungrounded` once the records no longer decide the question,
so it has no hidden fallback. Every carriage check passed, so the finding is
`carried`, with no obligation left. The same frame read by `WordMatcher` instead
becomes `coupled but misaligned`, because renaming *cobalt* changes its answer,
and it lists the fallback it was not cleared of: it answers `grounded` with the
binding line cut.

Run both scorers with:

```bash
uv run python examples/citation.py
```

## 6. Read what is missing

The first run is useful even when the category is not final. Check:

1. `finding.levels`: did every trial reach one agreed level?
2. `finding.evidence`: which rule produced the category?
3. `finding.obligations`: which checks did not pass or did not run?
4. `overall(findings)`: for several inputs, did the frame-level reading weaken?

Do not concatenate evidence and obligations into one list in your own UI. They
answer different questions.

## Common refusals

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

`uv run gadfly check-frame my-frame.json` shows these before any call, with the
schema's findings first when `jsonschema` is installed.

Next: [Write a frame](write-a-frame.md) for the complete field reference.

