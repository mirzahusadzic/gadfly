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
  no hidden fallback: bypass gave decline, not the designated opening (unclear)
rule-reader: carried
  ablation moved it decline -> grant; held under presentation, 2 shams
```

The frame declares one anchor: the receipt rule. The phrase matcher reads the
word *receipt*; the presentation trial renames it and exposes the difference,
and it keeps declining once the rules' binding line ("These rules decide every
request.") is cut, a fallback the bypass catches. The rule reader moves as the
promise allows, holds under presentation and both shams, and with the binding
line cut cannot decide: `unclear`, the opening the frame names under
`allowed.bypass`. Every check passed, so it is carried. The frame also has a
control (no rules at all), which these two never need; it is there for the
live critics of `examples/refund_live.py`.

## Review handoff: the essay's worked example

```text
$ python examples/review_handoff.py
system                       finding                  authority
state projection             carried                  carried
summary: fix ready           unresolved               unresolved
drops its openings           coupled but misaligned   carried
projection, a record lost    unresolved               -
```

Two frames ask separate questions: whether the failed test reaches the selected
claim, and whether the grant reaches the handoff's operations. The state
projection carries both with every check passed: cut the rule that makes a
failure a reason, and it opens the missing connection; cut the state that
grants G-1 to the reviewer, and it permits nothing. A handoff that drops its
openings is misaligned on the finding, and its grant still carries. A polished
summary that says *review complete; fix ready* says it whatever it is given:
ablation leaves it, and so does a control that removes the claim and the
capture, so no trial can single out the relation, and it is unresolved, not
cooled. A missing trial record is insufficient evidence.

## Cited source

```text
$ python examples/citation.py
word-matcher: coupled but misaligned
  presentation moved it grounded -> ungrounded
  no hidden fallback: bypass gave grounded, not the designated opening (ungrounded)
citation-reader: carried
  ablation moved it grounded -> ungrounded; held under presentation, 2 shams
```

The relation is the answer's crate count resting on `S-2`. Presentation renames
*cobalt* to *verdigris*; a reader that follows the source survives it, a word
matcher does not. The reader grounds an answer only while the records decide
the question, so cutting that line exposes the opening and it carries. See
[Your first frame](first-frame.md) for the frame.

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
  no hidden fallback: bypass gave read-only, not the designated opening (deny)
scope-reader: carried
  ablation moved it read-only -> deny; held under presentation, 1 sham
```

The frame says the grant permits read-only and that removing it should produce a
denial. A tool that permits modification without the grant is not merely noise:
it moves in the wrong direction, which is misalignment. The scope reader denies
both without the grant and without the contract's binding line, so it carries.

## Code invariant

```text
$ python examples/code_invariant.py
full run: carried
  ablation moved it sorted -> unsorted; held under presentation, 1 sham
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

The invariant is one sort line at the grain of one program line. The full run
carries: the order rests on the line and on the lines deciding the output. The
partial read demonstrates why a missing planned record is not evidence. The last two blocks
show what outside scope needs: the owner's declaration alone leaves the scope
check open; recorded under `scopeCheck`, the owner's check settles it.

## What the examples do not cover

They do not call a provider, establish a model's general policy, or establish
materialization in a real receiving system. The review handoff is a projection in
Python, not the actual review product. A live route is shown by
`examples/refund_live.py` but requires the local routers documented in
[Batteries](batteries.md).

