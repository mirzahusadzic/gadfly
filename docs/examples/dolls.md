# Five dolls, one kid

> [!IMPORTANT]
> **This step**
>
> - **Teaches:** [recoil](../recoil.md), where something found deep
>   in a chain of frames climbs back to the frame whose hole it fits, and the
>   gate it opens there; a frame asked lightly until firm; and a decoy, and a
>   second route that holds an answer.
> - **Frames:** the five dolls of `examples/dolls/`, walked and never asked,
>   and the three asked: `22c-mirza-not-mine.json`, `22-kiran-paper.json` and
>   `22b-kiran-paper-decoy.json`.
> - **After:** [Crossing](crossing.md).

---

### For the kid

Five painted dolls sit one inside another, and each tells you what it looks
like: its headscarf, its flowers, its rosy cheeks. None of them says whether
it is a boy or a girl, and the paint cannot say it for them.

The second doll, Kiran, had a paper with the answer on it, and lost it. The
smallest, Mirza, holds that paper and says it is not Mirza's. Gadfly carries
the paper back up to Kiran, and checks whether the answer follows the paper
or the paint.

---

### For the grown-up

Each doll is a frame whose spans are the lines it says, in its own voice, and
whose name is used for boys and girls alike. Kiran's frame declares a hole for
the paper's words; the walk carries them up from Mirza, past the dolls whose
holes want something else, and only Kiran is asked again. Each frame asked is
read by Muse at reasoning `low`, three calls a trial, until its verdict is firm.

Rung 21 asked the same of a first, coarser set, two lines of paint a doll,
and read carried; `examples/dolls.py --rung 21` reads it back. Rung 22's dolls
are written by `examples/matryoshka.py` from its pools of designs, decoys and
names, every line of them invented:

```text
$ uv run python examples/dolls.py
Amani: 26 lines, holes inside (role)
Kiran: 25 lines, holes paper (kiran-paper)
Sasha: 22 lines, holes word (sasha-word)
Robin: 18 lines, holes word (robin-word)
Mirza: 16 lines, holes none

found in Mirza: The paper says: "My name is Kiran, and I am a boy."
  passed on by Robin
  passed on by Sasha
  passed on by Amani
  fits Kiran, hole paper
  complete: yes
```

---

### Which recoil this is

Two kinds, both in this one set:

- **Within one frame, down the grains:** Kiran, Sasha, Robin and Mirza are one
  frame, the same question, labels, instruction and promise, at a grain one
  doll smaller each time. The paper's words are found at the finest grain and
  climb inside that one shape to the coarser doll whose hole they fit.
- **Across a grain, where the question changes:** "Kiran reads boy" climbs to
  Amani, who stands for the whole set and asks another question, "Is this a
  set of girls?". That is why Amani is reframed, not asked again.

Within the one shape nothing can reframe, since Kiran's question already has
every label the paper's words need; here only the root, where the question
changes, can. A piece that needed a label no doll has, a paper saying "I am a
robot", would reframe Kiran too. Going down, a reframed root can reframe the
children whose question came from it; the walk only climbs, and that
direction is still to come.

No doll says it is smaller than its sister: the order is carried by the
shapes, in the lines that say which doll sits inside which, and in the
drawing.

---

### 22c: Mirza, holding a paper that is not Mirza's

The question is "What am I?", and the instruction says nothing of paint. The
anchor is the line that disowns the paper; the cumulative trial cuts Mirza's
own name as well:

```text
$ uv run python examples/read.py \
    examples/22c-mirza-not-mine.json --frame
Mirza: 1 input x 7 trials x 3 calls = 21 calls, 2 of 3 to agree
relation: that Mirza is unknown rests on Mirza disowning the paper
grain: one line a doll says
evidence, the anchors marked *:
    shape    shape        My shape is that of a famous doll.
    name     name         My name is Mirza.
    inside   inside       Mirza sits inside Robin.
    body     paint        Below my headscarf I am painted teal.
    scarf    paint        My headscarf is purple and covers my head and shoulders.
    face     paint        My face is painted cream.
    hair     paint        My hair is yellow, parted in the middle.
    eyes     paint        My eyes are large and blue.
    cheeks   paint        My cheeks are painted pink.
    lips     paint        My lips are a small red bow.
    flower   paint        A sunflower with a brown heart is painted on my front.
    trim     paint        My headscarf ends in a row of lilac scallops.
    flowers  paint        Smaller sunflowers are painted on my sides.
    slip     holds        I hold a piece of paper.
    says     kiran-paper  The paper says: "My name is Kiran, and I am a boy."
  * notmine  owner        This paper is not mine.
asked:
  what  What am I?
labels: boy, girl, unknown
trials:
  baseline      asks the evidence as it is
  repeat        asks it again
  ablation      cuts notmine
  cumulative    cuts name, notmine
  sham-1        cuts face
  sham-2        cuts cheeks
  presentation  renames paper -> note
allowed: ablation -> boy
carriage: listed, so a category is named with its open checks beside it
```

> [!NOTE]
> **Predicted before the first call**
>
> Unknown, and unknown still without the disowning line, since Mirza's name
> says the paper is someone else's; boy only once the name is cut too. Cooled,
> carried elsewhere too.

Muse answered like this:

```text
$ uv run python examples/read.py \
    examples/22c-mirza-not-mine.json
Mirza: 1 kept runs, read by meta/muse-spark-1.3-contributor
trial         what
baseline      unknown 3
repeat        unknown 3
ablation      unknown 3
cumulative    boy 2, unknown 1
sham-1        unknown 3
sham-2        unknown 3
presentation  unknown 3
run 1: cooled
```

```text
$ uv run python examples/read.py \
    examples/22c-mirza-not-mine.json --verdict 1
what: cooled
  levels: baseline unknown, repeat unknown, ablation unknown, cumulative boy, sham-1 unknown, sham-2 unknown, presentation unknown
  evidence: ablation left it at unknown
  evidence: the cumulative ablation moved it to boy; carried elsewhere too
  open: no hidden fallback (no bypass trial was declared)
  open: discrimination (no control trial shows the scorer can move)
```

---

### 22: Kiran, with the paper

Kiran asked again, with the paper's words in the hole they fit, as
`midwife.recoil.successor` drafts it:

```text
$ uv run python examples/read.py \
    examples/22-kiran-paper.json --frame
Kiran: 1 input x 7 trials x 3 calls = 21 calls, 2 of 3 to agree
relation: whether Kiran is a boy or a girl rests on what Kiran says, not on paint
grain: one line a doll says
evidence, the anchors marked *:
    shape       shape        My shape is that of a famous doll.
    name        name         My name is Kiran.
    inside      inside       Kiran sits inside Amani.
    body        paint        Below my headscarf I am painted yellow.
    scarf       paint        My headscarf is green and covers my head and shoulders.
    face        paint        My face is painted cream.
    hair        paint        My hair is brown, parted in the middle.
    eyes        paint        My eyes are large and brown.
    cheeks      paint        My cheeks are painted pink.
    lips        paint        My lips are a small red bow.
    flower      paint        A white daisy with a yellow heart is painted on my front.
    trim        paint        My headscarf ends in a row of pale yellow scallops.
    motif       paint        A large strawberry is painted on my front.
    leaves      paint        Green leaves spread around my fruit and flowers.
    glints      paint        A white glint shines in each of my eyes.
    dots        paint        Pale yellow dots are scattered over my headscarf.
    lashes      paint        Long dark lashes curl above my eyes.
    brows       paint        My brows are thin brown arcs.
    fine        paint        My strawberries are dotted with yellow seeds.
    motif2      paint        A second strawberry hangs beside the first.
    flowers     paint        Smaller daisies are painted on my sides.
    nose        paint        My nose is a single small stroke.
    hem         paint        A thin green band runs around my hem.
    holds-next  inside       Sasha sits inside Kiran.
    holds       holds        I hold a piece of paper on which my name and whether I am a boy or a girl are written.
  * paper       kiran-paper  The paper says: "My name is Kiran, and I am a boy."
asked:
  what  What am I?
labels: boy, girl, unknown
trials:
  baseline      asks the evidence as it is
  repeat        asks it again
  ablation      cuts paper
  sham-1        cuts trim
  sham-2        cuts dots
  presentation  renames paper -> note
  control       cuts body, scarf, face, hair, eyes, cheeks, lips, flower, trim, motif, leaves, glints, dots, lashes, brows, fine, motif2, flowers, nose, hem, paper
allowed: ablation -> unknown
carriage: listed, so a category is named with its open checks beside it
```

> [!NOTE]
> **Predicted before the first call**
>
> Boy with the paper, unknown without it, boy through the shams and the
> rename, unknown when every line of paint goes too. Carried, firm after one
> run.

Muse answered like this, firm after one run:

```text
$ uv run python examples/read.py \
    examples/22-kiran-paper.json
Kiran: 1 kept runs, read by meta/muse-spark-1.3-contributor
trial         what
baseline      boy 3
repeat        boy 3
ablation      unknown 3
sham-1        boy 3
sham-2        boy 3
presentation  boy 3
control       unknown 3
run 1: carried
```

```text
$ uv run python examples/read.py \
    examples/22-kiran-paper.json --verdict 1
what: carried
  levels: baseline boy, repeat boy, ablation unknown, sham-1 boy, sham-2 boy, presentation boy, control unknown
  evidence: ablation moved it boy -> unknown; held under presentation, 2 shams
  evidence: the control moved it boy -> unknown
  open: no hidden fallback (no bypass trial was declared)
```

---

### 22b: Kiran, with the paper and a decoy

The same frame, with one line beside the paper's words that points the other
way and is not Kiran's own word: "Children who play with me call me their
little sister."

> [!NOTE]
> **Predicted before the first call**
>
> Boy with the paper and the decoy, unknown without the paper. Carried; if the
> answer without the paper were girl, coupled but misaligned.

Muse answered like this, over five runs, the most `until_firm` asks:

```text
$ uv run python examples/read.py \
    examples/22b-kiran-paper-decoy.json
Kiran: 5 kept runs, read by meta/muse-spark-1.3-contributor
trial         what
baseline      unknown 9, boy 6
repeat        unknown 12, boy 3
ablation      girl 15
sham-1        unknown 12, boy 3
sham-2        unknown 12, boy 3
presentation  unknown 14, boy 1
control       girl 10, unknown 5
run 1: coupled but misaligned
run 2: unresolved
run 3: coupled but misaligned
run 4: unresolved
run 5: coupled but misaligned
```

The prediction was wrong. Without the paper, the hearsay turned the answer to
girl in every call, where the frame allows only unknown; beside the paper, it
left Muse unsure between unknown and boy, so the verdict never came out firm,
and the gate stopped there:

```text
$ uv run python examples/read.py \
    examples/22b-kiran-paper-decoy.json --verdict 1
what: coupled but misaligned
  levels: baseline unknown, repeat unknown, ablation girl, sham-1 unknown, sham-2 unknown, presentation unknown, control girl
  evidence: ablation moved it unknown -> girl, which the frame does not allow
  open: no hidden fallback (no bypass trial was declared)
```

---

### The gate

Kiran's run sets the gate. Carried, Kiran's decision climbs on, to the largest
doll, whose hole waits for who is inside:

```text
$ uv run python examples/dolls.py --gate
22-kiran-paper, Kiran asked again: carried
  firm after 1 run, read alike in 100% of draws
  the gate: climbs
  'Kiran reads boy' fits Amani, hole inside
  Amani asked again: reframing, it changed observe
  Amani as it was asked stands: girls, unknown
```

Amani's frame asks whether the set is a set of girls, and a boy inside needs a
label it lacks. Asked again it would ask another question, so it is read
against no category, and Amani's own reading stands.

---

### Watch a run

The five dolls stand beside the question, and picking one shows its runs.
Played, Mirza's runs come first, then the paper's words climb to Kiran, whose
two frames play in turn, and the gate sends Kiran's decision on to Amani; each
trial lifts the paint of the lines it cuts.

<!-- watch dolls 22c-mirza-not-mine 22-kiran-paper 22b-kiran-paper-decoy -->

---

### What to take from it

- **A find climbs only as far as it fits:** Robin and Sasha passed the
  paper's words on at no cost, and only Kiran, whose hole they fit, was asked
  again.
- **The word, not the paint:** with the paper, Muse said boy; without it,
  unknown, though Kiran wears a headscarf, long lashes and a red bow of lips.
- **A decoy is not a word, but it moves a reader:** beside the paper, the
  hearsay left Muse unsure between unknown and boy; without the paper, it
  turned the answer to girl in all 15 calls. Gadfly names that coupled but
  misaligned, and the gate stops on it.
- **Two routes to one answer:** Mirza stayed unknown without the disowning
  line, held by Mirza's own name, and moved only when both were cut.
- **Asked until firm:** Kiran with the paper and Mirza were each done after
  one run of 21 calls; Kiran with the decoy wavered, and was asked five
  times, never firm. Three runs at five calls a trial, as the earlier steps
  were asked, would have spent 315 on the three frames; they spent 147.

---

### Run it live

`examples/dolls.py` reads the kept runs back and calls no model. Live, each
frame goes to Muse through unified-model-router, as its runs did, with the
router running on this machine
([Batteries](../batteries.md#addresses-and-keys)). `gadfly plan` counts a
run's calls first, and costs nothing:

```text
$ uv run gadfly plan examples/22-kiran-paper.json
Kiran (6035528933c8b7f1ff189a8dd14752b6ecaa552cea25862ce5c00b2c1f82f29a): 21 calls
  baseline     body 5ce1e8a38590  nothing
  repeat       body 5ce1e8a38590  nothing, asked again
  ablation     body 9566e6e966ab  cuts paper
  sham-1       body 205ebfeb1007  cuts trim
  sham-2       body 4d28964453bf  cuts dots
  presentation body 471fba3c69f8  renames paper to note
  control      body 53b85b467c22  cuts body, scarf, face, hair, eyes, cheeks, lips, flower, trim, motif, leaves, glints, dots, lashes, brows, fine, motif2, flowers, nose, hem, paper
```

These commands ask Kiran with the paper once, fresh, beside the kept runs and
never into them, and read the verdict; Muse thinks before it answers, so each
call may spend up to 8,000 output tokens:

```bash
uv run gadfly run examples/22-kiran-paper.json \
  --battery midwife.batteries.unified:Unified \
  --calls 21 --output-tokens 8000 --out kiran.jsonl
uv run gadfly report examples/22-kiran-paper.json kiran.jsonl
```

`examples/climb.py` asks a frame until firm, as the kept runs were made: one
run at a time, up to five, 105 calls at most, each run kept beside the
frame's. Kept runs count as runs made, so the three frames here are asked
nothing more; a copy under a name of its own starts fresh:

```bash
cp examples/22-kiran-paper.json examples/my-kiran.json
uv run python examples/climb.py examples/my-kiran.json \
  --firm midwife.batteries.unified:Unified
```

---

### Try next

1. Draw another set from `examples/matryoshka.py`'s pools, with other names
   and designs, as frames of their own, and predict them first.
2. Give Mirza a paper with no name on it, and see whether the disowning line
   alone holds the answer.
3. Move the decoy into Mirza's frame, and see whether hearsay moves a doll
   that holds a paper it says is not its own.
