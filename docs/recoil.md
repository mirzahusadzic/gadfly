# Recoil

A chain of frames is a chain of [crossings](crossings.md): each frame names,
by a span's `source`, the text it crossed with. Recoil runs that chain
backwards, carrying something found deep in it up, one frame at a time, to
the frames it can answer. Only those are asked again; every other frame
passes it on at no cost, and keeps its verdict.

> [!NOTE]
> Each step is both a command, `gadfly walk`, `successor`, `firm` and `gate`
> ([Command line](command-line.md#recoil-through-frames)), and a function of
> `midwife.recoil` of the same name. [Five dolls, one kid](examples/dolls.md)
> runs it with a real reader, and [Recoil through frames](breadth/recoil.md)
> keeps its design: why it was needed, its open calls, what comes later, and
> the case its tests hold.

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

A hole may also say what it is read for, under `about`, and its
`salience`: `consider`, the default, or `defer`, whose fit a walk lists as
deferred, kept and not asked. Both are written before any walk, as the hole
is, so a successor that changes them on a hole it leaves open reframes.

---

### The walk

`walk` reads frames and makes no call:

1. It starts at the frame the piece was found in and climbs to each parent,
   visiting each frame once by its hash, so two routes to one frame visit it
   once.
2. At each frame it offers the piece to the frame's holes. A frame with no
   hole of the piece's kind passes it on, and is reported as passed.
3. A frame with a hole of that kind is a fit. The walk names it and climbs on,
   since a piece may fit at more than one height. A hole that defers is
   listed as deferred instead: its fit is kept and not asked, never dropped.
4. It returns the fits, the deferred, the frames that passed, and its
   frontier: each quoted text that no frame it was given holds as its own. A
   walk with a frontier is never complete, and `lines()` keeps it as a
   record, one JSON line each.

---

### Artefacts as parents

A crossing's maker makes an artefact from each trial's body, and each record
keeps its SHA-256. Given a crossing's runs, `walk(..., made=[run, ...])` or
`gadfly walk --made FILE` takes each artefact as text that crossing frame
made, so a frame quoting it by `source` climbs to the crossing.

Each run is checked against its frame first, as a kept run is, and a frame
reached so names the trial and input of each record that made the artefact.
The walk still makes no call: where the piece fits the crossing, its
successor puts it on the near side, and the maker makes the artefact again.

---

### Sideways

A piece found in a frame can fit a frame beside it, which never quotes it.
`walk(..., sideways=True)` or `gadfly walk --sideways` offers it one step
aside too, from the start frame only: to each frame given that quotes, by
`source`, a text the start frame quotes.

Siblings come from that fixed rule, never from nearness, so none is dropped,
and vectors only order them. Each then climbs as usual, and is not followed
sideways again: a sibling's sibling is not reached.

---

### A walk's budget

Each hole a piece fits is a fit of its own, in `order`: frames as the walk
reached them, holes as each frame lists them. Given calls, `walk(...,
calls=N)` counts each fit before the first call, as `calls_until_firm`
counts its successor as drafted, over at most `most` runs.

The budget asks the fits in order up to the first it cannot cover. That fit
and every one after it are listed as not asked, so a later fit is never
asked before an earlier one, and `unasked` names them.

---

### Ordered by whole-text vectors

Gadfly never makes a vector: its caller acquires one for each whole text
and hands them over, as `walk(..., vectors=read_vectors(data))` or
`gadfly walk --vectors FILE`. Each is keyed by the SHA-256 of its exact
text, as a span's `source` is, and by an opaque `space` id that Gadfly only
compares. The fits are then ordered by the cosine of the piece's vector to
the vector of what each hole is read for, its `about`.

The vectors are JSON Lines, one a line. A text has at most one vector in a
space, and a second refuses them all, even with the same values:

```json
{"text": "<sha256>", "space": "<id>", "values": [0.6, 0.8]}
```

- **One space:** two vectors are compared only within one space, the one
  named or the only one given. The walk's record names it, and the SHA-256
  of the vectors.
- **Exact:** cosine is dot / (|a| |b|), each sum by `math.fsum`, highest
  first and ties by frame hash, so a replay orders alike. Nothing is cut or
  normalised: vectors come already cut.
- **No default score:** a fit with no cosine keeps its place, with why: the
  piece or the hole's `about` has no vector in the space, their lengths
  differ, a value is not finite, a vector has no length, or the cosine
  overflows. The fits with one are sorted among the places they hold.
- **Order only:** a vector never decides a fit, since the kind does, and a
  budget asks in this order.

---

### Climbing without asking again

Recoil is content-addressed, as a build is. A frame is its hash, it names its
parents by the SHA-256 of the texts it quotes, and a piece fits a hole by kind,
so a walk is lookups and comparisons, and makes no call.

- **Only a fit is asked again:** a frame the piece does not fit keeps its hash,
  and its kept runs still hold, as a cache's entry does. A successor only adds
  a span, so every frame that quotes the old text still finds it.
- **A decision climbs the same way:** it is another piece, and another walk.
  Where it fits, the frame is asked again only if the successor does not
  reframe; a reframing asks nothing.
- **Asked, not rebuilt:** unlike a compiler's, a reader's answer is not the
  same every time, so a fit is not built once but asked lightly until its
  verdict is firm. Kept runs are read, never asked again.

---

### The successor, and the gate

A fit is asked again as a successor: the frame with the piece as a span that
quotes it by `source`, and the piece as its anchor. `successor` drafts it for
the frame's author and writes nothing, since a frame is its author's. The
piece comes last, or right after the span `after` names, the line it amends;
either way its ablation cuts it and gives back the frame's own body byte for
byte.

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
`calls_until_firm`, or `gadfly plan --most`, counts the most calls it can make
before the first.

`examples/climb.py FRAME.json --firm module:Class` asks a frame so through the
battery named, and keeps each run as a records file of its own.

---

### Reframing

A piece can fit a hole and still need what the frame cannot say: a label it
lacks, another question, another promise. Then the successor is not the frame
with its hole filled but another question, and no category is read against
the old one. `gate` returns a reframing instead, with what changed, and asks
nothing; the old frame and its verdict stand.

A successor may change its name, baseline, body, anchors, interventions,
`allowed` and `standing`: its evidence, and how many calls read it. Of its
holes it may only close the one it fills, with a span of that hole's kind,
since what a frame can take in is part of its question. A change to any other key or hole reframes, and a
reframing stays open until its author declares how the two questions compare.

---

### Kinds of recoil

- **Within one frame, down the grains:** the frames share one shape, the same
  question, labels and promise, each at a smaller grain, and the piece climbs
  inside that shape to the frame whose hole it fits.
- **Across a grain, where the question changes:** a decision climbs to a frame
  that asks something else, as a doll's answer climbs to its set. Where it
  fits, the frame asked again would ask another question: a reframing.
- **Sideways, between frames of one grain:** one step aside, from the frame
  the piece was found in to the frames quoting a text it quotes, as above.

---

### From the command line

The steps on the dolls: the paper's walk up from Mirza, Kiran's successor
with the paper in its hole, asked until firm through the router, and the
gate it sets. `walk` and `gate` call no model, and `firm` keeps each run in
the folder it is given:

```bash
uv run gadfly walk examples/dolls/*.json \
  --from examples/dolls/5-mirza.json --span says
uv run gadfly successor examples/dolls/2-kiran.json \
  --hole paper --from examples/dolls/5-mirza.json \
  --span says --out kiran.json
mkdir kiran-runs
uv run gadfly firm kiran.json --runs kiran-runs \
  --battery midwife.batteries.unified:Unified \
  --calls 45 --output-tokens 8000
uv run gadfly gate examples/dolls/2-kiran.json \
  kiran.json --runs kiran-runs
```

Each takes `--json` and prints what its function below returns, so a script
or another model reads the same as Python does. When the gate climbs,
`walk --from kiran.json --decision boy` carries Kiran's decision on.

---

### In Python

The same steps in Python, with a battery of yours asking each fit's
successor live: a piece from the frame it was found in, its walk, the
successor asked until firm, and the gate it sets. `examples/dolls.py --gate`
reads the dolls' gate from their kept runs instead, with no battery:

```python
from midwife.frame import parse
from midwife.recoil import found, gate, successor
from midwife.recoil import until_firm, walk
from midwife.types import Budget

piece = found(smallest, "says")
climbed = walk(piece, smallest, dolls)
for frame, holes in climbed.fits:
    after = parse(successor(frame, holes[0], piece))
    asked = until_firm(after, battery, Budget(calls=45))
    recoil = gate(frame, after, asked)
```

`recoil.gate` is `climbs`, `absorbed`, `stops` or `reframing`. When it
climbs, each piece in `recoil.climbs` is walked again from the successor,
and [Python API](reference.md#midwiferecoil) has every name.
