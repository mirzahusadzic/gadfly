# Python API

Each module's section below is written from its public docstrings by
`tools/doc_outputs.py`, and a test keeps it current, so it reads the same here
and on GitHub. For narrative guidance start with
[Your first frame](first-frame.md) or [Reading a verdict](reading-a-verdict.md).

- **[`midwife.pipeline`](#midwifepipeline):** `situate`, `plan`, `run`,
  `judge`, `overall`, `calls_needed`.
- **[`midwife.frame`](#midwifeframe):** frame parsing, hashing and refusal
  errors.
- **[`midwife.types`](#midwifetypes):** `Observation`, `Record`, `Budget`,
  `Battery`.
- **[`midwife.verdict`](#midwifeverdict):** categories, levels, evidence and
  obligations.
- **[`midwife.interventions`](#midwifeinterventions):** trial planning,
  prompts and presentation renaming.
- **`midwife.batteries.*`:** the shipped loopback batteries, two critics and
  `local-json`.
- **[`midwife.cli`](#midwifecli):** the `gadfly` command, with plan, run,
  report, check-frame and portfolio.
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
and makes several calls at once for a battery that takes them.

#### situate

Another name for `parse` in `midwife.frame`:

Check a frame and hash it. The frame keeps its own copy: changing the
caller's dict afterwards cannot change what the hash names.

```python
situate = midwife.frame.parse
```

#### plan

Another name for `plan` in `midwife.interventions`:

The trials of one input, in a fixed order.

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
calls it skipped because their trial had settled.

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
    parallel=1,
)
```

`settle` makes no more calls for a trial whose level can no longer
change (`settled`); the verdict reads it as it would read every call.
Under `standing.stable` the baseline and repeat always run whole, as
their split is read across all their calls. `parallel` makes up to that
many calls at once, for a battery that says it takes them (a
`concurrent` attribute that is true); records are handed on as each
call ends, and a call already started is always kept.

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

#### FrameError

A frame that cannot be assessed as declared.

```python
class FrameError(ValueError)
```

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
same kinds, none cited, none bypassed, none a declared fallback, and no
span in two draws. A fallback is declared to carry the relation, so
cutting it is no sham. Each is the closest in length still free; spans
equally close are drawn among by the frame's own seed. A draw that
cannot be matched is left out; the verdict says so.

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

The trials of one input, in a fixed order.

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
opener()
```

#### Late

A reply still coming at its deadline, with the bytes that had arrived:
kept beside the opening, never read as an answer.

```python
class Late(TimeoutError)
```

Late has these properties:

- **`text`:** `str`. What had arrived, as text, for the record's raw.

#### read_reply

A reply as it comes, until it ends or passes the size cap; Late, with
what had arrived, if it is still coming at the deadline (the socket's
timeout waits per read).

```python
read_reply(response, deadline, clock)
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

The [unified model router](https://github.com/mirzahusadzic/codex-unified-model-router)
serves the Responses API on loopback and maps a model slug to its provider:
`anthropic/...` runs on Anthropic's API; `openrouter/...`, `deepseek/...`
and `ultra-spark/...` run on OpenRouter (DeepSeek's models through it), each
with the router's own key. `ultra-spark/` is training-tier: it is sent only
when the frame names its exact slug under `trainsOnInputs`.

One battery covers them all; calling a provider's own endpoint is a
different battery (a native one). An unprefixed slug is OpenAI's, which the
router reaches only with the caller's Codex sign-in: this battery refuses
it.

The critic answers in JSON to a schema, by default `{"label": &lt;one of the
frame's labels>}`. A critic of your own (its output schema, as your project
already has it) is adapted by saying where in its answer the label is:

```json
"battery": {"kind": "unified", "model": "anthropic/claude-sonnet-5-5",
            "reasoning": "low",
            "output": {"schema": {...}, "label": "/verdict"}}
```

What this battery promises, whatever the frame says:
- it talks only to a router on this machine (loopback);
- it sends no tools: the router's web search runs on another provider, and a
  body would leave the model's own provider with it;
- it refuses a model whose provider trains on its inputs unless the frame
  names that model under `battery.trainsOnInputs`, and asks every other
  request to reach only endpoints that keep no data (`data_collection: deny`;
  which endpoints serve a model is the OpenRouter account's provider setting,
  and DeepSeek's own endpoint may train on prompts);
- it uses no proxy and follows no redirect, so the body and the token go to
  the loopback address named and nowhere else;
- each call has a deadline (`timeout` seconds for the whole answer), the
  budget's cap on output tokens, and a cap on what it reads back;
- each record names what served it: the model the response names and the
  endpoint the router reports; `endpoints` pins OpenRouter endpoints, in
  order and without fallbacks, so one endpoint reads a quorum;
- the router's token comes from the environment or the router's own env file
  and is never logged, returned or recorded.

#### consented

Whether the frame lets this model go where inputs train: its slug,
exactly, in the list under trainsOnInputs (a string is no list).

```python
consented(battery)
```

#### payload

The request body. No `tools` key, ever.

```python
payload(frame, text, max_output_tokens)
```

#### parse_stream

The answer's text, its usage, an opening if the call did not complete,
and the model the response names, from the router's server-sent events.
A stream still coming at `deadline` (on `clock`) is cut there, and a
connection that times out or fails mid-stream keeps what arrived.

```python
parse_stream(lines, deadline=None, clock=time.monotonic)
```

#### Unified

`battery: {"kind": "unified", "model": "anthropic/claude-sonnet-5-5"}`

```python
class Unified
```

##### Unified.check

Refuse, before any call, a frame this battery must not serve: another
battery's, an unknown key, an OpenAI slug, tools, a model whose
provider trains on its inputs without the frame's consent, or no
router token.

```python
check(frame)
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
samples; at `temperature: 0` the battery is close to deterministic.

```json
"battery": {"kind": "egemma", "temperature": 0.7}
```

What this battery promises, whatever the frame says:
- it talks only to an eGemma on this machine (loopback), through no proxy
  and no redirect;
- each call has a deadline (`timeout` seconds for the whole reply), the
  budget's cap on output tokens, and a cap on what it reads back;
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
cap, and the frame's temperature if it names one.

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

##### EGemma.check

Refuse, before any call, a frame this battery must not serve:
another battery's, an unknown key, a temperature outside 0 to 2, an
empty pin, or no key; then read the budget eGemma publishes.

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

<!-- api midwife.cli -->

---

### midwife.cli

The command line: plan, run, report, check-frame, portfolio.

```bash
uv run gadfly plan examples/upgrade.json
uv run gadfly run examples/upgrade.json \
    --battery midwife.batteries.egemma:EGemma \
    --calls 40 --out records.jsonl
uv run gadfly report examples/upgrade.json records.jsonl
uv run gadfly check-frame my-frame.json
uv run gadfly portfolio a.json b.json
```

It uses only the public pipeline. `run` needs an explicit call budget,
writes each record as one JSON line the moment it exists, never writes over
a file and makes none until its first record, and says when it stopped
early; `report` keeps a finding's evidence and its open obligations apart.
A battery is named `module:Class` and is imported from the current
directory.

#### load_frame

The frame in a JSON file, checked and hashed.

```python
load_frame(path)
```

#### load_battery

An instance of the battery class `module:Class`.

```python
load_battery(spec)
```

#### load_records

The records kept in a JSON Lines file.

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
without a call.

```python
command_plan(args)
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
jsonschema is installed), then the parser's authoritative refusal.

```python
command_check_frame(args)
```

#### command_portfolio

`gadfly portfolio`: several reports counted side by side.

```python
command_portfolio(args)
```

#### parser

The command line's arguments.

```python
parser()
```

#### main

Run one command; a refusal is a message and exit status 2.

```python
main(argv=None)
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

