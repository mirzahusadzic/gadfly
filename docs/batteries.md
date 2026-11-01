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

- **`name`:** must equal the frame's `battery.kind`.
- **`check`:** refuses a frame the battery cannot serve, such as another
  battery's kind or a missing model. `run` calls it once before the first
  call, so a refusal spends nothing.
- **`observe`:** reads one prompt and returns one label or one opening.
- **`concurrent`:** an optional class attribute. A battery that can serve
  several calls at once sets it to `True`, and only then does
  `run(parallel=N)` make calls side by side; the unified battery sets it.

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

Four batteries come with Gadfly, and the guarantees in this section are
theirs, not the protocol's. A battery of your own may do anything its code
does.

| Battery | Reads with | Guarantees and recorded provenance |
|---|---|---|
| `unified` | an LLM through the [unified model router](https://github.com/mirzahusadzic/codex-unified-model-router): `anthropic/`, `openrouter/`, `deepseek/`, `ultra-spark/` | loopback, no tools, no proxy, no redirects, `data_collection: deny` unless the exact model slug is listed under `trainsOnInputs`; refuses OpenAI slugs; `endpoints` pins OpenRouter endpoints; records the model and endpoint that served |
| `egemma` | Gemma through [eGemma](https://github.com/mirzahusadzic/egemma)'s `/judge` | loopback, no persona, no cache, paced to `GET /rate-limits`; caps time, tokens and bytes; records `model` and `revision`; optional frame pins are enforced |
| `local-json` | any evaluator on this machine that answers JSON, at `battery.url` | loopback, no proxy, no redirects, no credentials; a whole-call deadline (`timeout`) and a size cap; records what the evaluator says served |
| `tendora` | [Tendora](https://github.com/mirzahusadzic/tendora)'s engine server, at `battery.url`, asked again against the trial's statements | loopback, no proxy, no redirects, no credentials; read-only on the engine's side; a whole-call deadline and a size cap; records the engine's version, revision and packs |
| your own | an evaluation engine, deterministic rule, or local system | yours; the class's `name` is the frame's `battery.kind`; a battery never sees the trial id |

#### Addresses and keys

Each shipped battery finds its service and its key on this machine:

- **`egemma`:** `EGEMMA_URL`, by default `http://127.0.0.1:8000`, and the key
  from the file named by `EGEMMA_API_KEY_FILE`, else `EGEMMA_API_KEY`, else
  `WORKBENCH_API_KEY`.
- **`unified`:** the router at `http://127.0.0.1:18766`, and its token from
  `CODEX_ROUTER_TOKEN`, else the router's own settings file.
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
`limited` and `needs-reading`, always.

#### Privacy and routing

The shipped batteries keep these promises, and a battery of your own owns its
consent, retention, credential and recording rules.

| Promise | `unified` | `egemma` | `local-json` | `tendora` | your own |
|---|---|---|---|---|---|
| destination | a router on loopback over plain HTTP | eGemma on loopback over plain HTTP | `battery.url` on loopback over plain HTTP | the engine server at `battery.url`, on loopback over plain HTTP | unknown |
| proxy | disabled in the opener | disabled in the opener | disabled in the opener | disabled in the opener | unknown |
| redirects | refused | refused | refused | refused | unknown |
| tools | never sent | no persona or cache fields added | never sent | never sent | unknown |
| provider collection | `data_collection: deny` unless the exact model slug is in `trainsOnInputs` | stays on this machine by contract | stays on this machine | stays on this machine; the engine reads a new text through eGemma unless offline | unknown |
| credentials | router token from environment or its env file; never placed in a request body or record | key from environment/file; sent only as an Authorization header | none sent | none sent | unknown |
| deadline | whole call, `timeout` seconds, even mid-line | whole call, per attempt | whole call, `battery.timeout` (30 s, at most an hour) | whole call, `battery.timeout` (60 s, at most an hour) | unknown |
| verification | model and endpoint recorded when the router reports them | model and revision recorded; frame pins are enforced | what the evaluator reports under `served` | the engine's version, revision and packs, from its reply | unknown |

#### Costs

`Budget.calls` is a hard count of calls, every answer is capped by
`Budget.output_tokens_per_call`, and `Budget.tokens` can cap the output tokens
in all. Input tokens and a provider's prices are outside the budget, so a model
may be slower or cost more than the caps suggest. Run `calls_needed(frame)`
before a live run.

The cap is the whole call's. A battery that writes before it answers reports
every output token it spent in `usage`, so set `--output-tokens`
(`Budget.output_tokens_per_call`) to what a whole call may spend: a call that
reports more stops the run after it. A cap of your own, on money or time,
goes through `run(cancelled=...)`, which is asked before every call.
`run(settle=True)` spends fewer calls: a trial stops once its level can no
longer change, and the verdict reads as it would over every call.

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
runner may leave it empty. A model route records the model the response names
and the provider's endpoint header, when present.

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
            raise ValueError(f"this frame asks for {kind}")

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

---

### Choosing a live quorum

Use `standing.quorum` of at least 3 for a sampled critic, and choose `agree`
before the run. More calls reduce sampling noise, but they do not make a
scorer that follows wording, or reacts to any cut, a valid one. A live run is
evidence from one model and endpoint at one encounter, not a guarantee about
that provider in general.
