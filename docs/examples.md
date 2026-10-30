# Examples

The examples are small, deterministic wherever possible, and runnable from the
repository root. Start with the refund frame, then read one of the four relation
kinds closest to your own question.

--8<-- "README.md:examples"

## Refund policy: two scorers, one frame

```text
$ python examples/refund.py records.jsonl
phrase-matcher: coupled but misaligned
  presentation moved it decline -> grant
rule-reader: carried
  ablation moved it decline -> grant; held under presentation, 2 shams
  no hidden fallback: bypass left it at decline
```

The frame declares one anchor: the receipt rule. The phrase matcher reads the
word *receipt*; the presentation trial renames it and exposes the difference.
The rule reader still declines after the binding connection is cut, so its
fallback check is an obligation rather than a passed carriage check. This is the
most compact example of a category and an open obligation appearing together.

## Review handoff: the essay's worked example

```text
$ python examples/review_handoff.py
system                       finding                  authority
state projection             carried                  carried
summary: fix ready           cooled                   cooled
drops its openings           coupled but misaligned   carried
projection, a record lost    unresolved               -
```

Two frames ask separate questions: whether the failed test reaches the selected
claim, and whether the grant reaches the handoff's operations. A polished summary
that says *review complete; fix ready* loses both distinctions and cools; a
handoff that drops its openings remains claim-bearing but misaligned; a missing
trial record is insufficient evidence.

## Cited source

```text
$ python examples/citation.py
word-matcher: coupled but misaligned
  presentation moved it grounded -> ungrounded
citation-reader: carried
  ablation moved it grounded -> ungrounded; held under presentation, 2 shams
  no hidden fallback: bypass left it at grounded
```

The relation is the answer's crate count resting on `S-2`. Presentation renames
*cobalt* to *verdigris*; a reader that follows the source survives, a word matcher
does not. See [Your first frame](first-frame.md) for the frame.

## One line of a system prompt

```text
$ python examples/system_prompt.py
request-alarm: cooled
  ablation left it at refuse
  the control moved it refuse -> comply: the scorer can tell
always-refuse: unresolved
  ablation left it at refuse, and so did the control: the scorer cannot tell
```

This example is about the **control** trial. Removing the system line does not
change the request-keyed scorer, so the relation is cooled. Removing the request
text moves it, showing the scorer can move. An always-refuse scorer holds under
both cuts and is unresolved: it cannot tell the relation from its own habit.

## Tool permission and contract clause

```text
$ python examples/tool_permission.py
eager-tool: coupled but misaligned
  ablation moved it read-only -> modify, which the frame does not allow
scope-reader: carried
  ablation moved it read-only -> deny; held under presentation, 1 sham
  no hidden fallback: bypass left it at read-only
```

The frame says the grant permits read-only and that removing it should produce a
denial. A tool that permits modification without the grant is not merely noise:
it moves in the wrong direction, which is misalignment.

## Code invariant

```text
$ python examples/code_invariant.py
full run: carried
  ablation moved it sorted -> unsorted; held under presentation, 1 sham
  no hidden fallback: bypass left it at sorted
records lost: unresolved
  no agreed level in: sham-1, presentation, bypass
declared out of scope: outside scope
  declared outside scope: the receiving owner excludes formatting-only outputs
  independent scope check: the exclusion is declared, not tested
```

The invariant is one sort line at the grain of one program line. The partial read
demonstrates why a missing planned record is not evidence. The last block also
shows the current `outsideScope` short-circuit: the owner's declaration yields
the category, while the independent scope check remains open. The essay requires
both, so read that block as an implementation warning, not a finished outside-scope finding.

## What the examples do not cover

They do not call a provider, establish a model's general policy, or establish
materialization in a real receiving system. The review handoff is a projection in
Python, not the actual review product. A live route is shown by
`examples/refund_live.py` but requires the local routers documented in
[Batteries](batteries.md).

