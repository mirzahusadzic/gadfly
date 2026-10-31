# Example report

`gadfly report` on one kept run of the payroll example (rung 12): one grant line,
"members of Finance may read the payroll table", and three requesters read
against it by Gemma through eGemma. It says first what the frame's inputs add
up to, then each input's category, its trials' levels, the evidence and what is
still open, each kept apart.

```text
$ uv run gadfly report examples/12-payroll-access.json examples/runs/12-payroll-access/1.jsonl
frame: payroll-access (202930b299ef9e09c878a7bec08524032b364c6d2fb91d94f72d8e018bff7cf7)
records: 120  planned calls: 120
overall: unresolved
  dana: ablation moved it allow -> deny; held under presentation, 2 shams
  dana: bypass moved it allow -> unclear: no hidden fallback
  dana: the control moved it allow -> deny
  sam: ablation left it at deny, and so did the control: the scorer cannot tell
  backup-job: ablation left it at allow
  backup-job: the control moved it allow -> deny: the scorer can tell
  obligation: sam: discrimination: the control left it at deny too
  obligation: backup-job: no hidden fallback: bypass gave allow, not the designated opening (unclear)
dana: carried
  level baseline: allow
  level repeat: allow
  level ablation: deny
  level sham-1: allow
  level sham-2: allow
  level presentation: allow
  level bypass: unclear
  level control: deny
  evidence: ablation moved it allow -> deny; held under presentation, 2 shams
  evidence: bypass moved it allow -> unclear: no hidden fallback
  evidence: the control moved it allow -> deny
sam: unresolved
  level baseline: deny
  level repeat: deny
  level ablation: deny
  level sham-1: deny
  level sham-2: deny
  level presentation: deny
  level bypass: unclear
  level control: deny
  evidence: ablation left it at deny, and so did the control: the scorer cannot tell
  obligation: discrimination: the control left it at deny too
backup-job: cooled
  level baseline: allow
  level repeat: allow
  level ablation: allow
  level sham-1: allow
  level sham-2: allow
  level presentation: allow
  level bypass: allow
  level control: deny
  evidence: ablation left it at allow
  evidence: the control moved it allow -> deny: the scorer can tell
  obligation: no hidden fallback: bypass gave allow, not the designated opening (unclear)
```

Read it from the bottom. The backup job is allowed by its own grant whatever
happens to Finance's (the ablation left it at allow), and the control, which
cuts every grant, shows the reader can move: **cooled**. Its bypass cut the
directory, which the backup job never needed, so it stayed at allow rather than
the designated opening, and that check stays open. Sam is denied whatever is
cut, the control included, so nothing shows the reader could move for him:
**unresolved**, with the `discrimination` obligation saying what is missing.
Dana is **carried**: cut the grant and she is denied, cut the directory entry
that puts her in Finance and the answer is unclear, rename and cut neighbours
and nothing moves.

The overall category is unresolved because one input is. Each input's evidence
is kept, prefixed with the input's name, and an obligation every input shares
would be said once. That one frame reads three ways here is by design, which the
frame's single set of allowed answers cannot yet say; see
[Several inputs](../examples/inputs.md).
