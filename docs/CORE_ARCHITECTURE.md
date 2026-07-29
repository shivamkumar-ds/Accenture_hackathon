# BidOps — Core Architecture

Status: **Reference document, not implemented.** Captures the architectural conclusions reached across an extended design discussion. Nothing here has been built; this is the target model future work is evaluated against.

## 1. Core Philosophy

BidOps is a decision-support system, not a decision-making one. Every design choice follows from four commitments, held since the project's earliest work and reaffirmed repeatedly across this discussion:

- **Evidence-first.** No conclusion is presented without a traceable link back to a specific requirement, a specific piece of evidence, and a specific reasoning step. Confidence is never asserted without a defined, computable basis.
- **Human-in-the-loop.** The AI advises; a human decides. This applies at every layer, not just the final business call — individual verdicts can be overridden by a human, not only the aggregate recommendation.
- **AI is a scarce resource.** An LLM call must solve something deterministic logic cannot, materially improve quality, create measurable value, or improve trust through better explanation. If none apply, it doesn't get called.
- **Never hide uncertainty.** When the source material is genuinely ambiguous or self-contradictory, the system surfaces the conflict rather than silently picking one interpretation.

## 2. The Atomic Object

Everything in the system is built from one lifecycle:

```
Requirement → Evidence → Evaluation → Verdict
```

- **Requirement** — an atomic claim extracted from a tender (e.g. "must hold ISO 9001"), with source page, type, and mandatory flag.
- **Evidence** — a piece of proof that may satisfy the requirement, drawn from the company's Capability Graph, with its own freshness/staleness state.
- **Evaluation** — the process connecting the two, decomposed into sub-checks. Some sub-checks are deterministic (does the certificate's expiry date pass; is the requirement's date field even present), some require genuine judgment (does this evidence semantically satisfy this clause's specific wording). This separation is what makes the deterministic-vs-LLM principle apply *inside* a single verdict, not just across the pipeline.
- **Verdict** — the output of Evaluation: met / not_met / conditional / review_required, with a risk level and a reasoning trace built from the sub-checks that produced it.

Everything else in the product is derived from this lifecycle, not a competing center:

- **Decision** aggregates Verdicts into a Go/No-Go recommendation.
- **Readiness** is a pure aggregate function over Verdicts (percentage of mandatory Verdicts that are `met`) — a view, not a separate computation.
- **Risk** is an attribute of a Verdict, not an independent entity.
- **Capability Graph** is the structured source Evidence is drawn from.
- **Audit trail / explainability** is the reasoning trace already attached to each Verdict, surfaced rather than regenerated.
- **Outcome tracking** references Verdicts (and, at finer grain, individual Verdicts within a Decision) to record what actually happened.

A useful working analogy: this pipeline behaves like a compiler front-end (extract structure, refuse to silently discard information, surface ambiguity rather than guess) more than a chatbot. The analogy explains the discipline; it should not be read as a claim that tender language is fully formalizable the way a programming grammar is. Real, irreducible ambiguity exists and will always require a human, not a better parser.

## 3. Architectural Principles

1. **AI is a scarce resource.** Never call an LLM where deterministic logic, already-computed facts, or existing structured data would answer the question.
2. **Intelligence should compound.** Every AI operation should ideally produce a reusable organizational asset (e.g. a Capability record usable across hundreds of future tenders), not a one-time inference thrown away after use.
3. **Reason once. Reuse while the underlying evidence remains valid. Recompute automatically when evidence changes.** Not "reuse indefinitely" — every reusable artifact needs a source reference, a version/hash, a generated timestamp, and an invalidation trigger, or reuse silently becomes staleness.
4. **Separate knowledge from reasoning.** Facts come from structured extraction, deterministic rules, or verified sources. The AI's reasoning budget is spent only on genuine judgment calls (does this evidence satisfy this requirement), never on rediscovering facts a database or a regex already has.
5. **Recommendation quality is sacred.** Cost optimization is acceptable everywhere except compliance matching and capability evaluation — the credibility of the whole product rests there. A 40% cost saving that measurably degrades match quality is rejected outright.
6. **Product value should compound.** The long-term moat is not prompts or model choice, it's the accumulated Capability Graph, Requirement/Evidence/Verdict history, and (eventually) real outcomes — assets that get more valuable the longer a customer stays and are not portable to a competitor on day one.
7. **Every feature must strengthen the moat, or it doesn't belong.** Before adding anything, ask whether it improves recommendation quality, retention, organizational knowledge, operational efficiency, explainability, trust, or differentiation. If none, it's scope creep.
8. **Every AI conclusion must be traceable.** Every Verdict must be able to answer "why": which requirement, which evidence, which sub-check, what confidence. Not chain-of-thought — evidence.

**Working test for any future feature: does it enrich the Requirement → Evidence → Evaluation → Verdict lifecycle? If yes, it belongs. If not, it's probably scope creep** — even if it sounds compelling in isolation.

## 4. Versioning

A Requirement is not immutable. Indian government tenders are routinely amended by corrigenda that change eligibility thresholds, dates, and quantities — a gap identified early in this project's own competitive research and never resolved. Under this architecture, a Requirement has a stable identity that can carry multiple versions (original NIT wording, corrigendum-amended wording), with old versions marked superseded. Any Verdict computed against a superseded Requirement version is automatically flagged stale, propagating downstream without a separate invalidation mechanism having to be built for every consumer.

## 5. Multiple Interpretations

When a tender's summary and its detailed annexure state conflicting values for the same requirement — a real, documented drafting pattern in Indian tenders, and a named feature ("Contradiction Finder") that at least one direct competitor already markets — the system does not silently pick one reading. Instead, a Requirement can carry multiple candidate interpretations, each producing its own Verdict, with the disagreement surfaced explicitly for a human to resolve. This is the same discipline as principle 8, applied to the input side rather than the output side: don't hide uncertainty, whichever direction it comes from.

## 6. Caching Strategy

Cache at the level of the atomic object, not the document. A Verdict is cached keyed on (requirement-pattern hash, evidence hash, **evaluation logic version**) — not on the tender document as a whole. Government tenders from the same department frequently reuse near-identical requirement templates; once a Verdict has been computed for "does this company hold ISO 9001" against the company's current evidence, a structurally similar requirement appearing in a different tender should reuse that Verdict rather than trigger fresh reasoning.

The evaluation-logic-version component is not optional. Without it, improving the matching prompt or algorithm would silently continue serving Verdicts reasoned under the old logic — a correctness bug, not a performance tradeoff, and exactly the staleness failure mode Principle 3 exists to prevent, one layer deeper than where it was first defined. Any change to how Evaluation reasons bumps the version and invalidates affected cache entries.

## 7. Human-in-the-Loop

Override exists at two layers, not one. At the atomic layer, a human can verify or reject an individual Verdict — this already exists in the product today. At the aggregate layer, a human makes the final Business Decision (Proceed / Rejected / Needs Changes) informed by, but never overridden by, an AI-generated verdict on the whole. The AI never issues a submit/don't-submit recommendation — only a diagnostic readiness state built from real, countable facts.

## 8. AI Boundaries

The LLM is used only for the genuine judgment sub-check inside Evaluation (does this evidence semantically satisfy this specific requirement's wording) and for summarizing already-computed structured results into an executive summary. It is not used to: guess at deterministic facts (dates, amounts, registration numbers — regex-extractable); invent categories the pipeline has no data to support (commercial, legal, competitive, or strategic advice — nothing in the system analyzes any of these); or issue a submission verdict. Confidence and readiness numbers shown to a user must map to one specific, named, computable statistic — never a blended or invented composite.

## 9. Non-Core Components

Explicitly peripheral to the atomic object, useful but not architecturally central, and should not receive investment disproportionate to their role:

- Tender metadata pre-fill (name/organization/date auto-guess) — a UX convenience, touches nothing in the Requirement-Evidence-Verdict lifecycle.
- Model tier routing (cheap vs. premium model per task) — an implementation cost decision, not a domain concept.
- External enrichment (Udyam verification, government circulars, portal metadata) — optional, and correctly modeled as either a new source of Evidence or added context on a Requirement's interpretation, never a hard dependency. Core BidOps must remain 100% functional if every external source disappears.

## 10. Future Extensions (Not Yet Designed, Not Yet Approved)

- **Decision rationale capture**, embedded into the existing Business Decision moment (structured assumptions/rationale fields, not a separate journaling module) — validated as a real but modest, currently-unclaimed niche within the existing product category, not a new category.
- **Per-Verdict outcome attribution** — recording which specific gap actually mattered to a real win/loss, not just a whole-decision note.
- **Udyam registration verification** — the one external integration with a solid, trustworthy, purpose-built API foundation confirmed by research; low AI cost, direct UX value.
- **Requirement composite structure** (constraint / condition / context / priority) — directionally correct, exact schema to be validated against real extracted requirements before being frozen.
- **Claim as a pre-classification step** (Claim → Classify → Requirement) — extraction currently assumes every extracted clause is already a Requirement. A more honest sequence treats extraction as producing unclassified Claims first, only some of which become Requirements — opening the door to modeling other clause types (payment terms, penalties, deliverables) the pipeline currently discards. Worth exploring once real tender variety justifies it, not adopting now.
- **Evaluation as its own sub-engine** (deterministic checks / semantic checks / policy checks / human review, as distinct stages) — a plausible future shape once evidence source variety genuinely grows beyond the current five capability types. Do not pre-build this structure for hypothetical scale; let it emerge from real evaluation types that actually recur.
- **Business-decision factors** (financial worth, execution capacity, customer relationship, risk appetite) are explicitly out of the Requirement-Evidence-Verdict engine — they are not evidence-evaluable claims. They belong as human-authored rationale captured at the Business Decision layer (see Bid Decision design), never scored or modeled by AI.
- Still unresolved, pending manual verification, not assumption: whether GeM/CPPP data access is stable and ToS-compliant enough to build on.
