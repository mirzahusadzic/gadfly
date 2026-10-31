# Gadfly in plain words

The same idea told twice: once for a kid, and once for a grown-up.

---

### For the kid

Your friend says it's raining outside, and you want to know how they know. They say: "I saw wet umbrellas by the door."

You can't make them forget what they saw, so you play a game with friends who haven't been to the door. You call each one, describe the hall a little differently each time, and ask if it's raining:

- Leave out the umbrellas. If they now say "I don't know", the umbrellas were the reason.
- If they still say "raining", something else you told them did. Maybe you mentioned the rain on the roof, or maybe they always say "raining".
- To tell those two apart, leave out everything: the umbrellas, the window, the sound. If they still say "raining", they aren't listening to anything you say. They're just guessing.

You also leave out a sock, which has nothing to do with rain, to make sure leaving out *anything* doesn't confuse them. And you say "brollies" instead of umbrellas, to check that they react to what things are, not to their names.

Gadfly plays that game with computers, and it plays it very carefully. A computer is even better at it than your friends: it forgets everything between questions, so Gadfly can ask the same one every time.

[Watch a run](examples/watch.md) shows the game played for real, one step at a time.

---

### For the grown-up

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

[The examples](examples/index.md) show why that's useful:

- Gemma enforces "no formatted SQL" with or without your rule, so the rule isn't doing the work.
- It applies a customer's contract clause without the line saying the customer signed it.
- With no evidence either way, it blames the service named in the symptom instead of saying "I don't know".
- It drops a database table without the one line showing nobody reads it.

[Your first frame](first-frame.md) builds one such test, a trial at a time.

---

### Why a gadfly and a midwife

Socrates gave himself both names. In Plato's *Apology* (30e) he is the gadfly
that stings a sluggish city awake with questions; in the *Theaetetus*
(148e–151d) he is a midwife, like his mother, who brings forth no ideas of his
own but helps others deliver theirs and tests whether each one holds.

Gadfly is the sting: the fixed trials that disturb a decision's evidence to see
whether the decision still stands. `midwife`, the library you install and
import, is the help in drawing out the premise you already hold and stating it
as a frame that can be tested.
