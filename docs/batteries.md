# Batteries

A battery is the scorer in a trial. Gadfly passes it the frame and the exact
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
  cannot answer within before any call; the unified and crossing batteries
  refuse one that leaves a thinking budget no room.

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
sends an empty body, and under presentation the input is renamed too. The instruction and the labels come from the frame, for the
battery to add as it needs.

---

### The shipped batteries

Five batteries come with Gadfly, and the guarantees in this section are
theirs, not the protocol's. A battery of your own may do anything its code
does.

| Battery | Reads with | Guarantees and recorded provenance |
|---|---|---|
| `unified` | an LLM through the [unified model router](https://github.com/mirzahusadzic/unified-model-router), named as the router names its models | loopback, no tools, no proxy, no redirects, the router's deny data policy unless the exact model slug is listed under `trainsOnInputs`, checked at the router's `GET /health` before any call; refuses OpenAI slugs; `endpoints` pins up to 16 endpoints the router may use, through the router's own header; `fallback` and `thinkingBudget` keep a Claude model on Anthropic's API, the second with a fixed thinking budget; records the model, the provider the router reports or a single pinned endpoint's tag, and the route |
| `egemma` | Gemma through [eGemma](https://github.com/mirzahusadzic/egemma)'s `/judge` | loopback, no persona, no cache, paced to `GET /rate-limits`; caps time, tokens and bytes; records `model` and `revision`; optional frame pins are enforced; Gemma thinks first with `reasoning: true` |
| `local-json` | any evaluator on this machine that answers JSON, at `battery.url` | loopback, no proxy, no redirects, no credentials; a whole-call deadline (`timeout`) and a size cap; records what the evaluator says served |
| `tendora` | Tendora's engine server, from its demo package, at `battery.url`, asked again against the trial's statements | loopback, no proxy, no redirects, no credentials; read-only on the engine's side; a whole-call deadline and a size cap; records the engine's version, revision and packs |
| `crossing` | a maker, then a reader: the maker writes an artefact from the trial's body, and the reader decides from it | each side's own guarantees, through the router the unified battery's; the maker never sees the input; the cap is shared between the two; records the artefact's SHA-256 and what made and read it |
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
  "reasoning": "low",
  "output": {
    "schema": {
      "type": "object",
      "properties": {"review": {"type": "object"}}
    },
    "label": "/review/verdict"
  }
}
```

#### Reasoning

A frame asks its model to think in its battery line. The `unified` battery
passes `battery.reasoning` to the model through the router as an effort, one
of `none`, `minimal`, `low`, `medium`, `high`, `xhigh` and `max`. A model that
does not take a level refuses the call, which comes back as an opening.

A level is a request: some models decide on each call whether to think at
all. Each record's `usage` keeps every whole count the router reports, and
each count of a breakdown such as `output_tokens_details` under its own name,
so a call's `reasoning_tokens` say whether it thought, when the router passes
them on.

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

#### Claude on Anthropic's API

The router serves an `anthropic/` model on Anthropic's own API, and by
default moves a call Anthropic refuses to another provider. `"fallback":
"none"` in the battery line keeps every call there, so one frame is read by
one route; a refusal comes back as an opening that says why. A thinking
budget keeps its calls there too. Name it for a new frame with a Claude
reader; a frame without it reads as before.

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

#### A maker before the reader

The `crossing` battery runs a [crossing](crossings.md) out through a maker
that runs again: the maker writes an artefact from each trial's body, and a
reader decides from it. Its line names each side in a line of its own. The
frame's instruction and labels are the reader's, the maker's instruction is
in its line, and the frame's hash names both:

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
router, and each side's line is held to every check of the `unified`
battery. Give each call room for both answers:

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
- **When a side fails:** an artefact not made is an opening that says so
  (`the maker made nothing (…)`), and the reader is not asked; a reading
  not made says so too (`the reader gave no label (…)`). A side that
  reports nothing, or a spend that is not a count, is charged all it was
  given.

A maker of your own is any object with a `name`, `check(line)` and
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
| verification | the model, the provider the router reports or a single pinned endpoint's tag, and the route; never a provider the router calls unknown | model and revision recorded; frame pins are enforced | what the evaluator reports under `served` | the engine's version, revision and packs, from its reply | unknown |

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
anthropic)`. The `crossing` battery records `made by …, read by …`,
and its raw answer keeps the artefact's SHA-256 whole, beside as much of the
artefact and the reader's answer as fit the record's 2,000 characters.

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
