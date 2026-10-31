# Is the premise load-bearing?

**Gadfly removes or changes one declared relation, asks a scorer to read each
trial, and returns one fixed-rule verdict.** It is a small Python library with
no runtime dependencies and no hidden state.

**[Test your first frame](first-frame.md)** · [Read the essay](load-bearing.md)

## Choose your path

- **I have a rule to test.** A changelog line, a contributing rule, a
  requirement, a contract clause or an access grant. Start with
  [Your first frame](first-frame.md).
- **I have read the essay.** Translate $L$ and $\Gamma$ into frame keys,
  interventions and records. Start with [Framework](framework.md).
- **I have two minutes.** Gadfly returns one of five categories, not a score.
  Read [Reading a verdict](reading-a-verdict.md), then decide from the
  [examples](examples/index.md) whether that vocabulary fits your question.

## What a result looks like

A pull request builds SQL by formatting a value into the query, and the
repository's rules forbid it. Gemma 4 26B, through eGemma, reviews it in five
kept runs; reading them back calls no model.

```text
$ uv run python examples/read.py examples/07-sql-rule.json
sql-rule: 5 kept runs, read by google/gemma-4-26B-A4B-it-qat-q4_0-gguf@d1c082be
trial         review
baseline      request-changes 25
repeat        request-changes 25
ablation      request-changes 25
sham-1        request-changes 25
sham-2        request-changes 25
presentation  request-changes 25
control       approve 25
run 1: cooled
run 2: cooled
run 3: cooled
run 4: cooled
run 5: cooled
```

Gemma asks for changes with the rule and without it, while the control (the
rule and the query both cut) moves it to approve: the reader can move, and the
rule is not what moves it. Its training rejects formatted SQL anyway, so the
rule carries nothing here: **cooled**. A rule Gemma cannot know from training
moves the other way ([Cooled](examples/cooled.md)).

<!-- copy README.md:verdicts -->
## What Gadfly says

Each input gets one **finding**; a multi-input frame gets one **overall**
category over the findings. The categories are not scores. The first matching
rule below names the category.

| Finding | Plain meaning |
|---|---|
| `carried` | Ablation moved the observation as the promise allows, and every carriage check passed: presentation and the shams held, the bypass exposed its opening, and the frame says the observation is what the recipient receives. |
| `coupled but misaligned` | The relation matters, but presentation or placement moved it, or ablation moved it where the promise disallows. |
| `cooled` | Ablation left the observation unchanged while a control showed the scorer can move: this relation has no operative influence here. |
| `unresolved` | There is not enough agreed evidence: a trial is missing or split, repeat is unstable, a sham moved too, the scorer cannot tell, or a check the category needs is still open. |
| `outside scope` | The receiving owner declares the distinction unnecessary, and their own check of that exclusion is recorded. |

Every finding separates **Evidence** (why this category) from **Obligations**
(what the trials did not settle). An obligation is not a passed check. By
default (`carriage: all-checks`) an open check keeps carried, cooled and
outside scope unresolved, and the evidence says so; a frame that says
`carriage: listed` names the category and lists its open checks beside it.
<!-- end copy -->

## Install

```bash
git clone https://github.com/mirzahusadzic/gadfly.git
cd gadfly
uv sync
uv run python examples/read.py examples/upgrade.json
```

## Where to go next

| If you want to... | Read |
|---|---|
| write and validate a frame | [Write a frame](write-a-frame.md) |
| choose trials and estimate calls | [Interventions](interventions.md) |
| understand evidence and obligations | [Reading a verdict](reading-a-verdict.md) |
| use a model, local service or your own scorer | [Batteries](batteries.md) |
| climb the examples, one capability a step | [Examples](examples/index.md) |
| run, report and check frames from the command line | [Extending Gadfly](roadmap.md) |
| see the trust boundaries and current limits | [Architecture and limits](architecture.md) |
| find a library name | [Reference](reference.md) |

