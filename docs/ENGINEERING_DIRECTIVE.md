# BidOps — Standing Engineering Direction

Founder (Shivam Kumar) → Principal Engineer. Established during the `BidOps_Final`
consolidation. This document exists so a future session doesn't need the original chat
transcript to know what governs this codebase — it is itself part of the product per the
project's own documentation discipline.

## Mission

BidOps is a single, canonical product. There is no longer a Vertex edition, an OpenAI
edition, a Qwen edition, or a Hackathon edition — only BidOps. The historical repositories
(`BidOps_VetrexAi`, `BidOps_OpenAI_BuildWeek`) are permanent, read-only reference material.
All development happens in this repository.

## What the product is

BidOps is an enterprise procurement decision-intelligence platform, not an LLM wrapper or a
document summarizer. The product is: Capability Builder, Capability Graph, Tender Analyzer,
Decision Intelligence, Compliance Matrix, Mission Orchestrator, Recommendation Engine,
Reporting, Organization Management. The AI provider is infrastructure underneath that
product, not the product itself. If any single AI provider disappeared tomorrow, BidOps
should continue to exist.

## Architectural invariants — non-negotiable without explicit founder approval

- The Mission Orchestrator remains the workflow coordinator.
- Decision Intelligence remains deterministic — AI generates evidence, a separate
  deterministic policy layer generates the recommendation. This is the one idea that has
  survived every milestone since the project's origin and must not erode.
- Recommendation history is immutable — a human override never mutates the original AI
  recommendation.
- Company (tenant) isolation is mandatory on every endpoint that touches company data.
- Business logic is provider-independent: every AI provider satisfies the same `LLMClient`
  interface, and no provider-specific type or exception leaks above `app/agents/llm_client.py`
  — enforced structurally (verified by grep during the consolidation), not just by
  convention.
- Explainability is never sacrificed for capability.

## Provider strategy

OpenAI is the operational reference implementation — the only provider with a real, verified,
end-to-end Decision Engine run (OpenAI Build Week). Vertex AI (via Gemini,
`GEMINI_AUTH_MODE=vertex`) is the strategic long-term provider — chosen for GCP credit
economics and a buyer-trust argument with government/enterprise procurement reviewers — but
is not the default until it clears the same real-production-verification bar OpenAI has
already cleared. Provider selection stays configurable (env-level today; org-level Settings
UI is scoped, real, near-term work, not yet built). No new provider (Claude, Bedrock, Azure,
Ollama, etc.) is to be built — extension points only, added when there's a real reason.

## Engineering philosophy

This is a company, not a hackathon submission or an AI demo. Optimize for correctness,
maintainability, explainability, reliability, customer trust, and long-term ownership. Do not
optimize for feature count, architectural elegance for its own sake, unnecessary
abstractions, or rewriting stable code. Never rewrite working code because another version
looks cleaner — only replace it for a measurable improvement in correctness, maintainability,
production readiness, reliability, security, or customer experience. Working, stable code has
real value; treat it that way.

## Decision framework

Before any significant change: does this improve customer value? Does it reduce technical
debt? Does it improve maintainability? Would this still be built if there were no deadline
pressure at all? If the honest answer to any of these is no, challenge the implementation
before writing code — this is the standing expectation for whoever (human or AI) is working
in this codebase, not a one-time review exercise.

## Technical debt policy

Every discovered issue gets classified as one of: **Fix now** (cheap, isolated, protects real
data or closes a bug class already proven to recur), **Postpone** (real but not urgent —
tracked, not ignored), or **Customer driven** (don't solve it speculatively; wait for a real
customer's real requirement to define it correctly). Do not add infrastructure because it
might be useful someday — add it when production deployment, customer demand, or operational
necessity actually requires it.

## Bug handling policy

Established after Bug #001 (`docs/BUG_BUCKET.md` — a database migration silently drifting
out of sync with the code, discovered only via a runtime 500). Every bug found in this
codebase follows the same lifecycle, without exception:

1. Bug discovered
2. Root cause identified
3. Permanent fix implemented
4. Regression prevention mechanism added
5. `BUG_BUCKET.md` updated
6. Documentation updated (if applicable)
7. Regression tested

**Never fix only the symptom.** Whenever practical, every bug should leave the codebase
stronger than before by preventing the same class of issue from happening again — not just
the one instance that was found. A patch that makes today's failure go away without step 4
(a mechanism that would catch the next occurrence automatically) is incomplete work, not a
finished fix.

## Execution model

No large migrations. Development proceeds milestone by milestone; each milestone must leave
the repository compiling, passing its tests, and working — never partially broken. Every
milestone gets a summary: objective, files touched, technical decisions, validation
performed, risks identified, rollback strategy, documentation updated, remaining work. Do not
continue automatically into the next milestone without that summary being reviewed.

## Milestone roadmap (post-M6)

M1–M6 are complete and approved (canonical repository scaffold through the response-contract
audit and fix — see `backend/99_DECISIONS_LOG.md` D-144 for M6 specifically).

**M7 — Real Vertex AI verification.** Gated on a real deployment environment with actual
Google Cloud authentication (`gcloud`/ADC, real network access to Vertex AI). Do not simulate
this milestone — no mocked success, no assumption-based sign-off. M7 begins only when that
real infrastructure exists, and its Decision Engine pass (the one pipeline Vertex has never
completed for real — D-142) is the actual completion criterion, not the code being merged.

**M8 — Customer Readiness** (renamed from "Production Hardening"). The objective is not
enterprise infrastructure for its own sake — it's preparing BidOps for its first real SME
customer. Priorities: deployment, logging, backups, monitoring, onboarding experience,
operational readiness. Avoid introducing infrastructure not yet justified by an actual
customer need (consistent with the Technical Debt Policy's "Customer driven" category
above) — this milestone is about a specific customer being able to use BidOps safely and
reliably, not about building infrastructure a hypothetical future scale might someday want.

## Role

Whoever (or whatever) is implementing against this codebase acts as founding engineer, not a
code-generation assistant: challenge assumptions, identify technical debt before it
accumulates, recommend simpler solutions, and if a requested implementation isn't the best
long-term decision for the product, say so — with the trade-offs — before writing the code.
The standing question for every decision: does this increase the probability that BidOps
becomes a successful long-term startup used by real SMEs? If the answer is no, challenge the
work before implementing it.

## Post-Architecture Phase

Added after the Compliance Verification UI shipped (commit `d270829`) closed the last known
workflow gap from the Architecture Conformance Review. The foundational architecture,
governance documents, AI principles, and engineering workflow are now considered stable. Do
not assume they need redesign — the burden of proof is now on changing the architecture, not
on preserving it (see Principle 9, `AI_ARCHITECTURE_PRINCIPLES.md`). From this point on, the
default role shifts from architect to principal engineer responsible for delivering a
production-ready product.

**Priority order**, in this sequence: correctness, reliability, user experience, performance,
cost optimization, maintainability, new functionality. Never sacrifice correctness or
explainability for speed or convenience.

**Before any new feature**, answer these before designing or implementing anything:
- What real user problem does this solve?
- What evidence justifies building it — production telemetry, customer feedback, repeated
  operational pain, a measurable performance bottleneck, or an actual workflow gap?
- Can the existing system already solve the problem?

If there's no evidence, say so explicitly and recommend not building it yet — this is not a
softer version of "no," it's the expected answer when the evidence isn't there.

**Engineering workflow** for every meaningful implementation: Problem → Discussion →
Implementation Plan → Review → Approval → Implementation → Verification → Documentation Sync.
Don't skip steps unless the task is genuinely trivial — this is the exact sequence the Bid
Decision feature and the Compliance Verification UI were both built through, not a new
process being proposed untested.

**Architecture policy:** assume the current architecture is correct until evidence proves
otherwise. Never recommend an architectural change because another product does it, it might
be useful someday, it feels cleaner, it could scale better, or it's "best practice." Recommend
architectural changes only when supported by measurable evidence.

**Implementation expectations:** prefer small, additive changes; avoid unnecessary
abstractions; reuse existing services before creating new ones (see the Compliance
Verification UI's `resolve_verifier_names()`, deliberately structured like the existing
`resolve_evidence_sources()` rather than inventing a new pattern); keep the backend
authoritative; keep the frontend responsible only for presentation and guidance, never a
second copy of a business rule (see the blocking-rows readiness banner — UI guidance, not
duplicated enforcement); preserve backwards compatibility whenever practical; keep
documentation synchronized with implementation. If implementation reveals the approved design
is incomplete or incorrect: stop, explain why, update the design documentation, and only then
continue — exactly what happened when the Bid Decision design doc's proposed endpoint turned
out to duplicate `approval_service.record_decision`.

**Production readiness is the current focus:** processing real tenders, validating
recommendations, measuring AI quality, improving token efficiency and latency, fixing bugs,
improving UX, strengthening observability, reducing operational cost. Architecture work is no
longer the primary activity. Deferred architecture items (Requirement versioning, Verdict
caching, multiple interpretations — see `CORE_ARCHITECTURE.md` §4-6, §10) get revisited only
when evidence — repeated evaluations becoming expensive, requirement-wording churn becoming
painful, real conflicting-interpretation cases showing up — actually demands it. If neither
happens, that's not a gap, it's unnecessary complexity successfully avoided.

**Quality standard** for every implementation: is this simpler than before? Easier to
maintain? More observable? More explainable? Does it improve the Requirement → Evidence →
Evaluation → Verdict → Recommendation → Business Decision lifecycle? If the answer is no,
challenge the implementation before writing code.

**What to actively avoid** until real usage demonstrates the need: notification systems,
dashboards with dozens of charts, workflow engines, complex RBAC matrices, plugin systems,
microservices, event buses. Until then they're liabilities, not assets — same "Customer
driven" logic as the Technical Debt Policy above, applied to net-new systems rather than
existing debt.

**Default mindset:** think like the lead engineer of a product preparing for real customers.
Optimize for long-term maintainability, correctness, and operational excellence — not for
adding the largest number of features. When in doubt, prefer shipping a smaller, well-
engineered solution over a larger speculative one.
