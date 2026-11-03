# Recoil through frames

Something found deep in a chain of frames can answer what an earlier frame
could not. Recoil carries it back up, one frame at a time, and asks again only
the frames it fits; the others pass it on at no cost.

> [!NOTE]
> How to use it is in [Recoil](../recoil.md). This page keeps its design: the
> need, its open calls, what comes later, and the case its tests hold it to,
> which [Five dolls, one kid](../examples/dolls.md) runs with a real reader.

---

### Need

A decision often rests on evidence reached through several
[crossings](../crossings.md), and each frame tests one of them. A frame knows
where its text came from, by each span's `source`, and nothing more: not who
read it next, nor where the chain began. When the last frame finds what an
earlier one lacked, nothing carried it back, and asking every frame again
spent every call again.

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
- **Reframing down:** going up, only a frame whose question changes can
  reframe, often the root; going down, a reframed frame can reframe the
  frames whose question came from it, each opened as a reframing in turn.
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
