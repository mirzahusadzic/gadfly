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
  no hidden fallback: bypass left it at decline
rule-reader: unresolved
  ablation moved it decline -> grant; held under presentation, 2 shams
  not carried while 1 carriage check is open
  no hidden fallback: bypass left it at decline
```

The frame declares one anchor: the receipt rule. The phrase matcher reads the
word *receipt*; the presentation trial renames it and exposes the difference.
The rule reader moves as the promise allows, but it still declines after the
binding connection is cut, so its fallback check is open and carried waits for
it. This is the most compact example of a category held back by an open check.

## Review handoff: the essay's worked example

```text
$ python examples/review_handoff.py
system                       finding                  authority
state projection             carried                  unresolved
summary: fix ready           unresolved               unresolved
drops its openings           coupled but misaligned   unresolved
projection, a record lost    unresolved               -
```

Two frames ask separate questions: whether the failed test reaches the selected
claim, and whether the grant reaches the handoff's operations. On the finding,
the state projection carries with every check passed: its bypass lands on the
designated opening. A polished summary that says *review complete; fix ready*
never moves, and with no control nothing shows its reading could, so it is not
cooled but unresolved. A handoff that drops its openings is misaligned, and a
missing trial record is insufficient evidence. The authority frame declares no
bypass and no sham, so its fallback and specificity checks stay open for every
system.

## Cited source

```text
$ python examples/citation.py
word-matcher: coupled but misaligned
  presentation moved it grounded -> ungrounded
  no hidden fallback: bypass left it at grounded
citation-reader: unresolved
  ablation moved it grounded -> ungrounded; held under presentation, 2 shams
  not carried while 1 carriage check is open
  no hidden fallback: bypass left it at grounded
```

The relation is the answer's crate count resting on `S-2`. Presentation renames
*cobalt* to *verdigris*; a reader that follows the source survives it, a word
matcher does not. The reader's fallback check stays open, so it is not yet
carried. See [Your first frame](first-frame.md) for the frame.

## One line of a system prompt

```text
$ python examples/system_prompt.py
request-alarm: cooled
  ablation left it at refuse
  the control moved it refuse -> comply: the scorer can tell
  no hidden fallback: no bypass trial was declared
always-refuse: unresolved
  ablation left it at refuse, and so did the control: the scorer cannot tell
  no hidden fallback: no bypass trial was declared
  discrimination: the control left it at refuse too
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
  no hidden fallback: bypass left it at read-only
scope-reader: unresolved
  ablation moved it read-only -> deny; held under presentation, 1 sham
  not carried while 1 carriage check is open
  no hidden fallback: bypass left it at read-only
```

The frame says the grant permits read-only and that removing it should produce a
denial. A tool that permits modification without the grant is not merely noise:
it moves in the wrong direction, which is misalignment.

## Code invariant

```text
$ python examples/code_invariant.py
full run: unresolved
  ablation moved it sorted -> unsorted; held under presentation, 1 sham
  not carried while 1 carriage check is open
  no hidden fallback: bypass left it at sorted
records lost: unresolved
  no agreed level in: sham-1, presentation, bypass
  no hidden fallback: the bypass has no agreed level to read against baseline
declared out of scope: unresolved
  declared outside scope: the receiving owner excludes formatting-only outputs
  not outside scope until the owner's check is recorded
  independent scope check: the exclusion is declared, not tested
declared and checked: outside scope
  declared outside scope: the receiving owner excludes formatting-only outputs
  the report's maintainers checked the scope at the October report review: the report re-sorts every table it prints (report spec RS-7)
```

The invariant is one sort line at the grain of one program line. The partial read
demonstrates why a missing planned record is not evidence. The last two blocks
show what outside scope needs: the owner's declaration alone leaves the scope
check open; recorded under `scopeCheck`, the owner's check settles it.

## What the examples do not cover

They do not call a provider, establish a model's general policy, or establish
materialization in a real receiving system. The review handoff is a projection in
Python, not the actual review product. A live route is shown by
`examples/refund_live.py` but requires the local routers documented in
[Batteries](batteries.md).

