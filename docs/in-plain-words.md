# Gadfly in plain words

## For the kid

Your friend says it's raining outside, and you want to know how they know. They say: "I saw wet umbrellas by the door."

So you play a game. You hide the umbrellas and ask again:

- If they now say "I don't know", the umbrellas were the reason.
- If they still say "raining", something else told them. Maybe they heard rain on the roof, or maybe they always say "raining".
- To tell those two apart, you hide everything: the umbrellas, the window, the sound. If they still say "raining", they aren't looking at anything. They're just guessing.

You also hide a sock, which has nothing to do with rain, to make sure hiding *anything* doesn't confuse them. And you call umbrellas "brollies", to check that they react to what things are, not to their names.

Gadfly plays that game with computers, and it plays it very carefully.

## For the father

When an AI, or a person, makes a decision from a pile of documents, you usually can't see *why*. You believe a code reviewer rejected a change because of your team's rule, but it might have rejected it anyway.

Gadfly is a test harness for that belief:

- **You say which line the decision should rest on**, and what a reader should answer without it.
- **Gadfly makes fixed edits to the documents:** cut that line, cut a harmless line, rename things, move a line, cut the link that makes the line apply, or cut everything that matters.
- **It asks the same question each time**, several times over, and keeps every answer.
- **Fixed rules, not another AI, turn the pattern into a verdict:**
    - *carried*: it rests on that line, for the reason you claimed;
    - *cooled*: it doesn't need that line, something else decides;
    - *misaligned*: the line matters, but the decision moves the wrong way, or names and order sway it;
    - *unresolved*: it can't tell yet, and it names the missing check.

Anyone can re-read the kept answers later without the AI.

The examples show why that's useful:

- Gemma enforces "no formatted SQL" with or without your rule, so the rule isn't doing the work.
- It applies a customer's contract clause without the line saying the customer signed it.
- With no evidence either way, it blames the service named in the symptom instead of saying "I don't know".
- It drops a database table without the one line showing nobody reads it.

## Pros
- **Nothing is judged by a model.** A verdict follows from the kept answers by fixed rules, so anyone can check it.
- **It says what it doesn't know.** "Unresolved" always names the open check, and the reasons are kept apart from what's still missing.
- **It can't be quietly adjusted after the fact.** Every answer is tied to the exact frame, so you can't edit a frame after seeing results. The pressure goes toward writing predictions first.
- **It checks its author too.** The control step caught my own badly built frame (10c).
- **It's cheap and works across fields.** About 5,500 calls ran on a laptop, across code review, contracts, access rules, incidents, migrations and performance work. It needs no extra libraries.
- **The findings matter in practice.** Anyone deploying an AI reviewer wants to know when it decides from its training instead of from the evidence it was given.

## Cons
- **It shows *that* a decision rests on a line, not *why*.** Cooled can't tell a training habit from another line without an extra step (the cumulative trial).
- **Everything depends on writing the frame well.** You must know the anchor, the line that connects it, and a fair control. That's where examples can turn into ones premade from the verdict. I got a control wrong myself.
- **Decisions must fit a few fixed labels.** Real decisions are nuanced free text.
- **It's strict, so most results come out unresolved.** With several inputs, one noisy trial sinks the whole frame (design calls A and B). Newcomers will read unresolved as failure.
- **The statistics are thin.** Each trial is about 15 calls with a 4-of-5 threshold: no confidence ranges, and the sampling temperature isn't fixed in the frame.
- **It only removes text.** It can't test a decision that comes from a default, like Sam being denied because nothing grants him access.
- **The vocabulary is a hurdle.** Words like carried, cooled, crossing and locus come from the essay. You felt this yourself at the start.
- **It doesn't say whether the decision is right**, only what it rests on. Blocking without the signature line may well be good caution.

## Future
Ordered by what I'd do first:

1. **Expectations per input** (design calls A and B). This is the biggest gain in usability. Today, several real frames read unresolved when they behaved exactly as promised.
2. **Regression tests for AI deployments.** Keep a set of frames and re-run them when the model, prompt or policy changes, then compare verdicts. "Does the new model still enforce our rule *because of* the rule?" I think this is its most valuable use. The portfolio command is already a start.
3. **Comparing readers.** Run the same frame on Gemma, Claude, or a panel of human reviewers. That's the essay's handoff idea, made measurable.
4. **Changes beyond cutting.** Change a value (400 ms becomes 100 ms) or add contrary evidence. That would test direction, not just dependence.
5. **Better statistics.** Report counts with ranges, stop early once a level is clear, and record the temperature with the answers.
6. **Help writing frames.** For example, a warning when a control leaves a line that still points to the answer, which is exactly my 10c mistake. It should flag problems, never write the frame from a result.

**Positioning:** the nearest neighbours are context-attribution tools for AI answers, such as ContextCite, which also cuts sources to see what an answer relies on. Gadfly's distinct part is the declared promise, the fixed rules, the list of what's still open, and the discipline around kept records. That fits an audit or governance tool better than a research method. Testing whether AI answers rest on the documents they were given, which is the biggest practical use of this kind of check, is a natural market.
