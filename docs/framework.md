# Framework

Gadfly applies the method in [When meaning is load-bearing](load-bearing.md). This
page is the bridge between the essay's symbols and the library's public names.
It is deliberately an overview: the tutorial runs one frame; the reference lists
every callable.

<!-- copy README.md:model -->
## The path from premise to verdict

| Stage | What it makes | What stays fixed |
|---|---|---|
| `situate` | a checked `Frame` and its SHA-256 | every declared coordinate, including grain and battery |
| `plan` | the trials derived from the frame | trial bodies and order; the caller may inspect them before spending anything |
| `run` | one `Record` per call | the exact body, input, trial and quorum index recorded beside the observation |
| `judge` | one `Finding` per input | the frame, battery, body hashes, trial set, quorum and label vocabulary |
| `overall` | one `Overall` over the findings | every input's category and evidence while combining the frame-level answer |

Gadfly is a library with no hidden store. `run()` is the only stage that calls a
battery; records go to your `on_record` callback as they are made. `judge()`
recomputes the reading from those records. Keep them as JSON Lines, database
rows, or fixtures, but keep them.
<!-- end copy -->

## The essay and the frame

The situated use $L=(I,B,r,g,P,T,B_0,C,p)$ becomes the descriptive keys of the
frame. The assessment frame $\Gamma=(A,r,g,P,T,B_0,p,o_p,D,\sigma)$ adds the
anchors, the observation map, the declared interventions and standing.

| Essay | Frame | Meaning in Gadfly |
|---|---|---|
| $I$ | `relation` | the premise under intervention |
| $v$ | `locus` | where it acts |
| $B$ | `body.spans` | the text it lives in, at the declared grain |
| $r,g,P,T$ | `role`, `grain`, `purpose`, `trajectory` | whose reading, at what unit, for what path |
| $B_0$ | `baseline` | everything pinned for the comparison |
| $C,p$ | `crossing`, `promise` | the boundary and the consequence required there |
| $A$ | `anchors` | span ids removed by ablation |
| $o_p$ | `observe.instruction`, `labels`, `order` plus your battery | what the scorer reads and the complete label vocabulary |
| $D$ | `interventions`, `allowed`, `standing` | the admissible changes, allowed influence, and sampling standing |
| $\sigma$ | `standing.quorum`, `agree`, `stable` | observation standing |
| $\simeq_p$ | exact label equality | no hidden similarity function |
| $E_{p,\delta}$ | `allowed` | the permitted influence relation |
| carriage checks | `carriage` | whether an open check holds carried and cooled back (`all-checks`) or is listed beside them (`listed`) |
| scope check | `outsideScope`, `scopeCheck` | the owner's exclusion, and the owner's own check of it |

The code hashes the **whole** frame, including the situated-use keys. This is
stricter than changing only $\Gamma$: editing any coordinate creates a new frame
hash and requires records to be made or replayed under that new frame.

`materialized`, `outsideScope` and `scopeCheck` are declarations about the
receiving side: Gadfly reads them, it does not inspect the receiving system. See
[Architecture and limits](architecture.md).

## The four data objects

| Object | Created by | What it answers |
|---|---|---|
| `Frame` | `situate` | what was declared, under one hash |
| `Trial` | `plan` | what one intervention changes |
| `Record` | `run` through `on_record` | what one scorer call read and observed |
| `Finding` / `Overall` | `judge` / `overall` | what the fixed rules say, with evidence and obligations |

The records are the durable evidence. `judge` does not rerun a scorer and does
not consult the frame's source file; it reads the records, checks they are records
this frame could have made, and applies the rules.

## Where the rest lives

- [Your first frame](first-frame.md) walks one frame from JSON to verdict.
- [Write a frame](write-a-frame.md) is the field and refusal reference.
- [Interventions](interventions.md) explains each trial and its cost.
- [Reading a verdict](reading-a-verdict.md) gives the category rules, evidence and obligations.
- [Batteries](batteries.md) covers deterministic and live scorers.

