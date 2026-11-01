# The local-json battery

It replaces copy-pasted loopback HTTP code for local evaluators that already
expose a JSON `judge` endpoint.

---

### Need

`unified` reaches cloud providers through a router, and `egemma` is specific
to one service's wire format. A team with a local classifier, test oracle or
retrieval checker should not have to rebuild loopback validation, no-proxy,
redirect refusal, deadlines, response caps, label pointers and provenance.

---

### Interface

A frame names the evaluator's address, its deadline and where the label lives
in its answer:

```json
{
  "battery": {
    "kind": "local-json",
    "url": "http://127.0.0.1:8765/judge",
    "timeout": 30,
    "output": {"schema": {"type": "object"}, "label": "/verdict"}
  }
}
```

The public class is `midwife.batteries.local_json.LocalJSON`.

#### The request

The request is fixed, with no headers or tools of the frame's choosing:

```json
{
  "instructions": "<frame.observe.instruction>",
  "input": "<exact Gadfly prompt>",
  "schema": {"type": "object"},
  "max_tokens": 64
}
```

#### The response

The evaluator answers with the parsed answer, its text, its usage and what
served it:

```json
{
  "answer": {"verdict": "decline"},
  "text": "{\"verdict\":\"decline\"}",
  "usage": {"output_tokens": 7},
  "served": "local-classifier@r3"
}
```

`usage.output_tokens` is every output token the call spent, the evaluator's
own drafting included. A run stops after a call that reports more than its
cap, so set `--output-tokens` to what a whole call may spend.

---

### Contracts

- only plain `http` URLs whose parsed host is `127.0.0.1`, `localhost` or `::1`;
- no environment proxy and no redirects, reusing `critic.opener()`;
- one whole-call deadline and the same read-back size cap as the shipped batteries;
- `check` validates `kind`, URL, timeout, schema pointer and keys before a call;
- `observe` returns an opening for a transport failure, a reply that is not
  JSON, or an answer whose label pointer finds no label of the frame; the
  rest of the answer is held to its schema by the evaluator, not here;
- no credentials in the frame; a deployment that needs auth should provide a
  separate battery with an explicit credential contract;
- records use the existing `Observation` and `Record` fields, including `served`.

---

### Tests

The request is the easy part; the tests are the negative ones: an address off
this machine, a proxy in the environment, a redirect, an unreachable evaluator,
a deadline passed, replies that are not JSON or not an object, an answer outside
the frame's labels, and no credentials in any request.

