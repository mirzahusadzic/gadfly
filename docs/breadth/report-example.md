# Example report

`gadfly report` on the refund example's records, read by the rule reader. It
keeps the category, each trial's level, the evidence and the open obligations
apart, and says first what the frame's inputs add up to.

```text
$ gadfly run examples/refund.json --battery examples.refund:RuleReader --calls 7 --out records.jsonl
$ gadfly report examples/refund.json records.jsonl
frame: refund-receipt (6a788e8843504c0828dc1dc8c236c349e8f9750c0cd2d52b2d124d2bb9580e9e)
records: 7  planned calls: 7
overall: unresolved
  no-receipt: ablation moved it decline -> grant; held under presentation, 2 shams
  no-receipt: not carried while 1 carriage check is open
  obligation: no hidden fallback: bypass left it at decline
no-receipt: unresolved
  level baseline: decline
  level repeat: decline
  level ablation: grant
  level sham-1: decline
  level sham-2: decline
  level presentation: decline
  level bypass: decline
  evidence: ablation moved it decline -> grant; held under presentation, 2 shams
  evidence: not carried while 1 carriage check is open
  obligation: no hidden fallback: bypass left it at decline
```

The ablation moved the level as the promise allows and the presentation and the
shams held, but the bypass left it where it was: the reader declines whether or
not the rules bind. Under the default `carriage: all-checks` that open fallback
check keeps the finding unresolved, and the report says so twice: once as
evidence (why the category is what it is) and once as an obligation (what would
settle it).
