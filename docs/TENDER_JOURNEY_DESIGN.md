# Tender Journey & Business Decision Experience — Design (Frozen)

Status: **Frozen — design complete, implementation not started.** Reached
through a discussion-first design pass (Discussion → Implementation Plan →
Review → Approval → Implementation, `ENGINEERING_DIRECTIVE.md` §"Post-
Architecture Phase"), the same discipline used for `BID_DECISION_DESIGN.md`
and the Compliance Verification UI. This document exists so implementation
doesn't have to reconstruct the reasoning from chat history, and so the
product philosophy below survives past this conversation.

The trigger for this discussion: the frontend authenticated experience had
never been designed from first principles — it grew page-by-page alongside
backend milestones and started to feel, in the founder's words, "like a
skin over Swagger." This document is the answer to that problem for the
tender lifecycle specifically. Authentication, organization onboarding,
RBAC, and production deployment are explicitly **not** covered here — see
§8.

## 1. Product Philosophy (the frozen core)

- **AI Recommendation, never AI Decision.** "Decision" is reserved
  exclusively for the human action. The AI's output is called "AI
  Recommendation" (the verdict card specifically) or "AI Analysis" (the
  read-only section as a whole — recommendation + risk summary + matrix).
  This isn't just wording — it's the existing `Recommendation` /
  `RecommendationType` domain objects finally being named what they already
  are, and it reinforces the architectural principle that has survived
  every milestone: AI advises, a human decides.
- **Executive-first information hierarchy.** A procurement manager's actual
  decision-making sequence is: can we bid (hard eligibility gates) → should
  we bid (strategic/risk judgment) → what's blocking us → what would change
  the answer → decide. It is never "read forty compliance rows in order."
  The page must be structured around that sequence, not around backend
  object order.
- **Compliance Matrix as supporting evidence, not the primary interface.**
  It remains complete and inspectable, but demoted below the decision
  point — the analyst/compliance officer's workspace, not the executive's
  front door.
- **Forward-looking guidance, not just failure reporting.** Where the
  product currently says "9 mandatory requirements not met," it should
  also say what would change that — "this would meet with two more
  completed government digital transformation projects." Per-tender, this
  is real and buildable (§6). Cross-tender aggregation is not (§7).
- **Business Decision owned by the human, distinct from Mission status.**
  Already true in the backend (`BusinessDecision` is a deliberately
  separate vocabulary from `RecommendationType` — see
  `BID_DECISION_DESIGN.md` §4) and stays true in the frontend: the decision
  UI never implies the AI chose anything.
- **Decision History as a first-class, visible concept.** Not yet true in
  the frontend today — see §5.
- **Deferred, not rejected: organizational learning.** The idea that
  BidOps should eventually say "ISO 14001 has blocked 18 opportunities" is
  real and valuable. It is explicitly deferred until real tender volume
  proves the underlying data clusters cleanly enough to aggregate honestly
  — see §7.

## 2. The Corrected Tender Journey

```
Tender Uploaded
      ↓
Requirements Extracted
      ↓
AI Recommendation (Decision Engine — "Capability Matching" is not a
                    separately visible stage; it happens inside this step)
      ↓
Executive Summary  (new front door — see §3)
      ↓
   ┌─ optional detour ─┐
   │ Compliance Matrix  │  (supporting evidence, not required reading)
   │ + Verification     │
   └────────────────────┘
      ↓
Business Decision (Proceed / Rejected / Needs Revision)
      ↓
Decision Recorded (visibly distinct per outcome — see §5)
      ↓
"Why We Passed" narrative, for Rejected tenders specifically (§6)
      ↓
Historical Reference (Decision History — backend exists, no UI yet, §5)
      ↓
Organizational Learning (deferred — §7)
```

Every stage above "Decision Recorded" already exists in the backend, mostly
unverified from the frontend, per §4. Everything from "Decision Recorded"
onward is a mix of real-but-unsurfaced backend capability and genuinely
new/deferred work — the distinction matters for whatever implementation
plan follows this document, and is kept explicit throughout.

## 3. Mission Page — Information Hierarchy

One page per mission (see §5's navigation note on collapsing today's
`TenderDetail`/`Evaluation` split into this), structured top to bottom as:

```
Executive Summary
      ↓
Can we bid?              (hard eligibility gates — mandatory + not_met,
                           visually dominant over everything below it)
      ↓
Should we bid?            (risk level, confidence, strategic framing)
      ↓
What is blocking us?      (existing "What's Blocking This Bid" panel)
      ↓
What would change this recommendation?   (new — forward-looking, §6)
      ↓
Business Decision         (Proceed / Rejected / Needs Revision, with a
                            condensed recap directly above the buttons —
                            recommendation, blocker count, confidence —
                            so the decision-maker isn't relying on memory
                            of what they read several screens up)
      ↓
Supporting Evidence       (full Compliance Matrix, evidence trails,
                            verification actions — expand-only, not
                            required reading for the executive path)
```

**Always visible, first thing seen:** the AI Recommendation verdict and its
confidence.

**Second:** hard blockers, visually separated from soft/discretionary risk
— a mandatory-and-not-met item is a fact that forecloses the decision; a
review-required item is a judgment call. These must not read as
equal-weight.

**Mandatory before the decision buttons, but condensed:** the recap
described above.

**Expand-only:** the full compliance matrix and evidence trails. This is
where the Reviewer/Compliance Officer persona (§5) lives; it should not be
the thing a first-time visitor is forced to scroll through.

**Decision experience:** given Proceed/Rejected are genuinely irreversible
in the current backend (§4 — no reopen mechanism exists), the confirmation
step should say so plainly — "this decision is final and cannot be changed
within BidOps once saved" — rather than presenting Save Decision as an
ordinary form submit.

## 4. Grounded in the Actual Backend (verified during discussion, not assumed)

These are facts about the current implementation, established by reading
`approval_service.py`, `mission_service.py`, `revalidation_service.py`, and
the `Mission` model directly — not inferred from the API surface:

- **Proceed and Rejected both set `mission.status = COMPLETED`.** They are
  currently indistinguishable by status alone. Reject requires a reason
  (Pydantic-enforced); the audit trail records which one happened, but
  nothing currently surfaces that distinction to the frontend without
  reading `AuditLog`.
- **Needs Revision leaves `mission.status` completely unchanged**
  (`AWAITING_APPROVAL`). It is genuinely resumable — compliance rows can
  still be verified, another decision can be recorded at any time — but
  nothing marks that a Needs Revision event happened. A freshly-sent-back
  mission is indistinguishable, status-wise, from one nobody has looked at
  yet.
- **No reopen/override mechanism exists.** Once `COMPLETED`, `record_decision`
  hard-rejects any further call. M9 revalidation can produce a new
  Recommendation for a completed mission (`preserve_mission_state=True`)
  for informational awareness only — it never touches the original
  decision.
- **`GET /api/v1/approval/{mission_id}` (`getApprovalHistory`) already
  returns mission, recommendation, full compliance matrix, and every
  decision event** (who via `user_id`, when via `timestamp`, why via
  `result`). It is defined in `frontend/src/api/endpoints.ts` and called
  from nowhere in the frontend today.
- **`Mission.actual_outcome` / `Mission.outcome_notes` already exist** in
  the schema and the read model (`MissionRead`), explicitly for future
  "Recommendation Accuracy" tracking. No write endpoint exists anywhere.
  Always `null` today.
- **`user_id` on `DecisionEventRead` is a raw UUID**, not resolved to a
  name — the same problem already solved for compliance verification
  (`verified_by_name`) would need to be repeated for decision events
  whenever Decision History gets built.

## 5. Decision History, Persona Defaults, and Navigation

**Decision History** becomes a tab on the merged mission page (see below),
backed by the already-existing `GET /approval/{mission_id}`. Building it
requires resolving `user_id` → name (repeat the `verified_by_name`
pattern) — the only new work needed; the data itself already exists.

**Roles, not separate dashboards.** Four of the five `UserRole` values map
to distinct entry points into the *same* mission page, via which tab they
land on by default, not via separate interfaces:

| Role | Default landing | What they mostly do |
|---|---|---|
| Executive | Executive Summary / Business Decision | Read the verdict, decide |
| Bid Manager | Whole page, no fixed default | Owns the tender day to day |
| Reviewer / Compliance Officer | Supporting Evidence (verification queue) | Clears flagged rows |
| Auditor | Decision History | Read-only audit trail |

`current_user.role` is already available and already used for a UI gate
elsewhere (`canDeleteCapabilities` in `Capabilities.tsx`), so this is a
frontend-only decision — no backend change required. **Open question,
unresolved:** where Administrator fits this table — treated so far as a
superset/admin concern rather than a distinct decision-making perspective.
Worth confirming before implementation.

**Navigation implication, carried over from the earlier information-
architecture discussion this design grew out of:** today's
`/tenders/:tenderId` (`TenderDetail.tsx`) and `/missions/:missionId`
(`Evaluation.tsx`) are two separate pages for what a user experiences as
one tender's journey, reachable via two different ID schemes, with no way
back to requirement-level detail once you leave the immediate post-upload
flow. The information hierarchy in §3 assumes these collapse into one page
at `/missions/:missionId`, with Requirements / AI Recommendation /
Business Decision / Decision History as sections or tabs of that one page,
defaulting to whichever stage the mission's actual status indicates. The
Reports page's near-duplicate summary (confidence ring, confidence bars,
status counts, already drifted out of sync with Evaluation's newer
grouped-matrix layout) is expected to collapse into a "Download PDF
Report" action on this same page rather than remain a parallel read-only
mirror.

## 6. What's Cheap to Build Now vs. What Isn't

Two ideas surfaced in this discussion look similar on the surface
("explain the gap forward-looking") but have very different costs — kept
deliberately separate so implementation doesn't conflate them:

**Cheap, buildable now: per-tender forward-looking rejection reasons.**
Every `gap_analysis` entry already has a `reason` (LLM-generated prose,
phrased retrospectively — "the provided record describes only one such
project, which doesn't meet the minimum of three"). Rephrasing this
forward ("would be met with two more completed government digital
transformation projects") is largely a presentation change; for reasons
too nuanced for templating, a small additive change to the Decision
Engine's existing prompt — asking it to also state the forward-looking
condition — is a "Fix now" item under the Technical Debt Policy (cheap,
isolated), not a redesign. Also cheap: assembling Rejected-tender gap
reasons into a coherent "why we passed" narrative attached to the
decision — the raw material exists, nothing currently formats it as one.

**Not cheap, explicitly deferred: cross-tender capability-gap
aggregation.** "ISO 14001 blocked 18 opportunities" requires knowing that
eighteen differently-worded requirements across eighteen tenders mean the
same underlying thing. `RequirementType` is a coarse seven-value enum, not
a taxonomy specific enough to distinguish "ISO 14001" from "ISO 9001" from
an unrelated certification, and `reason` is free LLM prose with no
structured category. Real value, but per Principle 9
(`AI_ARCHITECTURE_PRINCIPLES.md`) and the existing
`PRODUCTION_FINDINGS.md` validation backlog, this needs evidence from real
processed tenders before deciding whether a structured taxonomy is even
the right shape — not speculative architecture now.

## 7. Explicitly Deferred (recorded, not built)

- **Cross-tender organizational learning / capability-gap aggregation** —
  see §6. Revisit once real tender volume exists.
- **Multi-stakeholder collaboration before a final decision** (Legal,
  Finance, Technical Lead weighing in before Bid Manager decides). No v1
  build planned — no evidence yet that real customers need this over an
  out-of-product conversation. Nothing in the current or proposed model
  forecloses it later: `BusinessDecision` is already a single append-only
  event per decision, and `Needs Revision` already provides a resumable,
  non-terminal loop that a future multi-round review could be built on
  without a schema change. Revisit if real usage shows a single
  accountable decision-maker isn't how customers actually work.
- **Outcome tracking (`actual_outcome`/`outcome_notes`)** — schema exists,
  unpopulated, no write path. Genuinely a third lifecycle stage past
  Business Decision (did we actually win, weeks/months later), but
  recording it requires someone to remember to return to the product long
  after the decision — closer to a reminder/notification problem than a
  page-layout one. Whether this belongs in the product at all is an open
  question for the founder, not resolved by this document.

## 8. Explicitly Not Covered By This Document

Authentication, Google OAuth, email/password coexistence and account
linking, organization onboarding (create-new vs. join-via-invite),
invitations, RBAC/IAM, company multi-tenancy refinements, secrets/
environment configuration, and production deployment are all real,
substantial design surfaces surfaced during this discussion — deliberately
**not** designed here. Per the founder's explicit direction, these get
their own dedicated design pass, at the same depth as this document,
before any implementation. Grounding facts already established for that
session: registration (`POST /auth/register`) always creates a brand-new
Company + Administrator, with no "join an existing organization" path
today; `POST /users` is the only way to add a teammate, is admin-only, and
requires the admin to set the new user's password directly — no invite
email, no invite token, no email-sending capability exists anywhere in the
backend today.

## 9. Suggested Backend Change (flagged, not committed)

One additive backend change came out of this discussion worth carrying
into whatever implementation plan follows: exposing something like
`last_decision` (or the relevant recent decision event) directly on
`MissionRead`, so pages don't each need to separately fetch and parse
`AuditLog` to show "Proceeded" vs. "Rejected" vs. "Completed." Matches the
existing `verified_by_name` precedent — additive, non-breaking, no new
table.
