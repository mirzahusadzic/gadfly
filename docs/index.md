<div class="gadfly-hero" markdown>

# Is the premise load-bearing?

**Gadfly removes or changes one declared relation, asks a scorer to read each
trial, and returns one fixed-rule verdict.** It is a small Python library with
no runtime dependencies and no hidden state.

[Test your first frame](first-frame.md){ .md-button .md-button--primary }
[Read the essay](load-bearing.md){ .md-button }

</div>

## Choose your path

<div class="grid cards" markdown>

-   **I have a rule to test**

    ---

    A policy clause, prompt line, citation, permission or code invariant.
    Start with [Your first frame](first-frame.md).

-   **I have read the essay**

    ---

    Translate $L$ and $\Gamma$ into frame keys, interventions and records.
    Start with [Framework](framework.md).

-   **I have two minutes**

    ---

    Gadfly returns one of five categories, not a score. Read [Reading a verdict](reading-a-verdict.md),
    then decide from the examples whether that vocabulary fits your question.

</div>

## What a result looks like

This is the deterministic refund example: two batteries read the same relation.

```text
$ python examples/refund.py records.jsonl
phrase-matcher: coupled but misaligned
  presentation moved it decline -> grant
  no hidden fallback: bypass gave decline, not the designated opening (unclear)
rule-reader: carried
  ablation moved it decline -> grant; held under presentation, 2 shams
```

The category answers a narrow question. The evidence says why. An obligation
says what is still open: here the phrase matcher keeps declining with the
rules' binding line cut. The rule reader has nothing left open: carried.

--8<-- "README.md:verdicts"

## Install

```bash
git clone https://github.com/mirzahusadzic/gadfly.git
cd gadfly
uv sync
uv run python examples/refund.py refund-records.jsonl
```

## Where to go next

| If you want to... | Read |
|---|---|
| write and validate a frame | [Write a frame](write-a-frame.md) |
| choose trials and estimate calls | [Interventions](interventions.md) |
| understand evidence and obligations | [Reading a verdict](reading-a-verdict.md) |
| use a model, local service or your own scorer | [Batteries](batteries.md) |
| see the method on other relations | [Examples](examples.md) |
| run, report and check frames from the command line | [Extending Gadfly](roadmap.md) |
| see the trust boundaries and current limits | [Architecture and limits](architecture.md) |
| find a library name | [Reference](reference.md) |

