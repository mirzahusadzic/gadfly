# Extending Gadfly

The core is deliberately small. These extensions widen who can use the method,
each answering one need and keeping its contracts.

| Capability | Use it | What it keeps |
|---|---|---|
| Command line and report | `gadfly plan`, `run`, `report` | records as JSON Lines, an explicit budget, evidence apart from obligations |
| Frame schema and authoring check | `midwife/frame.schema.json`, `gadfly check-frame` | the parser as the authority |
| Portfolio summary | `gadfly portfolio` | no verdict across frames |
| `placement` intervention | `"placement": {"span": id, "after": id}` | old frames' hashes and categories |
| `local-json` battery | `"battery": {"kind": "local-json", "url": ...}` | loopback, no credentials, a whole-call deadline |
| Settled trials | `gadfly run --settle` | every level, category and evidence line of a whole run |
| Calls at once | `gadfly run --parallel N` | the budget, and every call already made |
| Dead ends before a call | `gadfly plan` | the verdict rules, read over every answer each trial could give |
| Shams of another kind | `"sham": {"draws": n, "kind": {anchor: kind}}` | old frames' hashes and plans |
| Stopping at unresolved | `gadfly run --stop-unresolved` | the category a whole run reads |
| Records through a pipe | `gadfly run --out -`, `gadfly report FRAME -` | each record written as it exists, never over a file |
| Errors and warnings as classes | `midwife.errors`, `--json` on every command | one exit status a class, and every message tabled |
| Inversion and input inversion | `"inversion"` and `"inputInversion"`, with their `allowed` | old frames' hashes and plans |
| Each anchor alone | `"eachAnchor": true` | every category: its trials are evidence only |
| Statistics beside a verdict | `gadfly stats`, `gadfly plan --agreement`, `midwife.stats` | every verdict as the rules read it; the same draws for the same records |
| Crossing battery | `"battery": {"kind": "crossing", "maker": ..., "reader": ...}` | each side's own guarantees; the maker never sees the input; one cap for the call |
| A span's source | `"source": {"sha256": ..., "from": ...}` on a span | the span's text, held to the hash byte for byte |

---

### Why each exists

Each extension answers a need the core left to the reader. Its page has the
details.

- **[Command line](command-line.md):** the essay requires kept evidence and
  visible obligations. Without it, a reader writes Python to keep records,
  then joins evidence and obligations in a print loop of their own.
- **Frame schema and authoring check:** declaration errors should show in an
  editor before a run. The parser stays the authority, because rules across
  fields are not all expressible in JSON Schema.
- **Portfolio summary:** `overall()` reads one frame over its inputs. No fixed
  rule combines different relations, promises and recipients, so a portfolio
  verdict would be a category error, and `gadfly portfolio` only counts.
- **[Placement](breadth/placement-intervention.md):** presentation
  invariance does not test whether a clause's place matters.
- **[Local JSON battery](breadth/local-json-battery.md):** a local evaluator
  gets the shipped batteries' privacy and deadline treatment without an
  adapter of its own.
- **Settled trials:** a trial whose level was already fixed still spent its
  remaining calls; with four of five to agree, four alike decide it.
- **Calls at once:** a battery that can serve several calls, such as a
  router, waited on one at a time.
- **Dead ends before a call:** a frame that no answers could make carried,
  such as one with no bypass under the default policy, spent every call
  before its verdict said so.
- **Shams of another kind:** an anchor alone of its kind got no sham, and the
  only way round was to give it a kind it does not have.
- **Stopping at unresolved:** an input that could read nothing else still
  spent every trial, such as one whose ablation and control both held.
- **Records through a pipe:** a run could only write a file, so a script
  that wanted the verdict kept one it did not need. `-` stands for standard
  output and input, as clig.dev asks.
- **[Errors and warnings as classes](troubleshooting.md):** a script or
  another model could tell a bad frame from a bad battery only by reading
  the words, and openings and early stops were lines with no class. Each is
  now a Python error or warning, with its own exit status.
- **[Inversion and input inversion](interventions.md#inversion-asks-for-a-direction):**
  cutting shows that an answer depends on a line, not that it follows the
  line's sense, or what is asked.
- **[Each anchor alone](interventions.md#each-anchor-alone-says-how-several-carry-it):**
  with two anchors the ablation cuts both, so it cannot tell a chain of rules
  from two routes either of which is enough.
- **[Statistics](statistics.md):** five calls a trial are evidence, not proof,
  and nothing said whether a verdict rested on all of its calls or on one.
- **[Crossings](crossings.md):** a decision is often made from something
  written from the evidence, and a trial could not reach the writing.
- **A span's source:** a frame could quote text it said came from across a
  boundary without anything holding it to that text.

---

### What comes next

The examples point at these, most useful first. None is built yet.

1. **Expectations per input:** an optional expected result for each input,
   so a frame whose inputs differ on purpose reads as promised. Today several
   real frames read unresolved when each input behaved as promised (design
   calls A and B in `examples/FINDINGS.md`).
2. **Regression tests for AI deployments:** keep a set of frames and run them
   again when the model, prompt or policy changes, then compare verdicts. Does
   the new model still enforce the rule because of the rule? `gadfly
   portfolio` is a start.
3. **Comparing readers:** run one frame on Gemma, Claude or a panel of human
   reviewers, which makes the essay's handoff measurable.
4. **Adding evidence:** add contrary evidence, beyond the cuts, the renames,
   the moves and the inversion's turned words.
5. **The temperature with the answers:** keep in each record the temperature
   its call was made at, which a frame that names none leaves unknown.
6. **Help writing frames:** beyond the dead ends `plan` names, a warning
   when a control leaves a line that still points to the answer, as in
   [A frame built wrong](examples/built-wrong.md). It flags problems and never
   writes a frame from a result.

---

### Deliberately left out

These stay out on purpose, each because it would undo a boundary the method
keeps.

- **A single score across categories:** the method returns distinctions, not
  a quality metric, and collapsing them would hide what the essay asks to
  keep.
- **Automatic consent to training-tier providers:** consent stays an
  explicit, exact model slug in the frame.
- **A hosted record store:** keeping no state is a boundary, and how long
  records are kept is a separate decision.
