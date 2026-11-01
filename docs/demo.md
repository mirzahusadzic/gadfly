# The payments demo

Tendora's payments demo asks 31 questions of 30 statements about a payments
team's on-call practice. Each question was read by Tendora's engine and by
Gemma 4 (26B-A4B, instruction-tuned) served by eGemma, at temperature 0.7
and at 0, and Gadfly read a verdict from each reader's own answers by the
same rules. Pick a question to see the three reads side by side, trial by
trial.

<div class="gadfly-compare gadfly-watch" data-compare="payments-demo"></div>

The view plays the records kept in `examples/payments-demo/`, copied byte
for byte from the tendora repository with its notice. Each frame was
predicted to carry before its first call, and none of them changes after it.

---

### The totals

The table counts the verdicts as the kept records read them, one run of
each question by each reader.

| Reader | Carried | Unresolved | Coupled but misaligned | Cooled |
|---|---|---|---|---|
| Tendora's engine | 31 | 0 | 0 | 0 |
| Gemma 4 at temperature 0.7 | 12 | 15 | 3 | 1 |
| Gemma 4 at temperature 0 | 14 | 11 | 3 | 3 |

Carried here means carried under the trials run: the cited statements cut,
other statements cut at random twice, the material reordered where a frame
asks it, and a control. The bypass and presentation checks were not run, so
every verdict lists them as still open. At temperature 0.7 the read shows
how steadily Gemma answers; at 0 its repeats agree almost by construction,
and the read shows whether a cut moves its answer.

---

### Watch one question

The watch view plays one question for one reader at a time: what it read,
how it answered, and the checks filling in. Pick a reader to see the same
trials through its answers.

<div class="gadfly-watch" data-frames="payments-which-key,payments-who-notifies,payments-on-call-check,payments-which-manager,payments-morgan-ships" data-titles="Which key must the security engineer rotate?|Who notifies the customers?|What does the on-call engineer check after acknowledging a page?|Which manager freezes deployments during a major incident?|Does Morgan ship a release?"></div>

Tendora's engine is sent the statements and the question, not Gemma's
instruction, and its answer reads as one of the same words. The view shows
the engine's answer line, not the rest of its reply.

---

### Read a verdict again

Any verdict comes back from its frame and records alone, with no engine,
model or network. Here is the first question as Tendora's engine read it.

```text
$ uv run gadfly report \
    examples/payments-demo/frames/tendora-which-key-must-the-security-engineer-rot-ac7eb56a.json \
    examples/payments-demo/runs/tendora-which-key-must-the-security-engineer-rot-ac7eb56a.jsonl
frame: tendora-which-key-must-the-security-engineer-rot-ac7eb56a (17555b5ad0584aacc3cf78d7b6792692145afeda2f4c384855eecd47cce59454)
records: 6  planned calls: 6
overall: carried
  which-key-must-the-secur: ablation moved it conditional -> open; held under 2 shams
  which-key-must-the-secur: the control moved it conditional -> open
  obligation: no hidden fallback: no bypass trial was declared
  obligation: presentation invariance: no presentation trial was declared
which-key-must-the-secur: carried
  level baseline: conditional
  level repeat: conditional
  level ablation: open
  level sham-1: conditional
  level sham-2: conditional
  level control: open
  evidence: ablation moved it conditional -> open; held under 2 shams
  evidence: the control moved it conditional -> open
  obligation: no hidden fallback: no bypass trial was declared
  obligation: presentation invariance: no presentation trial was declared
```

Gemma at 0.7 answered the same question open in every trial, the control
included, so the trials could not tell what its answer rests on.

```text
$ uv run gadfly report \
    examples/payments-demo/frames/gemma-which-key-must-the-security-engineer-rot-ac7eb56a.json \
    examples/payments-demo/runs/gemma-which-key-must-the-security-engineer-rot-ac7eb56a.jsonl
frame: gemma-which-key-must-the-security-engineer-rot-ac7eb56a (18588db7e2b2a6249fd02f19c05c9a4acfd9068f562c10ec0389a1826fb830a8)
records: 6  planned calls: 6
overall: unresolved
  which-key-must-the-secur: ablation left it at open, and so did the control: the scorer cannot tell
  obligation: no hidden fallback: no bypass trial was declared
  obligation: presentation invariance: no presentation trial was declared
  obligation: discrimination: the control left it at open too
which-key-must-the-secur: unresolved
  level baseline: open
  level repeat: open
  level ablation: open
  level sham-1: open
  level sham-2: open
  level control: open
  evidence: ablation left it at open, and so did the control: the scorer cannot tell
  obligation: no hidden fallback: no bypass trial was declared
  obligation: presentation invariance: no presentation trial was declared
  obligation: discrimination: the control left it at open too
```

---

### Ask the engine again

Tendora's demo package serves the engine on this machine, and the
[tendora battery](batteries.md#tendoras-engine) asks it again. The frames
name `http://127.0.0.1:8791`, so the engine is served there, offline.

```sh
gadfly run \
  examples/payments-demo/frames/tendora-which-key-must-the-security-engineer-rot-ac7eb56a.json \
  --battery midwife.batteries.tendora:Tendora \
  --out which-key.jsonl --calls 7
```
