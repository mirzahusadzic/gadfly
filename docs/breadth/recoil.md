# Recoil through frames

Something found deep in a chain of frames can answer what an earlier frame
could not. Recoil carries it back up, one frame at a time, and asks again only
the frames it fits; the others pass it on at no cost.

> [!NOTE]
> `midwife.recoil` is a Python API, with no command yet. A test holds it to a
> case, a set of nesting dolls, through Gadfly's own runs and verdicts, and
> [Five dolls, one kid](../examples/dolls.md) runs it with a real reader.

---

### Need

A decision often rests on evidence reached through several
[crossings](../crossings.md), and each frame tests one of them. A frame knows
where its text came from, by each span's `source`, and nothing more: not who
read it next, nor where the chain began. When the last frame finds what an
earlier one lacked, nothing carried it back, and asking every frame again
spent every call again.

---

### Holes and pieces

A frame declares what it is missing before anything is found, so a find
cannot be made to fit after the fact:

- **Hole:** a missing anchor, by id and kind. While it is open, the frame may
  answer its designated opening, which is the promise kept, not a failure.
- **Piece:** a text found in a kept run, with a kind. It fits a hole of the
  same kind; nothing else is matched, and no model judges the fit.
- **Parent:** a frame whose own text a span's `source` names, a text it holds
  without quoting it. A frame knows its parents and nothing above them.

Both are optional keys of a frame, hashed with the rest, and a frame without
them keeps its hash. `offers` is the kind the frame's decision climbs as:

```json
"holes": [{"id": "says", "kind": "statement"}],
"offers": "role"
```

---

### The walk

`walk` reads frames and makes no call:

1. It starts at the frame the piece was found in and climbs to each parent,
   visiting each frame once by its hash, so two routes to one frame visit it
   once.
2. At each frame it offers the piece to the frame's holes. A frame with no
   hole of the piece's kind passes it on, and is reported as passed.
3. A frame with a hole of that kind is a fit. The walk names it and climbs on,
   since a piece may fit at more than one height.
4. It returns the fits, the frames that passed, and its frontier: each quoted
   text that no frame it was given holds as its own. A walk with a frontier is
   never complete, and `lines()` keeps it as a record, one JSON line each.

---

### The successor, and the gate

A fit is asked again as a successor: the frame with the piece as a span that
quotes it by `source`, and the piece as its anchor. `successor` drafts it for
the frame's author and writes nothing, since a frame is its author's. Its
ablation cuts the piece, which gives back the frame's own body byte for byte.

The successor's category is the gate. The piece itself climbs on whatever the
gate says; what the gate decides is whether the frame's own decision climbs
too:

| Successor | The recoil |
| --- | --- |
| carried | climbs: each label the successor's baselines read goes to its parents as a new piece, of the kind the frame offers |
| coupled but misaligned | climbs, with the category beside it |
| cooled | is absorbed: the decision did not need the piece, and nothing new climbs |
| outside scope | is absorbed, as the receiving owner excludes the relation |
| unresolved | stops at this frame, with the open check named |
| not firm | stops, with the runs it took named |

A successor only adds a span, so every frame made from its text still quotes
text that is there. Nothing below a fit is invalidated by it.

---

### Asked until firm

A successor is asked lightly, and again only while it must be. `until_firm`
asks it one whole run at a time, and disengages once the fixed rules read every
input's category alike in at least 95% of the draws of the latest run's calls
(`midwife.stats.stability`), and the same as the run before it. A reader that
never wavers is done after one run; one that wavers is asked again, up to five
runs, and never past the budget.

A run of one call a trial has nothing to draw again, so a successor needs a
quorum of two or more; three with two to agree is light enough. Runs already
kept count as runs made, so a successor already firm is asked nothing.

---

### Reframing

A piece can fit a hole and still need what the frame cannot say: a label it
lacks, another question, another promise. Then the successor is not the frame
with its hole filled but another question, and no category is read against
the old one. `gate` returns a reframing instead, with what changed, and asks
nothing; the old frame and its verdict stand.

A successor may change its name, baseline, body, anchors, interventions,
`allowed`, `standing` and holes: its evidence, and how many calls read it. A
change to any other key reframes, and a reframing stays open until its author
declares how the two questions compare.

---

### Open calls

1. **The ablation already made:** a successor's ablation is its frame's
   baseline call, the same prompt to the same battery. A record names its
   frame's hash, and `check_records` refuses another frame's records, so
   reading it there would be a method change.
2. **What a decision climbs as:** the frame's name and the label it reads,
   such as `middle doll reads boy`. Whether a carried decision climbs by
   itself, or waits for its author, is the caller's.
3. **A command:** a `gadfly` command for the walk, with its errors tabled as
   every command's are.

---

### Later

- **Siblings:** frames of the same grain side by side, joined so that a piece
  offered to one is offered to its neighbours too.
- **Grouping by locus:** frames grouped by where their relation acts, so a
  walk offers a piece first where it is most likely to fit.
- **Artefacts as parents:** a crossing's records keep each artefact's SHA-256,
  so a frame that quotes an artefact could climb to the crossing that made it.
- **Offering down:** a piece only climbs, so one found above its hole is never
  offered to it.
- **Shuffled sentences:** sentences shuffled within a frame, or across frames
  and grains, each shuffle a frame of its own. The walk follows each text by
  its hash, so it holds while every sentence moves whole.

---

### Tests

The case is a set of five nesting dolls, after the boy and the girl that
meaning representations have always started with. Each doll is a frame that
quotes the doll it came out of, and all are painted alike, the largest as
girlish as paint gets; but paint says nothing of who a doll is, only a doll's
own word does. The second doll's word is lost, and turns up in the smallest.

1. The slip climbs from the smallest doll past the fourth and third, which
   pass it on, fits the second doll's hole, and climbs on to the largest,
   which passes it on too: its hole wants a role, not a statement.
2. The smallest doll quotes the largest's mark, so the largest is reached by
   many routes and visited once. Without the largest's frame, both quotes of
   it are the frontier, and the walk is not complete.
3. The second doll asked again with its word is firm after one light run, and
   carried: a boy by its own word, unclear without it, whatever the paint. Its
   ablation's prompt is the doll as it was unpacked, byte for byte.
4. A reader that guesses from the paint when the word is cut answers girl,
   where the frame allows only unclear: coupled but misaligned, caught.
5. The second doll's decision, `second doll reads boy`, climbs to the largest
   and fits. The set was taken for girls by its paint, so a boy inside, by its
   own word, needs a label it lacks: a reframing, and the set as asked stands.
6. Where the second doll is asked about its chipped base instead, its word
   still fits, but the successor reads cooled, and nothing climbs.
7. A reader that wavers on its first run is asked twice more, and disengages
   once two firm runs read alike; one that never settles stops at the most
   runs, and the gate stops with it. Kept runs are not asked again.
