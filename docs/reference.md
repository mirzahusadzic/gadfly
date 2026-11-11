# Python API

Each module's section below is written from its public docstrings by
`tools/doc_outputs.py`, and a test keeps it current, so it reads the same here
and on GitHub. For narrative guidance start with
[Your first frame](first-frame.md) or [Reading a verdict](reading-a-verdict.md).

- **[`midwife.pipeline`](#midwifepipeline):** `situate`, `plan`, `run`,
  `judge`, `overall`, `calls_needed`.
- **[`midwife.frame`](#midwifeframe):** frame parsing and hashing.
- **[`midwife.errors`](#midwifeerrors):** what Gadfly refuses, a class for
  each thing to fix, with its exit status.
- **[`midwife.types`](#midwifetypes):** `Observation`, `Record`, `Budget`,
  `Battery`.
- **[`midwife.verdict`](#midwifeverdict):** categories, levels, evidence and
  obligations.
- **[`midwife.stats`](#midwifestats):** how firm each trial and verdict is,
  and how likely a quorum is to reach a level.
- **[`midwife.withhold`](#midwifewithhold):** text that must not leave this
  machine, refused before any call.
- **[`midwife.interventions`](#midwifeinterventions):** trial planning,
  prompts and presentation renaming.
- **[`midwife.recoil`](#midwiferecoil):** something found deep in a chain of
  frames, carried back up to the holes it fills, and asked until firm.
- **`midwife.batteries.*`:** the shipped loopback batteries, two critics,
  `local-json`, `tendora`, and `crossing`, which reads across a boundary.
- **[`midwife.cli`](#midwifecli):** the `gadfly` command, with plan, run,
  report, stats, check-frame and portfolio.
- **[`midwife.portfolio`](#midwifeportfolio):** several frames' verdicts
  counted, never combined.

<!-- api midwife.pipeline -->

---

### midwife.pipeline

The pipeline: situate → plan → run → judge (→ overall, over the inputs).

```python
frame = situate(json.load(file))
trials = plan(frame)
result = run(frame, battery, Budget(calls=60))
findings = judge(frame, result.records)
verdict = overall(findings)
```

`overall` names one category over all the inputs. `run` is the only stage
that calls out. It never starts a call the budget cannot cover, stops
between calls when the caller says so, and hands each record to `on_record`
as soon as it exists, so the caller keeps what was spent even if the run
stops early. Asked to, it skips the calls a settled trial no longer needs,
stops an input once it reads unresolved whatever its other trials give, and
makes several calls at once for a battery that takes them.

#### situate

Another name for `parse` in `midwife.frame`:

Check a frame and hash it. The frame keeps its own copy: changing the
caller's dict afterwards cannot change what the hash names.

```python
situate = midwife.frame.parse
```

#### plan

Another name for `plan` in `midwife.interventions`:

The trials of one input, in a fixed order. A frame whose holes stand
in for its anchors is refused: it is walked, not asked.

```python
plan = midwife.interventions.plan
```

#### overall

Another name for `overall` in `midwife.verdict`:

One category over the frame's inputs: outside scope when declared;
otherwise coupled but misaligned if any input is; unresolved if any is,
or if the relation carried on some inputs and cooled on others; carried
or cooled only when every input is. Each input's evidence is kept; what
every input leaves open is said once, the rest names its input.

```python
overall = midwife.verdict.overall
```

#### RunResult

What a run made: its records, the calls it planned, why it stopped
early (None when it reached the end of its plan), and how many planned
calls it skipped because their trial had settled, their input could read
nothing but unresolved, or the category it was asked for was out of
reach.

```python
@dataclass(frozen=True)
class RunResult
```

#### calls_needed

The calls a whole run makes: every trial of every input, `quorum`
times each. A budget of this many calls covers it.

```python
calls_needed(frame)
```

#### summed_usage

Each whole count the records' calls reported, summed by name, as
`run --json`, `firm --json` and `report --json` give it under `usage`; a
count no call reported is absent, never a zero.

```python
summed_usage(records)
```

#### unthought

The calls whose provider reported no reasoning: of the `calls` that
reported `reasoning_tokens`, how many reported 0 (`unthought`), and
those by trial, as `run --json`, `firm --json` and `report --json` give
it. Read it against the reasoning the frame asked for; nothing is resent
and no answer is set aside, so a reflex answer counts as any other.

```python
unthought(records)
```

#### run

Every planned trial of every input, `quorum` times each, in a fixed
order. `only` limits the run to some trial ids (a partial run); the
verdict then reads what is there. `kept` finishes a run that stopped:
the calls those records made are not made again (drop a record from it
to make its call again), and the verdict reads the two runs together.

```python
run(
    frame,
    battery,
    budget,
    *,
    cancelled=lambda: False,
    on_record=lambda record: None,
    only=None,
    kept=(),
    settle=False,
    stop_unresolved=False,
    parallel=1,
    withhold=None,
    short_of=None,
)
```

`settle` makes no more calls for a trial whose level can no longer
change (`settled`); the verdict reads it as it would read every call.
With `parallel`, a trial has out only the calls that could fix its level.
Under `standing.stable` the baseline and repeat always run whole, as
their split is read across all their calls. `stop_unresolved` asks the
`DECISIVE` trials first and asks an input nothing more once every answer
its other trials could give reads unresolved (`unneeded`); the verdict
reads the category a whole run would, and names the trials not asked.
`short_of`, carried or cooled, is for a caller who needs only to know
whether the frame reads that category: the trials that most often rule
it out are asked first (`RULING`), and once no answer left could make an
input read it (`out_of_reach`), and so the frame, no further call starts.
With `parallel`, the other trials' calls wait until those first trials
have answered, so calls at once spare what one at a time spares.
Such a run is cut short (`short` counts the calls it left): it says the
frame does not read that category, and not which other it reads.
`parallel` makes up to that many calls at once, for a battery that says
it takes them (a `concurrent` attribute that is true); records are
handed on as each call ends, and a call already started is always kept:
a first Ctrl-C starts no more calls, keeps those already out, then goes
on as KeyboardInterrupt, and a second stops at once. `withhold` refuses,
before any call, a frame whose prompts hold text the set withholds
(`midwife.withhold`), its `training` part only when the battery says its
calls may train.

#### judge

One finding per input, read from the records alone: the Records of a
run, or the dicts a caller kept of them. A record the plan and the
frame's battery could not have made is refused.

```python
judge(frame, records)
```
<!-- end api -->

<!-- api midwife.frame -->

---

### midwife.frame

The frame you declare: the situated relation (L) and its assessment frame (Γ).

A frame is plain JSON. It is read whole, checked, and hashed in a canonical
form before any trial runs; the hash travels with every record, so a verdict
always names the frame it was read under. Changing any coordinate, the grain
included, gives another hash: another frame.

#### Span

One piece of the body at the frame's grain.

```python
@dataclass(frozen=True)
class Span
```

#### Frame

A checked frame. It keeps the canonical JSON its hash is taken of, and
every coordinate read from it is a fresh copy: nothing a battery or the
caller does with what it reads can change what the hash names.

```python
@dataclass(frozen=True)
class Frame
```

Frame has these properties:

- **`raw`:** `dict[str, Any]`
- **`name`:** `str`
- **`inputs`:** `tuple[dict[str, str], ...]`
- **`instruction`:** `str`
- **`interventions`:** `dict[str, Any]`
- **`allowed`:** `dict[str, Any]`
- **`battery`:** `dict[str, Any]`
- **`outside_scope`:** `str | None`
- **`holes`:** `tuple[dict[str, str], ...]`
- **`offers`:** `str | None`

#### canonical

The one serialization a hash is taken of.

```python
canonical(value)
```

#### digest

The SHA-256 of a value's canonical serialization.

```python
digest(value)
```

#### schema

The frame's JSON Schema (draft 2020-12), for editors and authoring
checks. It describes the shape; `parse` stays the authority on what only
code can check (anchors in the body, trials that change something).

```python
schema()
```

#### load

Read a frame from a JSON file, then check and hash it as `parse` does.

```python
load(path)
```

#### parse

Check a frame and hash it. The frame keeps its own copy: changing the
caller's dict afterwards cannot change what the hash names.

```python
parse(raw)
```
<!-- end api -->

<!-- api midwife.errors -->

---

### midwife.errors

What Gadfly refuses, as Python names it: a class for what the caller must
fix (PEP 8), its exit status an attribute of the class (PEP 352), a message
that says what went wrong, and notes that say what to do (PEP 678).

```python
UsageError     2  the command or the call: flags, budget, standard input
FrameError     4  the frame
RecordsError   5  records or a report that are not this frame's run
BatteryError   6  the battery: its module, its settings, its service
```

A file the command line cannot read or write is Python's own error
(PEP 3151), exit 7. Each class is a ValueError, as every refusal was.

What a run did not do as asked, though it went on and kept its records, is
a warning (PEP 230), raised with `warnings.warn`, which a caller may make an
error with Python's own filters (`-W error::midwife.errors.OpeningWarning`):

```python
OpeningWarning  1  calls came back with no answer (1 when every one did)
StoppedWarning  3  the run stopped before its plan's end
```

#### GadflyError

A refusal: the message says what went wrong, each note what to do.

```python
class GadflyError(ValueError)
```

#### one_line

Whether a value prints on one line: no line break, nor any other
control character a terminal could act on.

```python
one_line(value)
```

#### is_plain

Whether a value prints as one plain name: no line break, and no colon a
label would end at.

```python
is_plain(value)
```

#### plain

A value as a line prints it: as it is when it is one plain name, else
quoted as Python's repr, so it can neither end a label nor start a line.
A name that ends in a colon is quoted too: printed before a space, its
colon would end a label.

```python
plain(value)
```

#### quoted

Values as a message names them: each quoted, as Python's repr does.

```python
quoted(values)
```

#### noted

Python's own `error`, with notes that say what to do: its constructor
takes none.

```python
noted(error, *notes)
```

#### UsageError

The command or the call asks for what cannot be done: a flag, a
budget, standard input.

```python
class UsageError(GadflyError)
```

#### FrameError

A frame that cannot be assessed as declared.

```python
class FrameError(GadflyError)
```

#### RecordsError

Records or a report that are not what this frame's run made.

```python
class RecordsError(GadflyError)
```

#### BatteryError

A battery that cannot be made, cannot serve this frame as set up, or
cannot reach what it needs.

```python
class BatteryError(GadflyError)
```

#### StopRun

Raised by a battery or a maker when its harness, not the frame, has
failed, so no further call can be read: a refused key, a broken tool.
The run makes no record of that call and starts no other; calls already
out end and are kept, and it ends as a stopped run that quotes `reason`,
as a spent budget ends one, so `--kept` finishes it once the harness is
fixed. Never a label, and never an opening.

```python
class StopRun(Exception)
```

#### GadflyWarning

What a run did not do as asked, though it went on and kept its
records.

```python
class GadflyWarning(UserWarning)
```

#### OpeningWarning

Calls came back with no answer, as openings; exit 1 when every call did,
as then nothing was read.

```python
class OpeningWarning(GadflyWarning)
```

#### StoppedWarning

The run stopped before its plan's end, so its records are partial.

```python
class StoppedWarning(GadflyWarning)
```
<!-- end api -->

<!-- api midwife.types -->

---

### midwife.types

The types a pipeline passes from stage to stage, and the one a battery
implements. Gadfly keeps no state: every value here is returned to the caller,
who keeps it (a file, a database, a test fixture) as they see fit.

#### Observation

What a battery saw: one of the frame's labels, or a typed opening when
there is no outcome to read (a refusal, an unreadable answer, a failure).
`served` names the scorer that answered, as the service reports it (a
model, its revision, the endpoint), so a record says who read.

```python
@dataclass(frozen=True)
class Observation
```

#### Record

One scorer call: which frame, input, trial and run, what was read and
what it cost. A verdict is recomputed from records alone.

```python
@dataclass(frozen=True)
class Record
```

##### Record.as_dict

The record as a plain dict, as a caller keeps it (JSON Lines, say).

```python
as_dict()
```

#### Battery

A scorer: given the frame and the exact text it must read, one
observation. It never sees which trial it is serving. A battery that
can serve several calls at once says so with a class attribute
`concurrent = True`; without it, `run` makes one call at a time.

```python
@runtime_checkable
class Battery(Protocol)
```

##### Battery.check

Refuse a frame this battery must not serve (raise ValueError).

```python
check(frame)
```

##### Battery.observe

Read the prompt once and return what it observed, spending at most
`max_output_tokens` (the budget's cap per call) on the answer.

```python
observe(frame, prompt, max_output_tokens)
```

#### Budget

The most a run may spend: `calls` scorer calls, each answer capped at
`output_tokens_per_call`, and, if `tokens` is set, that many output tokens
in all. Because every call is capped, a call is never started that could
pass the budget; a battery that reports more than the cap has broken that
promise, and the run stops after its call.

```python
@dataclass(frozen=True)
class Budget
```
<!-- end api -->

<!-- api midwife.verdict -->

---

### midwife.verdict

The verdict, read from the trial records by fixed rules and nothing else.

For each input, each trial's observations are reduced to one level when the
frame's quorum agrees, or to none. The rules, in this order (the order of the
reference implementation, After the Poem's `finding` with `rules: 2`, in
scripts/load_bearing.py, https://github.com/mirzahusadzic/after-the-poem):

1. unresolved: a planned trial has no agreed level; with `standing.stable`,
   the baseline and repeat sessions do not all agree (a split level cannot show
   a one-level change); or repeat differs from baseline;
2. coupled but misaligned: presentation moves it, or placement does (the
   structure, not the wording, drove it);
3. coupled but misaligned: ablation moves it to an observation the frame does
   not allow (for ordered labels, the wrong way);
4. cooled: ablation leaves it as it was, unless a control trial (spans whose
   removal must move any scorer that reads) left it too: then unresolved, as
   the scorer cannot tell;
5. unresolved: a sham moves it (the change is not specific to the relation);
6. carried: otherwise.

Outside scope only when the frame declares the exclusion; never inferred.

With `eachAnchor`, each anchor is also cut alone. Those trials are evidence
only and never change a category: after the ablation moved it, they say
whether each anchor carries it, either suffices, or one adds nothing alone;
where the ablation left it, they name any anchor that moved it alone.

What the trials do not settle is recorded as an open obligation beside the
category:

- carried: no hidden fallback (a bypass trial), presentation invariance and
  specificity when their trials were not run, and materialization (whether
  the observation is the form the recipient receives, which the frame must
  say);
- cooled: discrimination, unless a control moved it;
- outside scope: the independent scope check, which only the receiving
  owner can make.

Traceability rests on the records: each names its frame, battery, body,
prompt and what served it.

#### Finding

One input's verdict: its category, each trial's agreed level (None
where the quorum did not agree), the evidence for the category, and the
obligations it leaves open.

```python
@dataclass
class Finding
```

##### Finding.as_dict

The finding as a plain dict.

```python
as_dict()
```

#### Overall

The frame's one category over its test domain: every input's.

```python
@dataclass
class Overall
```

##### Overall.as_dict

The verdict as a plain dict.

```python
as_dict()
```

#### overall

One category over the frame's inputs: outside scope when declared;
otherwise coupled but misaligned if any input is; unresolved if any is,
or if the relation carried on some inputs and cooled on others; carried
or cooled only when every input is. Each input's evidence is kept; what
every input leaves open is said once, the rest names its input.

```python
overall(findings)
```

#### level

The observation at least `agree` runs gave, if exactly one did.

```python
level(observations, agree)
```

#### settled

Whether a trial's level can no longer change: whatever its remaining
calls answer, `level` gives what it gives now. One label at `agree` that
no other can still reach settles it; so does no label able to reach it.

```python
settled(observations, quorum, agree, labels)
```

#### judge

One finding per input, from the records of one run of one frame.
Every planned trial is read; one without records has no level, and one
with fewer than `quorum` has a level only once it is settled, so a
stopped run never reads a level its missing calls could change.

```python
judge(frame, records)
```

#### unneeded

The trials input `x` need not be asked, given the answers so far: once
every answer the rest could give reads unresolved, all those not asked to
the end, but each anchor alone while a reading still gets as far as the
ablation, where its evidence is read. Empty while an answer could read
otherwise, or the answers are too many to read.

```python
unneeded(frame, x, samples)
```

#### out_of_reach

Whether input `x` can no longer read `category`, given the answers so
far: none of the answers its trials not asked to the end could give reads
it. False while one could, or the answers are too many to read.

```python
out_of_reach(frame, x, samples, category)
```

#### unreachable

What no answers can make this frame read, found before a call: carried
or cooled, each with the checks open in every reading that would name it
but for them (empty when none comes that near), or the exclusion when the
frame is declared outside scope. The rules themselves read every answer
each trial could give; None when the readings would be more than OUTCOMES
for an input.

```python
unreachable(frame)
```

#### check_records

Records are read only as the plan and the frame's battery made them:
this frame, its battery, its inputs and trials, each trial's own body,
runs within the quorum, each run once, and each a label of the frame or
an opening. A record copied twice can never make a quorum. `run` reads the
records it is given to keep by the same checks.

```python
check_records(frame, records, bodies=None)
```

#### allowed_for

What a trial may produce (ablation; bypass, its designated opening; an
inversion or input inversion, what it must reach): the labels listed, or,
for ordered labels, those below (or above) the baseline.

```python
allowed_for(frame, base, trial="ablation")
```
<!-- end api -->

<!-- api midwife.stats -->

---

### midwife.stats

Statistics beside the verdict: how firm each trial's answers are, how
likely a quorum is to reach a level at all, whether a trial moved the answer
or held it, and how often a run's verdict comes out the same when its calls
are drawn again.

Nothing here changes a verdict. The fixed rules in `midwife.verdict` read
every category from the records; this module only says how much the calls
behind a category support it, so a run of five calls is not read as if it
were five hundred. Every number is computed from kept records, and the draws
are seeded by the frame's hash, so the same records always give the same
report.

#### wilson

The Wilson score interval for `hits` of `n`: where the true share most
likely lies (95% by default). Unlike hits/n it stays honest at small n:
4 of 5 is anywhere from 38% to 96%.

```python
wilson(hits, n, z=Z)
```

#### at_least

The chance that at least `k` of `n` calls give the reader's usual
answer, when each gives it with chance `p`: a probability, kept within
0 and 1 however the sum's rounding falls.

```python
at_least(k, n, p)
```

#### fisher

Fisher's exact test, two-sided, for the table [[a, b], [c, d]]: the
chance of a split at least this uneven if the two rows read alike.

```python
fisher(a, b, c, d)
```

#### holm

Holm's adjustment: each p-value as it stands among the others, so that
of many trials tested at once, chance alone passes 5% only 5% of the
time.

```python
holm(pvalues)
```

#### Power

How likely a quorum is to reach a level, before a call is made.

```python
@dataclass(frozen=True)
class Power
```

##### Power.as_dict

The fields as a plain dict, as `--json` prints them.

```python
as_dict()
```

#### power

The chance that a trial, and every trial the plan asks of an input,
reaches a level, for a reader that gives its usual answer with chance
`agreement`. A trial with no level leaves its input unresolved, so this
is the most a run can resolve, whatever the evidence. The count is
every planned trial but the one-anchor ones, which are evidence only;
an input that no input inversion turns needs that trial's level no
more, so for it the figure is a floor.

```python
power(frame, agreement)
```

#### agreement

The share of calls that gave their trial's most common answer in their
own run: how steadily the reader answers when nothing changes between
its calls. An opening never agrees, and a call its trial asked alone in
its run has nothing to agree with, so it is not counted. None when no
trial was asked twice in a run: there is no repeat to measure.

```python
agreement(runs)
```

#### pooled

Calls made under other frames that are this frame's calls in all but
name: the same battery line, instruction and labels, and the same prompt.
Each comes back as a call of this frame's trial with that prompt (its
own input and trial when they have it), for counting, never for a
verdict, since its frame's plan is not this one's. A call whose prompt
is two of this frame's inputs' at once, and whose own input is neither,
could be either's, and is left out.

```python
pooled(frame, others)
```

#### TrialStats

One trial's calls for one input, pooled over runs, against the
baseline's most common answer.

```python
@dataclass(frozen=True)
class TrialStats
```

##### TrialStats.as_dict

The fields as a plain dict, as `--json` prints them.

```python
as_dict()
```

#### compare

Each input's trials over all the runs given, and `extra` calls pooled
in (see `pooled`): how many gave each answer, how firm the most common
is, whether the trial moved the baseline's answer (Fisher's exact test,
Holm-adjusted across the input's trials), and, for a repeat,
presentation, placement or sham, at most how many of its answers could
differ from the baseline's (the upper end of a 95% interval): "held" with
15 calls means less than with 150.

```python
compare(frame, runs, extra=())
```

#### stability

For each run, how often each input's verdict comes out each way when
every trial's calls are drawn again, with replacement, as many as it had:
the fixed rules read every draw, so no model judges anything. A verdict
that comes out the same in 95% of draws is firm; one at 55% rests on a
call or two. The draws are seeded by the frame's hash and the run's
place, and made in the plan's order, so the same records always give
the same shares, in whatever order they were kept. An input whose
trials were each asked once in a run has nothing to draw again, and gets
no shares for that run. `start` is the place of the first run given, when
they are the later runs of a frame's: each is drawn as at its own place.

```python
stability(frame, runs, resamples=RESAMPLES, *, start=0)
```

#### observed

Each run's verdict for each input, as the fixed rules read it.

```python
observed(frame, runs)
```

#### require_runs

Refuse a report with no calls to count.

```python
require_runs(runs)
```
<!-- end api -->

<!-- api midwife.recoil -->

---

### midwife.recoil

Recoil: something found deep in a chain of frames, carried back up.

A frame knows where its text came from, by each span's `source`, and nothing
above that. A piece is a text found in a kept run, with a kind. It climbs from
the frame it was found in to each frame whose own text that frame quotes, and
on up, and fits any of those frames' holes of its kind; a frame with no such
hole passes it on, at no cost. A hole may defer: its fit is listed, kept
and not asked. Given a crossing's records, each artefact it made is text
that frame made, so a frame quoting the artefact climbs to the crossing.
Sideways, the piece is also offered one step aside, to the frames quoting
a text the frame it was found in quotes, and climbs on from each.
The walk reads frames and makes no call; given vectors, it orders the fits
by cosine, and given a budget, it counts each fit's calls before the first
and lists those it cannot cover.

A fit is asked again as a successor: the frame with the piece as a span and
its anchor. `successor` drafts it for the frame's author and writes nothing.
The successor's category is the gate: carried or coupled but misaligned, the
frame's own decision climbs on, as a piece of the kind the frame `offers`;
cooled or outside scope, the recoil is absorbed; unresolved, it stops with
the open check named. A successor that changes anything but its evidence, or
any hole but closing the one it fills, asks another question, and is a
reframing opening, read against no category.

A successor is asked lightly, and again only while it must be (`until_firm`):
one run at a time, until the fixed rules read every input's category the same
in nearly every draw of the latest run's calls, and the same as the run before
it; then it disengages. Runs already kept count as runs made, so a frame
already firm is asked nothing.

Each step is also a command: `gadfly walk`, `gadfly successor`, `gadfly firm`
and `gadfly gate`.

#### sha256

The SHA-256 of a text, as a span's `source` names it.

```python
sha256(text)
```

#### Piece

A text found in a kept run, and the kind of hole it fills.

```python
@dataclass(frozen=True)
class Piece
```

Piece has these properties:

- **`sha256`:** `str`

#### found

A span of a frame as a piece of its kind.

```python
found(frame, span)
```

#### decided

A frame's decision as the piece it climbs as: its name and the label
it reads, of the kind the frame offers.

```python
decided(frame, label)
```

#### Vectors

Whole-text vectors a caller acquired: each a tuple of floats, keyed by
the SHA-256 of the exact text it stands for and the opaque id of the
space it was made in; and the SHA-256 of what they were read from.

```python
@dataclass(frozen=True)
class Vectors
```

Vectors has these properties:

- **`spaces`:** `tuple[str, ...]`. Each space a vector names, in sorted order.

#### read_vectors

Vectors from JSON Lines, one line each,
`{"text": SHA256, "space": ID, "values": [...]}`, as a caller acquired
them: whole texts only, one vector a text in each space. Spaces may mix,
and a walk compares two vectors only within one. A text named twice in
one space refuses them all, even with the same values, and a value that
is not finite is kept, to give no order where it is read. A refusal
names the file at `path` they were read from, `-` standard input.

```python
read_vectors(data, *, path=None)
```

#### Fit

A hole a piece fits, as a walk would ask it: the frame and the hole;
when the walk was given vectors, its cosine to the piece, or why it has
none, kept in its place; when it was given a budget, the most calls
asking its successor until firm can make, and whether the budget covers
them; when the walk reached the frame through an artefact it made, the
trial and input of each record that made it; and whether it reached the
frame sideways, as a sibling of the frame the piece was found in.

```python
@dataclass(frozen=True)
class Fit
```

#### Walk

Where a piece fits above the frame it was found in: each frame it
fits, with the holes it fits there that are considered; each frame it
passed; the frontier, each quoted text no frame given holds as its own;
each frame with the holes it fits there that defer, kept and not asked;
every considered fit, one hole each, in the order it would be asked;
the space its fits were ordered by and the SHA-256 of the vectors, when
it was given them; the budget in calls and the most runs a fit, when one
was given; for each frame it reached through an artefact the frame
made, by its hash, the trial and input of each record that made it; and
each frame it reached sideways, a sibling of the frame it started from.

```python
@dataclass(frozen=True)
class Walk
```

Walk has these properties:

- **`complete`:** `bool`. Every frame above was given: a walk with a frontier is never complete.
- **`unasked`:** `tuple[Fit, ...]`. Each fit the budget does not cover, in the order it would be asked.

##### Walk.lines

The walk as its record, one line each: every hole it fits, in the
order it would be asked, with its cosine or why it has none when it
was ordered, and its calls and whether the budget asks it when there
is one; then every frame whose holes of its kind defer, then every
frame that passed it on, each in the order the walk reached it; then
every text it could not follow. Each line names the space and the
vectors it was ordered by, and the budget, when there were any, and
each frame line the records that made the artefact it was reached
through, and whether it was reached sideways.

```python
lines()
```

#### walk

Climb from the frame a piece was found in to each frame whose own text
it quotes, and on up, visiting each frame once by its hash. A frame with
holes of the piece's kind is a fit, and the piece climbs on past it,
since it may fit at more than one height; any other frame passes it on.
A hole whose salience is defer is listed under `deferred`, its fit kept
and not asked, never dropped.

```python
walk(
    piece,
    start,
    frames,
    *,
    made=(),
    sideways=False,
    vectors=None,
    space=None,
    calls=None,
    most=MOST,
)
```

`made` holds runs of crossing frames given, each a list of its records,
each checked against its frame first; a run cut short still links what
its records made. Each artefact a record says its maker made is text
that frame made, so a frame quoting the artefact by `source` climbs to
the crossing, and the walk names the trial and input of each record
that made it.

`sideways` offers the piece one step aside too, from the start frame
only: to each frame given that quotes, by `source`, a text the start
frame quotes. Siblings come from that fixed rule, never from nearness,
so none is dropped; each then climbs as usual, and is not followed
sideways again.

Each considered hole is a fit in `order`, in the order the walk reached
its frame and the frame lists its holes. Given `vectors`, the fits are
ordered by the cosine of the piece's vector to the vector of what each
hole is read for, its `about`, both in one `space`, highest first, and
ties by frame hash. A fit with no cosine keeps its place, with why, and
the others are sorted among theirs, so no fit takes a default score and
a vector only orders.

Given `calls`, each fit is counted before the first call, as
`calls_until_firm` counts its successor as drafted over at most `most`
runs, and the budget asks the fits in order up to the first it cannot
cover: that one and every one after it are listed as not asked, so no
fit is asked before an earlier one. No call is made: the walk reads
frames, and is given no battery.

#### successor

A draft of the successor a fit is asked as, for the frame's author to
finish and keep: the piece a span with the hole's id, quoting the text it
was found as by its SHA-256, and the frame's one anchor; the hole closed.
The piece's span comes last, or right after the span `after` names, as
the line it amends; either way its ablation is the frame's body, byte
for byte. `changes` sets any other key, such as the trials that read the
anchor. Nothing is written, and the draft is not checked: parse it.

```python
successor(frame, hole, piece, *, after=None, **changes)
```

#### reframes

The keys a successor changed beyond its evidence, in sorted order:
none when it only filled a declared hole, and asked it with its own
trials and standing. Its holes are the frame's, in any order, less at
most the one it filled, now a span of the hole's kind: a hole added,
changed, dropped unfilled or closed by a span of another kind changes
what the frame can take in, and lists `holes`.

```python
reframes(before, after)
```

#### Firm

What asking a frame until its verdict was firm made: every run, kept
ones first, and the last cut short when it stopped short; the findings
of the latest whole run; how often the draws of its calls read each
input's category; whether that was firm; the calls made now; and why it
stopped short, if it did. `short` names the category asking was to stop
short of (`until_firm`'s `short_of`) once no firm reading of it was left
to reach: the verdict is then not firm, and says only that the frame does
not read that category firmly; `any` once no firm reading of any category
was left. `usage` sums each whole count the calls made
now reported, such as `input_tokens` and `output_tokens`, by name; a
count no call reported is absent, never a zero. `unthought` counts the
calls made now that reported no reasoning (`midwife.pipeline.unthought`).

```python
@dataclass(frozen=True)
class Firm
```

Firm has these properties:

- **`category`:** `str | None`. The frame's one category over its inputs, in the latest run.

#### until_firm

Ask a frame one whole run at a time, and disengage once its verdict
is firm: every input's category read alike in at least `firm` of the
draws of the latest run's calls (`midwife.stats.stability`), and the
same as the run before it, if there was one. Each kept run, a list of
one run's records, counts as a run made, in the order given, and only
the latest decides, so a frame whose last kept run is firm is asked
nothing. It reads at most `most` runs in all, kept ones included (the
frame's `standing.most` when it declares one, `most_of`), and
starts none the budget cannot cover whole, in calls and, when it caps
them, in tokens at each call's cap: a run cut short is never firm, and
a stop for the budget is a `StoppedWarning`, as a run's is. With no
battery, it reads the kept runs alone and asks nothing. `parallel`
makes up to that many calls at once within each run, as `run`'s does;
the runs stay one after another, since each decides whether the next
is asked. `withhold` refuses the frame before any call, as `run`'s does.

```python
until_firm(
    frame,
    battery,
    budget,
    *,
    kept=(),
    firm=FIRM,
    most=None,
    on_record=lambda record: None,
    parallel=1,
    withhold=None,
    short_of=None,
)
```

`short_of`, carried or cooled, is for a caller who needs only to know
whether the verdict is firm and that category. Asking then ends as soon
as it cannot be: a run that does not read the category leaves a firm
reading of it two runs away, so when `most` allows fewer, no further run
is asked, and such a run is itself cut short once no answer left could
make it read the category (`run`'s `short_of`). The result is not firm
and names the category in `short`; a firm verdict of another category,
which whole runs might have reached, is not looked for. `any` is for a
caller who needs to know whether the verdict is firm, whatever its
category: the last run `most` allows, when a run came before it, can be
firm only by reading each input as that run did, so it is cut short once
no answer left could make some input read so, and `short` is `any`. A
run before the last is always asked whole, as the run after it is read
against it.

#### calls_until_firm

The most calls `until_firm` can make on a frame, counted before its
first: a whole run's for each run `most` allows beyond the runs `kept`
holds. It is refused as `until_firm` refuses the frame or its kept
runs, and is a ceiling: asking stops sooner once a run is firm, and
makes no call when the latest kept run is.

```python
calls_until_firm(frame, *, kept=(), most=None)
```

#### declared_most

The most runs the frame itself says asking it until firm reads
(`standing.most`), or None when it leaves that to its caller.

```python
declared_most(frame)
```

#### most_of

The most runs asking a frame until firm reads: the frame's own
`standing.most`, else `most`, else `MOST`. A frame that declares it is
read so, and a different `most` is refused rather than taken.

```python
most_of(frame, most=None)
```

#### Recoil

What a fit did: the gate (climbs, absorbed, stops, or reframing), the
successor's category, what climbs on from it, what it changed when it
reframes, and the open check when it stops.

```python
@dataclass(frozen=True)
class Recoil
```

#### gate

The gate a fit sets. A successor that changed more than its evidence
is a reframing, read against no category and asked nothing. Any other is
read from its own runs (`until_firm`): one whose verdict never came out
firm stops, with why named; a firm one sets the gate by its category,
and a firm unresolved one stops with its open check named,
and when it climbs, its decision climbs on as one piece for each label
its inputs' baselines read, if the frame offers a kind.

```python
gate(before, after, asked=None)
```
<!-- end api -->

<!-- api midwife.withhold -->

---

### midwife.withhold

Text that must not leave this machine, checked before any call.

A withhold set is read from a file, `{"always": {...}, "training": {...}}`.
What `always` holds no call may carry, such as a credential; what `training`
holds may go to a reader that keeps no data, never to one that may train on
what it reads, such as a private name or a line read from elsewhere. Each part
may list `names`, matched as whole words in any case; `lines`, each the
SHA-256 of a line in its normal form, its words joined by single spaces; and
`patterns`, Python regular expressions. A line that opens with a diff marker,
`+` or `-`, is also read without it, so a line copied into a diff still
matches its source.

`withheld` reads all a run sends: what every call carries beside its prompt
(the frame's instruction, its labels, and the battery line, which holds an
output schema and a maker's instruction), then every prompt the frame's plan
makes. It names each place that holds withheld text; `refuse_withheld` refuses
the frame at the first, naming where and what kind, never the text. Whether the
`training` part applies is the battery's to say (`trains`); one that does not
say is read as one that may train. In a crossing, what the maker writes is not
checked before the reader reads it.

#### Part

One part of a withhold set: whole-word names, line hashes, patterns.

```python
@dataclass(frozen=True)
class Part
```

##### Part.kinds

The kinds of withheld text `text` holds: a name, a line, a pattern.

```python
kinds(text)
```

#### Withhold

What no call may carry (`always`), and what no call that may train may
carry (`training`).

```python
@dataclass(frozen=True)
class Withhold
```

#### Held

A place a run would send withheld text: the trial and input whose
prompt holds it, its kind, and the part of the set that withholds it. A
trial or input whose id the set itself withholds is named by its place
instead, `trial 3` or `input 2`, counted from 1 in the plan's and the
frame's order, so a refusal never says the text. Text every call carries
beside its prompt has no trial: its `input` says where it is, `the
instruction`, `the labels` or `the battery line`.

```python
@dataclass(frozen=True)
class Held
```

##### Held.as_dict

The place as JSON: its trial, input, kind and part.

```python
as_dict()
```

#### normal

A line's normal form, as its hash is taken: its words joined by single spaces.

```python
normal(line)
```

#### line_sha256

The SHA-256 a withhold set lists a line by: of its normal form, as UTF-8.

```python
line_sha256(line)
```

#### read_withhold

A withhold set from its JSON. A refusal names the file at `path` it
was read from, `-` standard input.

```python
read_withhold(data, *, path=None)
```

#### trains

Whether a battery says its calls for this frame may reach a reader
that trains on them; one that does not say may.

```python
trains(battery, frame)
```

#### withheld

Each place a run would send withheld text, of what kind, and under
which part: `always` for every frame, `training` too when the frame's
calls may train. Read before any call, over what every call carries
beside its prompt, then over every prompt the plan makes.

```python
withheld(frame, withhold, *, training=True)
```

#### refuse_withheld

Refuse a frame whose run would send withheld text, at its first
place, naming where and of what kind, never the text itself.

```python
refuse_withheld(frame, withhold, *, training=True)
```
<!-- end api -->

<!-- api midwife.interventions -->

---

### midwife.interventions

The admissible interventions Δ: each changes or removes the relation and
keeps everything else as it was.

Every trial body is derived from the frame alone, so the plan is fixed, and
recorded, before a single observation is made; the sham's draw is seeded by
the frame's hash, never by the clock.

#### Trial

One intervention, applied: the body the scorer will read.

```python
@dataclass(frozen=True)
class Trial
```

Trial has these properties:

- **`text`:** `str`
- **`body_hash`:** `str`

#### place

The spans with one moved to follow another; every text unchanged.

```python
place(spans, span_id, after)
```

#### without

The spans, in their order, less those named.

```python
without(spans, removed)
```

#### rename

Rename each word consistently, whole words only, in one pass: a word is
renamed once (a swap stays a swap), and a phrase wins over a word inside
it. A capital is kept, and so is a word written in capitals. A word may
begin or end in a sign, such as 20% or C++; it is never part of a longer
word, nor of a longer run of its edge's sign (C++ is not in C+++).

```python
rename(text, mapping)
```

#### renamer

`rename` with its map built once: the table and the pattern are made
here, and the function returned applies them to any text.

```python
renamer(mapping)
```

#### sham_draws

Spans to remove instead of the anchors: as many as the anchors, of the
same kinds (or the kind the sham's `kind` names for an anchor), none
cited, none bypassed, none a declared fallback, and no span in two
draws. A fallback is declared to carry the relation, so cutting it is no
sham. Each is the closest in length still free; spans equally close are
drawn among by the frame's own seed. A draw that cannot be matched is
left out; the verdict says so.

```python
sham_draws(frame, count)
```

#### trial_ids

The ids `plan` gives its trials, in its order, without building any
trial's body: what a budget is counted from.

```python
trial_ids(frame)
```

#### plan

The trials of one input, in a fixed order. A frame whose holes stand
in for its anchors is refused: it is walked, not asked.

```python
plan(frame)
```

#### prompt

What the scorer reads: the trial's body and one input, nothing else.
Presentation renames the input's words too, so only the wording moves;
an inversion changes the relation's sense in the body alone, and an input
inversion what is asked alone.

```python
prompt(frame, trial, x)
```
<!-- end api -->

<!-- api midwife.batteries.critic -->

---

### midwife.batteries.critic

What every critic battery shares: one safe way to call a loopback server,
and one way to read a label from a JSON answer (the frame's observation map).

#### loopback

The URL, if it names this machine over plain http on a valid port;
else ValueError, which never repeats a user or password the URL holds.

```python
loopback(url, what)
```

#### opener

No proxy from the environment, no redirect: only the address named is
called. Built per call, so no environment read at import can linger.

```python
opener(*handlers)
```

#### opened

The response to a request, opened through `opener()`, its status line
and headers in within `timeout` seconds of the call: a server still
sending the answer's head then is cut off, and the call raises
TimeoutError. The body is `read_reply`'s to bound, and a refusal's
`read_error`'s, both by the same deadline.

```python
opened(request, timeout)
```

#### Late

A reply still coming at its deadline, with the bytes that had arrived:
kept beside the opening, never read as an answer.

```python
class Late(TimeoutError)
```

Late has these properties:

- **`text`:** `str`. What had arrived, as text, for the record's raw.

#### wait_at_most

Let the next read on the response's socket wait at most `seconds`.

```python
wait_at_most(response, seconds)
```

#### read_reply

A reply as it comes, until it ends or passes the size cap; Late, with
what had arrived, if it is still coming at the deadline. Each read waits
only what is left of the deadline, so a stall never runs past it.

```python
read_reply(response, deadline, clock)
```

#### read_error

Up to 4,096 bytes of a refusal's body, read by the deadline: what had
arrived by then, or nothing. Each read waits only what is left.

```python
read_error(error, deadline, clock)
```

#### check_output

Refuse a battery.output that is not {schema, label}, the label a JSON
pointer into the answer.

```python
check_output(battery)
```

#### output_schema

The schema the critic answers to and the JSON pointer to its label.

```python
output_schema(frame)
```

#### pointed

The value at a JSON pointer (RFC 6901), or KeyError.

```python
pointed(document, pointer)
```

#### read_label

The label the answer gives at the frame's pointer, or an opening.

```python
read_label(text, frame)
```

#### label_at

The label at the frame's pointer in an answer already read as JSON.

```python
label_at(answer, frame)
```
<!-- end api -->

<!-- api midwife.batteries.unified -->

---

### midwife.batteries.unified

The unified battery: an LLM critic through the unified model router.

The [unified model router](https://github.com/mirzahusadzic/unified-model-router)
serves the Responses API on loopback and maps a model slug to the provider
that serves it, with the router's own key: this battery sees only the router.
Which models train is the router's declaration, never this battery's: every
call goes under the router's deny data policy unless the frame names its exact
slug under `trainsOnInputs`.

One battery covers them all; calling a provider's own endpoint is a
different battery (a native one). An unprefixed slug is OpenAI's, which the
router reaches only with the caller's Codex sign-in: this battery refuses
it.

The critic answers in JSON to a schema, by default `{"label": &lt;one of the
frame's labels>}`. A critic of your own (its output schema, as your project
already has it) is adapted by saying where in its answer the label is:

```json
"battery": {"kind": "unified", "model": "anthropic/claude-sonnet-5-5",
            "reasoning": "low", "fallback": "none",
            "output": {"schema": {...}, "label": "/verdict"}}
```

What this battery promises, whatever the frame says:
- it talks only to a router on this machine (loopback);
- it sends no tools: the router's web search runs on another provider, and a
  body would leave the model's own provider with it;
- it sends every call under the router's deny data policy
  (`X-Codex-Router-Data-Policy: deny`) unless the frame names that exact model
  under `battery.trainsOnInputs`, so the router refuses a model it declares
  training-tier, before anything is sent upstream, and that call is an
  opening, and reaches only endpoints that keep no data; before the first call it checks that the
  router lists the policy at `GET /health`, and refuses to run if not;
- it uses no proxy and follows no redirect, so the body and the token go to
  the loopback address named and nowhere else;
- each call has a deadline (`timeout` seconds for the whole answer), the
  budget's cap on output tokens, and a cap on what it reads back;
- each record names what served it: the model the response names, and the
  provider the router reports (`X-Codex-Router-Report: provider`, asked when
  the router lists it), or, for one pinned endpoint, that endpoint's tag;
  never a provider the router calls unknown; then the route the router
  names, the upstream the call went to (`anthropic`, `openrouter`, `openai`);
- `fallback: "none"` keeps an `anthropic/` model's calls on Anthropic's API,
  never moved to another provider (`X-Codex-Router-Fallback: none`): a
  refusal there is an opening that says why;
- `thinkingBudget` gives an `anthropic/` model that still takes one a fixed
  budget of thinking tokens on every call, in place of adaptive thinking and
  of `reasoning`, through `X-Codex-Router-Thinking-Budget`, which also keeps
  the call on Anthropic's API; it must be below each answer's cap, and a
  model that takes no budget answers each call with an opening;
- the router must list each of these at `GET /health` for a frame that names it;
- `endpoints` pins the endpoints the router may use, in order and without
  fallbacks, through the router's `X-Codex-Router-Endpoints`, so one endpoint
  reads a quorum; the router must list endpoint pins at `GET /health`;
- the router's token comes from the environment or the router's own env file
  and is never logged, returned or recorded.

#### consented

Whether the frame lets this model go where inputs train: its slug,
exactly, in the list under trainsOnInputs (a string is no list).

```python
consented(battery)
```

#### policy

The router's headers each call of this frame sends: the deny data
policy, unless the frame names its model under trainsOnInputs.

```python
policy(frame)
```

#### pinned

The router's header that pins this frame's endpoints, in order and
without fallbacks; none when the frame names none.

```python
pinned(frame)
```

#### routing

The router's headers that keep this frame's calls on Anthropic's API
(`fallback`) and give its model a fixed thinking budget
(`thinkingBudget`); none when the frame names neither.

```python
routing(frame)
```

#### over_cap

Why a battery line's thinking budget does not fit under a call's cap
on output tokens, which holds the thinking and the answer both; None
when it fits or the line names no budget.

```python
over_cap(battery, cap)
```

#### capabilities

What the router lists under `capabilities` at its health address,
which takes no token; empty when it lists nothing. The whole answer, its
body too, is read within `timeout` seconds.

```python
capabilities(url, timeout)
```

#### payload

The request body. No `tools` key, ever; the data policy and the
endpoints go in the router's headers (`policy`, `pinned`).

```python
payload(frame, text, max_output_tokens)
```

#### request_body

A request for one answer to `schema`, under `instructions`, from the
battery line's model: what `payload` sends for a frame, and what a maker
sends for an artefact. No `tools` key, ever.

```python
request_body(
    battery,
    instructions,
    text,
    schema,
    max_output_tokens,
)
```

#### parse_stream

The answer's text, its usage, an opening if the call did not complete,
and what served it, from the router's server-sent events: the model the
response names, then the provider the router reports, or the endpoint it
names, or `pin`, the one endpoint the call was pinned to, joined by
" via "; then the route the router names, as "(route anthropic)".
A stream still coming at `deadline` (on `clock`) is cut there, and a
connection that times out or fails mid-stream keeps what arrived.

```python
parse_stream(
    lines,
    deadline=None,
    clock=time.monotonic,
    pin=None,
)
```

#### Unified

`battery: {"kind": "unified", "model": "anthropic/claude-sonnet-5-5"}`

```python
class Unified
```

##### Unified.trains

Whether this frame's calls may reach a reader that trains on them:
only when the frame names its model under trainsOnInputs, since every
other call goes under the router's deny data policy.

```python
trains(frame)
```

##### Unified.check

Refuse, before any call, a frame this battery must not serve: another
battery's, an unknown key, an OpenAI slug, tools, or no router
token. Which models train is the router's to say: without the
frame's consent each call goes under the deny data policy, and the
router refuses a training-tier model then.

```python
check(frame)
```

##### Unified.check_cap

Refuse, before any call, a cap on each answer that leaves the
frame's thinking budget no room: the cap holds the thinking and the
answer both, and Anthropic takes a budget only below it.

```python
check_cap(frame, cap)
```

##### Unified.observe

One call through the router: the prompt under the frame's
instruction, answered to its schema; the label at the frame's
pointer, or an opening that says why there is none.

```python
observe(frame, prompt, max_output_tokens)
```
<!-- end api -->

<!-- api midwife.batteries.egemma -->

---

### midwife.batteries.egemma

The eGemma battery: Gemma 4 on this machine, through eGemma's /judge.

[eGemma](https://github.com/mirzahusadzic/egemma) reads the prompt under the frame's
instruction, with no persona added, and a grammar holds its answer to the
schema: by default `{"label": <one of the frame's labels>}`, or a critic's own
schema with the label's place named, as for the unified battery. Nothing
leaves this machine, and nothing is cached, so the quorum's runs are fresh
samples; at `temperature: 0` the battery is close to deterministic. With
`reasoning: true`, Gemma thinks before every answer, and only the answer is
held to the schema.

```json
"battery": {"kind": "egemma", "temperature": 0.7}
```

What this battery promises, whatever the frame says:
- it talks only to an eGemma on this machine (loopback), through no proxy
  and no redirect;
- each call has a deadline (`timeout` seconds for the whole reply), the
  budget's cap on output tokens, and a cap on what it reads back; with
  reasoning, the cap is the thought's and the answer's together: the answer
  keeps ANSWER_TOKENS of it and the thought gets the rest, up to
  MAX_THOUGHT_TOKENS, and a cap with no room left for a thought is an
  opening;
- it calls one at a time and paces itself to the judge budget eGemma
  publishes at GET /rate-limits (read once, before the first call); when
  eGemma is busy anyway (429 or 503) it waits as long as eGemma asks, at most
  a minute, and tries at most three more times before the call becomes an
  opening;
- each record names the model and revision eGemma reports; a frame that
  pins them (`model`, `revision`) gets an opening from any other;
- the key comes from the file named by EGEMMA_API_KEY_FILE, else from
  EGEMMA_API_KEY or WORKBENCH_API_KEY, and is never logged or recorded.

#### payload

The /judge request: the instruction, the text, the schema, the answer's
cap, and the frame's temperature if it names one. With reasoning, the call's
cap is split: the answer keeps ANSWER_TOKENS and the thought the rest.

```python
payload(frame, text, max_output_tokens)
```

#### EGemma

`battery: {"kind": "egemma"}`

```python
class EGemma
```

##### EGemma.read_budget

The judge budget eGemma publishes; without one, only the backoff.

```python
read_budget()
```

##### EGemma.pace

Wait until one more call fits the budget's window, then count it.

```python
pace()
```

##### EGemma.trains

Never: what it reads stays on this machine.

```python
trains(frame)
```

##### EGemma.check

Refuse, before any call, a frame this battery must not serve:
another battery's, an unknown key, a temperature outside 0 to 2, an
empty pin, reasoning that is not true or false, or no key; then read the
budget eGemma publishes.

```python
check(frame)
```

##### EGemma.observe

One /judge call, paced to eGemma's budget and retried while it is
busy: the label at the frame's pointer, or an opening that says why
there is none.

```python
observe(frame, prompt, max_output_tokens)
```
<!-- end api -->

<!-- api midwife.batteries.local_json -->

---

### midwife.batteries.local_json

The local-json battery: any evaluator on this machine that answers JSON.

A local classifier, test oracle or retrieval checker that already reads an
instruction and a text and answers to a schema needs no adapter of its own:
name its address in the frame and this battery calls it with the same care
the shipped critics take.

```json
"battery": {"kind": "local-json", "url": "http://127.0.0.1:8765/judge",
            "timeout": 30, "output": {"schema": {...}, "label": "/verdict"}}
```

The evaluator receives `{"instructions", "input", "schema", "max_tokens"}`
and answers `{"answer", "text", "usage", "served"}`: `answer` is the JSON
the label is read from (at `/label`, or the frame's own pointer), `served`
names what read it.

What this battery promises, whatever the frame says:
- it talks only to the address named, on this machine (loopback), over
  plain http, through no proxy and no redirect;
- it sends the instruction, the exact prompt, the schema and the answer's
  cap, and nothing else: no credentials, no tools;
- each call has a deadline (`timeout` seconds for the whole reply, 30 by
  default) and a cap on what it reads back;
- a reply it cannot read is an opening, never a guessed label, and each
  record names what the evaluator says served it.

#### payload

The request: the frame's instruction, the exact prompt, the schema the
answer is held to, and the answer's cap.

```python
payload(frame, text, max_output_tokens)
```

#### LocalJSON

`battery: {"kind": "local-json", "url": "http://127.0.0.1:8765/judge"}`

```python
class LocalJSON
```

##### LocalJSON.trains

Never: what it reads stays on this machine.

```python
trains(frame)
```

##### LocalJSON.check

Refuse, before any call, a frame this battery must not serve:
another battery's, an unknown key, an address off this machine, a
timeout that is not a positive number of seconds, or an output that
does not point at its label.

```python
check(frame)
```

##### LocalJSON.observe

One call to the evaluator: the label at the frame's pointer, or an
opening that says why there is none.

```python
observe(frame, prompt, max_output_tokens)
```
<!-- end api -->

<!-- api midwife.batteries.tendora -->

---

### midwife.batteries.tendora

The tendora battery: Tendora's engine, asked again against a trial's statements.

Tendora's engine server (in its demo package, `npm run serve -- --project P
--port N`) answers `POST /ask` with `statements` against exactly the
statements given, in their order, and saves nothing. This battery splits a trial's prompt by its
documented form (the statements one per line, a line `---` between blank
lines, then the input), asks the frame's saved question and case again
against those statements, and reads the label from the engine's answer.

```json
"battery": {"kind": "tendora", "url": "http://127.0.0.1:8791",
            "timeout": 60, "scope": "...", "offline": true}
```

Each input reads `Case: …` on its first line when there is a case, then
`Question: …`, exactly as the saved check asked it. The engine finds the
saved check by the question, the case and the scope, so all three must be
the check's own. When a trial has turned what is asked (an input inversion,
or a presentation that renames the input's words), the battery finds the
declared input that turned into it and names it as the `basis`, the saved
check to ask it against; it never learns the trial or the input's id.

The label, from the engine's answer:
- supported, with one answer whose text is a label: that label; several
  answers or another text: `another answer` when the frame lists it;
- open, conditional, ambiguous and conflict: the label of the same name when
  the frame lists it (a proposal one confirmation away is still open);
- limited, needs-reading, a refusal, any status or answer the frame does
  not list, and a reply out of the engine's form (answers that are not
  objects with words and a true or false condition, or no `served`) are
  openings, never labels.

With `"readings": "tab"`, each statement line carries a reading of it after
its first TAB: the text before the TAB is sent in `statements`, the reading
in `readings` at the same place, and a line with no TAB sends null. A line
with nothing before its TAB or nothing after it is an opening, and the
engine is not asked. The reply must list in `served.readings` exactly the
statements sent a reading, those it refused among them, or it is an
opening: an engine that ignored the readings answered another question.

Before any call, `check` refuses what the battery could not ask: no `open`
among the labels, an input not in the form above, a statement with a line
break in any trial (the engine is sent one a line), a rename that turns an
input out of the form, two inputs turned into one question, and, with
readings, a statement with nothing before or after its TAB in any trial.

What this battery promises, whatever the frame says:
- it talks only to the address named, on this machine (loopback), over
  plain http, through no proxy and no redirect, and sends no credentials;
- it sends the question, the case, the scope, the statements, with
  `readings` each one's reading, the offline flag and, for a turned input,
  the saved check it came from (`basis`), and nothing else; the trial's id
  is never among them;
- each call has a deadline (`timeout` seconds for the whole reply, its
  head included, 60 by default) and a cap on what it reads back: a reply
  past the cap is an opening, and nothing of it is kept;
- each record names the engine version, revision and packs that served it;
- each record keeps the answer, its status and each answer's text and
  condition, on its first line, then the reply as it came but for its echo
  of the statements: a long reply is cut at the record's cap, and the
  answer line holds as many answers as fit in half of it, with `more`
  saying how many were left out, so it is always whole JSON.

#### asked

The question and the case an input holds, or None when it is not in
the form `Case: …` (optional, first) then `Question: …`, each with words
in it, and no carriage return.

```python
asked(text)
```

#### bare

The side of a statement line's first TAB with nothing on it, `before`
or `after`, or None when the line holds no TAB or words on both sides.

```python
bare(text)
```

#### request_body

What the engine is sent for one prompt, or None when the prompt is not
in Gadfly's form: the question, the case and the scope, the statements in
their order, with `readings` each one's reading, and the offline flag.
With readings, a line with nothing on one side of its TAB is not in the
form either.

```python
request_body(frame, prompt)
```

#### turned

Each text a declared input turns into, through the frame's input
inversion or presentation, and the declared inputs that turn into it. A
text some declared input already is is left out: a swap asks that
input's own saved check. Worked out once for a frame.

```python
turned(frame)
```

#### malformed

Why a reply is not an answer in the engine's form, or None: a status
in words, and answers, if any, a list of objects, each with words for its
text and true or false for its condition, when it says one.

```python
malformed(reply)
```

#### label_of

The label the engine's answer gives, or the opening that says why it
gives none; a reply out of the engine's form gives none.

```python
label_of(reply, labels)
```

#### answer_line

The answer alone: its status, and each answer's text and condition,
as many as fit in half the record's cap, and how many more there were
(`more`), so the line a record keeps first is always whole JSON.

```python
answer_line(reply)
```

#### served_by

What a record names as having served the reply: the engine's version,
the first 16 characters of its revision, and its packs.

```python
served_by(reply)
```

#### unsent

Why `request_body` gives a prompt nothing to send: with readings, the
first statement line with nothing on one side of its TAB, by its place;
otherwise a prompt not in Gadfly's form.

```python
unsent(frame, prompt)
```

#### unacknowledged

Why a reply does not show the engine took the readings it was sent, or
None: `served.readings` lists exactly the statements sent one, by their
place in `statements`, those it refused among them.

```python
unacknowledged(served, readings)
```

#### Tendora

`battery: {"kind": "tendora", "url": "http://127.0.0.1:8791"}`

```python
class Tendora
```

##### Tendora.trains

Never: what it reads stays on this machine.

```python
trains(frame)
```

##### Tendora.check

Refuse, before any call, a frame this battery must not serve:
another battery's, an unknown key, an address off this machine, a
timeout that is not a positive number of seconds, a scope, offline
or readings flag of the wrong type, no `open` among the labels, a
statement with a line break in any trial, or with readings one with
nothing before or after its TAB, an input not in
the form `Case: …` then `Question: …`, an input inversion or
presentation that turns an input out of that form, or two inputs
turned into one question.

```python
check(frame)
```

##### Tendora.observe

One ask of the engine: the label its answer gives, or an opening
that says why there is none.

```python
observe(frame, prompt, max_output_tokens)
```
<!-- end api -->

<!-- api midwife.batteries.crossing -->

---

### midwife.batteries.crossing

The crossing battery: a reading made on the far side of a boundary.

Evidence at one grain often reaches a decision only through something made
from it at the next: metrics become an incident's cause, a meeting becomes
its minutes, a draft becomes the brief a reviewer reads. A frame can test
whether the decision still rests on the evidence across that crossing. Its
spans are the evidence at the near side; a maker writes the artefact that
crosses from each trial's body; a reader decides from the artefact and the
input, and that decision is the call's label. Ablation, shams and every
other trial change the evidence before the maker sees it, so the verdict
says whether what the anchors said survived the making.

```json
"battery": {"kind": "crossing",
            "maker": {"kind": "unified", "model": "...",
                      "instruction": "Write the incident's cause."},
            "reader": {"kind": "unified", "model": "..."}}
```

The frame's instruction and labels are the reader's; the maker's
instruction is its own, in its line. `Crossing()` makes the artefact and
reads it through the router; `Crossing(maker, reader)` takes any maker and
any battery, from Python. An artefact that cannot be made again (a dream,
a poem already written) crosses the other way: its spans name the source
they came from (`source` on a span), and an ordinary battery reads it.

What this battery promises, whatever the frame says:
- the maker sees the trial's body and nothing else, neither the input nor
  the trial's id; the reader sees the artefact and the input;
- each call's cap is shared: the maker is given half and the reader what
  the maker left, so the call as a whole keeps the budget's cap;
- an artefact not made is an opening, never a guessed label, and the reader
  is not asked; every opening names the side that gave no answer, and the
  reader's answer is held to the protocol as `run` holds any battery's;
- a side's report of its spend is taken only as whole counts, none
  negative, so a report can never buy the other side a larger cap; a side
  that reports nothing, or no such count, is charged all it was given;
- the record keeps the artefact's SHA-256 whole, with as much of its text
  and of the reader's answer as fit the record, and names what made it and
  what read it;
- each side keeps its own promises: through the router, the deny data
  policy and every other check of the unified battery hold for the maker's
  line as for the reader's.

#### Made

What a maker made of a body: the artefact's text, or an opening that
says why there is none, with what it said, spent and was served by.

```python
@dataclass(frozen=True)
class Made
```

#### Maker

What makes the artefact that crosses: from a trial's body, its text.
Like a battery, it never sees which trial it is serving.

```python
@runtime_checkable
class Maker(Protocol)
```

##### Maker.check

Refuse a maker line this maker must not serve (raise ValueError).

```python
check(line)
```

##### Maker.make

Make the artefact from the body's text once, spending at most
`max_output_tokens`.

```python
make(line, text, max_output_tokens)
```

#### Function

A maker that is a function of the body's text: a template, a parser,
a fixed rule. Its line names it by its kind and nothing else, so the
frame's hash names the function by that name alone: give a changed
function a new one. It keeps no state, so calls may run at once.

```python
class Function
```

##### Function.check

Refuse a line that says more than this maker's kind.

```python
check(line)
```

##### Function.make

The function's text for this body; a function spends no tokens.

```python
make(line, text, max_output_tokens)
```

#### UnifiedMaker

A model writes the artefact through the unified model router, under
the maker line's own instruction: `{"kind": "unified", "model": ...,
"instruction": ...}`, with `reasoning`, `trainsOnInputs` and
`endpoints` read as the unified battery reads them.

```python
class UnifiedMaker
```

##### UnifiedMaker.trains

Whether the maker's calls may reach a model that trains on them:
only when its line names the model under trainsOnInputs.

```python
trains(line)
```

##### UnifiedMaker.check

Refuse a line the router must not be sent, as the unified battery
refuses one, and a line with no instruction to write by.

```python
check(line)
```

##### UnifiedMaker.make

One call through the router: the artefact the model wrote, or an
opening that says why there is none.

```python
make(line, text, max_output_tokens)
```

#### Crossing

`battery: {"kind": "crossing", "maker": {...}, "reader": {...}}`

```python
class Crossing
```

##### Crossing.trains

Whether either side's calls may reach a reader that trains on them;
a maker or a reader that does not say is read as one that may.

```python
trains(frame)
```

##### Crossing.check

Refuse, before any call, a frame this crossing must not serve:
another battery's, an unknown key, a maker or reader line this
crossing was not made with or that its side refuses, or a prompt
whose body cannot be told from its input.

```python
check(frame)
```

##### Crossing.check_cap

Refuse, before any call, a cap that leaves a side's thinking budget
no room: the maker writes within half of each call's cap, and the
reader reads within what the maker leaves, at least the other half.

```python
check_cap(frame, cap)
```

##### Crossing.observe

One call across the boundary: the maker makes the artefact from
the body, then the reader reads it with the input; the reader's
label, or an opening that says which side gave none, and why.

```python
observe(frame, prompt, max_output_tokens)
```
<!-- end api -->

<!-- api midwife.cli -->

---

### midwife.cli

The command line: check-frame, plan, run, report, stats and portfolio,
and recoil's walk, successor, firm and gate.

```bash
uv run gadfly plan examples/upgrade.json
uv run gadfly run examples/upgrade.json \
    --battery midwife.batteries.egemma:EGemma \
    --calls 40 --out records.jsonl
uv run gadfly report examples/upgrade.json records.jsonl
uv run gadfly check-frame my-frame.json
uv run gadfly portfolio a.json b.json
```

It uses only the public pipeline, and each command is a public function's
parity: what Python offers, a command does, and `--json` prints what the
function returns. `run` needs an explicit call budget,
writes each record as one JSON line the moment it exists, never writes over
a file and makes none when it is refused, and says when it stopped early;
`report` keeps a finding's evidence and its open obligations apart.
A battery is named `module:Class` and is imported from the current
directory.

#### load_frame

The frame in a JSON file, or on standard input for `-`, checked and
hashed.

```python
load_frame(path)
```

#### load_battery

An instance of the battery class `module:Class`.

```python
load_battery(spec)
```

#### read_text

A file's text, or standard input's for `-`; text that is not UTF-8
is a `refusal`.

```python
read_text(path, refusal)
```

#### load_json

`text` as JSON, or a `refusal` that names its file and where it
broke; `line` is where `text` starts in the file, when it is one line.

```python
load_json(path, text, refusal, line=None)
```

#### read_bytes

A file's bytes, or standard input's for `-`, as they are: what a
file's SHA-256 is taken of.

```python
read_bytes(path)
```

#### load_records

The records kept in a JSON Lines file, or on standard input for `-`.

```python
load_records(path)
```

#### render_report

The person-readable report: the overall category, then each input's
levels, evidence and open obligations, each on its own line.

```python
render_report(frame, records)
```

#### command_plan

`gadfly plan`: the trials, what each changes, and the call count,
without a call; with --most or --runs, also the most calls asking the
frame until firm can make (`midwife.recoil.calls_until_firm`).

```python
command_plan(args)
```

#### command_stats

`gadfly stats`: how firm each trial's answers are over the kept runs,
whether each trial moved the baseline's answer, how likely the quorum was
to reach a level, and how often each run's verdict comes out the same
when its calls are drawn again. No verdict changes.

```python
command_stats(args)
```

#### command_run

`gadfly run`: every planned call the budget covers, each record kept.

```python
command_run(args)
```

#### command_report

`gadfly report`: the verdict read from a kept JSON Lines file.

```python
command_report(args)
```

#### command_check_frame

`gadfly check-frame`: the frame's shape against the schema (when
jsonschema is installed), then the parser's authoritative refusal, and
with --withhold, any prompt holding text the set withholds, every part
read, since no battery is named.

```python
command_check_frame(args)
```

#### command_portfolio

`gadfly portfolio`: several reports counted side by side.

```python
command_portfolio(args)
```

#### command_walk

`gadfly walk`: where a piece climbs from the frame it was found in, up
through the frames given, without a call (`midwife.recoil.walk`); with
--made, through the artefacts a crossing's records say it made; with
--sideways, one step aside to the siblings of the frame it starts from; with
--vectors, its fits ordered by cosine; with --calls, which fits that
many calls cover, each until firm.

```python
command_walk(args)
```

#### command_successor

`gadfly successor`: the frame a fit is asked again as, its hole filled
with the piece (`midwife.recoil.successor`), checked as any frame is and
written to standard output or a new file, never over one.

```python
command_successor(args)
```

#### command_firm

`gadfly firm`: ask a frame one whole run at a time until its verdict is
firm (`midwife.recoil.until_firm`). The runs --runs keeps count as runs
made, and each new run is kept there as a new file, record by record.

```python
command_firm(args)
```

#### command_gate

`gadfly gate`: what a fit did (`midwife.recoil.gate`), without a call.
A successor that asks another question is a reframing, read against no
category; any other is read from the runs --runs keeps, as `until_firm`
reads them.

```python
command_gate(args)
```

#### parser

The command line's arguments.

```python
parser()
```

#### main

Run one command. A refusal prints its class and message, then its
notes, and exits with its class's status; with `--json`, the same as one
object on standard error. Anything else is a bug: its traceback, and 70.

```python
main(argv=None)
```

#### refused

Say a refusal as the last lines of a Python traceback, or as JSON, and
give its exit status: a GadflyError's own, 7 for a file, 130 for Ctrl-C.

```python
refused(error, as_json)
```

#### described

A refusal or a warning as JSON: its type, the exit status it gives, its
message and notes, and its troubleshooting section.

```python
described(problem, status, message="", anchor="")
```

#### Parser

The arguments; a mistake in them is a UsageError.

```python
class Parser(argparse.ArgumentParser)
```

##### Parser.parse_args

The arguments; one no command takes is that command's mistake,
said before any that is missing, since a mistyped flag is often what
is missing.

```python
parse_args(args=None, namespace=None)
```

##### Parser.unknown

The flags in `args` that neither Gadfly nor the command takes.

```python
unknown(args)
```

##### Parser.error

Refuse as a UsageError, in one clause, pointing at the help.

```python
error(message)
```
<!-- end api -->

<!-- api midwife.portfolio -->

---

### midwife.portfolio

Several frames' verdicts side by side, without a verdict of their own.

`overall` reads one frame over its inputs. Different frames have different
relations, promises and recipients, and there is no fixed rule that combines
them, so a portfolio counts and groups: frames by category, open
obligations two or more frames share, and frames whose inputs disagree. It
never names a category for the portfolio.

#### Entry

One frame's overall verdict, as `gadfly report --json` writes it.

```python
@dataclass(frozen=True)
class Entry
```

#### summarize

Counts by category, the frames in each, the obligations frames share,
and the frames whose inputs reached different categories.

```python
summarize(entries)
```

#### entry_from

An entry from a `gadfly report --json` document (or a bare overall).

```python
entry_from(document)
```
<!-- end api -->

