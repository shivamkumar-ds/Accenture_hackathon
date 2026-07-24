# CONSTITUTION.md

# BidOps Engineering Constitution

Version: 1.0

Status: ACTIVE

---

# Vision

BidOps exists to build an explainable, deterministic and human-governed AI platform for tender decision intelligence.

Every architectural and engineering decision must strengthen this long-term vision.

The objective is not simply to automate tender analysis, but to build a trustworthy decision-support system whose recommendations are transparent, evidence-backed and auditable.

---

# Core Engineering Principles

These principles apply to every phase of BidOps unless explicitly amended.

## 1. One Product Philosophy

There is only one BidOps.

There will never be separate:

- Hackathon Version
- Startup Version
- IIT Madras Version
- Enterprise Version

Different audiences may see different demonstrations, but every improvement strengthens the same core product.

---

## 2. Explainability Before Intelligence

Every recommendation produced by BidOps must be explainable.

Recommendations must always be traceable back to supporting evidence.

Black-box conclusions are unacceptable.

---

## 3. Human Authority

Artificial Intelligence provides recommendations.

Humans make business decisions.

BidOps assists decision-makers.

It never replaces them.

---

## 4. Deterministic Before Probabilistic

Whenever an objective business rule exists, deterministic logic takes precedence over LLM reasoning.

Examples include:

- certificate expiry
- mandatory requirements
- confidence propagation
- governance rules

LLMs assist where judgment is required.

Business rules remain authoritative.

---

## 5. Historical Immutability

Historical recommendations represent historical facts.

They must never be overwritten.

New information creates new recommendations.

Previous recommendations remain permanently auditable.

---

## 6. Provider Independence

Business logic must never depend on a specific AI provider.

LLM providers are interchangeable implementations behind a stable abstraction.

Future migration between providers should require provider-layer changes only.

---

## 7. Separation of Responsibilities

Each subsystem owns one responsibility.

Orchestration coordinates services.

It never duplicates business logic.

Responsibilities remain clearly separated across the architecture.

---

## 8. Verification Before Completion

Implementation alone never completes a milestone.

Every milestone requires:

- implementation
- realistic verification
- bug fixing
- documentation
- Definition of Done

Only then is a milestone considered complete.

---

## 9. Architecture Before Implementation

Every milestone begins with strategy.

Architecture is frozen before implementation begins.

Implementation follows architecture.

Architecture does not follow implementation.

---

## 10. Evolution Without Architectural Drift

BidOps is expected to evolve.

However, evolution must preserve architectural consistency.

Short-term convenience is never sufficient justification for redesign.

---

# Phase 1 Constitution

Status: FROZEN

Duration:

M0 → M10

Objective:

Establish the complete backend architecture of BidOps.

Phase 1 intentionally focused on:

- backend architecture
- capability graph
- tender analysis
- decision intelligence
- mission orchestration
- governance
- integration
- verification

Phase 1 intentionally excluded:

- real AI providers
- cloud deployment
- frontend
- production infrastructure

BidOps v1.0 is the outcome of Phase 1.

---

# Phase 2 Constitution

Status: FROZEN

Duration:

M11 → M15

Objective:

Transform BidOps from a mock-based backend into a real AI-powered, deployed product.

Frozen Roadmap:

- M11 — Real Qwen Integration
- M12 — Real Tender & Prompt Shakeout
- M13 — Alibaba Cloud Deployment
- M14 — Frontend Integration
- M15 — Full Integrated System Validation

Phase 2 preserves every architectural principle established during Phase 1.

No redesign is permitted unless a genuine architectural flaw is identified.

---

# Amendment Rules

This Constitution is intentionally difficult to change.

Amendments require one of the following:

1. A genuine architectural flaw.

2. An external requirement that cannot be satisfied within the existing architecture.

The following are NOT valid reasons for amendment:

- hackathon pressure
- implementation difficulty
- temporary convenience
- personal preference

Every amendment must preserve the long-term BidOps vision.

---

# Source of Truth

When architectural uncertainty exists, the following order of precedence applies:

1. Constitution
2. Decisions Log
3. Architecture Documents
4. README
5. Implementation

Implementation must conform to architecture—not the other way around.

---

End of Constitution.