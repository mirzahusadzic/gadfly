# Gadfly

Is a premise **load-bearing**? Declare the relation, its grain and the promise
a recipient needs; Gadfly removes or changes it under fixed interventions, has
a scorer read each trial, and reads the verdict by fixed rules. The method:
[When meaning is load-bearing](https://github.com/mirzahusadzic/mirzahusadzic#when-meaning-is-load-bearing).

```mermaid
---
config:
    layout: elk
    look: neo
    themeVariables:
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif'
    flowchart:
        wrappingWidth: 220
        padding: 20
    themeCSS: >-
        foreignObject { overflow: visible; }
        .node foreignObject, .node foreignObject *, .edgeLabel, .edgeLabel * {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif !important; line-height: 1.5 !important; }
        .node foreignObject, .node foreignObject * { white-space: nowrap !important; }
        .edgeLabel, .edgeLabel p, .edgeLabel span {
        background: transparent !important; }
        .edgeLabel rect { fill: transparent !important; }
        .labelBkg { --knock: var(--vscode-editor-background,
        var(--bgColor-default, rgb(from currentColor
        clamp(30, (128 - r) * 100, 255) clamp(30, (128 - r) * 100, 255)
        clamp(30, (128 - r) * 100, 255)))); --ring: var(--knock);
        --fill: color-mix(in srgb, var(--ring) 30%, var(--knock));
        background: var(--fill) !important; border-radius: 4px;
        box-shadow: 0 0 0 5px var(--fill), 0 0 0 7px var(--ring); }
        .label[data-id^="L_RU_"] .labelBkg { --ring: #2e9e5b; }
        .label[data-id^="L_YOU_"] .labelBkg { --ring: #8e5bd6; }
        .edgeLabel p, .edgeLabel span, .edgeLabel text {
        --halo: var(--fill, var(--vscode-editor-background,
        var(--bgColor-default,
        rgb(from currentColor clamp(0, (128 - r) * 100, 255)
        clamp(0, (128 - r) * 100, 255) clamp(0, (128 - r) * 100, 255)))));
        text-shadow: 1px 0 var(--halo), -1px 0 var(--halo),
        0 1px var(--halo), 0 -1px var(--halo), 1px 1px var(--halo),
        -1px -1px var(--halo), 1px -1px var(--halo), -1px 1px var(--halo),
        0 0 3px var(--halo), 0 0 4px var(--halo); }
---
flowchart TB
    YOU["<b>Your code</b><br/>a frame, a battery,<br/>where records go"]
    subgraph M["This machine"]
        subgraph G["Gadfly: a library, no state"]
            SI["<b>situate</b><br/>check, hash"]
            PL["<b>plan</b><br/>trials from the frame"]
            RU["<b>run</b><br/>the only call out"]
            JU["<b>judge</b><br/>rules over records"]
        end
        ST["<b>Your records</b><br/>file, database, fixture"]
        subgraph B["Batteries: one Protocol"]
            UN["<b>unified</b><br/>an LLM critic"]
            EB["<b>egemma</b><br/>Gemma 4"]
            OW["<b>your own</b><br/>an eval, an engine"]
        end
        RT["<b>Unified router</b><br/>loopback, no tools,<br/>data collection denied"]
        ES["<b>eGemma /judge</b><br/>loopback, no persona,<br/>paced to its budget"]
    end
    PV["<b>Providers</b><br/>Anthropic, OpenRouter, DeepSeek"]

    YOU -->|"frame"| SI --> PL --> RU
    RU -->|"prompt, cap"| B
    UN --> RT --> PV
    EB --> ES
    RU -->|"each record"| ST
    ST --> JU
    JU -->|"finding"| YOU

    classDef default fill:#8a96a82e,stroke:#8a96a8,stroke-width:1px
    classDef person fill:#8e5bd64d,stroke:#8e5bd6,stroke-width:2px
    classDef interface fill:#ffffff40,stroke:#b5bcc6,stroke-width:2px
    classDef service fill:#e3a0084d,stroke:#e3a008,stroke-width:2px
    classDef kept fill:#4d6bfe4d,stroke:#4d6bfe,stroke-width:2px
    classDef engine fill:#2e9e5b4d,stroke:#2e9e5b,stroke-width:2px
    classDef group fill:#8a96a814,stroke:#8a96a8,stroke-width:2px,stroke-dasharray:6 4
    class YOU person
    class SI,PL,RU,JU engine
    class UN,EB,OW interface
    class RT,ES service
    class ST kept
    class M,G,B group
    style OW stroke-dasharray: 5 4
```

```mermaid
---
config:
    layout: elk
    look: neo
    themeVariables:
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif'
    flowchart:
        wrappingWidth: 220
        padding: 20
    themeCSS: >-
        foreignObject { overflow: visible; }
        .node foreignObject, .node foreignObject *, .edgeLabel, .edgeLabel * {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif !important; line-height: 1.5 !important; }
        .node foreignObject, .node foreignObject * { white-space: nowrap !important; }
        .edgeLabel, .edgeLabel p, .edgeLabel span {
        background: transparent !important; }
        .edgeLabel rect { fill: transparent !important; }
        .labelBkg { --knock: var(--vscode-editor-background,
        var(--bgColor-default, rgb(from currentColor
        clamp(30, (128 - r) * 100, 255) clamp(30, (128 - r) * 100, 255)
        clamp(30, (128 - r) * 100, 255)))); --ring: var(--knock);
        --fill: color-mix(in srgb, var(--ring) 30%, var(--knock));
        background: var(--fill) !important; border-radius: 4px;
        box-shadow: 0 0 0 5px var(--fill), 0 0 0 7px var(--ring); }
        .label[data-id^="L_Q"] .labelBkg { --ring: #b5bcc6; }
        .label[data-id^="L_FR_"] .labelBkg { --ring: #8e5bd6; }
        .edgeLabel p, .edgeLabel span, .edgeLabel text {
        --halo: var(--fill, var(--vscode-editor-background,
        var(--bgColor-default,
        rgb(from currentColor clamp(0, (128 - r) * 100, 255)
        clamp(0, (128 - r) * 100, 255) clamp(0, (128 - r) * 100, 255)))));
        text-shadow: 1px 0 var(--halo), -1px 0 var(--halo),
        0 1px var(--halo), 0 -1px var(--halo), 1px 1px var(--halo),
        -1px -1px var(--halo), 1px -1px var(--halo), -1px 1px var(--halo),
        0 0 3px var(--halo), 0 0 4px var(--halo); }
---
flowchart TB
    FR["<b>Frame</b><br/>relation, grain, promise,<br/>anchors, allowed, quorum; hashed"]
    subgraph T["Trials, each read quorum times"]
        BR["<b>baseline, repeat</b><br/>the level"]
        PS["<b>presentation</b><br/>words renamed"]
        AB["<b>ablation</b><br/>anchors removed"]
        SH["<b>sham</b><br/>as much other text"]
        BY["<b>bypass</b><br/>connection cut"]
    end
    Q1{{"agreed, stable?"}}
    Q2{{"wording held,<br/>direction allowed?"}}
    Q3{{"ablation moved it?"}}
    Q4{{"shams held?"}}
    R1["<b>unresolved</b>"]
    R2["<b>coupled but misaligned</b>"]
    R3["<b>cooled</b>"]
    R4["<b>unresolved</b><br/>not specific"]
    R5["<b>carried</b><br/>open checks listed"]
    OS["<b>outside scope</b><br/>only when declared"]

    FR --> T
    FR -.-> OS
    BR --> Q1
    PS --> Q2
    AB --> Q2
    AB --> Q3
    SH --> Q4
    Q1 -->|"yes"| Q2 -->|"yes"| Q3 -->|"yes"| Q4 -->|"yes"| R5
    Q1 -->|"no"| R1
    Q2 -->|"no"| R2
    Q3 -->|"no"| R3
    Q4 -->|"no"| R4
    BY -.->|"left it: open"| R5

    classDef default fill:#8a96a82e,stroke:#8a96a8,stroke-width:1px
    classDef person fill:#8e5bd64d,stroke:#8e5bd6,stroke-width:2px
    classDef interface fill:#ffffff40,stroke:#b5bcc6,stroke-width:2px
    classDef service fill:#e3a0084d,stroke:#e3a008,stroke-width:2px
    classDef kept fill:#4d6bfe4d,stroke:#4d6bfe,stroke-width:2px
    classDef engine fill:#2e9e5b4d,stroke:#2e9e5b,stroke-width:2px
    classDef group fill:#8a96a814,stroke:#8a96a8,stroke-width:2px,stroke-dasharray:6 4
    class FR person
    class BR,AB,SH,PS,BY engine
    class Q1,Q2,Q3,Q4 interface
    class R1,R2,R3,R4,R5,OS default
    class T group
```

## Frame

| Formalization | Field | What you write |
|---|---|---|
| relation $I$, locus $v$, body $B$ | `relation`, `locus`, `body` | the premise, where it acts, the spans it lives in |
| role $r$, grain $g$, purpose $P$ | `role`, `grain`, `purpose` | whose reading, at which unit, for what |
| trajectory $T$, baseline $B_0$ | `trajectory`, `baseline` | the path to the recipient; everything pinned |
| crossing $C$, promise $p$ | `crossing`, `promise` | the boundary, and what must cross it |
| anchors $A$, observation $o_p$ | `anchors`, `observe` | spans the relation rests on; labels (and their order) |
| test domain $X$, interventions $\Delta_I$ | `inputs`, `interventions` | the inputs; the trials below |
| $\simeq_p$, $E_{p,\delta}$ | `observe.labels`, `allowed` | same label, same observation; what ablation may produce |
| standing $\sigma$ | `standing` | `quorum` runs a trial, `agree` for a level, `stable` |

Hashed whole: change any coordinate, the grain included, and it is another frame.

| Trial | Changes | Settles |
|---|---|---|
| `baseline`, `repeat` | nothing | the level, and whether it holds |
| `ablation` | anchors removed | required influence |
| `cumulative` | anchors and what they fell back on | support carried elsewhere |
| `sham` | as much unanchored text, same kind | specificity |
| `presentation` | words renamed consistently | presentation invariance |
| `bypass` | the connection cut | no hidden fallback |

## Use

```python
import json
from pathlib import Path

from examples.refund import RuleReader  # or your own battery
from gadfly.pipeline import calls_needed, judge, run, situate
from gadfly.types import Budget

frame = situate(json.loads(Path("examples/refund.json").read_text()))
kept = []  # your state, kept your way
result = run(frame, RuleReader(), Budget(calls=calls_needed(frame)), on_record=kept.append)
[finding] = judge(frame, kept)
print(finding.category, finding.evidence)
```

| Example | Shows | Calls |
|---|---|---|
| [`refund.py`](examples/refund.py) | presentation tells a phrase matcher (misaligned) from a rule reader (carried) | none |
| [`refund_live.py`](examples/refund_live.py) | the same frame read by a live critic | 21 a model |
| [`after_the_poem.py`](examples/after_the_poem.py) | a study's retained sessions reach every published category ([After the Poem](https://github.com/mirzahusadzic/after-the-poem)) | none |

All three run as tests.

## Batteries

```python
class Battery(Protocol):
    name: str

    def check(self, frame: Frame) -> None: ...  # refuse before any call
    def observe(self, frame: Frame, prompt: str, max_output_tokens: int) -> Observation: ...
```

| Battery | Reads with | Guarantees |
|---|---|---|
| `unified` | an LLM through the [unified model router](https://github.com/mirzahusadzic/codex-unified-model-router): `anthropic/`, `openrouter/`, `deepseek/` | loopback, no tools, `data_collection: deny` unless the frame names the model under `trainsOnInputs`; OpenAI slugs refused (need Codex sign-in) |
| `egemma` | Gemma 4 through [eGemma](https://github.com/mirzahusadzic/egemma)'s `/judge` | loopback, no persona, no cache, paced to `GET /rate-limits` |
| your own | an evaluation, or a deterministic engine (`quorum: 1`) | yours |

Critics answer JSON to a schema, `{"label": ...}` by default. Your own critic
keeps its schema and points at the label:

```json
"battery": {"kind": "unified", "model": "anthropic/claude-sonnet-5-5", "reasoning": "low",
            "output": {"schema": {"type": "object", "properties": {"review": {"type": "object"}}},
                       "label": "/review/verdict"}}
```

## Runs and records

- `run` never starts a call the `Budget` cannot cover, stops between calls on `cancelled()`, and hands each `Record` to `on_record` as it is made.
- A failed or unreadable answer is an opening, never a guessed label.
- `judge` reads only records the plan could have made: this frame, its trials and bodies, runs within the quorum, each once.

## Development

```
uv sync
uv run pytest            # the After the Poem replay runs when GADFLY_ATP_PLANS names its plans
uv run ruff check . && uv run ruff format --check .
```
