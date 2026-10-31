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
4. **Changes beyond cutting:** change a value (400 ms becomes 100 ms) or add
   contrary evidence, which tests direction, not only dependence.
5. **Better statistics:** report counts with ranges, stop early once a level
   is clear, and keep the temperature with the answers.
6. **Help writing frames:** for example, a warning when a control leaves a
   line that still points to the answer, as in
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
