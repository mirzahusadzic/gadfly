# Is the premise load-bearing?

"It's raining," your friend says, back from the hall. "How do you know?" you
ask. "There were wet umbrellas by the door."

So you call another friend, one who hasn't been in, and describe the hall
without the umbrellas. If they say "I don't know", the umbrellas were the
reason; if they still say it's raining, something else you told them did.
Gadfly plays that game with whatever reads your evidence, to test whether a
decision rests on the line you think it does: it changes that line in fixed
ways, asks again each time, and reads one verdict by fixed rules.

---

### Choose your path

Start where your question is; every path ends in the same few pages.

- **I'm new to this:** [Gadfly in plain words](in-plain-words.md) tells the
  whole game, once for a kid and once for a grown-up.
- **I have a rule to test:** a changelog line, a contributing rule, a
  requirement, a contract clause or an access grant. Start with
  [Your first frame](first-frame.md).
- **I want to see it work:** [Watch a run](examples/watch.md) plays a kept
  run, one trial at a time.
- **I want the method first:** [When meaning is load-bearing](load-bearing.md)
  is the essay Gadfly applies, and [Framework](framework.md) translates its
  $L$ and $\Gamma$ into frame keys, interventions and records.
- **I have two minutes:** Gadfly returns one of five categories, not a score.
  The categories are below, and [the examples](examples/index.md) show whether
  that vocabulary fits your question.

---

### What a result looks like

A pull request formats a value into SQL, and the repository's rules forbid it.
Gemma 4 26B, through [eGemma](https://github.com/mirzahusadzic/egemma), reviewed it in five kept runs, and reading them
back calls no model:

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

Gemma asks for changes with the rule and without it, while the control, with
the rule and the query both cut, moves it to approve. So the reader can move,
and the rule is not what moves it: **cooled**. A rule Gemma cannot know from
training moves the other way ([Cooled](examples/cooled.md)).

---

<!-- copy README.md:verdicts -->
### What Gadfly says

Each input gets one **finding**, and a frame with several inputs gets one
**overall** category over them. The categories are not scores; the first rule
that matches names the category.

- **`carried`:** ablation moved the observation as the promise allows, and
  every carriage check passed: presentation and the shams held, the bypass
  exposed its opening, and the frame says the observation is what the
  recipient receives.
- **`coupled but misaligned`:** the relation matters, but presentation or
  placement moved it, or ablation moved it where the promise disallows.
- **`cooled`:** ablation left the observation unchanged while a control
  showed the scorer can move, so this relation has no operative influence
  here.
- **`unresolved`:** there is not enough agreed evidence: a trial is missing
  or split, repeat is unstable, a sham moved too, the scorer cannot tell, or a
  check the category needs is still open.
- **`outside scope`:** the receiving owner declares the distinction
  unnecessary, and their own check of that exclusion is recorded.

Every finding keeps its **evidence** (why this category) apart from its
**obligations** (what the trials did not settle), and an obligation is not a
passed check. Under the default `carriage: all-checks`, an open check keeps
carried, cooled and outside scope unresolved; a frame with
`carriage: listed` names the category and lists its open checks beside it.
<!-- end copy -->

---

### Install

Gadfly is a small Python library with no runtime dependencies and no hidden
state. It needs Python 3.13 or later and uv, and these commands install it and
read a kept example back:

```bash
git clone https://github.com/mirzahusadzic/gadfly.git
cd gadfly
uv sync
uv run python examples/read.py examples/upgrade.json
```

---

### Where to go next

Every page reads on GitHub as it does here.

| If you want to | Read |
|---|---|
| write a frame and check it before any call | [Write a frame](write-a-frame.md) |
| choose trials and estimate their calls | [Interventions](interventions.md) |
| read evidence apart from obligations | [Reading a verdict](reading-a-verdict.md) |
| use a model, a local service or your own scorer | [Batteries](batteries.md) |
| run, report and check frames from a terminal | [Command line](command-line.md) |
| look up a word such as anchor, grain or quorum | [Glossary](glossary.md) |
| see the trust boundaries and current limits | [Architecture and limits](architecture.md) |
| find a function or class | [Python API](reference.md) |
