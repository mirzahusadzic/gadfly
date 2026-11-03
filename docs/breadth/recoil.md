# Recoil through frames

Something found deep in a chain of frames can answer what an earlier frame
could not. Recoil carries it back up, one frame at a time, and asks again only
the frames it fits; the others pass it on at no cost.

> [!NOTE]
> A design, not built. `tests/test_recoil_design.py` holds it to a case, a set
> of nesting dolls, with a model of the walk and Gadfly's own runs and verdicts.

---

### Need

A decision often rests on evidence reached through several
[crossings](../crossings.md), and each frame tests one of them. A frame knows
where its text came from, by each span's `source`, and nothing more: not who
read it next, nor where the chain began. When the last frame finds what an
earlier one lacked, nothing carries it back, and asking every frame again
spends every call again.

---

### Holes and pieces

A frame declares what it is missing before anything is found, so a find
cannot be made to fit after the fact:

- **Hole:** a missing anchor, by id and kind. While it is open, the frame may
  answer its designated opening, which is the promise kept, not a failure.
- **Piece:** a text found in a kept run, by its SHA-256, with a kind. It fits
  a hole of the same kind; nothing else is matched, and no model judges the
  fit.
- **Parent:** a frame whose text a span's `source` names. A frame knows its
  parents and nothing above them, and the walk needs no more.

Both are new keys of a frame, with the kind its decision climbs as:

```json
"holes": [{"id": "head", "kind": "head"}],
"offers": "role"
```

---

### The walk

The walk reads frames and kept runs, and makes no call:

1. It starts at the frame the piece was found in and climbs to each parent,
   visiting each frame once by its hash, so two routes to one frame visit it
   once.
2. At each frame it offers the piece to the frame's holes. A frame with no
   hole of the piece's kind passes it on, and is reported as passed.
3. A frame with a hole of that kind is a fit. The walk names it and climbs on,
   since a piece may fit at more than one height.
4. It returns the fits, the frames that passed, and its frontier: each
   `source` that no frame it was given holds. A walk with a frontier is never
   reported complete.

---

### The successor, and the gate

A fit is asked again as a successor: the frame with the piece as a span that
quotes it by `source`, and the piece as its anchor. The walk prints what the
successor changes and never writes it, since a frame is its author's, and the
successor runs as any frame does, planned and counted first. Its ablation cuts
the piece, which gives back the frame's own body byte for byte.

The successor's category is the gate. The piece itself climbs on whatever the
gate says; what the gate decides is whether the frame's own change climbs too:

| Successor | The recoil |
| --- | --- |
| carried | climbs: the successor's decision goes to its parents as a new piece, of the kind the frame offers |
| coupled but misaligned | climbs, with the category beside it |
| cooled | is absorbed: the decision did not need the piece, and nothing new climbs |
| outside scope | is absorbed, as the receiving owner excludes the relation |
| unresolved | stops at this frame, with the open check named |

A successor only adds a span, so every frame made from its text still quotes
text that is there. Nothing below a fit is invalidated by it.

---

### Reframing

A piece can fit a hole and still need what the frame cannot say: a label it
lacks, another question, another promise. Then the successor is not the frame
with its hole filled but another question, and no category is read against
the old one. The walk reports a reframing opening instead, with both frames
by hash and what changed, beside the old frame's own verdict, which stands.

Filling a declared hole changes only the evidence: the body, the anchors, the
interventions and `allowed`. A successor that changes its relation, role,
locus, grain, purpose, trajectory, crossing, promise, inputs, `observe`,
`standing` or battery reframes. A reframing opening stays open until its
author declares how the two questions compare.

---

### State, not replays

- **A walk is a record:** the piece's hash, each frame's hash and outcome,
  and the frontier, one JSON line each. The same piece over the same frames
  gives the same record, so no walk is made twice.
- **Only fits spend:** a frame that passes costs nothing, and only a
  successor is asked, once `gadfly plan` has counted its calls.
- **Kept runs are read, not asked again:** a call whose prompt and battery
  are unchanged has its kept record. Asking a model again is a new
  observation, not a reproduction.

---

### Open calls

1. **The new keys:** `holes` and `offers`, and a frame whose only anchor is a
   hole, which today's parser refuses, since anchors name spans of the body.
2. **The ablation already made:** a successor's ablation is the frame's
   baseline call, the same prompt to the same battery. A record names its
   frame's hash, and `check_records` refuses another frame's records, so
   reading it there is a method change.
3. **What a decision climbs as:** the test's piece is the frame's name and
   its level, such as `middle doll reads boy`. Whether a carried decision
   climbs by itself, or waits for its author, is also open.

---

### Later

- **Siblings:** frames of the same grain side by side, joined so that a piece
  offered to one is offered to its neighbours too.
- **Grouping by locus:** frames grouped by where their relation acts, so a
  walk offers a piece first where it is most likely to fit.

---

### Tests

The case is a set of nesting dolls, after the boy and the girl that meaning
representations have always started with. Each doll is a frame that quotes the
doll it came out of: the set, the middle doll, whose head is missing, and the
smallest, which holds a painted head with a beard.

1. The head climbs from the smallest doll, fits the middle doll's hole, and
   climbs on to the set, which passes it on: the set's hole wants a role, not
   a head.
2. The smallest doll quotes both the set and the middle doll, which quotes the
   set again, and the set is visited once. Without the set's frame, both
   quotes of it are the frontier, and the walk is not complete.
3. The middle doll asked again with its head reads carried: a boy with the
   head, unclear without it. Its ablation's prompt is the doll as it was
   unpacked, byte for byte.
4. Its decision climbs to the set as a piece of kind `role`, and fits. The set
   was asked girls or unclear, so a boy inside needs a label it lacks: a
   reframing opening, and the set as it was asked stands, unchanged.
5. Where the middle doll is asked about its chipped base instead, its head
   still fits, but the successor reads cooled, and nothing climbs.
