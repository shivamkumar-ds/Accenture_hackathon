# Tender Journey — Implementation Plan (No Code)

Status: **Proposed — awaiting review.** Derived strictly from
`docs/TENDER_JOURNEY_DESIGN.md`, which is frozen. Nothing in this plan
introduces a product idea not already recorded there — if implementation
surfaces something new, it gets logged in §0's Deferred Enhancements Log,
not folded into scope silently.

## 0. Scope Discipline (explicit rule for this pass)

**No feature additions during implementation.** If a new idea emerges
while coding — a nicer wording, a related improvement, a "while we're
here" fix unrelated to the phase in progress — it is not built. It gets
logged in a new `docs/TENDER_JOURNEY_DEFERRED_ENHANCEMENTS.md` (created
alongside Phase 1, append-only) with a one-line description and which
phase surfaced it, and implementation continues on the plan as written.
This applies to every phase below equally — including phases that feel
"almost done" with just one more thing worth adding.

The seven phases below are ordered so each is independently shippable and
independently verifiable — matching "implementation in small, verifiable
phases." A phase is not started until the previous one is verified
(regression check: backend pytest if touched, `tsc -b`, `eslint .`, `vite
build`, manual walkthrough) and, per the project's established discipline,
summarized before moving on.

**Two decision points need your explicit sign-off before their phases
start** — flagged inline at Phase 4 and Phase 6, both because
`TENDER_JOURNEY_DESIGN.md` itself left them open rather than resolved.
Everything else below follows directly from what's already frozen.

---

## Phase 1 — Vocabulary: "AI Decision" → "AI Recommendation" / "AI Analysis"

**Design doc reference:** §1.

**Why first:** zero logic risk, mechanical, and it's the cheapest possible
proof that the new philosophy is actually landing in the product, not just
in a doc.

**Files:**
- `frontend/src/pages/Evaluation.tsx` — the `<span>AI Decision</span>` label
  on the hero card becomes "AI Recommendation"; page heading "Decision
  Engine Result" becomes "AI Recommendation" (the page itself keeps its
  route/name — only the visible heading text changes; renaming the file/
  route is Phase 4's concern, not this one).
- `frontend/src/pages/Reports.tsx` — "AI DECISION" label becomes "AI
  Recommendation."
- `frontend/src/pages/TenderDetail.tsx` — no "AI Decision" string present
  today (confirmed by reading the file); no change needed here, listed for
  completeness.

**Not touched:** `RecommendationType`, `BusinessDecision`, or any backend
value — this phase is display text only. No API contract change.

**Verification:** `tsc -b`, `eslint .`, `vite build`, manual visual check
of both pages.

---

## Phase 2 — Reorder the mission page around the decision, not the objects

**Design doc reference:** §3.

**Why second:** this is the core hierarchy change, and doing it before the
merge (Phase 4) means it's verified against the page as it exists today,
not entangled with a routing change in the same commit.

**Files:** `frontend/src/pages/Evaluation.tsx` only.

**Changes:**
- Reorder existing sections to: hero (AI Recommendation + confidence) →
  hard-blockers framing ("Can we bid?" — mandatory-and-not-met items,
  visually dominant) → risk/strategic framing ("Should we bid?" — existing
  Risk Summary card, relabeled) → "What's Blocking This Bid" (unchanged,
  existing) → Business Decision panel, moved up to immediately follow the
  blocking section → Compliance Matrix, moved down to after Business
  Decision, framed as "Supporting Evidence."
- Add a condensed recap (recommendation type, blocker count, overall
  confidence — three lines, no new data) directly above the Proceed/
  Rejected/Needs Revision buttons inside `BusinessDecisionPanel`, sourced
  from data already in `EvaluationResponse` — no new fetch.
- Confirmation copy on Save Decision: add a line stating the decision is
  final and cannot be changed within BidOps once saved (grounded in the
  verified fact that no reopen mechanism exists server-side).

**Not touched:** `MatrixRow`, verification logic, `recordDecision` call,
any API function.

**Verification:** `tsc -b`, `eslint .`, `vite build`, manual walkthrough
of an awaiting-approval mission confirming the Business Decision panel is
reachable without scrolling past the full matrix, and that the matrix
still renders correctly below it.

---

## Phase 3 — "What would change this recommendation?"

**Design doc reference:** §6 ("cheap, buildable now" half only — the LLM-
prompt option is explicitly out of scope for this phase, see below).

**Files:**
- `frontend/src/lib/` — new pure function, e.g. `forwardLookingGap(entry:
  GapAnalysisEntry): string`, template-based rewrite of the existing
  `reason` text (no new data, no LLM call). Cheapest, safest version:
  prefix framing ("To meet this requirement: ") over the existing reason
  text for `not_met` entries only, rather than attempting full sentence
  restructuring — a good candidate for the pure-function unit test this
  project's testing philosophy already calls out (`lib/` helpers are
  "cheapest to test").
- `frontend/src/pages/Evaluation.tsx` — new section between "What's
  Blocking" and the Business Decision recap, rendering the forward-looking
  text for each mandatory not-met gap.

**Explicitly not in this phase:** any change to the Decision Engine's
prompt. `TENDER_JOURNEY_DESIGN.md` §6 names an LLM-prompt version as a
legitimate future "Fix now" item, but it's a backend/AI behavior change,
not a frontend change, and bundling it here would violate this plan's own
scope-discipline rule. If the template-based version reads poorly once
implemented, that goes in the Deferred Enhancements Log, not into this
phase.

**Verification:** `tsc -b`, `eslint .`, `vite build`, manual check against
a real evaluation with multiple not-met mandatory requirements; if
`lib/forwardLookingGap.ts` lands, a small Vitest smoke test would be the
first frontend test in the repo — worth flagging as a small, separate,
explicitly-scoped addition if you want it, not assumed here.

---

## Phase 4 — Merge Requirements into the mission page

**Design doc reference:** §5 (navigation note).

**⚠ Needs your sign-off before starting** — this is the largest structural
change in the plan (a route removal) and, while it follows directly from
the frozen design, I want explicit confirmation before touching routing.

**Grounding fact, checked directly (sharper than what's in the design
doc):** `/tenders/:tenderId` (`TenderDetail.tsx`) is not just hard to find
— it is **currently unreachable from anywhere in the app.** I grepped
every frontend file for a link to that route: none exists.
`TenderUpload.tsx` navigates to `/missions` after upload, not to the new
tender's detail page. `Missions.tsx` ("Open" and the row link) navigates
to `/missions/:id` (`Evaluation.tsx`), never to `/tenders/:id`. The only
place `tenderId` is used at all is `api/endpoints.ts`'s `getTender()`
function — the API call, not a page link. So this phase isn't just
consolidating two pages into one; it's giving a completely orphaned page's
functionality (viewing extracted requirements) a UI entry point for the
first time since it was built.

**Files:**
- `frontend/src/pages/Evaluation.tsx` — new "Requirements" section,
  content adapted from `TenderDetail.tsx` (the extracted-requirements
  list, filter chips, "Run Tender Analyzer" / "Re-run Analyzer" actions).
  Fetches via `getTender(mission.tender_id)` — `mission.tender_id` is
  already present on `MissionRead` (confirmed in `api/types.ts`), so no
  new endpoint is needed.
- `frontend/src/App.tsx` — remove the `/tenders/:tenderId` route.
- `frontend/src/pages/TenderDetail.tsx` — deleted. Its logic is absorbed
  into `Evaluation.tsx`, not duplicated.
- `frontend/src/pages/TenderUpload.tsx` — no change needed to its own
  logic (it already navigates to `/missions`), but worth confirming during
  this phase that the new mission's default landing section makes sense
  for a freshly-uploaded, not-yet-analyzed tender (i.e., it should land on
  Requirements, not AI Recommendation, since there's nothing to recommend
  yet).

**Section/tab default logic:** the merged page shows Requirements, AI
Recommendation, or Business Decision as the default view depending on
`mission.status` — `created`/`running` → Requirements; `awaiting_approval`
→ AI Recommendation; `completed` → Business Decision (read-only, decision
already recorded). This is the mechanical form of "every screen should
naturally guide users toward the next stage" from the design doc's
journey diagram.

**Verification:** `tsc -b`, `eslint .`, `vite build`; manual walkthrough
of the full lifecycle — upload a tender, confirm it lands correctly at
each status; confirm no other file references `/tenders/:tenderId` or
imports `TenderDetail` after deletion (`grep -r TenderDetail frontend/src`
should return nothing).

---

## Phase 5 — Fold Reports into a "Download PDF Report" action

**Design doc reference:** §5.

**Files:**
- `frontend/src/pages/Evaluation.tsx` — add "Download PDF Report" button
  (calls the existing `generateEvaluationPdf` from `lib/pdfReport.ts`,
  currently only imported by `Reports.tsx`) to the AI Recommendation
  section.
- `frontend/src/pages/Reports.tsx` — remove the duplicated summary render
  (hero, confidence bars, status counts). Keep the left-column tender
  picker; selecting a tender navigates to `/missions/:id` instead of
  rendering a parallel preview. Reports becomes a browse/index surface
  over evaluated tenders, not a second rendering of evaluation data.

**Not touched:** `lib/pdfReport.ts` itself — same function, same output,
called from one place instead of two.

**Verification:** `tsc -b`, `eslint .`, `vite build`; manual check that a
PDF downloaded from the mission page is byte-identical in content to what
Reports previously produced (same function, same inputs — should be
mechanically guaranteed, verify once as a sanity check).

---

## Phase 6 — Decision History

**Design doc reference:** §4, §5.

**⚠ Needs your sign-off before starting** — this phase requires one small
additive backend change, not a pure frontend change, and per this
project's established discipline, backend changes get explicit approval
before implementation, same as the Compliance Verification UI's
`verified_by_name` addition did.

**Backend change (additive, no migration, no schema table):**
- `backend/app/schemas/approval.py` — `DecisionEventRead` gains
  `user_name: str | None = None`, resolved the same way
  `resolve_verifier_names()` / `resolve_evidence_sources()` already
  resolve names elsewhere: one small batch query against `User`, attached
  via `model_copy(update=...)` in the `get_approval_history` router
  handler. No new table, no new endpoint — `GET /approval/{mission_id}`
  already exists and already returns `decision_events`; this only adds
  one field to what it returns.

**Frontend files:**
- `frontend/src/api/types.ts` — add `user_name: string | null` to
  `DecisionEventRead`.
- `frontend/src/pages/Evaluation.tsx` — new "Decision History" section,
  fetches `getApprovalHistory(missionId)` (already defined in
  `endpoints.ts`, currently called from nowhere — this phase is what
  finally uses it), renders `decision_events` as a simple timeline (who,
  when, what, why).

**Verification:** backend — import check, full pytest suite (this touches
`approval.py`'s router and schema, both covered by existing tests);
frontend — `tsc -b`, `eslint .`, `vite build`; manual check of a mission
with multiple decision events (e.g., a Needs Revision followed by a
Proceed) showing correctly ordered, correctly attributed entries.

---

## Phase 7 — Role-based default section

**Design doc reference:** §5's persona table.

**Files:** `frontend/src/pages/Evaluation.tsx` — default section on load
determined by `current_user.role` in addition to `mission.status` from
Phase 4 (status determines *what's possible to show*; role determines
*where a given role lands* among what's available). Executive → AI
Recommendation/Business Decision; Bid Manager → no fixed default, whole
page; Reviewer → Supporting Evidence; Auditor → Decision History.

**Open item carried over from the design doc, not resolved by this plan:**
where Administrator fits this table. Defaulting Administrator the same as
Bid Manager (no fixed default, full page) unless you'd rather specify
otherwise — flagging this explicitly rather than picking silently.

**Verification:** `tsc -b`, `eslint .`, `vite build`; manual check logging
in as each role (or temporarily overriding `current_user.role` in dev) to
confirm correct default section per role.

---

## Explicitly Not In This Plan

Everything `TENDER_JOURNEY_DESIGN.md` §7 lists as deferred stays deferred:
cross-tender capability-gap aggregation, multi-stakeholder collaboration/
approval chains, and outcome tracking (`actual_outcome`/`outcome_notes`
write path). Also not in this plan, per §8 of the design doc:
authentication, OAuth, account linking, organization onboarding,
invitations, RBAC, and deployment — reserved for their own design pass
after this implementation is complete and QA'd, per the agreed sequencing.

The `last_decision`-on-`MissionRead` idea from the design doc's §9 is
**not included as a phase here** — it would only be needed to distinguish
Proceed from Reject in list views (Tender Workspace, Dashboard), and no
phase in this plan currently renders that distinction in a list view. If
you want that added to this pass, it's a small additive phase (batch-
resolving each mission's latest terminal decision, mirroring
`_attach_tender_info`'s existing batching pattern in `missions.py` —
no schema change needed, same reasoning as Phase 6) — flagging it as
available, not assumed.

---

## Components Affected

| Component | Modified | New | Deleted |
|---|---|---|---|
| `Evaluation.tsx` | Yes (every phase) | — | — |
| `Reports.tsx` | Yes (Phase 5) | — | — |
| `TenderDetail.tsx` | — | — | Yes (Phase 4) |
| `TenderUpload.tsx` | Reviewed, likely unchanged (Phase 4) | — | — |
| `App.tsx` | Yes (Phase 4 — route removal) | — | — |
| `lib/forwardLookingGap.ts` | — | Yes (Phase 3) | — |
| `api/types.ts` | Yes (Phase 6) | — | — |
| `backend/app/schemas/approval.py` | Yes (Phase 6) | — | — |
| `backend/app/api/v1/approval.py` | Yes (Phase 6 — name resolution) | — | — |

---

## API Calls

| Endpoint | Status |
|---|---|
| `GET /api/v1/evaluation/{missionId}` | Reused, no change |
| `GET /api/v1/tenders/{tenderId}` | Reused (Phase 4) — already exists, was only called from the now-orphaned `TenderDetail.tsx` |
| `GET /api/v1/approval/{mission_id}` | Reused (Phase 6) — already exists, called from nowhere until this phase |
| `POST /api/v1/approval` | Reused, no change |
| `POST /api/v1/compliance/{id}/verify` | Reused, no change |
| `POST /api/v1/analysis/run` | Reused (Phase 4, moved from `TenderDetail.tsx`) |

**No new endpoints except Phase 6's one additive schema field.**

---

## Out of Scope

Per §0's discipline rule, this list is binding, not aspirational:

- Any backend change beyond Phase 6's single additive field.
- Any change to `record_decision`, `verify_compliance_row`, or any other
  service-layer logic.
- Bulk actions of any kind (bulk verify, bulk decision).
- Notifications, reminders, or task creation.
- Automated frontend tests beyond the optional Phase 3 smoke test —
  consistent with this project's existing "protect real guarantees, not
  blanket coverage" testing philosophy.
- Anything listed in `TENDER_JOURNEY_DESIGN.md` §7 or §8.

---

## Risk Assessment

| Area | Risk | Why |
|---|---|---|
| Phase 1 (vocabulary) | Minimal | Text-only |
| Phase 2 (reorder) | Low | Same data, same component tree, JSX order only |
| Phase 3 (forward-looking) | Low | New, additive, pure-function-backed |
| Phase 4 (merge/route removal) | Medium | Deletes a file and a route — mitigated by the confirmed-orphaned status (nothing currently depends on it) and the explicit grep-verification step |
| Phase 5 (Reports fold) | Low-medium | Reuses existing PDF function unchanged; Reports' own picker UX is preserved, only the preview pane changes |
| Phase 6 (Decision History) | Low | One additive backend field, same pattern as `verified_by_name`, already proven safe |
| Phase 7 (role defaults) | Minimal | Pure frontend, `current_user.role` already available |
| Backend test suite | None outside Phase 6 | Phases 1-5, 7 touch no backend file |

---

## Rollback

Each phase is an independent commit; reverting any single phase's commit
is sufficient to undo it without affecting earlier phases, since no phase
depends on a later one. Phase 4's route removal is the only phase where
rollback needs a note: reverting restores `TenderDetail.tsx` and the
route, but since nothing currently links to it, restoring it doesn't
re-expose anything that was reachable before this plan started.

---

## Impact Summary

| Area | Change |
|---|---|
| Backend API | 1 additive schema field (Phase 6, `DecisionEventRead.user_name`) |
| Database | None |
| Migrations | None |
| Frontend pages | `Evaluation.tsx` substantially restructured; `Reports.tsx` reduced; `TenderDetail.tsx` deleted |
| Frontend routes | 1 removed (`/tenders/:tenderId`) |
| New frontend files | 1 (`lib/forwardLookingGap.ts`) |
| Existing APIs newly wired to the frontend | 2 (`GET /tenders/{id}`, `GET /approval/{mission_id}` — both already existed, neither was reachable/used before this plan) |
| New APIs | 0 |
| Breaking changes | None (additive schema field only; no request-contract or response-shape removal) |
