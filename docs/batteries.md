# Batteries

A battery is the scorer in a trial. Gadfly passes it the frame and the exact
prompt for one call; it returns one `Observation`: a declared label or a typed
opening. It is deliberately not told which trial produced the prompt.

## Start with your own deterministic battery

A deterministic scorer costs no provider tokens and makes the frame mechanics
visible. The smallest useful shape is:

```python
from gadfly.types import Observation

class CitationReader:
    name = "citation-reader"

    def check(self, frame):
        if frame.battery["kind"] != self.name:
            raise ValueError(f"this frame asks for {frame.battery['kind']}")

    def observe(self, frame, prompt, max_output_tokens):
        body, _, question = prompt.partition("\n\n---\n\n")
        if "Source S-2:" in body:
            return Observation(label="grounded")
        return Observation(label="ungrounded")
```

Use `check` to refuse a foreign battery kind, a missing model or any frame the
battery cannot safely serve. `run` calls `check` once before the first call, so a
refusal spends nothing.

<!-- copy README.md:protocol -->
```python
class Battery(Protocol):
    name: str

    def check(self, frame: Frame) -> None: ...  # refuse before any call
    def observe(self, frame: Frame, prompt: str, max_output_tokens: int) -> Observation: ...
```
<!-- end copy -->

The protocol's important invariant is **trial blindness**. A battery sees the
intervened body and input, not `baseline`, `sham-1` or `ablation`. If a scorer
could branch on the trial id, the comparison would be cued.

## Shipped critic batteries

<!-- copy README.md:batteries -->
| Battery | Reads with | Guarantees and recorded provenance |
|---|---|---|
| your own | an evaluation engine, deterministic rule, or local system | yours; the class's `name` is the frame's `battery.kind`; a battery never sees the trial id |
| `unified` | an LLM through the unified model router: `anthropic/`, `openrouter/`, `deepseek/`, `ultra-spark/` | loopback, no tools, no proxy, no redirects, `data_collection: deny` unless the exact model slug is listed under `trainsOnInputs`; refuses OpenAI slugs; `endpoints` pins OpenRouter endpoints; records the model and endpoint that served |
| `egemma` | Gemma through eGemma's `/judge` | loopback, no persona, no cache, paced to `GET /rate-limits`; caps time, tokens and bytes; records `model` and `revision`; optional frame pins are enforced |
| `local-json` | any evaluator on this machine that answers JSON, at `battery.url` | loopback, no proxy, no redirects, no credentials; a whole-call deadline (`timeout`) and a size cap; records what the evaluator says served |

The privacy and routing guarantees above belong to the shipped batteries.
The `Battery` protocol does not constrain arbitrary third-party code.
<!-- end copy -->

Both critics ask for JSON in a schema. The default is `{"label": ...}`. A critic
that already has its own answer shape keeps that shape and names where the label
lives with a JSON pointer.

<!-- copy README.md:adapter -->
Critics answer JSON to a schema, by default `{"label": <one of the frame's labels>}`.
A critic with its own schema names where the label lives with a JSON pointer:

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
<!-- end copy -->

### Costs

Every call is capped by `Budget.output_tokens_per_call`; `Budget.calls` is a hard
call count and `Budget.tokens` can add an output-token ceiling. The model may be
slower or cost more than the cap suggests because input tokens and provider
pricing are outside Gadfly's budget. Use `calls_needed(frame)` before a live run.

### Privacy and routing

| Promise | `unified` | `egemma` | `local-json` | your own |
|---|---|---|---|---|
| destination | a router on loopback over plain HTTP | eGemma on loopback over plain HTTP | `battery.url` on loopback over plain HTTP | unknown |
| proxy | disabled in the opener | disabled in the opener | disabled in the opener | unknown |
| redirects | refused | refused | refused | unknown |
| tools | never sent | no persona or cache fields added | never sent | unknown |
| provider collection | `data_collection: deny` unless the exact model slug is in `trainsOnInputs` | stays on this machine by contract | stays on this machine | unknown |
| credentials | router token from environment or its env file; never placed in a request body or record | key from environment/file; sent only as an Authorization header | none sent | unknown |
| deadline | whole call, `timeout` seconds, even mid-line | whole call, per attempt | whole call, `battery.timeout` (30 s) | unknown |
| verification | model and endpoint recorded when the router reports them | model and revision recorded; frame pins are enforced | what the evaluator reports under `served` | unknown |

These are guarantees of the shipped batteries, not of the Protocol. If you
write a battery that calls a cloud service, your battery owns its consent,
retention, credential and recording rules.

### Failure convention

`observe()` should return an opening for an unreadable answer or transport
failure; the shipped batteries do, keeping what arrived before the failure. The
pipeline turns an unexpected exception into an opening too, but the direct
battery API should not require that safety net. In particular, a timeout must
not be converted into a label or silently dropped.

## Your evaluator, without an adapter

A local classifier, test oracle or retrieval checker that already reads an
instruction and a text and answers JSON needs no battery of its own; see
[Local JSON battery](breadth/local-json-battery.md).

## Record provenance

Every `Record` names:

```text
frame hash, input id, trial id, quorum index, body hash, prompt hash,
battery name, observation or opening, raw answer prefix, usage, served
```

`served` is as the service reports it, not a trust statement. A local runner can
leave it empty. A model route records the model response value and provider
endpoint header when present.

## Choosing a live quorum

Use `standing.quorum >= 3` for a sampled critic and choose `agree` before the run.
More calls reduce sampling noise but do not turn a presentation-sensitive or
non-specific scorer into a valid one. A live run is evidence from a model and
endpoint at one encounter, not a guarantee about that provider in general.

