# Batteries

A battery is the scorer in a trial, the reader under test; the fixed rules,
not the battery, read the verdict. Gadfly passes it the frame and the exact
prompt for one call, and it returns one observation: a declared label, or a
typed opening when there is no answer to read. It is never told which trial
produced the prompt.

---

### The protocol

A battery is any class with a `name` and these two methods:

```python
class Battery(Protocol):
    name: str

    def check(self, frame: Frame) -> None: ...

    def observe(
        self,
        frame: Frame,
        prompt: str,
        max_output_tokens: int,
    ) -> Observation: ...
```

- **`name`:** must equal the frame's `battery.kind`. Another battery is
  another frame, so call `situate()` again when you swap it.
- **`check`:** refuses a frame the battery cannot serve, such as another
  battery's kind or a missing model. `run` calls it once before the first
  call, so a refusal spends nothing.
- **`observe`:** reads one prompt and returns one label or one opening.
- **`concurrent`:** an optional class attribute. A battery that can serve
  several calls at once sets it to `True`, and only then does
  `run(parallel=N)` make calls side by side; the unified battery sets it.
- **`check_cap`:** an optional method, `check_cap(frame, cap)`. `run` calls
  it after `check` with each answer's cap, so a battery refuses a cap it
  cannot answer within before any call; the unified, crossing and branch
  batteries refuse one that leaves a thinking budget no room.
- **`StopRun`:** raised by a battery or a maker when its harness, not the
  frame, has failed, such as a refused key or a broken tool. The run keeps no
  record of that call, starts no other, keeps the calls already out, and ends
  as a stopped run that quotes the reason, as a spent budget ends one.
- **`trains`:** an optional method, `trains(frame) -> bool`, whether this
  frame's calls may reach a reader that trains on what it reads. A withhold
  set's `training` part applies only when it says yes, and a battery that does
  not say is read as one that may. A maker may say the same of its line.

The protocol's invariant is **trial blindness**: a battery sees the changed
body and the input, never `baseline`, `sham-1` or `ablation`. A scorer that
could branch on the trial would cue the comparison.

The prompt's form is a contract a battery may rely on: the trial's spans
joined by line breaks, then a line `---` between blank lines, then the
input's text:

```text
<the trial's spans, one per line>

---

<the input>
```

A span the trial cuts is simply absent, so a control that names every span
sends an empty body, and under presentation the input is renamed too. The
instruction and the labels come from the frame, for the battery to add as it
needs.

---

### The shipped batteries

Six batteries come with Gadfly, and the guarantees in this section are
theirs, not the protocol's. A battery of your own may do anything its code
does.

| Battery | Reads with | Guarantees and recorded provenance |
|---|---|---|
| `unified` | an LLM through the [unified model router](https://github.com/mirzahusadzic/unified-model-router), named as the router names its models | loopback, no tools, no proxy, no redirects, the router's deny data policy unless the exact model slug is listed under `trainsOnInputs`, checked at the router's `GET /health` before any call; refuses OpenAI slugs; `endpoints` pins up to 16 endpoints the router may use, through the router's own header; `fallback` and `thinkingBudget` keep a Claude model on Anthropic's API, the second with a fixed thinking budget; records the model, the provider the router reports or a single pinned endpoint's tag, and the route |
| `egemma` | Gemma through [eGemma](https://github.com/mirzahusadzic/egemma)'s `/judge` | loopback, no persona, no cache, paced to `GET /rate-limits`; caps time, tokens and bytes; records `model` and `revision`; optional frame pins are enforced; Gemma thinks first with `reasoning: true` |
| `local-json` | any evaluator on this machine that answers JSON, at `battery.url` | loopback, no proxy, no redirects, no credentials; a whole-call deadline (`timeout`) and a size cap; records what the evaluator says served |
| `tendora` | Tendora's engine server, from its demo package, at `battery.url`, asked again against the trial's statements | loopback, no proxy, no redirects, no credentials; read-only on the engine's side; a whole-call deadline and a size cap; records the engine's version, revision and packs |
| `crossing` | a maker, then a reader: the maker writes an artefact from the trial's body, and the reader decides from it | each side's own guarantees, through the router the unified battery's; the maker never sees the input; the cap is shared between the two; records the artefact's SHA-256 and what made and read it |
| `branch` | a maker, then a reader: the maker writes from a trial's input, once, what an answer would have to rest on, and the reader decides every trial against it | each side's own guarantees, through the router the unified battery's; the maker never sees the body; an input's artefact is made once and read by every call that carries the input; records the artefact's SHA-256 and what made and read it |
| your own | an evaluation engine, deterministic rule, or local system | yours; the class's `name` is the frame's `battery.kind`; a battery never sees the trial id |

#### Addresses and keys

Each shipped battery finds its service and its key on this machine:

- **`egemma`:** `EGEMMA_URL`, by default `http://127.0.0.1:8000`, and the key
  from the file named by `EGEMMA_API_KEY_FILE`, else `EGEMMA_API_KEY`, else
  `WORKBENCH_API_KEY`.
- **`unified`:** the router at `http://127.0.0.1:18766`, and its token from
  `CODEX_ROUTER_TOKEN`, else the router's own settings file. The router's
  `GET /v1/models` lists the models a frame may name.
- **`local-json`:** the frame's `battery.url`, and no key at all.
- **`tendora`:** the frame's `battery.url`, the engine server's address, and
  no key.

#### The answer's shape

The two critics, `unified` and `egemma`, ask for JSON to a schema, by default
`{"label": <one of the frame's labels>}`. A critic with its own answer shape
keeps it, and names where the label lives with a JSON pointer:

```json
"battery": {
  "kind": "unified",
  "model": "anthropic/claude-sonnet-5-5",
  "reasoning": "none",
  "fallback": "none",
  "output": {
    "schema": {
      "type": "object",
      "properties": {
        "review": {
          "type": "object",
          "properties": {"verdict": {"enum": ["approve", "reject"]}},
          "required": ["verdict"],
          "additionalProperties": false
        }
      },
      "required": ["review"],
      "additionalProperties": false
    },
    "label": "/review/verdict"
  }
}
```

The schema is sent as a strict one, so name the label's place in it, list
the frame's labels there and require it, as the default schema does. An
answer with nothing at the pointer, or a label the frame does not list, is
an opening.

#### Reasoning

A frame asks its model to think in its battery line. The `unified` battery
passes `battery.reasoning` to the model through the router as an effort, one
of `none`, `minimal`, `low`, `medium`, `high`, `xhigh` and `max`. The router's
catalog lists the levels each model takes; one outside them may be sent as
another, passed on as it is, or refused as an opening, so name a level the
catalog lists.

On Anthropic's API, `none` turns thinking off for Claude Sonnet 5.5 alone,
and Claude takes `minimal`, and `none` on any other model, as `low`.
Wherever its thinking is not off, Claude thinks adaptively: it decides on
each call whether to think, and the level only leans it.

A record's `served` says how the router asked the call to think, where it
says so, and its `usage` keeps every whole count the router reports, each
count of a breakdown such as `output_tokens_details` under its own name. A
call's `reasoning_tokens` then say whether it thought, when the router
passes them on.

A Claude model that still takes a thinking budget, such as Claude Sonnet 4.6,
thinks on every call within it. With `thinkingBudget` in the battery line, in
place of `reasoning`, the router sends that budget, from 1,024 tokens, and
each answer's cap must be above it, since the cap holds the thinking and the
answer both. A later model that takes no budget answers each call with an
opening:

```json
"battery": {
  "kind": "unified",
  "model": "anthropic/claude-sonnet-4-6",
  "thinkingBudget": 2048
}
```

Gemma 4 has no levels: its thinking is on or off. With `reasoning: true` in
the battery line, eGemma lets Gemma think before every answer, and only the
answer is held to the schema:

```json
"battery": {"kind": "egemma", "reasoning": true}
```

`--output-tokens` stays the whole call's cap: the answer keeps 64 of it and
the thought gets the rest, up to 4,096, so `--output-tokens 4160` gives a
whole thought. A cap of 64 or less leaves no room for one, and each call
opens before any request.

Each record's `usage` counts the thought's tokens as `reasoning_tokens`. It
needs an eGemma newer than its v0.5.0, whose `/judge` takes `reasoning`; an
older one answers 422, which the battery records as an opening.

#### Claude on Anthropic's API

The router serves an `anthropic/` model on Anthropic's own API, and by
default moves a call Anthropic refuses to another provider. `"fallback":
"none"` in the battery line keeps every call there, so one frame is read by
one route; a refusal comes back as an opening that says why. A thinking
budget keeps its calls there too. Name it for a new frame with a Claude
reader; a frame without it reads as before.

#### Tendora's engine

The `tendora` battery asks a saved question again against exactly the
trial's statements, through the engine server's `POST /ask`, and nothing is
saved there. Each input is the saved check's own case and question:

```text
Case: A certificate expires.
Question: Who notifies the customers?
```

The case line is left out when the check had none, and `battery.scope`
names the check's scope when it has one. `battery.offline` keeps the engine
from reading a new text, such as a statement presentation renamed.

The label is the engine's answer: one supported answer whose text is a
label gives that label, and several answers or another text give `another
answer`. Open, conditional, ambiguous and conflict give the label of the
same name. A label the frame does not list is an opening, and so are
`limited`, `needs-reading` and a reply out of the engine's form, always.

The frame must list `open`, and its statements must hold no line break,
since the engine is sent one statement a line. The battery refuses either
before any call, as it does a rename that turns an input out of its form
or two inputs into one question.

With `"readings": "tab"` in the battery's line, each statement line carries
a reading of it after its first TAB: the text before the TAB is sent as the
statement, the reading in `readings` at the same place, and a line with no
TAB sends `null`. A line with nothing on one side of its TAB is refused
before any call when it is a span, and is an opening, never sent, when a
crossing's maker wrote it. The reply must list in `served.readings` exactly
the statements sent a reading, or the call is an opening, since an engine
that ignored them answered from the bare statements.

#### Privacy and routing

The shipped batteries keep these promises, and a battery of your own owns its
consent, retention, credential and recording rules.

| Promise | `unified` | `egemma` | `local-json` | `tendora` | your own |
|---|---|---|---|---|---|
| destination | a router on loopback over plain HTTP | eGemma on loopback over plain HTTP | `battery.url` on loopback over plain HTTP | the engine server at `battery.url`, on loopback over plain HTTP | unknown |
| proxy | disabled in the opener | disabled in the opener | disabled in the opener | disabled in the opener | unknown |
| redirects | refused | refused | refused | refused | unknown |
| tools | never sent | no persona or cache fields added | never sent | never sent | unknown |
| provider collection | the router's deny data policy, `X-Codex-Router-Data-Policy: deny`, unless the exact model slug is in `trainsOnInputs` | stays on this machine by contract | stays on this machine | stays on this machine; the engine reads a new text through eGemma unless offline | unknown |
| credentials | router token from environment or its env file; never placed in a request body or record | key from environment/file; sent only as an Authorization header | none sent | none sent | unknown |
| deadline | whole call, `timeout` seconds, even mid-line | whole call, per attempt | whole call, `battery.timeout` (30 s, at most an hour) | whole call, `battery.timeout` (60 s, at most an hour) | unknown |
| trains on what it reads | only when the frame names the model under `trainsOnInputs` | never | never | never | read as yes, unless it says |
| verification | the model, the provider the router reports or a single pinned endpoint's tag, and the route; never a provider the router calls unknown | model and revision recorded; frame pins are enforced | what the evaluator reports under `served` | the engine's version, revision and packs, from its reply | unknown |

`--withhold FILE`, or `withhold=` in Python, refuses before any call a frame
whose prompts, instruction, labels or battery line hold text that must not
leave this machine. Its `always` part binds every battery, and its `training`
part binds a battery whose calls may train;
[the command line](command-line.md#withhold-text) shows the file.

#### Costs

`Budget.calls` is a hard count of calls, every answer is capped by
`Budget.output_tokens_per_call`, and `Budget.tokens` can cap the output tokens
in all. Input tokens and a provider's prices are outside the budget, so a model
may be slower or cost more than the caps suggest. Run `calls_needed(frame)`
before a live run.

The cap is the whole call's. A battery that writes before it answers reports
every output token it spent in `usage`, so set `--output-tokens`
(`Budget.output_tokens_per_call`) to what a whole call may spend: a call that
reports more stops the run after it.

A cap of your own, on money or time, goes through `run(cancelled=...)`,
which is asked before every call. `run(settle=True)` spends fewer calls: a
trial stops once its level can no longer change, and the verdict reads as
it would over every call.

#### Record provenance

Every record names these, so a verdict can be traced to what was read and who
read it:

```text
frame hash, input id, trial id, quorum index,
body hash, prompt hash, battery name,
observation or opening, raw answer prefix,
usage, served
```

`served` is what the service reports, not a statement of trust, and a local
runner may leave it empty. The `unified` battery records the model the
response names, then the provider the router reports, or, for a call pinned to
one endpoint, that endpoint's tag; a provider the router does not yet know is
left out, never guessed. Then it records the route the router names, the
upstream the call went to, as `claude-sonnet-5-5 via Anthropic (route
anthropic)`.

Where the router reports how a call thought, which it does on Anthropic's
API, `served` says that after the route: `thinking off`, `thinking adaptive`
or `thinking budget`. It is the router's word for the request it sent, not
a count of tokens. What a crossing's and a branch's records keep is said
with [a maker and a reader](#a-maker-and-a-reader).

### A maker and a reader

Two shipped batteries put a maker before the reader. The `crossing`
battery's maker writes from each trial's body, and the `branch` battery's
from each trial's input, before any evidence is seen; the reader then
decides from what the maker wrote. The frame's instruction and labels are
the reader's, the maker's instruction is in its own line, and the frame's
hash names both.

With no arguments, `Crossing` and `Branch` make and read through the unified
model router, and each side's line is held to every check of the `unified`
battery. Give each call room for both answers:

```text
gadfly run incident.json \
    --battery midwife.batteries.crossing:Crossing \
    --calls 150 --output-tokens 4000 \
    --out incident.jsonl
```

Both batteries keep these promises:

- **What a call spends:** the call that makes an artefact gives the maker
  half of `--output-tokens` and the reader what the maker left, so the cap
  and the token budget hold for the call as a whole. A side that reports
  nothing, or a spend that is not a count, is charged all it was given.
- **When a side fails:** an artefact not made is an opening that says so
  (`the maker made nothing (…)`), and the reader is not asked; a reading not
  made says so too (`the reader gave no label (…)`).
- **What a record keeps:** `served` reads `made by …, read by …`, and the raw
  answer keeps the artefact's SHA-256 whole, beside as much of the artefact
  and the reader's answer as fit the record's 2,000 characters, the longer
  cut first. A cut artefact no longer hashes to its SHA-256.

Both examples below have the maker think and tell the reader not to:

- **Why the reader need not think:** the thinking is the maker's, once for
  each input in a branch and once for each trial's body in a crossing, so the
  reader's part is only to read, to see whether what it is given says what
  the maker's text says it must.
- **What that gains:** a reading in a few tokens, about ten from Claude
  Sonnet 5.5 at `none`, so a quorum and repeated runs cost little beyond
  their input, and no reader's thought can shift the standard from trial to
  trial.
- **Why only the reader:** the maker's text is the standard every reading is
  held to, so the maker must think, and for certain: pick one whose thinking
  cannot be skipped, as Muse Spark 1.3's cannot, never one that decides call
  by call whether to think. A reader that does not think cannot add what a
  thin standard lacks.
- **Why a good model:** without thought, the reader has only the model's own
  reading to go on, so pick one that reads well without it. The router turns
  Claude Sonnet 5.5's thinking off at `none`, and each record's `served`
  says "thinking off".

#### A maker before the reader

The `crossing` battery runs a [crossing](crossings.md) out through a maker
that runs again. The maker sees the trial's body alone, never the input and
never which trial it serves; the reader sees the artefact, the `---` line
and the input, as any battery sees a body and its input:

```json
"battery": {
  "kind": "crossing",
  "maker": {
    "kind": "unified",
    "model": "openrouter/meta/muse-spark-1.3-contributor",
    "reasoning": "low",
    "trainsOnInputs": ["openrouter/meta/muse-spark-1.3-contributor"],
    "instruction": "You write the cause section of an incident report from the signals and changes given. In two or three sentences, say what most likely caused what the signals show, using only what is given. Do not recommend an action."
  },
  "reader": {
    "kind": "unified",
    "model": "anthropic/claude-sonnet-5-5",
    "reasoning": "none",
    "fallback": "none"
  }
}
```

#### A maker before the evidence

Someone holds a claim, and a reader is to say whether a page bears it. The
`branch` battery puts one written step between the two: from the claim
alone, before any page is read, a maker writes what the claim would have to
look like in the lines of its own locus, and the reader holds every trial's
page against that step. The step has four parts:

- **What its words mean there:** what each key term of the claim must mean
  in such lines.
- **What else must be so:** what else the lines must show for the claim to
  hold.
- **What the lines would say if it were false.**
- **What one would believe with no line at all:** a belief from experience
  that would make the claim seem true with no evidence, named so that the
  reader keeps it out.

Each part has a trial beside it: renaming tests the words, cutting the
anchors what else must be so, turning them the false case, and the bypass
the belief, with a control beside them all. The step is thin when it adds
nothing of its own, and that takes two befores: the claim is said before its
page is read, and the step is written from the claim alone before the page
is read. A page that cannot bear the claim is then the first finding, before
any reader is called.

| | One turn | Through the branch |
| --- | --- | --- |
| What the reader is given | the trial's page and the claim | the step, the page and the claim |
| Who reasons, and when | the reader, in every call, after it has seen the page | a maker, once for each claim, before any page is seen |
| The reader's effort | as the frame sets it | none needed, since the reasoning is done |
| Requests a call | one | two in the first call for a claim, the maker's and then the reader's, and one after |

Three things follow from that order:

- **Fixed first:** the standard is fixed before any page is seen, and is the
  same in every trial, so it cannot bend to what one trial shows or lacks.
- **On record:** the step is in the record, so a verdict can be read back to
  what it rested on.
- **Paid once:** the reasoning is paid once for a claim, not once for a
  trial, so the reader can be told not to think.

Three public examples, each said as a claim, were read one call at a time:
in one turn by Muse at `low`, thinking, and through the branch twice, with
Muse at `low` making the step anew each run and Claude Sonnet 5.5 at `none`
reading. An arrow leads from one turn to the branch, whose figures, in
bold, are the mean of its two runs; the frames, records and predictions are
[kept with the examples](https://github.com/mirzahusadzic/gadfly/tree/main/examples/branch):

| Example, as a claim | Readings | Verdict | Input tokens a reading | Output tokens | Time |
| --- | --- | --- | --- | --- | --- |
| [19](examples/index.md), "Gadfly, a separate library, calls the router over the same Responses API that Codex uses, so Codex is not the router's only client" | 35 | carried → **carried** | 451 → **1,044** | 23,087 → **2,785, 88% fewer** | 150 s → **78 s, 48% less** |
| [22](examples/dolls.md#22-kiran-with-the-paper), "Kiran is a boy" | 24 | carried → **carried** | 353 → **879** | 13,915 → **2,772, 80% fewer** | 101 s → **79 s, 22% less** |
| [22c](examples/dolls.md#22c-mirza-holding-a-paper-that-is-not-mirzas), "the paper that the doll holds is about someone other than the doll" | 27 | cooled → **cooled** | 275 → **746** | 15,845 → **2,712, 83% fewer** | 102 s → **73 s, 28% less** |

The branch reached the one-turn verdict on all three, in both of its runs,
and the maker wrote nearly the same step each time: on 22 both runs gave the
same key terms, the same false case and the same belief to keep out, that the
name sounds like a boy's. Output tokens fell by four fifths or more, and time
by a fifth to a half, since a call's time is not only what it writes. These
are one or two runs a frame, an indication and not a rate, and the two
models differ in price, so tokens compare work, not money.

Reach for it where someone will act on a decision without rereading what it
rests on. Say the input as a claim someone holds, never as an open question:
"What am I?" gives the maker nothing to take apart, and "Kiran is a boy"
does. Carried then means that the answer rests on what was declared, for
this reader and this page; it does not mean the claim is true.

Its line names each side, as a crossing's does. Here the maker thinks at
`low` and writes the step, and the reader, Claude Sonnet 5.5 at `none`, does
not think at all:

```json
"battery": {
  "kind": "branch",
  "maker": {
    "kind": "unified",
    "model": "openrouter/meta/muse-spark-1.3-contributor",
    "reasoning": "low",
    "trainsOnInputs": ["openrouter/meta/muse-spark-1.3-contributor"],
    "instruction": "You are given a claim about an incident. It will be checked against lines of evidence that you are not shown. Take the claim apart, as a numbered list of at most eight short lines: first, what each key term of the claim must mean in such lines; second, what else the lines must show for the claim to hold; third, what the lines would show if the claim were false; fourth, any belief from experience that would make the claim seem true with no evidence at all, named so that the reader keeps it out. Use only the claim. Write no line of dashes."
  },
  "reader": {
    "kind": "unified",
    "model": "anthropic/claude-sonnet-5-5",
    "reasoning": "none",
    "fallback": "none"
  }
}
```

It runs as a crossing does, with `--battery midwife.batteries.branch:Branch`.
The maker sees the claim alone, never the page and never which trial it
serves, so nothing a trial took out of the evidence can come back through
the step; the reader sees the step, the page and the claim, with a `---`
line between each.

- **One step for each claim:** the first call that carries a claim makes its
  step, and every later one reads it, giving the reader the whole of
  `--output-tokens` and counting nothing for the making. A making that fails
  is made again by the next call, and a step that holds a `---` line of its
  own is an opening.
- **Repeated runs:** one battery object keeps a claim's step for as long as
  it lives, so within one `gadfly firm` the reader's variation is measured
  over one step, never the maker's. A new command, or a run resumed with a
  new object, makes the step again from the same claim, and `--json` gives
  each claim's steps as `steps`, with the trials that read more than one.
- **A renamed claim:** presentation and input inversion rename the claim, so
  the maker writes a step for it too, and a run's records name two SHA-256
  values. Reading the first there would bring back the words the trial
  renamed.

When to use which:

- **One turn:** a reader that does not reason on its own, where the branch
  only costs more; a question nobody holds as a claim; and once on any
  frame, as the reference.
- **Through the branch:** a claim someone holds, a standard wanted fixed
  before the page and on record, and many readings of each claim (a quorum,
  the runs of `gadfly firm`).

Why both:

- **One turn is the reference:** it is the simpler path, and Gadfly's count
  of calls is the same for both.
- **The branch holds the claim to its step:** each claim the maker reads
  costs one more request.
- **They are not quite the same measurement:** in one turn the reader can
  set its standard after it has seen the page, and through the branch it
  cannot. Run both once on a frame of your own before relying on the branch.

#### How to ask the maker

The maker's instruction is the instrument itself, and a fault in it reaches
every trial at once:

- **Ask for the four parts, from the claim alone:** for the kind of lines
  there are, as the frame's locus and grain name it, in at most a few short
  lines.
- **Leave the reader room:** every call reads the step, and a record keeps
  2,000 characters of it and the answer. A small reader with a short output
  limit cannot read through a long one.
- **Try it on a known answer first:** run a new maker instruction on a frame
  whose answer is known, beside its one-turn reading. The baseline must
  still carry and the ablation must still move.

The worst cases, each worth a check before a run:

- **The step grows thick:** it adds rivals, softenings or readings the claim
  never made. A sign is a line that goes back neither to a word of the claim
  nor to what that word must mean in such lines.
- **The claim is fitted to its page:** worded after the page was read, or
  reworded until it passes.
- **The step presses every claim down to what the page literally says:** it
  then comes back carried and shows little.
- **A page composed for the claim:** it cannot falsify it.

The frame's instruction tells the reader what its three parts are; with the
labels `supports`, `does-not-support` and `unclear`, it opens:

> You are given three parts, parted by lines of dashes: first what the claim
> needs, written before the evidence was seen; then the lines of evidence;
> then the claim. Decide from the lines of evidence alone, held against the
> first part; where the first part names a belief to keep out, do not use it.

Asked what would show the claim false, a maker names lines that would be
missing, and a reader holding the page against that list can then read a gap
as a no. One sentence more in the frame's instruction keeps a gap undecided:

> A thing the lines leave out makes the answer unclear, even where the first
> part counts it as a sign that the claim is false. Answer does-not-support
> only where a line shows that the claim is not so or contradicts it.

A reader under that sentence still answers no where a line gives the no, as
"whatever is not granted above is denied" does in an access policy. Where
silence must answer, because the evidence is the whole of its subject, say
so in a line of the evidence; without such a line, the reader answers
unclear.

#### A maker of your own

A maker is any object with a `name`, `check(line)` and `make(line, text,
max_output_tokens)`, which returns a `Made`: the text it wrote, or an
opening that says why there is none, with what it spent in `usage` and what
served it. Any battery reads.

For a crossing, `Function` makes a maker of a plain function of the body's
text, such as a template, a parser or a fixed rule:

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

A branch's maker writes the step every reading is held to, so it is a model
that thinks, held to the method:

- **From the claim alone:** `text` is the claim. Ask for the four parts and
  nothing else, as the maker's instruction in the branch's example does.
- **Thinking, for certain:** call a model whose thinking cannot be skipped,
  at a level it declares.
- **Within its share:** spend at most `max_output_tokens`, and report every
  whole count in `usage`; a maker that reports nothing is charged all it was
  given.
- **Never a guess:** where it writes no step, return an opening; write no
  `---` line; raise `StopRun` when its own harness fails; and say
  `trains(line)` when its calls may reach a model that trains on them.

```python
from midwife.batteries.branch import Branch
from midwife.batteries.crossing import Made
from midwife.batteries.unified import Unified

STEP = "Take the claim apart, as a numbered list ..."


class ClaimMaker:
    name = "claim-maker"

    def check(self, line):
        if set(line) != {"kind"}:
            raise ValueError("claim-maker's line names its kind alone")

    def make(self, line, text, max_output_tokens):
        reply = your_model(STEP, text, max_output_tokens)
        if not reply.text:
            return Made(None, opening="no step", usage=reply.usage)
        return Made(reply.text, usage=reply.usage, served=reply.model)


branch = Branch(ClaimMaker(), Unified())
```

`your_model` stands for your own call to a model that thinks. `Branch()`
with no arguments already makes the step through the router, with the
maker's instruction in its line, so write your own only for a model the
router does not serve.

---

### Write your own

A deterministic battery costs no tokens and shows the frame's mechanics
plainly. This is the smallest useful shape:

```python
from midwife.types import Observation


class CitationReader:
    name = "citation-reader"

    def check(self, frame):
        kind = frame.battery["kind"]
        if kind != self.name:
            raise ValueError(f"this frame asks for battery {kind!r}")

    def observe(self, frame, prompt, max_output_tokens):
        body, _, question = prompt.partition("\n\n---\n\n")
        if "Source S-2:" in body:
            return Observation(label="grounded")
        return Observation(label="ungrounded")
```

`tests/fixtures/refund.py` holds two more, ten lines each, and
[Write a frame](write-a-frame.md#run-it-without-a-model) runs one. A
deterministic battery tests the frame, not a model; the examples use a live
one.

#### Your evaluator, without an adapter

A local classifier, test oracle or retrieval checker that already reads an
instruction and a text and answers JSON needs no battery of its own. The
[Local JSON battery](breadth/local-json-battery.md) calls it with the shipped
batteries' guarantees.

#### When a call fails

`observe()` should return an opening for an unreadable answer or a failed
call, keeping what arrived before the failure, as the shipped batteries do.
The pipeline turns an unexpected exception into an opening too, but a battery
should not lean on that net. A timeout in particular must never become a label
or be dropped.

A battery refuses a frame it must not serve with a `ValueError`, from `check`
as above, or while its module is imported or it is made. Gadfly raises each as
a `BatteryError`, exit 6 on the command line, with the battery's own words as
its note.

---

### Choosing a live quorum

Use `standing.quorum` of at least 3 for a sampled critic, and choose `agree`
before the run. More calls reduce sampling noise, but they do not make a
scorer that follows wording, or reacts to any cut, a valid one. A live run is
evidence from one model and endpoint at one encounter, not a guarantee about
that provider in general.
