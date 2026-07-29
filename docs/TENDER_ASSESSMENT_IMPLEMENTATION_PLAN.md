# Tender Assessment — Implementation Plan (No Code)

Status: **Proposed — awaiting review. No frontend code has been changed
by this document.** Derived strictly from `docs/TENDER_ASSESSMENT_REDESIGN.md`
(frozen). Nothing below introduces a product idea not already recorded
there — anything that surfaces during implementation gets logged in
`docs/TENDER_JOURNEY_DEFERRED_ENHANCEMENTS.md` (kept as the single
running log across both the Tender Journey and Tender Assessment work,
rather than forked into a second file) instead of folded into scope
silently.

## 0. Architecture check (done before proposing phases, per request)

Checked against `docs/CORE_ARCHITECTURE.md`, `docs/ENGINEERING_DIRECTIVE.md`,
and `docs/TENDER_ASSESSMENT_REDESIGN.md` §7 itself:

- **No backend or API change required.** Every grounded item in the
  redesign doc's §5 is a presentation reorganization of fields already
  returned by `GET /api/v1/evaluation/{missionId}`
  (`RecommendationRead`, `GapAnalysisEntry`, `ComplianceMatrixEntryRead`).
  Confirmed by re-reading `frontend/src/api/types.ts`: `risk_level`,
  `requirement_type`, `mandatory`, `requirement_id` all already exist on
  the types this plan touches. No phase below needs a schema, migration,
  or endpoint change, and therefore **no phase needs backend sign-off.**
- **No violation of the Requirements / Assessment / Decision History
  three-way separation** (`TENDER_JOURNEY_DESIGN.md` §1, restated in the
  redesign doc §2). Every phase below stays inside the `recommendation`
  section of `Evaluation.tsx`; none touches the `requirements` or
  `history` sections or their data fetches.
- **No violation of the vocabulary rule** ("AI Recommendation," never "AI
  Decision"). No phase below introduces new user-facing copy that implies
  the AI is deciding rather than advising.
- **One real architectural risk, flagged before Phase 1 rather than
  discovered mid-phase:** `mergeRequirementContext`
  (`frontend/src/lib/complianceMerge.ts`) is shared between this page and
  `Reports.tsx`'s PDF export (`lib/pdfReport.ts`). The redesign doc's §5
  implementation note says the merge needs to carry the gap's `reason`
  field through, which it doesn't today. Adding a field to that shared
  return type is additive (existing consumers keep working unchanged) but
  it is a shared-file change, not a page-local one — called out as its
  own step in Phase 1 below rather than bundled invisibly into a page
  change.
- **Conclusion: nothing below breaks architecture.** No phase is gated on
  further confirmation before starting; approval to begin Phase 1 covers
  the whole plan, same as the Tender Journey plan's model, unless review
  below raises something.

## 1. Scope Discipline (same rule as the Tender Journey plan)

**No feature additions during implementation.** Anything that comes up
mid-phase and isn't already written into `TENDER_ASSESSMENT_REDESIGN.md`
gets logged in `docs/TENDER_JOURNEY_DEFERRED_ENHANCEMENTS.md`, not built.
Each phase is not started until the previous one is verified (`tsc -b`,
`eslint .`, `vite build`, manual walkthrough against a real mission at
each of the four `recommendation_type` values where practical) and
summarized before moving on. Stop after each phase for review — do not
proceed to the next phase without explicit approval, same discipline as
the seven Tender Journey phases.

| Phase | What | Backend touch? | Approval needed before starting? |
|---|---|---|---|
| 1 | Foundation: severity ranking + Administrative/Structural mapping + `reason` threaded through the merge | No | No — pure additive lib code, no UI change |
| 2 | The Assessment — merge hero + "Can we bid?" + "Should we bid?" into one block, add the consequence line | No | No |
| 3 | Why — grouped, severity-ranked blockers (replaces "What's Blocking This Bid") | No | No |
| 4 | What Would It Take — Administrative/Structural framing, renamed tier (replaces "What Would Change This Recommendation") | No | No |
| 5 | What Should We Do — Business Decision panel becomes the page's visual destination | No | No |
| 6 | Evidence — single collapsed disclosure (Compliance Summary + Compliance Matrix + confidence breakdown) | No | No |

All six phases are additive/restructuring changes to
`frontend/src/pages/Evaluation.tsx` (plus two new lib files in Phase 1).
No phase deletes a route, a component file, or an API call — closer in
size to Tender Journey's Phase 2/3 than to its Phase 4 (route deletion),
so none of them carry that phase's extra sign-off requirement.

---

## Phase 1 — Foundation: ranking, classification, and the `reason` field

**Design doc reference:** §4 ("Top Priorities" ranking), §5 (grounding —
explicitly flags the `mergeRequirementContext` gap), §3 (Administrative/
Structural).

**Why first:** Phases 2 and 3 both consume this data (Phase 2's
consequence line needs "the #1-ranked blocker"; Phase 3's grouping needs
both the ranking and the classification). Building it once, correctly,
before either consumer exists avoids two independent, possibly
inconsistent implementations of the same join.

**Files:**
- `frontend/src/lib/complianceMerge.ts` — add `reason: gap?.reason ?? null`
  to the object `mergeRequirementContext` returns. Additive field on an
  existing return type; `Reports.tsx`/`pdfReport.ts`, the only other
  consumer, ignores unknown fields today and needs no change.
- `frontend/src/lib/blockerPriority.ts` (new) — a `rankBlockers(gaps:
  GapAnalysisEntry[], matrix: ComplianceMatrixEntryRead[])` helper that
  joins each mandatory-and-not-met gap to its matrix row by
  `requirement_id` (same exact-ID join `mergeRequirementContext` already
  uses, not fuzzy matching) and sorts by `risk_level`
  (critical > high > medium > low), with unresolved `risk_level` sorted
  last rather than assigned a fabricated value, per the redesign doc's
  explicit rule.
- `frontend/src/lib/requirementCategory.ts` (new) — a static, documented,
  deterministic `Record<RequirementType, "administrative" | "structural">`
  map (eligibility → structural, technical → administrative or structural
  per redesign doc's own examples, certification/experience →
  administrative, evaluation_criteria/deadline/submission → judgment call
  documented inline at implementation time), plus a `requirementCategory
  (type: RequirementType)` accessor. Built as its own file so it's a
  single, reviewable place for the mapping — same pattern as
  `RECOMMENDATION_LABELS` in `recommendationLabels.ts` — satisfying the
  redesign doc §8's binding condition ("lives in one file, documented
  inline, deterministic").

**Not touched:** `Evaluation.tsx` itself — this phase has no visible UI
change. Verification is code-level, not a walkthrough.

**Verification:** `tsc -b`, `eslint .`, `vite build`; a manual sanity
check (temporary console log against a real evaluated mission, removed
before commit) confirming `rankBlockers` orders a known critical-risk
blocker before a known medium-risk one, and that `requirementCategory`
returns a value for all seven `RequirementType` values with no `undefined`
fallthrough.

---

## Phase 2 — The Assessment

**Design doc reference:** §4 ("The Assessment"), §3 (Review/Conditional
calibration), §5 (consequence-sentence grounding).

**Files:** `frontend/src/pages/Evaluation.tsx` only.

**Changes:**
- Merge the existing hero block, "Can we bid?" block, and "Should we
  bid?" card into one block: opens with a spoken claim
  (`recommendationLabel(recommendation.recommendation_type)` rendered as
  a sentence, e.g. "We recommend not bidding," not a bare label), holds
  the eligibility gate (`blockingIssues.length`) and the risk judgment
  (`recommendation.risk_level`) as two distinct sentences inside the one
  block — preserving the `blockingIssues` vs. `blockingRows` distinction
  as content, not as two separate full-width sections.
- Copy is `recommendation_type`-aware per §3: `go`/`no_go` get a plain
  declarative opening sentence; `review`/`conditional_go` get calibrated-
  uncertainty phrasing ("This one is close — here's the split, your
  judgment decides it"). `overall_confidence` continues to render both as
  the existing `ConfidenceRing` and inside the sentence wording.
- Add the fourth line: a consequence sentence synthesized from
  `rankBlockers(...)[0]` (Phase 1), templated per `recommendation_type` —
  hard disqualification phrasing only when the #1 blocker's
  `requirement_type` is genuinely `eligibility` and the recommendation is
  `no_go`; softer risk-framed phrasing otherwise. No claim about the
  tender issuer's internal process (§5's explicit rejection).
- The four `ConfidenceBar` breakdown (document/entity/matching/
  recommendation confidence) moves out of this block — it belongs to
  Evidence (Phase 6), not the Assessment; leaving a `// TODO Phase 6`
  comment rather than deleting-then-re-adding across two phases would be
  reasonable, or simply leave it in place until Phase 6 removes it here —
  implementer's call, noted so it isn't mistaken for scope creep in
  either phase.

**Not touched:** `BusinessDecisionPanel`, the Compliance Matrix, decision
recording logic.

**Verification:** `tsc -b`, `eslint .`, `vite build`; manual walkthrough
against at least one mission at each of `go`, `no_go`, and one of
`review`/`conditional_go` if real data exists for it, confirming the
opening sentence and consequence line read correctly and the eligibility/
risk facts are both still present.

---

## Phase 3 — Why

**Design doc reference:** §4 ("Why"), §5 (severity ranking grounding).

**Files:** `frontend/src/pages/Evaluation.tsx` only.

**Changes:**
- Replace "What's Blocking This Bid" with a version grouped by
  `requirement_type` (using `blockingIssues`, i.e. mandatory-and-not-met
  gaps), each group carrying a plain-language consequence line ("Technical:
  1 requirement unmet — this would likely be screened out before
  evaluation"), not just a bare count.
- Within Why, order blockers using `rankBlockers` from Phase 1 as a "Top
  Priorities" list — severity-ranked, not just grouped. Each blocker
  still shows its `reason` (now available via Phase 1's merge change)
  alongside its `requirement_type` group.
- This is the point where the current two duplicated sections ("What's
  Blocking This Bid" and "What Would Change This Recommendation") stop
  being duplicates of each other — Why answers "why," the next phase's
  tier answers "what would it take." Do not merge the "what would change
  this" content into this phase; that's explicitly Phase 4's tier.

**Not touched:** the "What Would Change This Recommendation" card itself
— left as-is until Phase 4, so this phase's diff is reviewable on its
own.

**Verification:** `tsc -b`, `eslint .`, `vite build`; manual check that
grouping + ranking produce a stable, correctly-ordered list against a
mission with blockers spanning at least two `requirement_type` values and
at least two `risk_level` values.

---

## Phase 4 — What Would It Take

**Design doc reference:** §4 ("What Would It Take"), §5 (Administrative/
Structural grounding), §8 (rename resolution).

**Files:** `frontend/src/pages/Evaluation.tsx` only.

**Changes:**
- Rename "What Would Change This Recommendation?" to "What Would It
  Take" (confirmed name per redesign doc §8; "Path to Eligibility"
  remains valid as in-tier language for the eligibility-failure case
  specifically, not as the tier's title).
- For each blocker, add its Administrative/Structural classification
  (from Phase 1's `requirementCategory`) alongside the existing
  `forwardLookingGap(g)` text — rendered as a label, not a score or
  percentage, per §5's explicit constraint.
- Keep this tier visually and structurally distinct from Why (Phase 3):
  diagnosis (Why) vs. prognosis (What Would It Take) stay two sections,
  per the redesign doc's explicit "stays a distinct tier" instruction —
  do not collapse them into one card in this phase even though they sit
  next to each other.

**Not touched:** `forwardLookingGap.ts` itself — no change to its
template logic, only to what's rendered alongside its output.

**Verification:** `tsc -b`, `eslint .`, `vite build`; manual check that
every blocker shows exactly one Administrative/Structural label, sourced
from the Phase 1 map, with no `undefined` rendering for any
`requirement_type`.

---

## Phase 5 — What Should We Do

**Design doc reference:** §4 ("What Should We Do").

**Files:** `frontend/src/pages/Evaluation.tsx` only.

**Changes:** Content of `BusinessDecisionPanel` is explicitly unchanged
per the redesign doc — this phase is presentation weight only. Concretely:
visually distinguish the panel as the page's destination rather than
another card of equal weight to the four tiers above it (e.g. stronger
border/background treatment consistent with `DESIGN_SYSTEM.md` — exact
styling is an implementation-time decision within the existing design
system, not a new design-system rule, since §7 confirms the design system
itself is out of scope for this redesign).

**Not touched:** `recordDecision` call, `DECISION_OPTIONS`, the condensed
recap fields, the finality copy — all unchanged in content per the
redesign doc.

**Verification:** `tsc -b`, `eslint .`, `vite build`; manual visual check
that the panel now reads as more prominent than the tiers above it
without changing any of its functional behavior.

---

## Phase 6 — Evidence

**Design doc reference:** §4 ("Evidence"), §8 (single-disclosure
resolution).

**Files:** `frontend/src/pages/Evaluation.tsx` only.

**Changes:**
- Collapse the Compliance Summary tiles (`StatusStat` row), the
  confidence breakdown (four `ConfidenceBar`s, moved out of Phase 2's
  Assessment block if left there), and the existing Compliance Matrix
  card into **one** closed-by-default disclosure titled "Evidence" —
  not three independently-collapsible pieces. Existing per-row
  verification metadata (`verified_by_name`, `verified_at`) stays exactly
  where it is inside the Compliance Matrix rows — not duplicated at the
  disclosure level.
- The disclosure is closed by default on load; opening it does not
  trigger any new fetch — all of this data is already present in `data`
  from the existing `refresh()` call.
- No change to `MatrixRow`, verification logic, `handleRowVerified`, or
  the search/filter/group behavior of the matrix itself — only its
  container changes from "always visible" to "inside one closed
  disclosure."
- Explicitly confirm in this phase's own verification: Evidence remains
  structurally separate from the Decision History section — no merging,
  per the redesign doc's explicit non-merge instruction in §4.

**Not touched:** the Decision History section, `getApprovalHistory`,
`decisionEvents` state — entirely outside this phase.

**Verification:** `tsc -b`, `eslint .`, `vite build`; manual walkthrough
confirming the Evidence disclosure is closed by default, opening it shows
all three pieces (summary tiles, confidence breakdown, matrix) without a
network request, and that verifying a compliance row from inside the
open disclosure still works exactly as before (calls `verifyComplianceRow`,
updates via `handleRowVerified`, no regression from Phase 6 through
Phase 2 of the Tender Journey plan).

---

## After Phase 6

Once all six phases are implemented and verified, update
`docs/TENDER_ASSESSMENT_REDESIGN.md`'s status line and
`docs/INDEX.md`'s entry for it from "frozen, implementation not started"
to "implemented," with a phase→commit table matching the format at the
top of `TENDER_JOURNEY_IMPLEMENTATION_PLAN.md`. Not done as part of this
planning document — deferred to the point where Phase 6 actually lands,
same sequencing as the Tender Journey plan's own status update.
