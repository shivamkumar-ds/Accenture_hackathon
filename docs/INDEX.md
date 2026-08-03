# Documentation Index

Phase 1.5 finding #16. 24 files have accumulated in `docs/` (plus
`backend/99_DECISIONS_LOG.md`, `BACKLOG.md`, and the three READMEs)
across design discussions, audits, and shipped features. This maps each
to what it actually is today, so a new session doesn't have to open all
of them to find out.

## Frozen / governing — read these first

The documents that currently govern the codebase. Changing anything
here requires the workflow in `ENGINEERING_DIRECTIVE.md` §"Post-
Architecture Phase" (Discussion → Implementation Plan → Review →
Approval), not a routine edit.

| Doc | What it governs |
|---|---|
| `ENGINEERING_DIRECTIVE.md` | The standing engineering direction — mission, architectural invariants, provider strategy, technical debt policy, Post-Architecture Phase workflow. Start here. |
| `AI_ARCHITECTURE_PRINCIPLES.md` | 9-principle governance checklist for evaluating any new AI feature before it's designed. |
| `CORE_ARCHITECTURE.md` | Target architectural model (Requirement → Evidence → Verdict → Recommendation lifecycle) that future work is evaluated against. |
| `PRODUCT_CONSTITUTION.md` | Founding product principles — explicitly a *working* constitution pending customer validation, not yet frozen. |
| `DESIGN_SYSTEM.md` | Frozen v1.0 visual/interaction design principles, with one recorded amendment (D-147). |
| `API_CONTRACTS.md` | Developer reference for core endpoints — companion to the live OpenAPI spec, not a replacement for it. |
| `KNOWN_LIMITATIONS.md` | What BidOps deliberately doesn't do yet, and why — check before treating a gap as a bug. |
| `DEPLOYMENT.md` | How BidOps runs today and the rate-limiter constraint to resolve before scaling horizontally. |
| `PRODUCTION_FINDINGS.md` | Live validation backlog/log for real-tender dogfooding — the evidence source Principle 9 requires before any new architecture discussion. |
| `BUG_BUCKET.md` | Permanent, append-only log of production-affecting/development-blocking bugs — what happened, root cause, fix, and the prevention mechanism now in place. |
| `../BACKLOG.md` | Carried-forward unresolved items. |
| `../backend/99_DECISIONS_LOG.md` | Full chronological engineering decisions log (D-101 onward). |

## Historical / superseded

Original MVP planning docs (`00_Project_Context.md` through
`11_Risk_Assessment.md`) — the project's early-stage vision, PRD, and
architecture drafts. Superseded by `CORE_ARCHITECTURE.md` and
`AI_ARCHITECTURE_PRINCIPLES.md` for anything architectural; kept as
historical record of the project's origin, not as current direction.
Do not treat these as authoritative if they conflict with a frozen/
governing doc above.

| Doc | Original scope |
|---|---|
| `00_Project_Context.md` | Purpose & early design decisions |
| `01_Vision.md` | Executive vision |
| `02_Product_Requirements_Document.md` | Original PRD |
| `03_Software_Architecture.md` | Original architecture draft |
| `04_System_Design.md` | Original system design |
| `05_Database_Design.md` | Original database design |
| `06_API_Design.md` | Original API design |
| `07_AI_Agent_Architecture.md` | Original AI agent architecture |
| `08_User_Workflows.md` | Original user workflows |
| `09_MVP_Roadmap.md` | Original MVP roadmap |
| `10_Future_Roadmap.md` | Original future roadmap |
| `11_Risk_Assessment.md` | Original risk assessment |

## Feature-specific

Design/implementation records for individual shipped features — useful
when working on that feature again, not general-purpose reference.

| Doc | Feature |
|---|---|
| `BID_DECISION_DESIGN.md` | Bid Decision feature design note |
| `COMPLIANCE_VERIFICATION_UI_NOTE.md` | Compliance Verification UI design note |
| `COMPLIANCE_VERIFICATION_UI_IMPLEMENTATION_PLAN.md` | Compliance Verification UI implementation plan |
| `TENDER_JOURNEY_DESIGN.md` | Tender Journey & Business Decision experience design (frozen, implemented) — the frontend product philosophy for the mission lifecycle |
| `TENDER_JOURNEY_IMPLEMENTATION_PLAN.md` | Tender Journey implementation plan (implemented — all 7 phases complete) — derived from the design doc above |
| `TENDER_JOURNEY_DEFERRED_ENHANCEMENTS.md` | Append-only log of ideas/interpretations that surfaced during the 7-phase implementation but weren't built, per its own scope-discipline rule |
| `TENDER_ASSESSMENT_REDESIGN.md` | Tender Assessment information architecture redesign (frozen, implemented) — supersedes `TENDER_JOURNEY_DESIGN.md` §3's page hierarchy specifically, after using the finished implementation end to end |
| `TENDER_ASSESSMENT_IMPLEMENTATION_PLAN.md` | Tender Assessment implementation plan (implemented — all 6 phases complete) — derived strictly from the redesign doc above, no backend changes required |

## Audit reports

Point-in-time assessments. Read for context on *why* something changed;
don't treat findings as still-open without checking whether the linked
remediation happened.

| Doc | Assessment |
|---|---|
| `ARCHITECTURE_CONFORMANCE_REVIEW.md` | Architecture conformance review that surfaced the Compliance Verification UI gap (closed, `d270829`) |
| `RC1_ENGINEERING_AUDIT.md` | RC-1 external beta readiness audit |
| `RC2_REMEDIATION_REPORT.md` | Implementation report for the RC-2 remediation punch list |
| `PHASE1_5_CODE_REVIEW.md` | Phase 1.5 production-readiness findings (16 items) — this doc and `DEPLOYMENT.md` are two of its own outputs |

## Setup docs (not in `docs/`)

`../README.md` (project overview, provider status, safe-export
instructions), `../backend/README.md`, `../frontend/README.md` — local
dev setup for each side. `DEPLOYMENT.md` above references these rather
than duplicating them.
