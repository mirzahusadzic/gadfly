# Pros, cons and future

These notes followed [Gadfly in plain words](in-plain-words.md) when it was first
written, and are kept as written until they are folded into
[Architecture and limits](architecture.md) and the [roadmap](roadmap.md).

---

### Pros

- **Nothing is judged by a model.** A verdict follows from the kept answers by fixed rules, so anyone can check it.
- **It says what it doesn't know.** "Unresolved" always names the open check, and the reasons are kept apart from what's still missing.
- **It can't be quietly adjusted after the fact.** Every answer is tied to the exact frame, so you can't edit a frame after seeing results. The pressure goes toward writing predictions first.
- **It checks its author too.** The control step caught my own badly built frame (10c).
- **It's cheap and works across fields.** About 5,500 calls ran on a laptop, across code review, contracts, access rules, incidents, migrations and performance work. It needs no extra libraries.
- **The findings matter in practice.** Anyone deploying an AI reviewer wants to know when it decides from its training instead of from the evidence it was given.

---

### Cons

- **It shows *that* a decision rests on a line, not *why*.** Cooled can't tell a training habit from another line without an extra step (the cumulative trial).
- **Everything depends on writing the frame well.** You must know the anchor, the line that connects it, and a fair control. That's where examples can turn into ones premade from the verdict. I got a control wrong myself.
- **Decisions must fit a few fixed labels.** Real decisions are nuanced free text.
- **It's strict, so most results come out unresolved.** With several inputs, one noisy trial sinks the whole frame (design calls A and B). Newcomers will read unresolved as failure.
- **The statistics are thin.** Each trial is about 15 calls with a 4-of-5 threshold: no confidence ranges, and the sampling temperature isn't fixed in the frame.
- **It only removes text.** It can't test a decision that comes from a default, like Sam being denied because nothing grants him access.
- **The vocabulary is a hurdle.** Words like carried, cooled, crossing and locus come from the essay. You felt this yourself at the start.
- **It doesn't say whether the decision is right**, only what it rests on. Blocking without the signature line may well be good caution.

---

### Future

Ordered by what I'd do first:

1. **Expectations per input** (design calls A and B). This is the biggest gain in usability. Today, several real frames read unresolved when they behaved exactly as promised.
2. **Regression tests for AI deployments.** Keep a set of frames and re-run them when the model, prompt or policy changes, then compare verdicts. "Does the new model still enforce our rule *because of* the rule?" I think this is its most valuable use. The portfolio command is already a start.
3. **Comparing readers.** Run the same frame on Gemma, Claude, or a panel of human reviewers. That's the essay's handoff idea, made measurable.
4. **Changes beyond cutting.** Change a value (400 ms becomes 100 ms) or add contrary evidence. That would test direction, not just dependence.
5. **Better statistics.** Report counts with ranges, stop early once a level is clear, and record the temperature with the answers.
6. **Help writing frames.** For example, a warning when a control leaves a line that still points to the answer, which is exactly my 10c mistake. It should flag problems, never write the frame from a result.

**Positioning:** the nearest neighbours are context-attribution tools for AI answers, such as ContextCite, which also cuts sources to see what an answer relies on. Gadfly's distinct part is the declared promise, the fixed rules, the list of what's still open, and the discipline around kept records. That fits an audit or governance tool better than a research method. Testing whether AI answers rest on the documents they were given, which is the biggest practical use of this kind of check, is a natural market.
