# Example report

`gadfly report` on the refund example's records, read by the rule reader. It
keeps the category, each trial's level, the evidence and the open obligations
apart, and says first what the frame's inputs add up to.

```text
$ gadfly run examples/refund.json --battery examples.refund:RuleReader --calls 8 --out records.jsonl
$ gadfly report examples/refund.json records.jsonl
frame: refund-receipt (dd916080072539784691a5232645b4d9c5b00e9cfdddd51650d15b347b385f85)
records: 8  planned calls: 8
overall: carried
  no-receipt: ablation moved it decline -> grant; held under presentation, 2 shams
no-receipt: carried
  level baseline: decline
  level repeat: decline
  level ablation: grant
  level sham-1: decline
  level sham-2: decline
  level presentation: decline
  level bypass: unclear
  level control: grant
  evidence: ablation moved it decline -> grant; held under presentation, 2 shams
```

The ablation moved the level as the promise allows, the presentation and the
shams held, and the bypass exposed the designated opening (`unclear`: no rule
binds). Every carriage check passed, so the report lists no obligation. Had one
been open, the evidence would say why the category waits, and an `obligation:`
line what would settle it.
