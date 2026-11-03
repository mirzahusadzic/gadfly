# Crossings

A decision often rests on its evidence only through something made from it:
metric lines become an incident's cause, a meeting becomes its minutes, a
year of findings becomes a strategy. A crossing frame tests whether what the
anchors said survives that making, with the maker inside the reading. The
verdict then says whether the decision is carried across the boundary, or
cooled at it.

---

### Two directions

A crossing changes the grain, and the locus moves with it. Which way a frame
reads it depends on whether the artefact can be made again:

- **Out, through a maker that runs again:** the frame's spans are the
  evidence on the near side, and the `crossing` battery has a maker write the
  artefact from each trial's body before a reader decides from it. Every
  trial changes the evidence before the maker sees it, so ablation asks
  whether the decision still moves when the maker never saw the anchors.
- **In, from an artefact made once:** a poem already written, a report
  already filed, a dream told the morning after. Nothing can make it again
  from changed evidence, so a frame reads its lines as they are, with any
  battery, and each span names the exact text it crossed with in `source`.

The same holds upward: findings become a brief, and a brief a decision about
a product's posture. Each step is a crossing of its own, and each can be
tested where it happens.

---

### The crossing battery

The battery line names the maker and the reader, each in a line of its own.
The frame's instruction and labels are the reader's; the maker's
instruction is in its line, and the frame's hash names both:

```json
"battery": {
  "kind": "crossing",
  "maker": {
    "kind": "unified",
    "model": "anthropic/claude-sonnet-5-5",
    "instruction": "Write the incident's cause in two sentences."
  },
  "reader": {
    "kind": "unified",
    "model": "anthropic/claude-sonnet-5-5",
    "reasoning": "low"
  }
}
```

`Crossing` with no arguments makes and reads through the unified model
router, and each line is held to every check of the
[unified battery](batteries.md#the-shipped-batteries). Give each call room
for both answers:

```text
gadfly run incident.json \
    --battery midwife.batteries.crossing:Crossing \
    --calls 150 --output-tokens 4000 \
    --out incident.jsonl
```

- **What the maker sees:** the trial's body alone, never the input and never
  which trial it serves.
- **What the reader sees:** the artefact, the `---` line, and the input, as
  any battery sees a body and its input.
- **What a call spends:** the maker is given half of `--output-tokens`, and
  the reader what the maker left, so the cap and the token budget hold for
  the call as a whole.
- **What a record keeps:** `served` reads `made by …, read by …`, and the raw
  answer holds the reader's answer, then the artefact's SHA-256 and text.
- **When a side fails:** an artefact not made is an opening that says so
  (`the maker made nothing (…)`), and the reader is not asked.

---

### What the verdict says

The categories read as they do for any frame, with the maker inside the
reading:

- **Carried:** what the anchors said reached the decision through the
  artefact, and the frame's checks held.
- **Cooled:** the decision did not move without the anchors. Either the
  maker dropped what they said, or the reader never used it.
- **Unresolved:** often openings from one side, and each opening names which.

To tell a lossy maker from a reader that ignores the evidence, read the
baseline's artefact on its own, in a frame of its own: its span is the
artefact, its `source` is the SHA-256 the crossing's record kept, and its
anchor is the artefact itself. If the reader moves there but not through the
crossing, the maker lost it.

---

### From Python

A maker is any object with a `name`, `check(line)` and
`make(line, text, max_output_tokens)`, which returns a `Made`; any battery
reads. `Function` makes a maker of a plain function of the body's text:

```python
from midwife.batteries.crossing import Crossing, Function
from midwife.batteries.egemma import EGemma


def cause(body: str) -> str:
    if "connection pool" in body:
        return "The deploy shrank the connection pool."
    return "The cause is not known yet."


crossing = Crossing(Function("incident-cause", cause), EGemma())
```

Kept in a module of your own, `--battery yourmodule:crossing` runs it. The
function's line is `{"kind": "incident-cause"}`, so the frame's hash names
the function by that name alone: give a changed function a new name.

---

### Provenance across the boundary

A span may name the text it crossed with: `source` holds that text's
SHA-256 and, optionally, where it came from. The parser holds the span's
text to the hash byte for byte, so a frame cannot quote what it did not
receive, and a changed source is a changed frame:

```json
{
  "id": "s2",
  "text": "The deploy shrank the connection pool.",
  "kind": "cause",
  "source": {
    "sha256": "<the SHA-256 of the text>",
    "from": "the incident's cause, as written"
  }
}
```

A crossing's records keep each artefact's SHA-256, so the next frame in a
chain names the one it reads, and a reader of both can follow the evidence
from one grain to the next.
