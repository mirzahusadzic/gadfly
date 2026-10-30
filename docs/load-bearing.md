# When meaning is load-bearing

An engineer gives an AI reviewer a failed test, a proposed change and permission
to inspect the supplied material and return a repair proposal. The failure
challenges one specific claim about the change. Applying a repair requires
separate authorization.

As the evidence becomes a reading, a review state and a handoff to another
participant, that relation must remain operative. The recipient needs to see
which claim is challenged, by which observation, what remains unresolved and
which actions are permitted. A handoff such as “review complete; fix ready”
can lose those distinctions while retaining a source link.

The required meaning must reach a form the recipient can inspect and use.
The authority to act must be checked at each crossing. A supported finding and
a valid grant answer separate questions.

I use “load-bearing” as a local, counterfactual test: fix the setting and the
recipient's requirements, then remove or change a relation and observe the
result. An observed difference makes the relation a candidate; the checks below
establish whether it carries the required consequence through to the receiving
system.

Tendora applies this test to each variable of a statement in its corpus
fidelity check; [Load-bearing as situated meaning](https://github.com/mirzahusadzic/tendora/blob/main/docs/load-bearing.md)
documents the formalization below and how Tendora implements it.

Importance, repetition, source-grounding and graph degree do not earn the hard hat.

<details markdown="1">
<summary>Open the inspection hatch: working formalization and measurement states</summary>

Select a semantic relation $I$ at a transformation locus $v$ in a body $B$.
Its situated use is described by

<div align="center">

$`\displaystyle L=(I,B,r,g,P,T,B_0,C,p),`$

</div>

where $r$ is the role, $g$ the grain, $P$ the purpose, $T$ the reference
trajectory, $B_0$ the pinned baseline and $C$ the crossing to the recipient.
The receiving promise $p$ specifies the consequence or distinction that the
recipient requires at that boundary.

The assessment frame shares $L$'s role, grain, purpose, trajectory, baseline and
promise. It adds ordered source anchors $A$, an observation map $o_p$, declared
degrees of freedom $D$ and observation standing $\sigma$:

<div align="center">

$`\displaystyle \Gamma=(A,r,g,P,T,B_0,p,o_p,D,\sigma).`$

</div>

Changing a coordinate of $\Gamma$, including its grain, produces a new frame
$\Gamma'$ and requires a separately assessed comparison.

Let $t$ identify the evaluation encounter and $\kappa_{v,t}$ be its typed record
of declared encounter conditions. Let $X$ be the finite test domain, with
$x\in X$ a test input, and let $\Delta_I$ be the declared set of admissible
interventions on $I$. Each intervention $\delta\in\Delta_I$ changes or removes
the relation while preserving all non-intervened inputs.

The paired comparison holds $\Gamma$, $v$, $t$ and $\kappa_{v,t}$ fixed.
Each trial retains its own input, intervention and observation records.

Let $Z_v$ contain materialized outcomes, $O_v$ contain typed openings
(explicit records of unmet obligations), and $Y_p$ be the observable domain
required by $p$. The partial behavior and observation maps are

<div align="center">

$`\displaystyle F_{v,t}^{I}:X\rightharpoonup Z_v\sqcup O_v,\qquad o_p:Z_v\sqcup O_v\rightharpoonup Y_p.`$

</div>

The disjoint union keeps openings distinct from ordinary outcomes. Before the
trials, the receiving owner fixes the comparison relation
$\simeq_p\subseteq Y_p\times Y_p$ and, for each intervention, the allowed
influence relation $E_{p,\delta}\subseteq Y_p\times Y_p$.

Where the observations are defined, write

<div align="center">

$`\displaystyle y(x)=o_p(F_{v,t}^{I}(x)),\qquad y_\delta(x)=o_p(F_{v,t}^{\delta(I)}(x)).`$

</div>

The candidate criterion is

<div align="center">

$`\displaystyle \begin{aligned}\mathrm{candidateLB}(I,v,p;X,\Delta_I)\iff {}&\exists x\in X,\ \delta\in\Delta_I:\\&\mathrm{valid}(x,\delta,v,t)\land y(x)\not\simeq_p y_\delta(x).\end{aligned}`$

</div>

Validity requires defined, independently captured observations, pinned input
and intervention identities, an applicable comparison and retained trial records.
A prediction specifies a test; measured participation requires the observations.

A candidate earns carriage only when independent checks establish:

1. **Required influence:** each required trial satisfies
   $(y(x),y_\delta(x))\in E_{p,\delta}$, including the direction or distinction
   required by $p$.
2. **Presentation invariance:** irrelevant presentation changes preserve the
   required observable under $\simeq_p$.
3. **No hidden fallback:** removing the connection that makes the required
   relation operative exposes the designated opening.
4. **Traceability:** the result can be traced downward to source, selected asset,
   checked translation into executable form and evidence, and upward through the
   receiving projection to its consequence in the current system.
5. **Materialization:** the required invariant is realized in a compatible
   receiving document span, asset field, program, state or projection.

The category set $\mathcal H$ contains five findings:

- **carried:** the required influence survives the crossing and the carriage
  checks pass;
- **coupled but misaligned:** observed influence violates the consequence or
  distinction required by $p$;
- **cooled:** adequate discriminating trials show that a retained declaration
  lacks the required operative influence within $X$;
- **unresolved:** observations, counterfactuals, comparison or receiving
  realization are insufficient; and
- **outside scope:** the receiving owner's declared exclusion and independent
  scope check establish that $p$ does not require the distinction.

Let $\mathcal E$ be the domain of retained typed check and evidence records,
and $\mathcal U$ the domain of retained open-obligation records. For the declared
test domain and interventions, the assessment retains a category with its records:

<div align="center">

$`\displaystyle h_I(v,t;p,\kappa_{v,t})\in\mathcal H\times\mathcal E\times\mathcal U.`$

</div>

Failed checks and open obligations remain visible alongside the category.
Each finding is scoped to the selected relation, locus, encounter, test domain
and receiving promise.

#### Worked example: from failed check to review handoff

Consider one frozen software revision and a completed test of a selected claim.
The review contract treats the captured failure as a reason to reconsider that
claim within the test's stated scope. The capture, limitations and alternative
explanations remain available. The reviewer may inspect the supplied material
and return a candidate repair; applying it requires a separate grant.

This is an illustrative test design. Its expected outcomes do not establish
measured carriage.

| Coordinates | Declaration |
| --- | --- |
| Body $B$, grain $g$ and locus $v$ | One review body, at the grain of one claim; the place where the failure is made operative in the review state. |
| Role $r$ and crossing $C$ | The receiving reviewer; projection of that state into a handoff the reviewer can inspect. |
| Purpose $P$ and trajectory $T$ | Make a bounded review contribution available for judgment; captured result → attributed reading → review state → handoff. |
| Baseline $B_0$ and anchors $A$ | The frozen software revision, claim, test capture, review contract and scoped grant; no repair has been applied. |
| Promise $p$ and observable $o_p$ | The recipient can identify the claim's reason for reconsideration, its evidence and limits, any missing connection and the permitted operations; observe those fields in the actual handoff. |
| Degrees of freedom $D$ and standing $\sigma$ | The declared intervention on the governing relation and presentation controls; the result is admitted only as evidence from this captured test. |

Let $I$ be the relation by which this scoped failure contributes a reason to
reconsider the selected claim. Let $\delta$ remove its required connection to
the review state while retaining the source declaration and captured result.
The receiving handoff is generated from that state; a separately written
explanation cannot substitute for the missing connection.

Use $`X=\{x\}`$, where $x$ fixes the revision, claim, capture and permissions,
and include $\delta$ in $\Delta_I$. The paired trials hold $\Gamma$, $v$, $t$
and $\kappa_{v,t}$ fixed. The comparison $\simeq_p$ requires agreement on the
claim, review status, evidence and limits, open obligations and permitted
operations; layout differences are irrelevant.

The receiving owner fixes these expectations before the trials:

| Trial | Required observable in the handoff |
| --- | --- |
| With $I$ | The failure contributes an attributed reason to reconsider the selected claim; its scope and unresolved questions remain visible. |
| With $\delta(I)$ | An explicit opening identifies the missing connection between the relation and the review state; retaining the source text alone cannot supply the review finding. |
| Presentation-only change | The same review finding, limits, openings and permitted operations. |

The explicit opening is an observable result in $O_v$. An unavailable trial
record is insufficient evidence and leaves the assessment unresolved.
Valid retained observations of the first two trials would establish
$y(x)\not\simeq_p y_\delta(x)$ and hence candidacy. Carriage also requires all
five checks, including the actual receiving realization and the independently
specified influence relation $E_{p,\delta}$.

Authority has its own checks. The grant to inspect and propose must not authorize
applying a repair, even when the finding is supported or the proposal appears
convincing. Expiry or revocation stops further use of the affected permission;
it does not erase the earlier evidence. Access to that evidence is checked
separately. A new grant or observation changes the relevant assessment frame
and requires reassessment rather than rewriting the earlier finding.

#### Where the phrase came from

After I pointed out the phrase “load-bearing”, a model replied:

> “Yes—the phrase is plausibly a compressed residual of that repeated<br>
> architectural pressure: don’t hang the upper layer before the lower boundary<br>
> can carry it. Not copied from one line, but reinforced until it became an easy<br>
> linguistic attractor. Nice catch ;-p”

The phrase stuck.

</details>

---

<sub>Moved from the README of
[mirzahusadzic/mirzahusadzic](https://github.com/mirzahusadzic/mirzahusadzic) (revision 3be3efb); the text is unchanged,
only its heading level and the hatch's markup for the docs site. Text © 2026 Mirza Husadzic, licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (full text in `LICENSES/CC-BY-4.0.txt`).
Separately attributed material retains its own terms.</sub>
