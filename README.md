# Gadfly

Gadfly tests whether a premise is **load-bearing**: you situate a relation (its
grain, scope and the promise a recipient needs), Gadfly removes or changes it
under declared interventions, runs a scorer, and reads the result by fixed
rules. It never reasons about the content itself.

The method is the counterfactual load-bearing test formalized in
[When meaning is load-bearing](https://github.com/mirzahusadzic/mirzahusadzic#when-meaning-is-load-bearing):
fix the setting and the recipient's requirements, remove or change a relation,
observe. An observed difference makes the relation a candidate; independent
checks decide whether it is carried.

> Status: design. Nothing here runs yet.

## The formulation you declare

| README | Gadfly field | What you write |
|---|---|---|
| relation $I$ at locus $v$ in body $B$ | `relation`, `locus`, `body` | the premise under test, where it acts, and the material it lives in |
| role $r$, grain $g$, purpose $P$ | `role`, `grain`, `purpose` | whose reading, at which unit (a line, a claim, a span), for what |
| trajectory $T$, baseline $B_0$ | `trajectory`, `baseline` | the path from body to recipient; everything pinned (hashes, versions, models) |
| crossing $C$, promise $p$ | `crossing`, `promise` | the boundary to the recipient and the distinction it must receive |
| anchors $A$, observation map $o_p$ | `anchors`, `observe` | the source spans the relation rests on; how a scorer's output becomes the observable |
| test domain $X$, interventions $\Delta_I$ | `inputs`, `interventions` | the finite inputs; the admissible changes to the relation |
| $\simeq_p$, $E_{p,\delta}$ | `same`, `allowed` | when two observations count as the same; the influence each intervention may have |
| standing $\sigma$ | `standing` | how far an observation counts (quorum, independent capture) |

The whole frame is hashed before any trial runs. Changing any coordinate,
the grain included, makes a new frame that is assessed separately.

## The internals

| Intervention | What changes | What it can show |
|---|---|---|
| `baseline` | nothing | the observation the others are compared with |
| `repeat` | nothing, fresh run | whether the scorer is stable enough to read (stochastic scorers need a quorum) |
| `presentation` | the domain's distinctive words masked or renamed consistently | presentation invariance (carriage check 2) |
| `ablation` | the anchors removed | required influence (check 1) |
| `cumulative ablation` | the anchors and what the first ablation fell back on | whether support is carried elsewhere |
| `sham` | spans of the same size and kind, not cited, removed | specificity: an effect from any removal is not this relation's |
| `bypass` | the connection that makes the relation operative removed | no hidden fallback (check 3): the designated opening must appear |

Verdicts, in order (the README's five categories): **unresolved** when there is
no quorum, repeat differs, or a sham moves it; **coupled but misaligned** when
presentation changes it or ablation moves it the wrong way; **cooled** when
adequate trials show no operative influence; **carried** when the required
influence holds and the carriage checks pass; **outside scope** only by the
recipient's declared exclusion, never inferred. Each finding keeps its
category, its evidence records and its open obligations.

## Batteries (scorers)

A battery runs the body, with or without an intervention, and returns an
outcome or a typed opening. Gadfly orchestrates; the battery observes.

| Battery | Scorer | Kind |
|---|---|---|
| `router-critic` (first) | an LLM critic through the [unified model router](https://github.com/mirzahusadzic/codex-unified-model-router) (`POST /v1/responses` on loopback; any routed slug, Claude on Anthropic's API included) | stochastic: quorum per trial, a cost cap per trial and per frame |
| later | a project's own evaluation (a rubric reader, a prompt pack's eval gate) | stochastic |
| later | a deterministic engine (Tendora: corpus as body, a statement as relation) | deterministic: one run per trial; repeat is its determinism check |

A frame names the models it may send its body to. A model whose provider trains
on its inputs must be named as such in the frame; Gadfly refuses to send a body
there otherwise. The critic sends no tools: through the router, Claude runs on
Anthropic's API, but its web search runs elsewhere (OpenRouter, Exa), so a body
would leave Anthropic. A frame that wants search says so, and names that route.

## Records

Every trial keeps its input, intervention, scorer call (model, parameters,
cost) and observation, beside the frame hash. A verdict is recomputed from the
records without new calls.
