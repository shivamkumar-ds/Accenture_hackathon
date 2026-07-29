# Tender Journey — Deferred Enhancements Log

Append-only. Per `TENDER_JOURNEY_IMPLEMENTATION_PLAN.md` §0's scope
discipline rule: anything that surfaces during implementation but isn't
in the approved plan gets logged here, not built. Each entry: which phase
surfaced it, what it is, why it wasn't just done anyway.

## Phase 1

- **`frontend/src/lib/pdfReport.ts:98`** — the generated PDF report has its
  own `"AI Decision"` label (`["AI Decision", recommendationLabel(...)]`),
  in the same spirit as the two strings Phase 1 changed. Not in the
  approved Phase 1 file list (`Evaluation.tsx`, `Reports.tsx`,
  `TenderDetail.tsx`) and PDF output wasn't reviewed against the
  vocabulary rule before this plan was approved, so left untouched rather
  than assumed in scope. Trivial fix whenever explicitly approved — same
  one-word label swap as the two already made.
- **`frontend/src/pages/Landing.tsx:70`** and
  **`frontend/src/components/landing/landingData.ts:510`** — both say
  "Explainable AI Decisions" as marketing copy (plural, tagline usage, not
  the authenticated-app "AI Decision" label context the design doc's
  vocabulary rule addresses). Confirmed out of scope, not logged as a
  deferred enhancement — the Tender Journey design doc's philosophy
  governs the authenticated product experience, not the public marketing
  page, and this phrase reads differently in a tagline than as a UI label
  implying the AI made a choice. Noting the distinction here so it isn't
  re-flagged as an oversight later.

## Phase 3

- **Vitest smoke test for `frontend/src/lib/forwardLookingGap.ts`** — the
  implementation plan's Phase 3 verification section names this as "the
  first frontend test in the repo... worth flagging as a small, separate,
  explicitly-scoped addition if you want it, not assumed here." No test
  runner is currently configured for the frontend package, so adding one
  is itself a small scope decision, not just a test file. Not added;
  `forwardLookingGap` was verified manually against a real evaluation with
  multiple not-met mandatory requirements instead, per the plan's
  verification step.
- **LLM-prompt version of the forward-looking gap reasons**
  (`docs/TENDER_JOURNEY_DESIGN.md` §6's "Fix now" item) — the template
  prefix implemented in Phase 3 reuses the existing retrospective `reason`
  text verbatim after a forward-looking lead-in, so it reads as "To meet
  this requirement: <retrospective explanation>" rather than a fully
  rewritten forward-looking sentence. This is the explicitly-scoped
  outcome of Phase 3 (backend/prompt change ruled out of this phase by the
  plan itself), not a defect — noting it here in case the template reads
  poorly enough in practice to justify revisiting the prompt-based version
  later.

## Phase 4

- **Two sections built, not the three the design doc names.** §5 of
  `TENDER_JOURNEY_DESIGN.md` and the implementation plan's default-section
  table both name three landing targets (Requirements / AI Recommendation /
  Business Decision). Business Decision was not built as a separate third
  section: Phase 2 already integrated the Business Decision panel directly
  into the AI Recommendation scroll (positioned right after the blockers),
  so a literal third tab would either duplicate that content or need to
  strip it back out of the AI Recommendation section — neither is a small
  change, and neither was asked for by this phase. Implemented instead as
  two sections (Requirements, AI Recommendation), with `completed` missions
  defaulting to AI Recommendation the same as `awaiting_approval` --
  Phase 2's reorder already puts the recorded/recordable decision near the
  top of that section, so the practical effect (land somewhere that shows
  the decision quickly) is preserved without a separate tab. Flagging this
  as a documented interpretation, not a silent scope cut — worth revisiting
  explicitly if Decision History (Phase 6) ends up wanting its own tab
  alongside a literal Business Decision tab rather than folded into AI
  Recommendation.
- **Requirement type filter chip labels use raw enum text**
  (`t.replace(/_/g, " ")`, e.g. "evaluation criteria") rather than a
  human-friendly label map, identical to how `TenderDetail.tsx` already did
  this before deletion. Carried over unchanged rather than improved, since
  Phase 4's scope is the merge, not new copy polish.

## Tender Assessment Redesign Review

- **Rename `Reports` page** — raised while reviewing
  `docs/TENDER_ASSESSMENT_REDESIGN.md`. "Reports" no longer describes what
  the page does post-Phase-5 (a browse/index over evaluated tenders, not a
  reporting module). "Tender Library" was preferred over "Completed
  Assessments" specifically because the page's own filter logic
  (`reportable = missions.filter(m => m.recommendation_id)`,
  `Reports.tsx`) deliberately includes `awaiting_approval` missions, not
  just `completed` ones — "Completed Assessments" would reintroduce the
  exact wrong implication an earlier fix removed. Not implemented here:
  out of scope for the Tender Assessment redesign document, which covers
  the mission page only, not `Reports.tsx`. Revisit if/when Reports itself
  gets its own design pass. Added on final review: "Tender Workspace" and
  "Tender Library" would read as a coherent navigation pair in a way
  "Tender Workspace" and "Reports" currently don't — "Reports" sounds like
  a PDF export feature, "Tender Library" sounds like institutional memory,
  which is closer to what the page actually became after Phase 5. Worth
  weighing alongside the rename itself when Reports gets its own pass.
