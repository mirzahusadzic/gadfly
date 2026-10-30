# Proposal: a `placement` intervention

**Priority:** medium. **Effort:** large. **Replaces:** the common workaround of
making a second frame just to move one span, which loses a paired in-frame
comparison and doubles setup.

## Need

The essay treats each intervention as a change to the declared relation that
preserves the rest of the encounter. `presentation` changes wording with a
one-to-one rename. It cannot test whether structural location matters: a grant
placed before or after an instruction, a caveat moved out of its section, or a
code invariant moved away from the operation it governs.

## Interface

Add one optional key:

```json
{
  "interventions": {
    "ablation": true,
    "placement": {"span": "grant", "after": "audit"}
  }
}
```

Semantics:

- `span` and `after` name distinct body spans.
- The trial removes `span` from its current position and inserts it immediately
  after `after`; all span text is unchanged.
- The frame is refused if the resulting order is identical to baseline.
- The plan appends a `placement` trial after `presentation` and before `bypass`.
- `judge` checks it immediately after the presentation rule. A changed level is
  `coupled but misaligned`: structure, not just wording, drove the observation.
- The cost is one trial times `quorum`.

## Contracts

- The key is additive. Existing frame hashes and records are unchanged until a
  frame declares `placement`.
- A new frame that uses it has a new hash.
- The record format is unchanged; `trial` is `placement`.
- The battery still never sees the trial id.
- The `After the Poem` replay has no placement trial and its rule path is unchanged.
- `frame.py`, `interventions.py`, `verdict.py`, the frame table, trials table and
  JSON Schema all need matching updates.

## Tests that would fail before the change

1. A placement that reorders the body yields a distinct `body_hash` and a
   `placement` record.
2. A placement equal to baseline order is a `FrameError` before a call.
3. A scorer whose label changes only under placement is `coupled but misaligned`.
4. A legacy frame's hash and category are byte-for-byte unchanged.

