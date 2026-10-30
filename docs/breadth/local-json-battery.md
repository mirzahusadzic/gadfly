# Proposal: a `local-json` battery

**Priority:** medium. **Effort:** medium. **Replaces:** copy-pasted loopback
HTTP code for local evaluators that already expose a JSON `judge` endpoint.

## Need

`unified` reaches cloud providers through a router. `egemma` is specific to one
service's wire format. A team with a local classifier, test oracle or retrieval
checker should not have to reimplement loopback validation, no-proxy, redirect
refusal, deadlines, response caps, label pointers and provenance.

## Interface

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

Public class: `gadfly.batteries.local_json.LocalJSON`.

Request (fixed, no arbitrary headers or tools):

```json
{
  "instructions": "<frame.observe.instruction>",
  "input": "<exact Gadfly prompt>",
  "schema": {"type": "object"},
  "max_tokens": 64
}
```

Response:

```json
{
  "answer": {"verdict": "decline"},
  "text": "{\"verdict\":\"decline\"}",
  "usage": {"output_tokens": 7},
  "served": "local-classifier@r3"
}
```

## Contracts

- only plain `http` URLs whose parsed host is `127.0.0.1`, `localhost` or `::1`;
- no environment proxy and no redirects, reusing `critic.opener()`;
- one whole-call deadline and the same read-back size cap as the shipped batteries;
- `check` validates `kind`, URL, timeout, schema pointer and keys before a call;
- `observe` returns an opening for transport failure or invalid JSON/schema;
- no credentials in the frame; a deployment that needs auth should provide a
  separate battery with an explicit credential contract;
- records use the existing `Observation` and `Record` fields, including `served`.

## Cost

About 180 lines including the HTTP adapter and tests. The difficult work is not
the request: it is the negative tests for proxy, redirect, loopback DNS, deadline,
oversized and malformed replies, and secret-free records.

