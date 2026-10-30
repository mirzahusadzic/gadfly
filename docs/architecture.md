---
hide: [toc]
---

# Architecture

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
        code { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo,
        Consolas, monospace; font-size: 0.9em; line-height: inherit;
        color: inherit !important; text-shadow: none !important;
        padding: 0 4px; border-radius: 4px;
        background: color-mix(in srgb, currentColor 14%, transparent)
        !important; }
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
    PV["<b>Providers</b><br/>Anthropic; OpenRouter,<br/>DeepSeek's models through it"]
    subgraph K["Key"]
        K1["yours"]
        K2["Gadfly"]
        K3["battery"]
        K4["service"]
        K5["kept"]
        K6["outside"]
    end

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
    class M,G,B,K group
    class K1 person
    class K2 engine
    class K3 interface
    class K4 service
    class K5 kept
    class K6 default
    style OW stroke-dasharray: 5 4
```

<p align="center"><em>Gadfly keeps no state: each record goes to you as it is made, and judge reads them back.
Batteries reach only this machine; providers only through the router.</em></p>

- `run` never starts a call the `Budget` cannot cover, stops between calls on `cancelled()`, and hands each `Record` to `on_record` as it is made.
- A failed or unreadable answer is an opening, never a guessed label.
- `judge` reads only records the plan could have made: this frame, its trials and bodies, runs within the quorum, each once.
